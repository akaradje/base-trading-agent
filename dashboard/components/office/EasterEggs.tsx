"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect, useCallback } from "react";

// ──────────────────────────────────────────────
// Easter Eggs — Easter eggs สำหรับ office
// ──────────────────────────────────────────────

// Konami Code Easter Egg
function useKonamiCode(callback: () => void) {
  const [sequence, setSequence] = useState<string[]>([]);
  const konamiCode = [
    "ArrowUp", "ArrowUp", "ArrowDown", "ArrowDown",
    "ArrowLeft", "ArrowRight", "ArrowLeft", "ArrowRight",
    "b", "a",
  ];

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      setSequence((prev) => {
        const next = [...prev, e.key].slice(-10);
        if (next.join(",") === konamiCode.join(",")) {
          callback();
          return [];
        }
        return next;
      });
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [callback]);
}

// ──────────────────────────────────────────────
// Matrix Rain Easter Egg
// ──────────────────────────────────────────────

function MatrixRain({ visible, onClose }: { visible: boolean; onClose: () => void }) {
  const [columns, setColumns] = useState<string[][]>([]);

  useEffect(() => {
    if (!visible) return;

    const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789@#$%^&*()";
    const cols = 30;
    const rows = 20;

    const initial: string[][] = [];
    for (let i = 0; i < cols; i++) {
      const col: string[] = [];
      for (let j = 0; j < rows; j++) {
        col.push(chars[Math.floor(Math.random() * chars.length)]);
      }
      initial.push(col);
    }
    setColumns(initial);

    const interval = setInterval(() => {
      setColumns((prev) =>
        prev.map((col) => {
          const newCol = [...col];
          newCol.pop();
          newCol.unshift(chars[Math.floor(Math.random() * chars.length)]);
          return newCol;
        })
      );
    }, 100);

    return () => clearInterval(interval);
  }, [visible]);

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          className="fixed inset-0 z-[100] bg-black/90 flex items-center justify-center cursor-pointer"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        >
          <div className="absolute inset-0 overflow-hidden opacity-30">
            {columns.map((col, i) => (
              <div
                key={i}
                className="absolute top-0 text-green-400 text-xs font-mono"
                style={{ left: `${(i / columns.length) * 100}%` }}
              >
                {col.map((char, j) => (
                  <motion.div
                    key={j}
                    animate={{ opacity: [0, 1, 0] }}
                    transition={{ duration: 2, delay: j * 0.1 }}
                  >
                    {char}
                  </motion.div>
                ))}
              </div>
            ))}
          </div>
          <motion.div
            className="relative text-center"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", stiffness: 200 }}
          >
            <h2 className="text-4xl font-bold text-green-400 mb-4">🎮 KONAMI CODE!</h2>
            <p className="text-green-300">You found the secret!</p>
            <p className="text-green-500 text-sm mt-2">Click anywhere to exit</p>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// ──────────────────────────────────────────────
// Party Mode Easter Egg
// ──────────────────────────────────────────────

function PartyMode({ visible, onClose }: { visible: boolean; onClose: () => void }) {
  const [confetti, setConfetti] = useState<{ id: number; x: number; y: number; color: string; rotation: number }[]>([]);

  useEffect(() => {
    if (!visible) return;

    const colors = ["#4ade80", "#facc15", "#ef4444", "#22d3ee", "#a78bfa", "#f97316", "#ec4899"];
    const particles: typeof confetti = [];

    for (let i = 0; i < 100; i++) {
      particles.push({
        id: i,
        x: Math.random() * 100,
        y: -10 - Math.random() * 100,
        color: colors[Math.floor(Math.random() * colors.length)],
        rotation: Math.random() * 360,
      });
    }
    setConfetti(particles);

    const timeout = setTimeout(onClose, 5000);
    return () => clearTimeout(timeout);
  }, [visible, onClose]);

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          className="fixed inset-0 z-[100] pointer-events-none"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          {confetti.map((c) => (
            <motion.div
              key={c.id}
              className="absolute w-3 h-3 rounded-sm"
              style={{
                left: `${c.x}%`,
                top: `${c.y}%`,
                background: c.color,
                rotate: c.rotation,
              }}
              animate={{
                y: ["0%", "120%"],
                x: [0, (Math.random() - 0.5) * 200],
                rotate: [c.rotation, c.rotation + 720],
                opacity: [1, 1, 0],
              }}
              transition={{
                duration: 3 + Math.random() * 2,
                delay: Math.random() * 2,
                ease: "easeIn",
              }}
            />
          ))}
          <motion.div
            className="absolute inset-0 flex items-center justify-center"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", stiffness: 200, delay: 0.5 }}
          >
            <h2 className="text-6xl font-bold text-white drop-shadow-lg">🎉 PARTY MODE! 🎉</h2>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// ──────────────────────────────────────────────
// Click Counter Easter Egg
// ──────────────────────────────────────────────

function useClickCounter(threshold: number, callback: () => void) {
  const [clicks, setClicks] = useState(0);

  useEffect(() => {
    const handleClick = () => {
      setClicks((prev) => {
        const next = prev + 1;
        if (next >= threshold) {
          callback();
          return 0;
        }
        return next;
      });

      // Reset after 3 seconds of no clicks
      const timeout = setTimeout(() => setClicks(0), 3000);
      return () => clearTimeout(timeout);
    };

    window.addEventListener("click", handleClick);
    return () => window.removeEventListener("click", handleClick);
  }, [threshold, callback]);
}

// ──────────────────────────────────────────────
// Main Easter Eggs Provider
// ──────────────────────────────────────────────

export default function EasterEggs() {
  const [showMatrix, setShowMatrix] = useState(false);
  const [showParty, setShowParty] = useState(false);

  // Konami Code → Matrix Rain
  useKonamiCode(() => setShowMatrix(true));

  // 10 rapid clicks → Party Mode
  useClickCounter(10, () => setShowParty(true));

  return (
    <>
      <MatrixRain visible={showMatrix} onClose={() => setShowMatrix(false)} />
      <PartyMode visible={showParty} onClose={() => setShowParty(false)} />
    </>
  );
}

// ──────────────────────────────────────────────
// Hint Component
// ──────────────────────────────────────────────

export function EasterEggHint() {
  const [showHint, setShowHint] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setShowHint(true), 30000); // Show after 30 seconds
    return () => clearTimeout(timer);
  }, []);

  if (!showHint) return null;

  return (
    <motion.div
      className="fixed bottom-4 right-4 z-50"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
    >
      <div className="bg-gray-800/90 backdrop-blur-sm border border-gray-600 rounded-lg px-4 py-2 text-xs text-gray-400">
        <span className="text-yellow-400">💡</span> Try the Konami Code or click 10 times fast!
        <button
          className="ml-2 text-gray-500 hover:text-white"
          onClick={() => setShowHint(false)}
        >
          ✕
        </button>
      </div>
    </motion.div>
  );
}
