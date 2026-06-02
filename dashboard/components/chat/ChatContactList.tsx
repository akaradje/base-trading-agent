"use client";

import { useAgents } from "@/lib/AgentContext";

const AGENT_INFO: Record<string, { name: string; role: string; color: string }> = {
  strategist: { name: "Jing", role: "Strategist", color: "#60a5fa" },
  analyst:    { name: "Joe", role: "Analyst", color: "#4ade80" },
  critic:     { name: "James", role: "RiskCritic", color: "#ef4444" },
  onchain:    { name: "Jade", role: "OnChain", color: "#a78bfa" },
  risk:       { name: "Jeed", role: "RiskMgr", color: "#facc15" },
  engine:     { name: "Jai", role: "Engine", color: "#f97316" },
};

interface Props {
  selected: string | null;
  onSelect: (agentId: string | null) => void;
}

export default function ChatContactList({ selected, onSelect }: Props) {
  const { agents } = useAgents();

  return (
    <div className="w-36 border-r border-gray-700 flex flex-col overflow-y-auto">
      {/* Group chat */}
      <button
        onClick={() => onSelect(null)}
        className={`flex items-center gap-2 px-3 py-2.5 text-left transition-colors ${
          selected === null
            ? "bg-blue-600/20 border-l-2 border-blue-400"
            : "hover:bg-gray-800/50 border-l-2 border-transparent"
        }`}
      >
        <span className="text-sm">💬</span>
        <div>
          <div className="text-[10px] font-bold text-gray-200">Group Chat</div>
          <div className="text-[8px] text-gray-500">Dispatcher</div>
        </div>
      </button>

      <div className="border-t border-gray-700/50 mx-2" />

      {/* Agent list */}
      {Object.entries(AGENT_INFO).map(([id, info]) => {
        const agent = agents[id];
        const status = agent?.status || "idle";

        return (
          <button
            key={id}
            onClick={() => onSelect(id)}
            className={`flex items-center gap-2 px-3 py-2.5 text-left transition-colors ${
              selected === id
                ? "bg-gray-700/40 border-l-2"
                : "hover:bg-gray-800/50 border-l-2 border-transparent"
            }`}
            style={{
              borderLeftColor: selected === id ? info.color : "transparent",
            }}
          >
            {/* Status dot */}
            <div className="relative">
              <div
                className="w-5 h-5 rounded-full flex items-center justify-center text-[7px] font-bold"
                style={{ backgroundColor: info.color + "25", color: info.color }}
              >
                {info.name[0]}
              </div>
              <div
                className={`absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full border border-gray-900 ${
                  status === "working"
                    ? "bg-green-400 animate-pulse"
                    : status === "thinking"
                    ? "bg-yellow-400"
                    : status === "error"
                    ? "bg-red-400"
                    : "bg-gray-500"
                }`}
              />
            </div>
            <div>
              <div className="text-[10px] font-bold text-gray-200">{info.name}</div>
              <div className="text-[8px] text-gray-500">{info.role}</div>
            </div>
          </button>
        );
      })}
    </div>
  );
}
