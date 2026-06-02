"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AgentProvider, useAgents } from "@/lib/AgentContext";
import PhaserGame from "@/components/PhaserGame";
import AgentStatusBar from "@/components/office/AgentStatusBar";
import ChatBox from "@/components/chat/ChatBox";
import TokenUsageChart from "@/components/analytics/TokenUsageChart";
import TradePerformance from "@/components/analytics/TradePerformance";
import AgentActivityTimeline from "@/components/analytics/AgentActivityTimeline";
import CostTracker from "@/components/analytics/CostTracker";
import PortfolioPanel from "@/components/PortfolioPanel";
import TradeLog from "@/components/TradeLog";
import StatusIndicator from "@/components/StatusIndicator";

function DashboardContent() {
  const { connected, lastUpdate, agents } = useAgents();
  const [showChat, setShowChat] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);

  const workingCount = Object.values(agents).filter((a) => a.status === "working").length;
  const thinkingCount = Object.values(agents).filter((a) => a.status === "thinking").length;
  const idleCount = Object.values(agents).filter((a) => a.status === "idle").length;

  return (
    <div className="min-h-screen bg-[#06060f] text-gray-200">
      {/* Ambient background */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute inset-0 bg-gradient-to-b from-blue-950/10 via-transparent to-purple-950/10" />
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-blue-500/3 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-purple-500/3 rounded-full blur-3xl" />
      </div>

      {/* Header */}
      <header className="relative z-50 border-b border-gray-800/50 bg-gray-950/60 backdrop-blur-xl">
        <div className="max-w-[1600px] mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <motion.div
              className="text-3xl"
              animate={{ rotate: [0, 5, -5, 0] }}
              transition={{ repeat: Infinity, duration: 4, ease: "easeInOut" }}
            >
              🤖
            </motion.div>
            <div>
              <h1 className="text-sm font-bold tracking-wider bg-gradient-to-r from-blue-400 via-purple-400 to-green-400 bg-clip-text text-transparent">
                BASE TRADING AGENT
              </h1>
              <p className="text-[10px] text-gray-500 tracking-wide">AI War Room — Live Trading Dashboard</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Quick stats */}
            <div className="hidden md:flex items-center gap-4 mr-4 text-[10px]">
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                <span className="text-gray-400">{workingCount} active</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-yellow-400" />
                <span className="text-gray-400">{thinkingCount} thinking</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-gray-500" />
                <span className="text-gray-400">{idleCount} idle</span>
              </div>
            </div>

            {/* Action buttons */}
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setShowChat(!showChat)}
              className={`px-3 py-1.5 rounded-lg text-xs border transition-all duration-200 ${
                showChat
                  ? "bg-blue-500/20 border-blue-400/50 text-blue-300 shadow-lg shadow-blue-500/10"
                  : "bg-gray-800/40 border-gray-700/50 text-gray-400 hover:text-blue-300 hover:border-blue-500/30"
              }`}
            >
              💬 Chat
            </motion.button>

            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setShowAnalytics(!showAnalytics)}
              className={`px-3 py-1.5 rounded-lg text-xs border transition-all duration-200 ${
                showAnalytics
                  ? "bg-purple-500/20 border-purple-400/50 text-purple-300 shadow-lg shadow-purple-500/10"
                  : "bg-gray-800/40 border-gray-700/50 text-gray-400 hover:text-purple-300 hover:border-purple-500/30"
              }`}
            >
              📊 Analytics
            </motion.button>

            <div className="w-px h-6 bg-gray-700/50 mx-1" />

            <StatusIndicator connected={connected} lastUpdate={lastUpdate} />
            <PortfolioPanel />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="relative z-10 max-w-[1600px] mx-auto px-6 py-6">
        {/* Phaser 3 Virtual Office */}
        <motion.section
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="mb-4"
        >
          <PhaserGame />
        </motion.section>

        {/* Agent Status Bar */}
        <motion.section
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.5 }}
          className="mb-6"
        >
          <AgentStatusBar />
        </motion.section>

        {/* Analytics Dashboard */}
        <AnimatePresence>
          {showAnalytics && (
            <motion.section
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.4 }}
              className="mb-6 overflow-hidden"
            >
              <h2 className="text-xs text-gray-400 mb-3 flex items-center gap-2 font-mono tracking-wider">
                <span className="w-2 h-2 rounded-full bg-purple-400 animate-pulse" />
                ANALYTICS DASHBOARD
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                <TokenUsageChart />
                <TradePerformance />
                <AgentActivityTimeline />
                <CostTracker />
              </div>
            </motion.section>
          )}
        </AnimatePresence>

        {/* Bottom panels */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Pipeline Flow */}
          <motion.section
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3, duration: 0.5 }}
            className="lg:col-span-2"
          >
            <h2 className="text-xs text-gray-400 mb-3 flex items-center gap-2 font-mono tracking-wider">
              <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
              PIPELINE FLOW
            </h2>
            <div className="bg-gray-900/40 backdrop-blur-sm rounded-xl border border-gray-700/30 p-5">
              {/* Pipeline steps */}
              <div className="flex items-center justify-center gap-1.5 text-[10px] text-gray-400 flex-wrap">
                {[
                  { emoji: "📊", label: "Prices", color: "blue" },
                  { emoji: "⚠️", label: "Risk", color: "yellow" },
                  { emoji: "🧭", label: "Strategist", color: "blue" },
                  { emoji: "🔗", label: "OnChain", color: "purple" },
                  { emoji: "📊", label: "Analyst", color: "green" },
                  { emoji: "🛡️", label: "Critic", color: "red" },
                  { emoji: "⚡", label: "Execute", color: "orange" },
                ].map((step, i) => (
                  <div key={i} className="flex items-center gap-1.5">
                    <motion.span
                      className={`px-2.5 py-1 bg-${step.color}-900/30 rounded-md border border-${step.color}-700/30`}
                      whileHover={{ scale: 1.05, borderColor: `var(--color-${step.color}-500)` }}
                    >
                      {step.emoji} {step.label}
                    </motion.span>
                    {i < 6 && <span className="text-gray-600 text-lg">→</span>}
                  </div>
                ))}
              </div>

              {/* Agent status summary */}
              <div className="mt-5 pt-4 border-t border-gray-800/50">
                <div className="grid grid-cols-3 gap-6 text-center">
                  <motion.div whileHover={{ y: -2 }}>
                    <div className="text-[9px] text-gray-500 tracking-wider">ACTIVE</div>
                    <div className="text-2xl font-bold text-green-400 mt-1">{workingCount}</div>
                  </motion.div>
                  <motion.div whileHover={{ y: -2 }}>
                    <div className="text-[9px] text-gray-500 tracking-wider">THINKING</div>
                    <div className="text-2xl font-bold text-yellow-400 mt-1">{thinkingCount}</div>
                  </motion.div>
                  <motion.div whileHover={{ y: -2 }}>
                    <div className="text-[9px] text-gray-500 tracking-wider">IDLE</div>
                    <div className="text-2xl font-bold text-gray-400 mt-1">{idleCount}</div>
                  </motion.div>
                </div>
              </div>
            </div>
          </motion.section>

          {/* Trade Log */}
          <motion.section
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.4, duration: 0.5 }}
          >
            <h2 className="text-xs text-gray-400 mb-3 flex items-center gap-2 font-mono tracking-wider">
              <span className="w-2 h-2 rounded-full bg-yellow-400 animate-pulse" />
              TRADE LOG
            </h2>
            <TradeLog />
          </motion.section>
        </div>
      </main>

      {/* Chat Box */}
      <ChatBox visible={showChat} onClose={() => setShowChat(false)} />

      {/* Footer */}
      <footer className="relative z-10 border-t border-gray-800/30 mt-12 py-4">
        <div className="max-w-[1600px] mx-auto px-6 flex items-center justify-between text-[10px] text-gray-600">
          <span>Base Trading Agent v0.2 — Phaser 3 + Chat + Analytics</span>
          <span>Paper Trading Mode — All decisions are simulated</span>
        </div>
      </footer>
    </div>
  );
}

export default function Dashboard() {
  return (
    <AgentProvider>
      <DashboardContent />
    </AgentProvider>
  );
}
