"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect, useCallback } from "react";

// ──────────────────────────────────────────────
// Trading Mini-Game — เกมเทรดเร็ว
// ──────────────────────────────────────────────

interface TradingMiniGameProps {
  visible: boolean;
  onClose: () => void;
}

type Direction = "up" | "down";

export default function TradingMiniGame({ visible, onClose }: TradingMiniGameProps) {
  const [price, setPrice] = useState(100);
  const [balance, setBalance] = useState(1000);
  const [position, setPosition] = useState<{ side: Direction; entry: number; size: number } | null>(null);
  const [history, setHistory] = useState<number[]>([100]);
  const [gameOver, setGameOver] = useState(false);
  const [score, setScore] = useState(0);
  const [round, setRound] = useState(0);
  const maxRounds = 10;

  // Generate random price movement
  useEffect(() => {
    if (!visible || gameOver) return;

    const interval = setInterval(() => {
      setPrice((prev) => {
        const change = (Math.random() - 0.48) * 5; // Slight upward bias
        const newPrice = Math.max(50, Math.min(200, prev + change));
        setHistory((h) => [...h.slice(-20), newPrice]);
        return newPrice;
      });
    }, 500);

    return () => clearInterval(interval);
  }, [visible, gameOver]);

  // Check position P&L
  useEffect(() => {
    if (!position) return;

    const pnl =
      position.side === "up"
        ? (price - position.entry) * position.size
        : (position.entry - price) * position.size;

    // Auto close if big loss
    if (pnl < -50) {
      closePosition();
    }
  }, [price, position]);

  const openPosition = (side: Direction) => {
    if (position || gameOver) return;
    const size = Math.min(100, balance * 0.1);
    setPosition({ side, entry: price, size: size / price });
    setRound((r) => r + 1);
  };

  const closePosition = useCallback(() => {
    if (!position) return;

    const pnl =
      position.side === "up"
        ? (price - position.entry) * position.size
        : (position.entry - price) * position.size;

    setBalance((b) => b + pnl);
    setScore((s) => s + (pnl > 0 ? 1 : 0));
    setPosition(null);

    if (round >= maxRounds) {
      setGameOver(true);
    }
  }, [position, price, round]);

  const resetGame = () => {
    setPrice(100);
    setBalance(1000);
    setPosition(null);
    setHistory([100]);
    setGameOver(false);
    setScore(0);
    setRound(0);
  };

  // Draw mini chart
  const drawChart = () => {
    if (history.length < 2) return null;

    const min = Math.min(...history);
    const max = Math.max(...history);
    const range = max - min || 1;

    const points = history
      .map((p, i) => {
        const x = (i / (history.length - 1)) * 280;
        const y = 80 - ((p - min) / range) * 70;
        return `${x},${y}`;
      })
      .join(" ");

    const lastPrice = history[history.length - 1];
    const isUp = lastPrice >= history[0];

    return (
      <svg width="280" height="80" className="mx-auto">
        <polyline
          points={points}
          fill="none"
          stroke={isUp ? "#4ade80" : "#ef4444"}
          strokeWidth="2"
        />
        {/* Current price dot */}
        <circle
          cx={280}
          cy={80 - ((lastPrice - min) / range) * 70}
          r="3"
          fill={isUp ? "#4ade80" : "#ef4444"}
        />
      </svg>
    );
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
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

          <motion.div
            className="relative w-96 max-w-[90vw] rounded-xl border-2 border-yellow-500 overflow-hidden"
            style={{
              background: "linear-gradient(135deg, #1a1a2e, #16213e)",
              boxShadow: "0 0 30px rgba(250, 204, 21, 0.3)",
            }}
            initial={{ scale: 0.8, y: 20 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.8, y: 20 }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="p-4 bg-yellow-500/20 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-yellow-400">🎮 Quick Trade</h3>
                <p className="text-xs text-gray-400">Round {round}/{maxRounds}</p>
              </div>
              <button
                className="text-gray-400 hover:text-white transition-colors"
                onClick={onClose}
              >
                ✕
              </button>
            </div>

            <div className="p-4 space-y-4">
              {gameOver ? (
                /* Game Over Screen */
                <div className="text-center space-y-4">
                  <motion.div
                    className="text-4xl"
                    animate={{ scale: [1, 1.2, 1] }}
                    transition={{ repeat: Infinity, duration: 1 }}
                  >
                    {score >= 7 ? "🏆" : score >= 4 ? "🎯" : "😅"}
                  </motion.div>
                  <h4 className="text-xl font-bold">
                    {score >= 7 ? "Master Trader!" : score >= 4 ? "Not Bad!" : "Keep Learning!"}
                  </h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-3 bg-gray-800/50 rounded-lg text-center">
                      <div className="text-2xl font-bold text-green-400">{score}</div>
                      <div className="text-xs text-gray-400">Wins</div>
                    </div>
                    <div className="p-3 bg-gray-800/50 rounded-lg text-center">
                      <div className="text-2xl font-bold" style={{ color: balance >= 1000 ? "#4ade80" : "#ef4444" }}>
                        ${balance.toFixed(0)}
                      </div>
                      <div className="text-xs text-gray-400">Balance</div>
                    </div>
                  </div>
                  <button
                    className="w-full py-2 bg-yellow-500 text-black rounded-lg font-bold hover:bg-yellow-400 transition-colors"
                    onClick={resetGame}
                  >
                    Play Again
                  </button>
                </div>
              ) : (
                /* Game Screen */
                <>
                  {/* Price Display */}
                  <div className="text-center">
                    <div className="text-3xl font-bold" style={{ color: price >= 100 ? "#4ade80" : "#ef4444" }}>
                      ${price.toFixed(2)}
                    </div>
                    <div className="text-xs text-gray-400">
                      {price >= history[0] ? "📈" : "📉"} {(price - history[0]).toFixed(2)}
                    </div>
                  </div>

                  {/* Chart */}
                  <div className="bg-gray-800/50 rounded-lg p-2">
                    {drawChart()}
                  </div>

                  {/* Position Info */}
                  {position && (
                    <motion.div
                      className="p-3 bg-gray-800/50 rounded-lg"
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                    >
                      <div className="flex justify-between items-center">
                        <span className="text-sm">
                          {position.side === "up" ? "🟢 LONG" : "🔴 SHORT"} @ ${position.entry.toFixed(2)}
                        </span>
                        <span
                          className="font-bold"
                          style={{
                            color:
                              position.side === "up"
                                ? price >= position.entry ? "#4ade80" : "#ef4444"
                                : price <= position.entry ? "#4ade80" : "#ef4444",
                          }}
                        >
                          {position.side === "up"
                            ? ((price - position.entry) * position.size).toFixed(2)
                            : ((position.entry - price) * position.size).toFixed(2)}
                        </span>
                      </div>
                    </motion.div>
                  )}

                  {/* Action Buttons */}
                  <div className="grid grid-cols-2 gap-3">
                    {!position ? (
                      <>
                        <button
                          className="py-3 bg-green-500/20 border border-green-500 text-green-400 rounded-lg font-bold hover:bg-green-500/30 transition-colors"
                          onClick={() => openPosition("up")}
                        >
                          📈 LONG
                        </button>
                        <button
                          className="py-3 bg-red-500/20 border border-red-500 text-red-400 rounded-lg font-bold hover:bg-red-500/30 transition-colors"
                          onClick={() => openPosition("down")}
                        >
                          📉 SHORT
                        </button>
                      </>
                    ) : (
                      <button
                        className="col-span-2 py-3 bg-yellow-500/20 border border-yellow-500 text-yellow-400 rounded-lg font-bold hover:bg-yellow-500/30 transition-colors"
                        onClick={closePosition}
                      >
                        ⚡ CLOSE POSITION
                      </button>
                    )}
                  </div>

                  {/* Balance */}
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-gray-400">Balance</span>
                    <span className="font-bold">${balance.toFixed(2)}</span>
                  </div>
                </>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
