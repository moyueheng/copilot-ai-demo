
"use client";

import { CopilotSidebar ,CopilotPopup} from "@copilotkit/react-ui"; 
import { useState } from "react";
import { useCoAgent, useCopilotAction ,useLangGraphInterrupt} from "@copilotkit/react-core";

export default function YourApp() {
  return (
    <>
    <Home/>    
    <CopilotPopup
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
  //proverbs: string[],
  search_history: string[],
  //approval_status: string
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
                  className="bg-white/15 p-4 rounded-xl text-white relative group hover:bg-white/20 transition-all"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-blue-200">🔍</span>
                    <p className="pr-8 text-sm">{search}</p>
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
