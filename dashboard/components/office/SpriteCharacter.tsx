"use client";

import { motion, AnimatePresence } from "framer-motion";
import { AgentState } from "@/lib/supabaseClient";

// ──────────────────────────────────────────────
// Pixel Art Sprite Sheet Generator (CSS-based)
// ──────────────────────────────────────────────

// Generate SVG sprite sheet for different character states
function generateSpriteSheet(color: string, state: string): string {
  const frames: string[] = [];

  switch (state) {
    case "idle":
      // 4 frames: breathing animation
      for (let i = 0; i < 4; i++) {
        const yOffset = i % 2 === 0 ? 0 : -1;
        frames.push(`
          <g transform="translate(${i * 32}, 0)">
            <!-- Head -->
            <circle cx="16" cy="${10 + yOffset}" r="8" fill="${color}"/>
            <circle cx="13" cy="${9 + yOffset}" r="1.5" fill="white"/>
            <circle cx="19" cy="${9 + yOffset}" r="1.5" fill="white"/>
            <rect x="13" y="${13 + yOffset}" width="6" height="1" rx="0.5" fill="white" opacity="0.5"/>
            <!-- Body -->
            <rect x="10" y="${18 + yOffset}" width="12" height="10" rx="2" fill="${color}" opacity="0.9"/>
            <!-- Arms -->
            <rect x="6" y="${19 + yOffset}" width="3" height="6" rx="1.5" fill="${color}"/>
            <rect x="23" y="${19 + yOffset}" width="3" height="6" rx="1.5" fill="${color}"/>
          </g>
        `);
      }
      break;

    case "working":
      // 4 frames: typing animation
      for (let i = 0; i < 4; i++) {
        const armAngle = i % 2 === 0 ? -15 : 15;
        frames.push(`
          <g transform="translate(${i * 32}, 0)">
            <!-- Head -->
            <circle cx="16" cy="10" r="8" fill="${color}"/>
            <rect cx="12" cy="9" width="2" height="2.5" rx="0.5" fill="white"/>
            <rect cx="18" cy="9" width="2" height="2.5" rx="0.5" fill="white"/>
            <!-- Glasses -->
            <rect x="10" y="8" width="12" height="4" rx="1" fill="none" stroke="white" stroke-width="0.5" opacity="0.4"/>
            <!-- Body -->
            <rect x="10" y="18" width="12" height="10" rx="2" fill="${color}" opacity="0.9"/>
            <!-- Arms typing -->
            <g transform="translate(6, 19) rotate(${armAngle}, 1.5, 0)">
              <rect x="0" y="0" width="3" height="6" rx="1.5" fill="${color}"/>
            </g>
            <g transform="translate(23, 19) rotate(${-armAngle}, 1.5, 0)">
              <rect x="0" y="0" width="3" height="6" rx="1.5" fill="${color}"/>
            </g>
            <!-- Monitor -->
            <rect x="28" y="20" width="8" height="6" rx="1" fill="#1e293b" stroke="#475569" stroke-width="0.5"/>
            <rect x="29" y="21" width="6" height="4" rx="0.5" fill="#0f172a"/>
            <!-- Code lines on monitor -->
            <rect x="29.5" y="22" width="${3 + i}" height="0.8" rx="0.4" fill="#4ade80" opacity="0.7"/>
            <rect x="29.5" y="23.2" width="${2 + (i % 3)}" height="0.8" rx="0.4" fill="#60a5fa" opacity="0.7"/>
          </g>
        `);
      }
      break;

    case "thinking":
      // 4 frames: head tilted + thought dots
      for (let i = 0; i < 4; i++) {
        const tilt = i % 2 === 0 ? -5 : 5;
        frames.push(`
          <g transform="translate(${i * 32}, 0)">
            <!-- Thought dots -->
            <circle cx="26" cy="${4 - i}" r="1" fill="white" opacity="${0.3 + i * 0.2}"/>
            <circle cx="28" cy="${2 - i}" r="1.5" fill="white" opacity="${0.2 + i * 0.15}"/>
            <!-- Head tilted -->
            <g transform="translate(16, 10) rotate(${tilt})">
              <circle cx="0" cy="0" r="8" fill="${color}"/>
              <circle cx="-3" cy="-1" r="1.5" fill="white"/>
              <circle cx="3" cy="-1" r="1.5" fill="white"/>
              <!-- Eyes looking up -->
              <circle cx="-3" cy="-2" r="0.8" fill="${color}"/>
              <circle cx="3" cy="-2" r="0.8" fill="${color}"/>
            </g>
            <!-- Body -->
            <rect x="10" y="18" width="12" height="10" rx="2" fill="${color}" opacity="0.9"/>
            <!-- Hand on chin -->
            <rect x="20" y="14" width="3" height="4" rx="1.5" fill="${color}"/>
          </g>
        `);
      }
      break;

    case "error":
      // 4 frames: shaking + exclamation
      for (let i = 0; i < 4; i++) {
        const shake = i % 2 === 0 ? -2 : 2;
        frames.push(`
          <g transform="translate(${i * 32}, 0)">
            <!-- Exclamation -->
            <rect x="14" y="0" width="4" height="8" rx="2" fill="#ef4444"/>
            <rect x="14" y="10" width="4" height="2" rx="1" fill="#ef4444"/>
            <!-- Head shaking -->
            <g transform="translate(${16 + shake}, 14)">
              <circle cx="0" cy="0" r="8" fill="${color}"/>
              <!-- Worried eyes -->
              <rect x="-4" y="-2" width="2.5" height="2" rx="0.5" fill="white"/>
              <rect x="1.5" y="-2" width="2.5" height="2" rx="0.5" fill="white"/>
              <!-- Open mouth -->
              <ellipse cx="0" cy="4" rx="2" ry="1.5" fill="white" opacity="0.7"/>
            </g>
            <!-- Body shaking -->
            <g transform="translate(${16 + shake * 0.5}, 24)">
              <rect x="-6" y="0" width="12" height="10" rx="2" fill="${color}" opacity="0.9"/>
            </g>
          </g>
        `);
      }
      break;

    case "sleeping":
      // 4 frames: drooping + Zzz
      for (let i = 0; i < 4; i++) {
        const droop = i * 2;
        frames.push(`
          <g transform="translate(${i * 32}, 0)">
            <!-- Zzz -->
            <text x="24" y="${6 - i}" font-size="6" fill="#93c5fd" opacity="${0.3 + i * 0.2}" font-weight="bold">Z</text>
            <text x="26" y="${3 - i}" font-size="4" fill="#93c5fd" opacity="${0.2 + i * 0.1}" font-weight="bold">z</text>
            <!-- Head drooping -->
            <g transform="translate(16, ${12 + droop})">
              <circle cx="0" cy="0" r="8" fill="${color}"/>
              <!-- Closed eyes -->
              <rect x="-4" y="-1" width="3" height="0.8" rx="0.4" fill="white"/>
              <rect x="1" y="-1" width="3" height="0.8" rx="0.4" fill="white"/>
            </g>
            <!-- Body slouching -->
            <g transform="translate(16, ${22 + droop}) rotate(${5 + i})">
              <rect x="-6" y="0" width="12" height="8" rx="2" fill="${color}" opacity="0.9"/>
            </g>
          </g>
        `);
      }
      break;

    case "celebrate":
      // 4 frames: jumping + confetti
      for (let i = 0; i < 4; i++) {
        const jumpY = i % 2 === 0 ? 0 : -4;
        const confettiColors = ["#4ade80", "#facc15", "#ef4444", "#22d3ee", "#a78bfa", "#f97316"];
        const confetti = confettiColors.map((c, j) => `
          <circle cx="${8 + j * 4}" cy="${2 + (i + j) % 4}" r="1" fill="${c}" opacity="${0.5 + ((i + j) % 3) * 0.2}"/>
        `).join("");
        frames.push(`
          <g transform="translate(${i * 32}, 0)">
            ${confetti}
            <!-- Head bouncing -->
            <g transform="translate(16, ${8 + jumpY})">
              <circle cx="0" cy="0" r="8" fill="${color}"/>
              <!-- Happy eyes -->
              <path d="M-4,-1 Q-3,-3 -2,-1" stroke="white" stroke-width="1.5" fill="none"/>
              <path d="M2,-1 Q3,-3 4,-1" stroke="white" stroke-width="1.5" fill="none"/>
              <!-- Big smile -->
              <path d="M-3,3 Q0,6 3,3" stroke="white" stroke-width="1" fill="none"/>
            </g>
            <!-- Body jumping -->
            <g transform="translate(16, ${18 + jumpY})">
              <rect x="-6" y="0" width="12" height="10" rx="2" fill="${color}" opacity="0.9"/>
              <!-- Arms raised -->
              <rect x="-9" y="-3" width="3" height="6" rx="1.5" fill="${color}" transform="rotate(-30, -7.5, 0)"/>
              <rect x="6" y="-3" width="3" height="6" rx="1.5" fill="${color}" transform="rotate(30, 7.5, 0)"/>
            </g>
          </g>
        `);
      }
      break;
  }

  return `data:image/svg+xml,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="${32 * frames.length}" height="32" viewBox="0 0 ${32 * frames.length} 32">${frames.join("")}</svg>`)}`;
}

// ──────────────────────────────────────────────
// Walk Cycle Sprite Sheet
// ──────────────────────────────────────────────

function generateWalkSheet(color: string): string {
  const frames: string[] = [];

  // 8 frames: walk cycle
  for (let i = 0; i < 8; i++) {
    const legAngle = Math.sin((i / 8) * Math.PI * 2) * 20;
    const armAngle = Math.sin((i / 8) * Math.PI * 2) * 15;
    const bodyY = Math.abs(Math.sin((i / 8) * Math.PI * 2)) * 2;

    frames.push(`
      <g transform="translate(${i * 32}, 0)">
        <!-- Head -->
        <circle cx="16" cy="${8 - bodyY}" r="8" fill="${color}"/>
        <circle cx="13" cy="${7 - bodyY}" r="1.5" fill="white"/>
        <circle cx="19" cy="${7 - bodyY}" r="1.5" fill="white"/>
        <!-- Body -->
        <rect x="10" y="${16 - bodyY}" width="12" height="10" rx="2" fill="${color}" opacity="0.9"/>
        <!-- Arms walking -->
        <g transform="translate(7, ${17 - bodyY}) rotate(${armAngle}, 1.5, 0)">
          <rect x="0" y="0" width="3" height="6" rx="1.5" fill="${color}"/>
        </g>
        <g transform="translate(22, ${17 - bodyY}) rotate(${-armAngle}, 1.5, 0)">
          <rect x="0" y="0" width="3" height="6" rx="1.5" fill="${color}"/>
        </g>
        <!-- Legs walking -->
        <g transform="translate(12, ${26 - bodyY}) rotate(${legAngle}, 0, 0)">
          <rect x="0" y="0" width="3" height="6" rx="1.5" fill="${color}" opacity="0.8"/>
        </g>
        <g transform="translate(17, ${26 - bodyY}) rotate(${-legAngle}, 0, 0)">
          <rect x="0" y="0" width="3" height="6" rx="1.5" fill="${color}" opacity="0.8"/>
        </g>
      </g>
    `);
  }

  return `data:image/svg+xml,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="${32 * 8}" height="32" viewBox="0 0 ${32 * 8} 32">${frames.join("")}</svg>`)}`;
}

// ──────────────────────────────────────────────
// Sprite Sheet CSS Animation Component
// ──────────────────────────────────────────────

interface SpriteSheetProps {
  color: string;
  state: string;
  size?: number;
}

function SpriteSheet({ color, state, size = 64 }: SpriteSheetProps) {
  const spriteUrl = generateSpriteSheet(color, state);
  const frameCount = 4;
  const frameWidth = size;
  const totalWidth = frameWidth * frameCount;

  // Animation speed varies by state
  const durations: Record<string, number> = {
    idle: 2,
    working: 0.6,
    thinking: 1.5,
    error: 0.2,
    sleeping: 3,
    celebrate: 0.4,
  };

  const duration = durations[state] || 1;

  return (
    <div
      className="relative"
      style={{
        width: frameWidth,
        height: size,
        backgroundImage: `url("${spriteUrl}")`,
        backgroundSize: `${totalWidth}px ${size}px`,
        backgroundRepeat: "no-repeat",
        animation: `${state}-walk ${duration}s steps(${frameCount}) infinite`,
        imageRendering: "pixelated",
      }}
    />
  );
}

// ──────────────────────────────────────────────
// Walk Cycle Component
// ──────────────────────────────────────────────

interface WalkCycleProps {
  color: string;
  direction?: "left" | "right";
  speed?: number;
}

function WalkCycle({ color, direction = "right", speed = 1 }: WalkCycleProps) {
  const spriteUrl = generateWalkSheet(color);
  const frameCount = 8;
  const size = 64;
  const frameWidth = size;
  const totalWidth = frameWidth * frameCount;

  return (
    <motion.div
      className="relative"
      style={{
        width: frameWidth,
        height: size,
        backgroundImage: `url("${spriteUrl}")`,
        backgroundSize: `${totalWidth}px ${size}px`,
        backgroundRepeat: "no-repeat",
        animation: `walk-cycle ${0.8 / speed}s steps(${frameCount}) infinite`,
        imageRendering: "pixelated",
        transform: direction === "left" ? "scaleX(-1)" : "none",
      }}
      animate={{
        x: direction === "right" ? [0, 100] : [100, 0],
      }}
      transition={{
        repeat: Infinity,
        duration: 4 / speed,
        ease: "linear",
      }}
    />
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
// Status Indicator with Glow
// ──────────────────────────────────────────────

function StatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = {
    idle: "bg-gray-400",
    working: "bg-green-400",
    thinking: "bg-yellow-400",
    error: "bg-red-400",
    celebrate: "bg-yellow-400",
  };

  const glows: Record<string, string> = {
    idle: "none",
    working: "0 0 8px rgba(74, 222, 128, 0.6)",
    thinking: "0 0 8px rgba(250, 204, 21, 0.6)",
    error: "0 0 8px rgba(239, 68, 68, 0.6)",
    celebrate: "0 0 8px rgba(250, 204, 21, 0.6)",
  };

  return (
    <motion.div
      className={`absolute -top-1 -right-1 w-3 h-3 rounded-full border-2 border-gray-900 ${colors[status] || colors.idle}`}
      animate={{
        scale: status === "working" || status === "celebrate" ? [1, 1.3, 1] : 1,
        boxShadow: [glows[status] || "none", "0 0 12px rgba(255,255,255,0.3)", glows[status] || "none"],
        opacity: status === "error" ? [1, 0.3, 1] : 1,
      }}
      transition={{ repeat: Infinity, duration: status === "error" ? 0.5 : 1.5 }}
    />
  );
}

// ──────────────────────────────────────────────
// Main Sprite Character Component
// ──────────────────────────────────────────────

interface SpriteCharacterProps {
  agent: AgentState;
  color: string;
  name: string;
  role: string;
}

export default function SpriteCharacter({ agent, color, name, role }: SpriteCharacterProps) {
  const status = agent.status || "idle";
  const mood = agent.avatar_mood || "neutral";
  const message = agent.bubble_message || "";
  const task = agent.current_task || "";

  const currentState = mood === "sleeping" ? "sleeping" : status;

  return (
    <div className="relative flex flex-col items-center">
      {/* Speech bubble */}
      <SpeechBubble
        message={status === "working" ? task : message}
        visible={status === "working" || status === "thinking" || !!message}
      />

      {/* Status dot */}
      <StatusDot status={status} />

      {/* Sprite sheet character */}
      <motion.div
        className="relative"
        whileHover={{ scale: 1.1 }}
        transition={{ type: "spring", stiffness: 300 }}
      >
        <SpriteSheet color={color} state={currentState} size={64} />
      </motion.div>

      {/* Name tag */}
      <NameTag name={name} role={role} color={color} />
    </div>
  );
}

// ──────────────────────────────────────────────
// CSS Keyframes (add to globals.css)
// ──────────────────────────────────────────────

export const spriteKeyframes = `
@keyframes idle-walk {
  from { background-position: 0 0; }
  to { background-position: -256px 0; }
}

@keyframes working-walk {
  from { background-position: 0 0; }
  to { background-position: -256px 0; }
}

@keyframes thinking-walk {
  from { background-position: 0 0; }
  to { background-position: -256px 0; }
}

@keyframes error-walk {
  from { background-position: 0 0; }
  to { background-position: -256px 0; }
}

@keyframes sleeping-walk {
  from { background-position: 0 0; }
  to { background-position: -256px 0; }
}

@keyframes celebrate-walk {
  from { background-position: 0 0; }
  to { background-position: -256px 0; }
}

@keyframes walk-cycle {
  from { background-position: 0 0; }
  to { background-position: -512px 0; }
}
`;
