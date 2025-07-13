"""
简化版搜索智能体 - 使用MCP Tavily API执行搜索查询
采用定制的CopilotKitState状态管理
"""
import asyncio
import os
import requests
import logging
import time
import uuid
from typing_extensions import Literal
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END
from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import tool
from copilotkit import CopilotKitState
from langgraph.types import interrupt 
import json
import random

from langgraph.graph import MessagesState

# 配置日志记录
logger = logging.getLogger("agent")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("agent.log"),
            logging.StreamHandler()
        ]
    )

# 工具调用追踪
tool_calls_tracker = {}
    
class AgentState(CopilotKitState):
    """
    定制的Agent状态类
    继承自CopilotKitState，获得CopilotKit的所有状态字段
    同时添加自定义字段用于扩展功能
    """
    # 自定义状态字段
    proverbs: list[str] = []        # 谚语列表（来自agent_old.py）
    search_history: list[str] = []  # 搜索历史记录
    
    # 审核相关字段
    approval_status: str = "none"   # 审核状态

@tool
def get_weather(location: str):
    """
    使用该工具获取指定位置的天气信息
    
    Args:
        location: 地点名称，如"北京"、"上海"等
        
    Returns:
        str: 天气信息描述
    """
    
    # 模拟天气数据
    weather_conditions = ["晴朗", "多云", "阴天", "小雨", "大雨", "雷阵雨", "小雪", "大雪"]
    temp = round(random.uniform(5, 35), 1)
    humidity = random.randint(30, 95)
    wind_speed = round(random.uniform(0, 10), 1)
    wind_direction = random.choice(["东", "南", "西", "北", "东北", "西北", "东南", "西南"])
    
    # 构建JSON格式的天气数据
    weather_data = {
        "location": location,
        "condition": random.choice(weather_conditions),
        "temperature": temp,
        "humidity": humidity,
        "wind": {
            "speed": wind_speed,
            "direction": wind_direction
        },
        "updated_at": "2023-06-15 14:30"
    }
    
    result = json.dumps(weather_data, ensure_ascii=False)
    logger.info(f"天气查询结果: {result[:100]}...")
    return result

# 全局工具变量，避免重复初始化
_all_tools = None

async def get_all_tools():
    """
    统一的工具准备函数，避免重复初始化MCP客户端
    
    Returns:
        list: 包含所有可用工具的列表
    """
    global _all_tools
    
    # 如果已经初始化过，直接返回
    if _all_tools is not None:
        return _all_tools
    
    # 创建MCP客户端以获取搜索工具
    try:
        client = MultiServerMCPClient(
            {
                "tavily-mcp": {
                    "command": "npx",
                    "args": ["-y", "tavily-mcp"],
                    "env": {**os.environ},
                    "transport": "stdio"
                }
            }
        )
        
        # 获取MCP工具
        mcp_tools = await client.get_tools()
        _all_tools = mcp_tools + [get_weather]
        logger.info(f"工具初始化成功，可用工具: {[tool.name for tool in _all_tools]}")
        
    except Exception as e:
        logger.warning(f"⚠️ MCP工具初始化失败: {e}")
        # 如果MCP工具失败，只使用邮件工具
        _all_tools = [get_weather]
        logger.info(f"使用备用工具: {[tool.name for tool in _all_tools]}")
    
    return _all_tools

async def chat_node(state: AgentState, config: RunnableConfig) -> Command[Literal["tool_node", "__end__"]]:
    """
    主要的聊天节点，基于ReAct设计模式
    处理以下功能:
    - 模型配置和工具绑定
    - 系统提示设置
    - 获取模型响应
    - 处理工具调用
    """
    
    # 1. 定义模型
    model = ChatOpenAI(model="qwen-plus",
                       api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                       )
    
    # 2. 获取所有工具
    all_tools = await get_all_tools()
    
    # 3. 绑定工具到模型
    model_with_tools = model.bind_tools(
        [
            *state["copilotkit"]["actions"],  # CopilotKit actions
            *all_tools,  # 我们的工具
        ],
        # 禁用并行工具调用以避免竞争条件
        parallel_tool_calls=False,
    )
    
    # 4. 定义系统消息
    system_message = SystemMessage(
        content=f"""你是一个智能助手，具备搜索和邮件发送功能。请用中文回答。
        
当前状态信息:
- 谚语收藏: {len(state.get('proverbs', []))}条谚语
- 搜索历史: {len(state.get('search_history', []))}次搜索

如果用户提到谚语或格言，你可以将有价值的谚语添加到收藏中。
如果需要用户提供更多信息，请直接询问，不要返回JSON格式。
"""
    )
    
    # 5. 运行模型生成响应

    # 打印当前历史消息以供调试
    print("当前历史消息1:")
    print(state["messages"])
    
    response = await model_with_tools.ainvoke([
        system_message,
        *state["messages"],
    ], config)
    
    # 6. 检查响应中的工具调用
    if isinstance(response, AIMessage) and response.tool_calls:
        actions = state["copilotkit"]["actions"]
        #actions =[]
        # 6.1 检查是否有非CopilotKit的工具调用
        if not any(
            action.get("name") == response.tool_calls[0].get("name")
            for action in actions
        ):
            # 更新状态信息
            updated_state = {"messages": response}
            
            # 如果是搜索工具，更新搜索历史
            if response.tool_calls[0].get("name") in ["tavily-search", "tavily-extract", "tavily-crawl"]:
                search_history = state.get("search_history", [])
                search_query = response.tool_calls[0].get("args", {})

                logger.info(f"🔍 添加搜索查询到历史: {search_query}")
                print(f"🔍 添加搜索查询到历史: {search_query}")
                search_history.append(search_query["query"])
                updated_state["search_history"] = search_history
            
            return Command(goto="tool_node", update=updated_state)
    
    # 7. 所有工具调用已处理，结束对话
    return Command(
        goto=END,
        update={"messages": response}
    )

async def tool_node(state: AgentState, config: RunnableConfig) -> Command[Literal["chat_node"]]:

    print('*****************进入 tool_node *****************')
    
    print("当前历史消息2:")
    print(state["messages"])
    """
    自定义工具调用节点，替代内置的ToolNode
    处理工具调用并返回结果，包含简化的人工审核流程
    """
    # 获取最后一条消息
    last_message = state["messages"][-1]
    
    # 检查是否有工具调用
    if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
        logger.warning("⚠️ 没有找到工具调用")
        return Command(goto="chat_node", update={})
        
    # 只处理第一个工具调用
    tool_call = last_message.tool_calls[0]
    
    # 创建结构化的审核消息
    approval_request = {
        "type": "tool_approval_request",
        "tool_name": tool_call.get("name"),
        "tool_args": tool_call.get("args", {}),
        "tool_id": tool_call.get("id"),
        "timestamp": "2025-07-08",
        "instructions": {
            "approve": "输入 'approve' 或 '通过' 来批准此工具调用",
            "reject": "输入 'reject' 或 '拒绝' 来拒绝此工具调用"
        }
    }
    
    # 使用interrupt等待用户审核决定
    #approve_status = state["approval_status"]
    approve_status = 'approve'
    if(approve_status == "none"):
        approve_status = interrupt(approval_request)
    
    if approve_status in ["rejected", "reject"]:
        logger.info("❌ 工具调用被拒绝")
        
        from langchain_core.messages import ToolMessage
        rejection_message = ToolMessage(
            content="工具调用被用户拒绝执行。",
            tool_call_id=last_message.tool_calls[0].get("id"),
            name=last_message.tool_calls[0].get("name")
        )
        
        # 重置审核状态
        return Command(
            goto="chat_node",
            update={
                "messages": [rejection_message],
                "approval_status": "none",  # 重置审核状态
            }
        )
    
    # 如果审核通过，执行工具调用
    elif approve_status in ["approved", "approve"]:
        logger.info("✅ 工具调用已获得审核通过，开始执行")
        
        # 获取所有可用工具
        all_tools = await get_all_tools()
        
        # 创建工具名称到工具函数的映射
        tool_map = {tool.name: tool for tool in all_tools}
        
        # 获取待审核的工具调用信息
        tool_call = last_message.tool_calls[0]
        pending_calls = [{
            "name": tool_call.get("name"),
            "args": tool_call.get("args", {}),
            "id": tool_call.get("id")
        }]
        
        # 处理单个工具调用
        tool_call_info = pending_calls[0]  # 只处理第一个工具调用
        tool_name = tool_call_info.get("name")
        tool_args = tool_call_info.get("args", {})
        tool_id = tool_call_info.get("id")
        
        logger.info(f"🔧 执行已审核的工具: {tool_name}")
        logger.info(f"📝 参数: {tool_args}")
        
        if tool_name in tool_map:
            try:
                # 调用工具函数
                tool_func = tool_map[tool_name]
                
                # 检查是否为LangChain工具(有.func属性)
                if hasattr(tool_func, 'func') and callable(tool_func.func):
                    # 这是我们自定义的工具(如get_weather)
                    if asyncio.iscoroutinefunction(tool_func.func):
                        result = await tool_func.func(**tool_args)
                    else:
                        result = tool_func.func(**tool_args)
                elif hasattr(tool_func, 'ainvoke'):
                    # 这是MCP工具，使用ainvoke方法
                    result = await tool_func.ainvoke(tool_args)
                elif hasattr(tool_func, 'invoke'):
                    # 这是MCP工具，使用invoke方法
                    result = await tool_func.invoke(tool_args)
                elif callable(tool_func):
                    # 直接调用工具函数
                    if asyncio.iscoroutinefunction(tool_func):
                        result = await tool_func(**tool_args)
                    else:
                        result = tool_func(**tool_args)
                else:
                    raise ValueError(f"不支持的工具类型: {type(tool_func)}")
                
                logger.info(f"✅ 工具调用成功: {str(result)[:100]}...")
                
                # 创建工具结果消息
                from langchain_core.messages import ToolMessage
                tool_message = ToolMessage(
                    content=str(result),
                    tool_call_id=tool_id,
                    name=tool_name
                )
                
            except Exception as e:
                logger.error(f"❌ 工具调用失败: {e}")
                import traceback
                traceback.print_exc()
                # 创建错误消息
                from langchain_core.messages import ToolMessage
                tool_message = ToolMessage(
                    content=f"工具调用失败: {str(e)}",
                    tool_call_id=tool_id,
                    name=tool_name
                )
        else:
            logger.warning(f"❌ 未知工具: {tool_name}")
            from langchain_core.messages import ToolMessage
            tool_message = ToolMessage(
                content=f"未知工具: {tool_name}",
                tool_call_id=tool_id,
                name=tool_name
            )
        
        # 重置审核状态并返回工具结果
        return Command(
            goto="chat_node",
            update={
                "messages": [tool_message],
                "approval_status": approve_status,  # 重置审核状态
            }
        )
    
    # 如果状态异常，重置状态
    else:
        logger.warning(f"⚠️ 异常的审核状态")
        return Command(
            goto="chat_node",
            update={
            }
        )

async def create_search_agent():
    """创建使用定制状态的搜索智能体
    
    Returns:
        配置好的LangGraph StateGraph
    """
    # 获取所有工具（用于验证工具可用性）
    all_tools = await get_all_tools()
    
    # 创建状态图
    workflow = StateGraph(AgentState)
    workflow.add_node("chat_node", chat_node)
    workflow.add_node("tool_node", tool_node)  # 使用自定义的tool_node
    workflow.set_entry_point("chat_node")
    
    # 创建内存检查点保存器
    checkpointer = MemorySaver()
    
    # 编译并返回图
    agent = workflow.compile(checkpointer=checkpointer)
    return agent

# 创建全局graph实例
graph = None

async def get_graph():
    """获取graph实例，如果不存在则创建"""
    global graph
    if graph is None:
        graph = await create_search_agent()
    return graph

# 运行初始化
try:
    asyncio.run(get_graph())
except Exception as e:
    logger.error(f"初始化graph失败: {e}")
    # 创建一个简单的fallback graph
    workflow = StateGraph(AgentState)
    
    async def simple_chat_node(state: AgentState, config: RunnableConfig):
        model = ChatOpenAI(model="gpt-4o-mini")
        response = await model.ainvoke([
            SystemMessage(content="你是一个智能助手。"),
            *state["messages"]
        ], config)
        return Command(goto=END, update={"messages": response})
    
    workflow.add_node("chat_node", simple_chat_node)
    workflow.set_entry_point("chat_node")
    checkpointer = MemorySaver()
    graph = workflow.compile(checkpointer=checkpointer)
