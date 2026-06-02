"use client";

import { motion, AnimatePresence } from "framer-motion";
import { AgentState } from "@/lib/supabaseClient";

// ──────────────────────────────────────────────
// Agent Detail Panel — แสดงรายละเอียด agent เมื่อคลิก
// ──────────────────────────────────────────────

interface AgentDetailPanelProps {
  agent: AgentState;
  agentId: string;
  color: string;
  name: string;
  role: string;
  visible: boolean;
  onClose: () => void;
}

export default function AgentDetailPanel({
  agent,
  agentId,
  color,
  name,
  role,
  visible,
  onClose,
}: AgentDetailPanelProps) {
  const status = agent.status || "idle";
  const mood = agent.avatar_mood || "neutral";
  const task = agent.current_task || "No active task";
  const message = agent.bubble_message || "";
  const lastAction = agent.last_action_ts || "";

  const statusEmoji: Record<string, string> = {
    idle: "🟢",
    working: "💻",
    thinking: "🤔",
    error: "🔴",
    sleeping: "😴",
    celebrate: "🎉",
  };

  const moodEmoji: Record<string, string> = {
    neutral: "😐",
    happy: "😊",
    focused: "🧐",
    worried: "😟",
    excited: "🤩",
    tired: "😴",
  };

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        >
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

          {/* Panel */}
          <motion.div
            className="relative w-96 max-w-[90vw] rounded-xl border-2 overflow-hidden"
            style={{
              borderColor: color,
              background: "linear-gradient(135deg, #1a1a2e, #16213e)",
              boxShadow: `0 0 30px ${color}40`,
            }}
            initial={{ scale: 0.8, y: 20 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.8, y: 20 }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div
              className="p-4 flex items-center gap-3"
              style={{ background: `${color}20` }}
            >
              <div
                className="w-12 h-12 rounded-full flex items-center justify-center text-2xl"
                style={{ background: color }}
              >
                {agentId === "strategist" ? "🧭" :
                 agentId === "analyst" ? "📊" :
                 agentId === "critic" ? "🛡️" :
                 agentId === "onchain" ? "🔗" :
                 agentId === "risk" ? "⚠️" : "⚙️"}
              </div>
              <div>
                <h3 className="text-lg font-bold" style={{ color }}>{name}</h3>
                <p className="text-sm text-gray-400">{role}</p>
              </div>
              <button
                className="ml-auto text-gray-400 hover:text-white transition-colors"
                onClick={onClose}
              >
                ✕
              </button>
            </div>

            {/* Content */}
            <div className="p-4 space-y-4">
              {/* Status */}
              <div className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
                <span className="text-sm text-gray-400">Status</span>
                <span className="text-sm font-medium">
                  {statusEmoji[status]} {status}
                </span>
              </div>

              {/* Mood */}
              <div className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
                <span className="text-sm text-gray-400">Mood</span>
                <span className="text-sm font-medium">
                  {moodEmoji[mood]} {mood}
                </span>
              </div>

              {/* Current Task */}
              <div className="p-3 bg-gray-800/50 rounded-lg">
                <span className="text-xs text-gray-400 block mb-1">Current Task</span>
                <p className="text-sm">{task}</p>
              </div>

              {/* Message */}
              {message && (
                <div className="p-3 bg-gray-800/50 rounded-lg">
                  <span className="text-xs text-gray-400 block mb-1">Message</span>
                  <p className="text-sm italic">"{message}"</p>
                </div>
              )}

              {/* Last Action */}
              {lastAction && (
                <div className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
                  <span className="text-sm text-gray-400">Last Action</span>
                  <span className="text-xs text-gray-500">
                    {new Date(lastAction).toLocaleTimeString()}
                  </span>
                </div>
              )}

              {/* Agent Stats */}
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-gray-800/50 rounded-lg text-center">
                  <div className="text-2xl font-bold" style={{ color }}>
                    {agentId === "analyst" ? "156" :
                     agentId === "strategist" ? "42" :
                     agentId === "critic" ? "89" :
                     agentId === "onchain" ? "1.2k" :
                     agentId === "risk" ? "∞" : "3.4k"}
                  </div>
                  <div className="text-xs text-gray-400">
                    {agentId === "analyst" ? "Signals" :
                     agentId === "strategist" ? "Regime Changes" :
                     agentId === "critic" ? "Reviews" :
                     agentId === "onchain" ? "Blocks Scanned" :
                     agentId === "risk" ? "Safety Checks" : "Cycles"}
                  </div>
                </div>
                <div className="p-3 bg-gray-800/50 rounded-lg text-center">
                  <div className="text-2xl font-bold" style={{ color }}>
                    {agentId === "analyst" ? "67%" :
                     agentId === "strategist" ? "85%" :
                     agentId === "critic" ? "23%" :
                     agentId === "onchain" ? "99.9%" :
                     agentId === "risk" ? "100%" : "99.7%"}
                  </div>
                  <div className="text-xs text-gray-400">
                    {agentId === "analyst" ? "Win Rate" :
                     agentId === "strategist" ? "Accuracy" :
                     agentId === "critic" ? "Veto Rate" :
                     agentId === "onchain" ? "Uptime" :
                     agentId === "risk" ? "Safety" : "Uptime"}
                  </div>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-gray-700 flex justify-between items-center">
              <span className="text-xs text-gray-500">Agent ID: {agentId}</span>
              <button
                className="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                style={{ background: color, color: "#0a0a1a" }}
                onClick={onClose}
              >
                Close
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
