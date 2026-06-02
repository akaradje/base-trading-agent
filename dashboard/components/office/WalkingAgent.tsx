"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";

// ──────────────────────────────────────────────
// Walking Agent Animation
// Agent เดินไปมาใน office
// ──────────────────────────────────────────────

interface WalkingAgentProps {
  color: string;
  name: string;
  startX?: number;
  endX?: number;
  y?: number;
  speed?: number;
  direction?: "left" | "right";
}

export default function WalkingAgent({
  color,
  name,
  startX = 0,
  endX = 100,
  y = 50,
  speed = 1,
  direction = "right",
}: WalkingAgentProps) {
  const [isWalking, setIsWalking] = useState(true);

  // Generate walk cycle sprite sheet inline
  const generateWalkSprite = () => {
    const frames: string[] = [];
    for (let i = 0; i < 8; i++) {
      const legAngle = Math.sin((i / 8) * Math.PI * 2) * 20;
      const armAngle = Math.sin((i / 8) * Math.PI * 2) * 15;
      const bodyY = Math.abs(Math.sin((i / 8) * Math.PI * 2)) * 2;

      frames.push(`
        <g transform="translate(${i * 32}, 0)">
          <circle cx="16" cy="${8 - bodyY}" r="8" fill="${color}"/>
          <circle cx="13" cy="${7 - bodyY}" r="1.5" fill="white"/>
          <circle cx="19" cy="${7 - bodyY}" r="1.5" fill="white"/>
          <rect x="10" y="${16 - bodyY}" width="12" height="10" rx="2" fill="${color}" opacity="0.9"/>
          <g transform="translate(7, ${17 - bodyY}) rotate(${armAngle}, 1.5, 0)">
            <rect x="0" y="0" width="3" height="6" rx="1.5" fill="${color}"/>
          </g>
          <g transform="translate(22, ${17 - bodyY}) rotate(${-armAngle}, 1.5, 0)">
            <rect x="0" y="0" width="3" height="6" rx="1.5" fill="${color}"/>
          </g>
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
  };

  const spriteUrl = generateWalkSprite();

  return (
    <motion.div
      className="absolute pointer-events-none z-15"
      style={{
        top: `${y}%`,
        left: direction === "right" ? `${startX}%` : `${endX}%`,
      }}
      animate={{
        left: direction === "right" ? [`${startX}%`, `${endX}%`] : [`${endX}%`, `${startX}%`],
      }}
      transition={{
        repeat: Infinity,
        duration: 10 / speed,
        ease: "linear",
        repeatDelay: 3,
      }}
    >
      {/* Walk cycle sprite */}
      <div
        className="w-8 h-8"
        style={{
          backgroundImage: `url("${spriteUrl}")`,
          backgroundSize: "256px 32px",
          backgroundRepeat: "no-repeat",
          animation: `walk-cycle ${0.8 / speed}s steps(8) infinite`,
          imageRendering: "pixelated",
          transform: direction === "left" ? "scaleX(-1)" : "none",
        }}
      />

      {/* Name tag floating */}
      <motion.div
        className="absolute -top-4 left-1/2 -translate-x-1/2 text-[8px] font-bold whitespace-nowrap"
        style={{ color }}
        animate={{ y: [0, -2, 0] }}
        transition={{ repeat: Infinity, duration: 1 }}
      >
        {name}
      </motion.div>
    </motion.div>
  );
}
