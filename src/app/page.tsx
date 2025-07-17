
"use client";

import { CopilotSidebar ,CopilotPopup} from "@copilotkit/react-ui"; 
import { useState } from "react";
import { useCoAgent, useCoAgentStateRender,useCopilotAction ,useLangGraphInterrupt} from "@copilotkit/react-core";

export default function YourApp() {
  return (
    <>
    <Home/>    
    <CopilotSidebar
      defaultOpen={true}
      instructions={"您应尽可能地帮助用户。请根据您拥有的数据以最佳方式回答问题。"}
      labels={{
      title: "智能AI Copilot",
      initial: `# 👋 您好！

我是你的智能Copilot。演示功能：

- **共享状态**: 搜索历史实时的展示
- **前端工具**: 调用前端工具打招呼
- **生成式UI**: 获取天气信息展示卡片
- **HITL流程**: 工具调用的人工审核`
      }}/>  
    </>
  );
}

type AgentState = {
  search_history: Array<{
    query: string;
    completed: boolean;
    timestamp: string;
    tool_name?: string;
    completed_at?: string;
  }>
}

function Home() {
  
  const {state, setState} = useCoAgent<AgentState>({
    name: "sample_agent",
    initialState: {
      search_history: []
    },
  })

  useCopilotAction({
    name: "sayHello",              // Action 名称，Agent 将通过此名称来调用工具
    description: "向指定用户问好", // 对该 Action 的描述（供 Agent 理解用途）
    parameters: [                 // 定义参数列表
      { name: "name", type: "string", description: "要问好的对象名字" }
    ],
    render: "正在发送问候...",    // (可选) 执行时在Chat中显示的提示文本
    handler: async ({ name }) => { // 定义具体执行逻辑的函数（异步支持）
      alert(`Hello, ${name}!`);    // 这里在浏览器弹出提示框
      return('问候已发送给' + name); // 返回结果将显示在Chat中
      }
  });
    
  useCoAgentStateRender<AgentState>({
      name: "sample_agent", // the name the agent is served as
      render: ({ state }) => (
        <div>
          {state.search_history?.map((search, index) => (
            <div key={index}>
              {search.completed ? "✅" : "❌"} 正在执行：{search.query} {search.completed ? "" : "..."}
            </div>
          ))}
        </div>
      ),
  });

  useCopilotAction({
    name: "get_weather",
    description: "获取指定位置的天气信息。",
    available: "disabled", // 保持为disabled，确保不被当作前端工具
    render: ({status, args, result}) => {
      return (
        <p className="text-gray-500 mt-2">
          {status !== "complete" && "Calling weather API..."}
          {status === "complete" && <WeatherCard location={args.location} result={result} themeColor="#3b82f6" />}
        </p>
      );
    },
  });

  useLangGraphInterrupt({
      render: ({ event, resolve }) => {
          const { tool_name, tool_args } = event.value;
          return (
              <div className="bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-2xl p-6 my-4 shadow-lg">
                  {/* 标题 */}
                  <div className="flex items-center gap-3 mb-4">
                      <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                          <span className="text-lg">🔧</span>
                      </div>
                      <div>
                          <h3 className="text-lg font-bold text-gray-800">工具调用审核</h3>
                          <p className="text-sm text-gray-600">请确认是否执行以下工具调用</p>
                      </div>
                  </div>

                  {/* 工具信息 */}
                  <div className="bg-white rounded-xl p-4 mb-4 border border-gray-100">
                      <div className="grid grid-cols-1 gap-3">
                          <div>
                              <label className="block text-xs font-medium text-gray-500 mb-1">工具名称</label>
                              <div className="bg-gray-50 px-3 py-2 rounded-lg">
                                  <code className="text-blue-600 font-mono text-sm">{tool_name}</code>
                              </div>
                          </div>
                          
                          <div>
                              <label className="block text-xs font-medium text-gray-500 mb-1">参数</label>
                              <div className="bg-gray-50 px-3 py-2 rounded-lg max-h-24 overflow-y-auto">
                                  <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono">
                                      {JSON.stringify(tool_args, null, 2)}
                                  </pre>
                              </div>
                          </div>
                      </div>
                  </div>

                  {/* 操作按钮 */}
                  <div className="mt-4">
                      <div className="flex gap-2">
                          <button 
                              type="button"
                              onClick={() => resolve("approve")}
                              className="flex-1 bg-green-500 hover:bg-green-600 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200 flex items-center justify-center gap-2 text-sm"
                          >
                              <span>✅</span>
                              通过
                          </button>
                          <button 
                              type="button"
                              onClick={() => resolve("reject")}
                              className="flex-1 bg-red-500 hover:bg-red-600 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200 flex items-center justify-center gap-2 text-sm"
                          >
                              <span>❌</span>
                              拒绝
                          </button>
                      </div>
                  </div>
              </div>
          );
      }
  });
  
  return (
    <div
      style={{ backgroundColor: '#6366f1' }}
      className="h-screen w-screen flex justify-center items-center flex-col transition-colors duration-300"
    >
      <div className="bg-white/20 backdrop-blur-md p-24 rounded-4xl shadow-xl max-w-2xl w-full">
        <h1 className="text-4xl font-bold text-white mb-2 text-center">CopilotKit演示主应用</h1>
        <p className="text-gray-200 text-center italic mb-6">这里可以是你的任何现有的企业应用！</p>
        <hr className="border-white/20 my-6" />
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* 搜索历史区域 */}
          <div>
            <h2 className="text-2xl font-bold text-white mb-4">搜索历史</h2>
            <div className="flex flex-col gap-3">
              {state.search_history?.map((search, index) => (
                <div 
                  key={index} 
                  className={`bg-white/15 p-4 rounded-xl text-white relative group hover:bg-white/20 transition-all ${
                    search.completed ? 'border-l-4 border-green-400' : 'border-l-4 border-yellow-400'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 flex-1">
                      <span className="text-blue-200">🔍</span>
                      <div className="flex-1">
                        <p className="text-sm font-medium">{search.query}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {search.completed ? (
                        <span className="text-green-400 text-xs bg-green-400/20 px-2 py-1 rounded-full">
                          ✅ 已完成
                        </span>
                      ) : (
                        <span className="text-yellow-400 text-xs bg-yellow-400/20 px-2 py-1 rounded-full">
                          ⏳ 进行中
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
            {state.search_history?.length === 0 && <p className="text-center text-white/80 italic my-8">
              暂无搜索历史。
            </p>}
          </div>
        </div>
      </div>
    </div>
  );
}

function SunIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-14 h-14 text-yellow-200">
      <circle cx="12" cy="12" r="5" />
      <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" strokeWidth="2" stroke="currentColor" />
    </svg>
  );
}

function WeatherCard({ location, result, themeColor }: { location?: string, result?: any, themeColor: string }) {
  return (
    <div
    style={{ backgroundColor: themeColor }}
    className="rounded-xl shadow-xl mt-6 mb-4 max-w-md w-full"
  >
    <div className="bg-white/20 p-4 w-full">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-bold text-white capitalize">{location}</h3>
          <p className="text-white">天气</p>
        </div>
        <SunIcon />
      </div>
      
      <div className="mt-4 flex items-end justify-between">
        <div className="text-3xl font-bold text-white">{result.temperature}</div>
        <div className="text-sm text-white">{result.condition}</div>
      </div>
      
      <div className="mt-4 pt-4 border-t border-white">
        <div className="grid grid-cols-3 gap-2 text-center">
          <div>
            <p className="text-white text-xs">湿度</p>
            <p className="text-white font-medium">{result.humidity}</p>
          </div>
          <div>
            <p className="text-white text-xs">风速</p>
            <p className="text-white font-medium">{result.wind.speed}级</p>
          </div>
          <div>
            <p className="text-white text-xs">日期</p>
            <p className="text-white font-medium">{result.updated_at?.substring(0, 10)}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
  );
}
