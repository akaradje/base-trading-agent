"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";

// ──────────────────────────────────────────────
// Floating Dust Particles
// ──────────────────────────────────────────────

interface Particle {
  id: number;
  x: number;
  y: number;
  size: number;
  duration: number;
  delay: number;
  opacity: number;
}

function DustParticles({ count = 20 }: { count?: number }) {
  const [particles, setParticles] = useState<Particle[]>([]);

  useEffect(() => {
    const p: Particle[] = [];
    for (let i = 0; i < count; i++) {
      p.push({
        id: i,
        x: Math.random() * 100,
        y: Math.random() * 100,
        size: Math.random() * 3 + 1,
        duration: Math.random() * 10 + 15,
        delay: Math.random() * 10,
        opacity: Math.random() * 0.3 + 0.1,
      });
    }
    setParticles(p);
  }, [count]);

  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden z-5">
      {particles.map((p) => (
        <motion.div
          key={p.id}
          className="absolute rounded-full bg-green-400/20"
          style={{
            left: `${p.x}%`,
            top: `${p.y}%`,
            width: p.size,
            height: p.size,
          }}
          animate={{
            y: [0, -30, -60, -30, 0],
            x: [0, 10, -10, 5, 0],
            opacity: [p.opacity, p.opacity * 2, p.opacity, p.opacity * 0.5, p.opacity],
          }}
          transition={{
            repeat: Infinity,
            duration: p.duration,
            delay: p.delay,
            ease: "easeInOut",
          }}
        />
      ))}
    </div>
  );
}

// ──────────────────────────────────────────────
// Sparkle Effects (เมื่อ agent ทำงาน)
// ──────────────────────────────────────────────

function Sparkles({ x, y, active }: { x: number; y: number; active: boolean }) {
  if (!active) return null;

  return (
    <div className="absolute pointer-events-none" style={{ left: `${x}%`, top: `${y}%` }}>
      {[...Array(6)].map((_, i) => (
        <motion.div
          key={i}
          className="absolute w-1 h-1 bg-yellow-400 rounded-full"
          animate={{
            scale: [0, 1, 0],
            opacity: [0, 1, 0],
            x: [0, (Math.random() - 0.5) * 40],
            y: [0, (Math.random() - 0.5) * 40],
          }}
          transition={{
            repeat: Infinity,
            duration: 1.5,
            delay: i * 0.2,
          }}
        />
      ))}
    </div>
  );
}

// ──────────────────────────────────────────────
// Ambient Light Orbs
// ──────────────────────────────────────────────

function AmbientLights() {
  const lights = [
    { x: 20, y: 30, color: "bg-blue-500", size: 40, duration: 8 },
    { x: 80, y: 60, color: "bg-purple-500", size: 35, duration: 10 },
    { x: 50, y: 80, color: "bg-green-500", size: 30, duration: 12 },
    { x: 15, y: 70, color: "bg-cyan-500", size: 25, duration: 9 },
  ];

  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden">
      {lights.map((light, i) => (
        <motion.div
          key={i}
          className={`absolute rounded-full ${light.color} blur-3xl`}
          style={{
            left: `${light.x}%`,
            top: `${light.y}%`,
            width: light.size,
            height: light.size,
          }}
          animate={{
            opacity: [0.05, 0.15, 0.05],
            scale: [1, 1.3, 1],
          }}
          transition={{
            repeat: Infinity,
            duration: light.duration,
            ease: "easeInOut",
          }}
        />
      ))}
    </div>
  );
}

// ──────────────────────────────────────────────
// Scan Line Effect
// ──────────────────────────────────────────────

function ScanLine() {
  return (
    <motion.div
      className="absolute left-0 right-0 h-px bg-green-400/10 pointer-events-none z-30"
      animate={{
        top: ["0%", "100%"],
      }}
      transition={{
        repeat: Infinity,
        duration: 8,
        ease: "linear",
      }}
    />
  );
}

// ──────────────────────────────────────────────
// Export
// ──────────────────────────────────────────────

export { DustParticles, Sparkles, AmbientLights, ScanLine };
