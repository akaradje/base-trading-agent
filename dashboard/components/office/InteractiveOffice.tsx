"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { useAgents } from "@/lib/AgentContext";
import IsometricOffice from "./IsometricOffice";
import AgentDetailPanel from "./AgentDetailPanel";
import TradingMiniGame from "./TradingMiniGame";
import EasterEggs, { EasterEggHint } from "./EasterEggs";

// ──────────────────────────────────────────────
// Interactive Office — ห้องทำงานแบบ interactive
// ──────────────────────────────────────────────

export default function InteractiveOffice() {
  const { agents } = useAgents();
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [showMiniGame, setShowMiniGame] = useState(false);
  const [clickCount, setClickCount] = useState(0);
  const [showEasterEgg, setShowEasterEgg] = useState(false);

  // Agent config
  const agentConfig: Record<string, { name: string; role: string; color: string }> = {
    strategist: { name: "Jing", role: "Strategist", color: "#60a5fa" },
    analyst: { name: "Joe", role: "Analyst", color: "#4ade80" },
    critic: { name: "James", role: "RiskCritic", color: "#ef4444" },
    onchain: { name: "Jade", role: "OnChain", color: "#a78bfa" },
    risk: { name: "Jeed", role: "RiskMgr", color: "#facc15" },
    engine: { name: "Jai", role: "Engine", color: "#f97316" },
  };

  // Handle agent click
  const handleAgentClick = (agentId: string) => {
    setSelectedAgent(agentId);
    setClickCount((prev) => prev + 1);

    // Easter egg: 5 clicks on same agent
    if (clickCount >= 4) {
      setShowEasterEgg(true);
      setClickCount(0);
    }
  };

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // 'G' → Open mini-game
      if (e.key === "g" || e.key === "G") {
        setShowMiniGame(true);
      }
      // 'Escape' → Close all panels
      if (e.key === "Escape") {
        setSelectedAgent(null);
        setShowMiniGame(false);
      }
      // Number keys 1-6 → Select agent
      const agentIds = ["strategist", "analyst", "critic", "onchain", "risk", "engine"];
      const num = parseInt(e.key);
      if (num >= 1 && num <= 6) {
        setSelectedAgent(agentIds[num - 1]);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <div className="relative">
      {/* Main Office */}
      <IsometricOffice />

      {/* Interactive Overlay — Clickable Agent Areas */}
      <div className="absolute inset-0 pointer-events-none">
        {/* Agent click areas (positioned over desks) */}
        {Object.entries({
          strategist: { x: 25, y: 20 },
          analyst: { x: 75, y: 20 },
          onchain: { x: 15, y: 55 },
          critic: { x: 85, y: 55 },
          risk: { x: 35, y: 80 },
          engine: { x: 65, y: 80 },
        }).map(([agentId, pos]) => (
          <motion.button
            key={agentId}
            className="absolute pointer-events-auto cursor-pointer rounded-full"
            style={{
              left: `${pos.x}%`,
              top: `${pos.y}%`,
              transform: "translate(-50%, -50%)",
              width: 80,
              height: 80,
            }}
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => handleAgentClick(agentId)}
          />
        ))}
      </div>

      {/* Floating Action Buttons */}
      <div className="absolute bottom-4 right-4 flex flex-col gap-2 z-20">
        {/* Mini-game button */}
        <motion.button
          className="w-10 h-10 rounded-full bg-yellow-500/20 border border-yellow-500 text-yellow-400 flex items-center justify-center text-lg hover:bg-yellow-500/30 transition-colors"
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={() => setShowMiniGame(true)}
          title="Quick Trade Game (G)"
        >
          🎮
        </motion.button>

        {/* Keyboard shortcuts hint */}
        <motion.div
          className="w-10 h-10 rounded-full bg-gray-800/80 border border-gray-600 text-gray-400 flex items-center justify-center text-xs font-mono"
          whileHover={{ scale: 1.1 }}
          title="Keyboard Shortcuts: 1-6=Agents, G=Game, Esc=Close"
        >
          ?
        </motion.div>
      </div>

      {/* Agent Detail Panel */}
      {selectedAgent && agentConfig[selectedAgent] && (
        <AgentDetailPanel
          agent={agents[selectedAgent] || { agent_id: selectedAgent, status: "idle", avatar_mood: "neutral" }}
          agentId={selectedAgent}
          color={agentConfig[selectedAgent].color}
          name={agentConfig[selectedAgent].name}
          role={agentConfig[selectedAgent].role}
          visible={!!selectedAgent}
          onClose={() => setSelectedAgent(null)}
        />
      )}

      {/* Trading Mini-Game */}
      <TradingMiniGame
        visible={showMiniGame}
        onClose={() => setShowMiniGame(false)}
      />

      {/* Easter Eggs */}
      <EasterEggs />
      <EasterEggHint />

      {/* Easter Egg Notification */}
      {showEasterEgg && (
        <motion.div
          className="fixed top-4 left-1/2 -translate-x-1/2 z-50"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
        >
          <div className="bg-purple-500/20 border border-purple-500 rounded-lg px-4 py-2 text-sm text-purple-400">
            🎉 You found a secret! Try the Konami Code or press G for a mini-game!
            <button
              className="ml-2 text-purple-500 hover:text-purple-300"
              onClick={() => setShowEasterEgg(false)}
            >
              ✕
            </button>
          </div>
        </motion.div>
      )}
    </div>
  );
}
