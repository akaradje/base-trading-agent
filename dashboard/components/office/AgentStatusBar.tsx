"use client";

import { motion } from "framer-motion";
import { useAgents } from "@/lib/AgentContext";
import { EventBus, EVENTS } from "@/lib/EventBus";

const AGENT_INFO: Record<string, { name: string; role: string; color: string }> = {
  strategist: { name: "Jing", role: "Strategist", color: "#60a5fa" },
  analyst:    { name: "Joe", role: "Analyst", color: "#4ade80" },
  critic:     { name: "James", role: "RiskCritic", color: "#ef4444" },
  onchain:    { name: "Jade", role: "OnChain", color: "#a78bfa" },
  risk:       { name: "Jeed", role: "RiskMgr", color: "#facc15" },
  engine:     { name: "Jai", role: "Engine", color: "#f97316" },
};

export default function AgentStatusBar() {
  const { agents } = useAgents();

  const handleAgentClick = (agentId: string) => {
    EventBus.emit(EVENTS.AGENT_CLICKED, agentId);
    EventBus.emit(EVENTS.CAMERA_FOCUS, agentId);
  };

  return (
    <div className="flex gap-2 overflow-x-auto pb-1 px-1">
      {Object.entries(AGENT_INFO).map(([id, info]) => {
        const agent = agents[id];
        const status = agent?.status || "idle";
        const task = agent?.current_task || "";

        return (
          <motion.button
            key={id}
            whileHover={{ scale: 1.03, y: -2 }}
            whileTap={{ scale: 0.97 }}
            onClick={() => handleAgentClick(id)}
            className="flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors min-w-[140px]"
            style={{
              backgroundColor: info.color + "08",
              borderColor: info.color + "30",
            }}
          >
            {/* Avatar */}
            <div className="relative">
              <div
                className="w-7 h-7 rounded-full flex items-center justify-center text-[9px] font-bold"
                style={{ backgroundColor: info.color + "25", color: info.color }}
              >
                {info.name[0]}
              </div>
              <div
                className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-gray-900 ${
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

            {/* Info */}
            <div className="text-left">
              <div className="text-[10px] font-bold text-gray-200">{info.name}</div>
              <div className="text-[8px] text-gray-500 truncate max-w-[80px]">
                {task || info.role}
              </div>
            </div>
          </motion.button>
        );
      })}
    </div>
  );
}
