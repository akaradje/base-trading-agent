"use client";

import { useAgent } from "@/lib/AgentContext";
import { motion, AnimatePresence } from "framer-motion";

// Agent display config
const AGENT_CONFIG: Record<string, { name: string; emoji: string; color: string; role: string }> = {
  strategist: { name: "Jing", emoji: "🧭", color: "#60a5fa", role: "Strategist" },
  analyst:    { name: "Joe",  emoji: "📊", color: "#4ade80", role: "Analyst" },
  critic:     { name: "James", emoji: "🛡️", color: "#ef4444", role: "RiskCritic" },
  onchain:    { name: "Jade", emoji: "🔗", color: "#a78bfa", role: "OnChain" },
  risk:       { name: "Jeed", emoji: "⚠️", color: "#facc15", role: "RiskMgr" },
  engine:     { name: "Jai",  emoji: "⚙️", color: "#f97316", role: "Engine" },
};

// Status-based CSS classes
const STATUS_STYLES: Record<string, string> = {
  idle:     "border-gray-600 bg-gray-800/50",
  working:  "border-green-500 bg-green-900/20 shadow-green-500/20 shadow-lg",
  thinking: "border-yellow-500 bg-yellow-900/20 shadow-yellow-500/20 shadow-lg",
  error:    "border-red-500 bg-red-900/20 shadow-red-500/20 shadow-lg",
};

// Mood-based emoji
const MOOD_EMOJI: Record<string, string> = {
  neutral: "😐",
  happy:   "😊",
  worried: "😟",
  angry:   "😠",
  sleeping: "😴",
};

export default function AgentCard({ agentId }: { agentId: string }) {
  const agent = useAgent(agentId);
  const config = AGENT_CONFIG[agentId] || { name: agentId, emoji: "🤖", color: "#888", role: "Agent" };

  const status = agent.status || "idle";
  const mood = agent.avatar_mood || "neutral";
  const message = agent.bubble_message || "";
  const task = agent.current_task || "";

  // Animation based on status
  const getAnimation = () => {
    switch (status) {
      case "working":
        return { y: [0, -6, 0], transition: { repeat: Infinity, duration: 1.2 } };
      case "thinking":
        return { rotate: [-2, 2, -2], transition: { repeat: Infinity, duration: 0.8 } };
      case "error":
        return { x: [-3, 3, -3], transition: { repeat: Infinity, duration: 0.2 } };
      default:
        return { y: [0, -2, 0], transition: { repeat: Infinity, duration: 3 } };
    }
  };

  return (
    <motion.div
      className={`agent-card relative border-2 rounded-xl p-4 text-center transition-all duration-300 ${
        STATUS_STYLES[status] || STATUS_STYLES.idle
      }`}
      style={{ borderColor: config.color }}
      animate={getAnimation()}
      whileHover={{ scale: 1.05, borderColor: config.color }}
    >
      {/* Agent emoji (placeholder for pixel art) */}
      <motion.div
        className="text-5xl mb-2"
        animate={mood === "happy" ? { scale: [1, 1.1, 1] } : {}}
        transition={{ repeat: Infinity, duration: 2 }}
      >
        {config.emoji}
      </motion.div>

      {/* Agent name & role */}
      <div className="text-sm font-bold mb-0.5" style={{ color: config.color }}>
        {config.name}
      </div>
      <div className="text-[10px] text-gray-500 mb-2">
        {config.role}
      </div>

      {/* Status indicator dot */}
      <div className={`status-dot ${status}`} />

      {/* Current task (when working/thinking) */}
      {(status === "working" || status === "thinking") && task && (
        <motion.div
          className="text-[10px] text-green-400 mt-2 truncate"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          ⚡ {task}
        </motion.div>
      )}

      {/* Speech bubble */}
      <AnimatePresence>
        {message && (
          <motion.div
            className="speech-bubble"
            initial={{ opacity: 0, scale: 0.8, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{ duration: 0.3 }}
          >
            {message}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Mood indicator */}
      <div className="absolute top-2 right-2 text-sm">
        {MOOD_EMOJI[mood] || MOOD_EMOJI.neutral}
      </div>
    </motion.div>
  );
}
