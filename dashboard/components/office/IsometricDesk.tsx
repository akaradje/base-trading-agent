"use client";

import { motion } from "framer-motion";
import { AgentState } from "@/lib/supabaseClient";
import SpriteCharacter from "./SpriteCharacter";

// Agent config
const AGENT_CONFIG: Record<string, { name: string; role: string; color: string; emoji: string }> = {
  strategist: { name: "Jing", role: "Strategist", color: "#60a5fa", emoji: "🧭" },
  analyst:    { name: "Joe",  role: "Analyst",    color: "#4ade80", emoji: "📊" },
  critic:     { name: "James", role: "RiskCritic", color: "#ef4444", emoji: "🛡️" },
  onchain:    { name: "Jade", role: "OnChain",    color: "#a78bfa", emoji: "🔗" },
  risk:       { name: "Jeed", role: "RiskMgr",    color: "#facc15", emoji: "⚠️" },
  engine:     { name: "Jai",  role: "Engine",     color: "#f97316", emoji: "⚙️" },
};

interface IsometricDeskProps {
  agentId: string;
  agent: AgentState;
  position: { x: number; y: number };
}

export default function IsometricDesk({ agentId, agent, position }: IsometricDeskProps) {
  const config = AGENT_CONFIG[agentId] || { name: agentId, role: "Agent", color: "#888", emoji: "🤖" };
  const status = agent.status || "idle";

  // Desk glow based on status
  const getDeskGlow = () => {
    switch (status) {
      case "working":
        return "0 0 20px rgba(74, 222, 128, 0.3)";
      case "thinking":
        return "0 0 20px rgba(250, 204, 21, 0.3)";
      case "error":
        return "0 0 20px rgba(239, 68, 68, 0.3)";
      default:
        return "none";
    }
  };

  return (
    <motion.div
      className="absolute"
      style={{
        left: `${position.x}%`,
        top: `${position.y}%`,
        transform: "translate(-50%, -50%)",
      }}
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay: Math.random() * 0.5 }}
    >
      {/* Isometric desk container */}
      <div
        className="relative"
        style={{
          transform: "rotateX(60deg) rotateZ(-45deg)",
          transformStyle: "preserve-3d",
        }}
      >
        {/* Desk surface */}
        <motion.div
          className="w-20 h-20 rounded-lg border-2"
          style={{
            borderColor: config.color,
            background: `linear-gradient(135deg, ${config.color}15, ${config.color}05)`,
            boxShadow: getDeskGlow(),
          }}
          animate={status === "working" ? {
            borderColor: [config.color, `${config.color}80`, config.color],
          } : {}}
          transition={{ repeat: Infinity, duration: 2 }}
        >
          {/* Desk items */}
          <div className="absolute inset-2 flex items-center justify-center">
            {/* Monitor on desk */}
            {status === "working" && (
              <motion.div
                className="w-8 h-6 bg-gray-800 rounded border border-gray-600"
                animate={{
                  borderColor: ["#4ade80", "#22d3ee", "#4ade80"],
                }}
                transition={{ repeat: Infinity, duration: 2 }}
              >
                <motion.div
                  className="absolute inset-0.5 rounded-sm bg-gradient-to-b from-blue-900 to-gray-900"
                />
              </motion.div>
            )}

            {/* Paper/documents for thinking */}
            {status === "thinking" && (
              <div className="flex gap-0.5">
                <div className="w-4 h-5 bg-white/10 rounded-sm border border-white/20" />
                <div className="w-4 h-5 bg-white/10 rounded-sm border border-white/20 rotate-3" />
              </div>
            )}

            {/* Warning sign for error */}
            {status === "error" && (
              <motion.div
                className="text-2xl"
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ repeat: Infinity, duration: 0.5 }}
              >
                ⚠️
              </motion.div>
            )}

            {/* Idle - coffee mug */}
            {status === "idle" && (
              <div className="text-lg">☕</div>
            )}
          </div>
        </motion.div>

        {/* Desk legs (3D effect) */}
        <div
          className="absolute -bottom-2 left-1 w-1 h-2 rounded-b"
          style={{ background: `${config.color}40` }}
        />
        <div
          className="absolute -bottom-2 right-1 w-1 h-2 rounded-b"
          style={{ background: `${config.color}40` }}
        />
      </div>

      {/* Phase 9: Sprite Sheet Character (not rotated - stays upright) */}
      <div
        className="absolute -top-16 left-1/2 -translate-x-1/2"
        style={{ transform: "rotateZ(45deg) rotateX(-60deg)" }}
      >
        <SpriteCharacter
          agent={agent}
          color={config.color}
          name={config.name}
          role={config.role}
        />
      </div>

      {/* Agent emoji badge */}
      <motion.div
        className="absolute -top-2 -right-2 w-6 h-6 rounded-full flex items-center justify-center text-xs z-10"
        style={{
          background: config.color,
          transform: "rotateZ(45deg) rotateX(-60deg)",
        }}
        whileHover={{ scale: 1.2 }}
      >
        {config.emoji}
      </motion.div>
    </motion.div>
  );
}
