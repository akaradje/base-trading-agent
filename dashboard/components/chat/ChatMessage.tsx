"use client";

import { motion } from "framer-motion";
import type { ChatMessage as ChatMessageType } from "@/lib/chatClient";

const AGENT_COLORS: Record<string, string> = {
  strategist: "#60a5fa",
  analyst: "#4ade80",
  critic: "#ef4444",
  onchain: "#a78bfa",
  risk: "#facc15",
  engine: "#f97316",
};

const AGENT_NAMES: Record<string, string> = {
  strategist: "Jing",
  analyst: "Joe",
  critic: "James",
  onchain: "Jade",
  risk: "Jeed",
  engine: "Jai",
};

export default function ChatMessage({ msg }: { msg: ChatMessageType }) {
  const isUser = msg.role === "user";
  const isSystem = msg.role === "system" || msg.role === "dispatcher";
  const agentColor = msg.agentId ? AGENT_COLORS[msg.agentId] || "#6b7280" : "#6b7280";
  const agentName = msg.agentId ? AGENT_NAMES[msg.agentId] || msg.agentId : "System";

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex gap-2 mb-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}
    >
      {/* Avatar */}
      {!isUser && (
        <div
          className="w-6 h-6 rounded-full flex items-center justify-center text-[8px] font-bold flex-shrink-0"
          style={{ backgroundColor: agentColor + "30", color: agentColor, border: `1px solid ${agentColor}50` }}
        >
          {agentName[0]}
        </div>
      )}

      {/* Bubble */}
      <div
        className={`max-w-[80%] rounded-lg px-3 py-2 text-xs leading-relaxed ${
          isUser
            ? "bg-blue-600/30 border border-blue-500/30 text-blue-100"
            : isSystem
            ? "bg-gray-700/30 border border-gray-600/30 text-gray-400 italic"
            : "bg-gray-800/60 border border-gray-600/30 text-gray-200"
        }`}
      >
        {!isUser && !isSystem && (
          <div className="text-[9px] font-bold mb-1" style={{ color: agentColor }}>
            {agentName} — {msg.agentId && AGENT_NAMES[msg.agentId] ? msg.agentId : "system"}
          </div>
        )}
        <div className="whitespace-pre-wrap break-words">
          {renderContent(msg.content)}
          {msg.streaming && (
            <span className="inline-block w-1.5 h-3 bg-gray-400 animate-pulse ml-0.5" />
          )}
        </div>
        <div className="text-[8px] text-gray-500 mt-1 text-right">
          {new Date(msg.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </div>
      </div>
    </motion.div>
  );
}

function renderContent(content: string) {
  // Simple markdown: bold, code blocks, inline code
  return content
    .replace(/\*\*(.*?)\*\*/g, '<strong class="text-white">$1</strong>')
    .replace(/`([^`]+)`/g, '<code class="bg-gray-700 px-1 rounded text-green-300">$1</code>')
    .split("\n")
    .map((line, i) => {
      if (line.startsWith("- ")) {
        return (
          <span key={i}>
            <span className="text-gray-500">•</span> {line.slice(2)}
            <br />
          </span>
        );
      }
      return (
        <span key={i}>
          <span dangerouslySetInnerHTML={{ __html: line }} />
          <br />
        </span>
      );
    });
}
