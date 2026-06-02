"use client";

import { motion, AnimatePresence } from "framer-motion";
import { AgentState } from "@/lib/supabaseClient";

// ──────────────────────────────────────────────
// Pixel Art Sprite Components (CSS-based)
// ──────────────────────────────────────────────

function IdleSprite({ color }: { color: string }) {
  return (
    <div className="relative w-12 h-16">
      {/* Head */}
      <motion.div
        className="absolute top-0 left-1/2 -translate-x-1/2 w-8 h-8 rounded-full"
        style={{ background: color }}
        animate={{ y: [0, -2, 0] }}
        transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
      >
        {/* Eyes */}
        <div className="absolute top-3 left-1.5 w-1.5 h-1.5 bg-white rounded-full" />
        <div className="absolute top-3 right-1.5 w-1.5 h-1.5 bg-white rounded-full" />
        {/* Mouth */}
        <div className="absolute bottom-1.5 left-1/2 -translate-x-1/2 w-2 h-0.5 bg-white/50 rounded" />
      </motion.div>
      {/* Body */}
      <motion.div
        className="absolute bottom-0 left-1/2 -translate-x-1/2 w-10 h-8 rounded-t-lg"
        style={{ background: `linear-gradient(180deg, ${color}, ${color}dd)` }}
        animate={{ y: [0, -1, 0] }}
        transition={{ repeat: Infinity, duration: 2, ease: "easeInOut", delay: 0.1 }}
      >
        {/* Arms */}
        <motion.div
          className="absolute -left-1.5 top-1 w-1.5 h-4 rounded-full"
          style={{ background: color }}
          animate={{ rotate: [-5, 5, -5] }}
          transition={{ repeat: Infinity, duration: 3 }}
        />
        <motion.div
          className="absolute -right-1.5 top-1 w-1.5 h-4 rounded-full"
          style={{ background: color }}
          animate={{ rotate: [5, -5, 5] }}
          transition={{ repeat: Infinity, duration: 3, delay: 0.5 }}
        />
      </motion.div>
    </div>
  );
}

function WorkingSprite({ color }: { color: string }) {
  return (
    <div className="relative w-16 h-16">
      {/* Head */}
      <motion.div
        className="absolute top-0 left-1/2 -translate-x-1/2 w-8 h-8 rounded-full"
        style={{ background: color }}
        animate={{ y: [0, -1, 0] }}
        transition={{ repeat: Infinity, duration: 0.5 }}
      >
        {/* Eyes - focused */}
        <div className="absolute top-3 left-1.5 w-1.5 h-2 bg-white rounded-full" />
        <div className="absolute top-3 right-1.5 w-1.5 h-2 bg-white rounded-full" />
        {/* Glasses */}
        <div className="absolute top-2.5 left-0.5 right-0.5 h-3 border border-white/30 rounded" />
      </motion.div>
      {/* Body */}
      <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-10 h-8 rounded-t-lg"
        style={{ background: `linear-gradient(180deg, ${color}, ${color}dd)` }}>
        {/* Arms typing */}
        <motion.div
          className="absolute -left-2 top-2 w-2 h-3 rounded-full origin-top"
          style={{ background: color }}
          animate={{ rotate: [-20, 0, -20] }}
          transition={{ repeat: Infinity, duration: 0.3 }}
        />
        <motion.div
          className="absolute -right-2 top-2 w-2 h-3 rounded-full origin-top"
          style={{ background: color }}
          animate={{ rotate: [0, -20, 0] }}
          transition={{ repeat: Infinity, duration: 0.3, delay: 0.15 }}
        />
      </div>
      {/* Monitor */}
      <motion.div
        className="absolute -right-4 bottom-2 w-6 h-5 bg-gray-800 rounded border border-gray-600"
        animate={{
          borderColor: ["#4ade80", "#22d3ee", "#4ade80"],
          boxShadow: [
            "0 0 5px rgba(74, 222, 128, 0.3)",
            "0 0 10px rgba(34, 211, 238, 0.4)",
            "0 0 5px rgba(74, 222, 128, 0.3)",
          ],
        }}
        transition={{ repeat: Infinity, duration: 2 }}
      >
        <motion.div
          className="absolute inset-0.5 rounded-sm"
          animate={{
            background: [
              "linear-gradient(180deg, #1e3a5f, #0f172a)",
              "linear-gradient(180deg, #1e4035, #0f172a)",
              "linear-gradient(180deg, #1e3a5f, #0f172a)",
            ],
          }}
          transition={{ repeat: Infinity, duration: 3 }}
        />
        {/* Code lines */}
        <motion.div
          className="absolute top-1 left-0.5 w-3 h-0.5 bg-green-400/60 rounded"
          animate={{ width: ["40%", "70%", "40%"] }}
          transition={{ repeat: Infinity, duration: 1 }}
        />
        <motion.div
          className="absolute top-2 left-0.5 w-2 h-0.5 bg-blue-400/60 rounded"
          animate={{ width: ["30%", "50%", "30%"] }}
          transition={{ repeat: Infinity, duration: 1.5 }}
        />
        <motion.div
          className="absolute top-3 left-0.5 w-4 h-0.5 bg-yellow-400/60 rounded"
          animate={{ width: ["60%", "40%", "60%"] }}
          transition={{ repeat: Infinity, duration: 1.2 }}
        />
      </motion.div>
    </div>
  );
}

function ThinkingSprite({ color }: { color: string }) {
  return (
    <div className="relative w-12 h-16">
      {/* Head - tilted */}
      <motion.div
        className="absolute top-0 left-1/2 -translate-x-1/2 w-8 h-8 rounded-full"
        style={{ background: color }}
        animate={{ rotate: [-5, 5, -5] }}
        transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
      >
        {/* Eyes - looking up */}
        <div className="absolute top-2 left-1.5 w-1.5 h-1.5 bg-white rounded-full" />
        <div className="absolute top-2 right-1.5 w-1.5 h-1.5 bg-white rounded-full" />
        {/* Thought dots */}
        <motion.div
          className="absolute -top-3 -right-1 w-1.5 h-1.5 bg-white/60 rounded-full"
          animate={{ opacity: [0, 1, 0], y: [0, -4, -8] }}
          transition={{ repeat: Infinity, duration: 1.5 }}
        />
        <motion.div
          className="absolute -top-5 right-0 w-2 h-2 bg-white/40 rounded-full"
          animate={{ opacity: [0, 1, 0], y: [0, -4, -8] }}
          transition={{ repeat: Infinity, duration: 1.5, delay: 0.3 }}
        />
      </motion.div>
      {/* Body */}
      <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-10 h-8 rounded-t-lg"
        style={{ background: `linear-gradient(180deg, ${color}, ${color}dd)` }}>
        {/* Hand on chin */}
        <motion.div
          className="absolute -right-1 top-0 w-2 h-3 rounded-full"
          style={{ background: color }}
          animate={{ y: [0, -2, 0] }}
          transition={{ repeat: Infinity, duration: 1.5 }}
        />
      </div>
    </div>
  );
}

function ErrorSprite({ color }: { color: string }) {
  return (
    <div className="relative w-12 h-16">
      {/* Exclamation badge */}
      <motion.div
        className="absolute -top-4 left-1/2 -translate-x-1/2 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center z-10"
        animate={{
          scale: [1, 1.2, 1],
          boxShadow: [
            "0 0 0 0 rgba(239, 68, 68, 0.4)",
            "0 0 0 8px rgba(239, 68, 68, 0)",
            "0 0 0 0 rgba(239, 68, 68, 0.4)",
          ],
        }}
        transition={{ repeat: Infinity, duration: 1 }}
      >
        <span className="text-white text-xs font-bold">!</span>
      </motion.div>
      {/* Head - shaking */}
      <motion.div
        className="absolute top-0 left-1/2 -translate-x-1/2 w-8 h-8 rounded-full"
        style={{ background: color }}
        animate={{ x: [-2, 2, -2] }}
        transition={{ repeat: Infinity, duration: 0.2 }}
      >
        {/* Eyes - worried */}
        <motion.div
          className="absolute top-3 left-1.5 w-1.5 h-1.5 bg-white rounded-full"
          animate={{ scaleY: [1, 0.5, 1] }}
          transition={{ repeat: Infinity, duration: 0.5 }}
        />
        <motion.div
          className="absolute top-3 right-1.5 w-1.5 h-1.5 bg-white rounded-full"
          animate={{ scaleY: [1, 0.5, 1] }}
          transition={{ repeat: Infinity, duration: 0.5 }}
        />
        {/* Mouth - open */}
        <div className="absolute bottom-1 left-1/2 -translate-x-1/2 w-2 h-1.5 bg-white/70 rounded-full" />
      </motion.div>
      {/* Body - shaking */}
      <motion.div
        className="absolute bottom-0 left-1/2 -translate-x-1/2 w-10 h-8 rounded-t-lg"
        style={{ background: `linear-gradient(180deg, ${color}, ${color}dd)` }}
        animate={{ x: [-1, 1, -1] }}
        transition={{ repeat: Infinity, duration: 0.15 }}
      />
    </div>
  );
}

function SleepingSprite({ color }: { color: string }) {
  return (
    <div className="relative w-12 h-16">
      {/* Zzz */}
      <motion.div className="absolute -top-3 right-0">
        <motion.span
          className="text-blue-300 text-xs font-bold"
          animate={{ opacity: [0, 1, 0], y: [0, -8, -16], x: [0, 4, 8] }}
          transition={{ repeat: Infinity, duration: 2 }}
        >
          Z
        </motion.span>
        <motion.span
          className="text-blue-300/70 text-[10px] font-bold absolute top-0 left-3"
          animate={{ opacity: [0, 1, 0], y: [0, -6, -12], x: [0, 3, 6] }}
          transition={{ repeat: Infinity, duration: 2, delay: 0.5 }}
        >
          z
        </motion.span>
      </motion.div>
      {/* Head - drooping */}
      <motion.div
        className="absolute top-2 left-1/2 -translate-x-1/2 w-8 h-8 rounded-full"
        style={{ background: color }}
        animate={{ rotate: [10, 15, 10] }}
        transition={{ repeat: Infinity, duration: 3 }}
      >
        {/* Eyes - closed */}
        <div className="absolute top-3 left-1.5 w-2 h-0.5 bg-white rounded" />
        <div className="absolute top-3 right-1.5 w-2 h-0.5 bg-white rounded" />
      </motion.div>
      {/* Body - slouching */}
      <motion.div
        className="absolute bottom-0 left-1/2 -translate-x-[45%] w-10 h-6 rounded-t-lg"
        style={{ background: `linear-gradient(180deg, ${color}, ${color}dd)` }}
        animate={{ rotate: [5, 8, 5] }}
        transition={{ repeat: Infinity, duration: 3 }}
      />
    </div>
  );
}

// ──────────────────────────────────────────────
// Speech Bubble
// ──────────────────────────────────────────────

function SpeechBubble({ message, visible }: { message: string; visible: boolean }) {
  return (
    <AnimatePresence>
      {visible && message && (
        <motion.div
          className="absolute -top-14 left-1/2 -translate-x-1/2 z-20"
          initial={{ opacity: 0, scale: 0.8, y: 5 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.8, y: 5 }}
          transition={{ duration: 0.2 }}
        >
          <div className="bg-white text-gray-800 text-[10px] px-3 py-1.5 rounded-lg shadow-lg max-w-[160px] text-center whitespace-normal">
            {message}
          </div>
          {/* Arrow */}
          <div className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-3 h-3 bg-white rotate-45" />
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// ──────────────────────────────────────────────
// Name Tag
// ──────────────────────────────────────────────

function NameTag({ name, role, color }: { name: string; role: string; color: string }) {
  return (
    <div className="absolute -bottom-6 left-1/2 -translate-x-1/2 text-center whitespace-nowrap">
      <div className="text-[10px] font-bold" style={{ color }}>{name}</div>
      <div className="text-[8px] text-gray-500">{role}</div>
    </div>
  );
}

// ──────────────────────────────────────────────
// Status Indicator
// ──────────────────────────────────────────────

function StatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = {
    idle: "bg-gray-400",
    working: "bg-green-400",
    thinking: "bg-yellow-400",
    error: "bg-red-400",
  };

  const glows: Record<string, string> = {
    idle: "none",
    working: "0 0 8px rgba(74, 222, 128, 0.6)",
    thinking: "0 0 8px rgba(250, 204, 21, 0.6)",
    error: "0 0 8px rgba(239, 68, 68, 0.6)",
  };

  return (
    <motion.div
      className={`absolute -top-1 -right-1 w-3 h-3 rounded-full border-2 border-gray-900 ${colors[status] || colors.idle}`}
      animate={
        status === "working"
          ? { scale: [1, 1.3, 1], boxShadow: [glows.working, "0 0 12px rgba(74, 222, 128, 0.8)", glows.working] }
          : status === "error"
          ? { opacity: [1, 0.3, 1], boxShadow: [glows.error, "0 0 12px rgba(239, 68, 68, 0.8)", glows.error] }
          : status === "thinking"
          ? { boxShadow: [glows.thinking, "0 0 12px rgba(250, 204, 21, 0.8)", glows.thinking] }
          : {}
      }
      transition={{ repeat: Infinity, duration: status === "error" ? 0.5 : 1.5 }}
    />
  );
}

// ──────────────────────────────────────────────
// Celebration Sprite (เมื่อเทรดกำไร)
// ──────────────────────────────────────────────

function CelebrateSprite({ color }: { color: string }) {
  return (
    <div className="relative w-12 h-16">
      {/* Confetti */}
      {[...Array(8)].map((_, i) => (
        <motion.div
          key={i}
          className="absolute w-1 h-1 rounded-full"
          style={{
            background: ["#4ade80", "#facc15", "#ef4444", "#22d3ee", "#a78bfa", "#f97316", "#ec4899", "#14b8a6"][i],
            left: `${20 + Math.random() * 60}%`,
            top: "-10px",
          }}
          animate={{
            y: [0, -30 - Math.random() * 20, 10],
            x: [(Math.random() - 0.5) * 30, (Math.random() - 0.5) * 50],
            opacity: [1, 1, 0],
            rotate: [0, 360, 720],
          }}
          transition={{
            repeat: Infinity,
            duration: 2,
            delay: i * 0.15,
          }}
        />
      ))}
      {/* Head - bouncing */}
      <motion.div
        className="absolute top-0 left-1/2 -translate-x-1/2 w-8 h-8 rounded-full"
        style={{ background: color }}
        animate={{ y: [0, -8, 0] }}
        transition={{ repeat: Infinity, duration: 0.5 }}
      >
        {/* Eyes - happy */}
        <div className="absolute top-3 left-1.5 w-1.5 h-0.5 bg-white rounded-full transform rotate-12" />
        <div className="absolute top-3 right-1.5 w-1.5 h-0.5 bg-white rounded-full transform -rotate-12" />
        {/* Mouth - big smile */}
        <div className="absolute bottom-1 left-1/2 -translate-x-1/2 w-3 h-1.5 bg-white/70 rounded-b-full" />
      </motion.div>
      {/* Body - jumping */}
      <motion.div
        className="absolute bottom-0 left-1/2 -translate-x-1/2 w-10 h-8 rounded-t-lg"
        style={{ background: `linear-gradient(180deg, ${color}, ${color}dd)` }}
        animate={{ y: [0, -4, 0] }}
        transition={{ repeat: Infinity, duration: 0.5, delay: 0.05 }}
      >
        {/* Arms - raised */}
        <motion.div
          className="absolute -left-2 -top-2 w-2 h-4 rounded-full origin-bottom"
          style={{ background: color }}
          animate={{ rotate: [-30, -60, -30] }}
          transition={{ repeat: Infinity, duration: 0.5 }}
        />
        <motion.div
          className="absolute -right-2 -top-2 w-2 h-4 rounded-full origin-bottom"
          style={{ background: color }}
          animate={{ rotate: [30, 60, 30] }}
          transition={{ repeat: Infinity, duration: 0.5, delay: 0.1 }}
        />
      </motion.div>
    </div>
  );
}

// ──────────────────────────────────────────────
// Main Character Component
// ──────────────────────────────────────────────

interface IsometricCharacterProps {
  agent: AgentState;
  color: string;
  name: string;
  role: string;
}

export default function IsometricCharacter({ agent, color, name, role }: IsometricCharacterProps) {
  const status = agent.status || "idle";
  const mood = agent.avatar_mood || "neutral";
  const message = agent.bubble_message || "";
  const task = agent.current_task || "";

  const renderSprite = () => {
    switch (status) {
      case "working":
        return <WorkingSprite color={color} />;
      case "thinking":
        return <ThinkingSprite color={color} />;
      case "error":
        return <ErrorSprite color={color} />;
      case "celebrate":
        return <CelebrateSprite color={color} />;
      default:
        if (mood === "sleeping") return <SleepingSprite color={color} />;
        return <IdleSprite color={color} />;
    }
  };

  return (
    <div className="relative flex flex-col items-center">
      {/* Speech bubble */}
      <SpeechBubble
        message={status === "working" ? task : message}
        visible={status === "working" || status === "thinking" || !!message}
      />

      {/* Status dot */}
      <StatusDot status={status} />

      {/* Character sprite */}
      <motion.div
        className="relative"
        whileHover={{ scale: 1.1 }}
        transition={{ type: "spring", stiffness: 300 }}
      >
        {renderSprite()}
      </motion.div>

      {/* Name tag */}
      <NameTag name={name} role={role} color={color} />
    </div>
  );
}
