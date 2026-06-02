"use client";

import { usePortfolio } from "@/lib/AgentContext";
import { motion } from "framer-motion";

export default function PortfolioPanel() {
  const portfolio = usePortfolio();

  const equity = portfolio?.equity || 10000;
  const cash = portfolio?.cash || 10000;
  const pnl = portfolio?.pnl_pct || 0;
  const positions = portfolio?.positions || 0;
  const tradesToday = portfolio?.trades_today || 0;

  return (
    <motion.div
      className="flex items-center gap-4 bg-gray-900/40 backdrop-blur-sm rounded-xl px-4 py-2 border border-gray-700/30"
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
    >
      {/* Equity */}
      <div className="text-center">
        <div className="text-[8px] text-gray-500 tracking-wider">EQUITY</div>
        <div className="text-xs font-bold text-white font-mono">
          ${equity.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </div>
      </div>

      <div className="w-px h-6 bg-gray-700/50" />

      {/* PnL */}
      <div className="text-center">
        <div className="text-[8px] text-gray-500 tracking-wider">P&L</div>
        <div className={`text-xs font-bold font-mono ${pnl >= 0 ? "text-green-400" : "text-red-400"}`}>
          {pnl >= 0 ? "+" : ""}{(pnl * 100).toFixed(2)}%
        </div>
      </div>

      <div className="w-px h-6 bg-gray-700/50" />

      {/* Cash */}
      <div className="text-center">
        <div className="text-[8px] text-gray-500 tracking-wider">CASH</div>
        <div className="text-xs font-bold text-blue-400 font-mono">
          ${cash.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
        </div>
      </div>

      <div className="w-px h-6 bg-gray-700/50" />

      {/* Positions */}
      <div className="text-center">
        <div className="text-[8px] text-gray-500 tracking-wider">POS</div>
        <div className="text-xs font-bold text-yellow-400 font-mono">{positions}</div>
      </div>

      <div className="w-px h-6 bg-gray-700/50" />

      {/* Trades today */}
      <div className="text-center">
        <div className="text-[8px] text-gray-500 tracking-wider">TODAY</div>
        <div className="text-xs font-bold text-purple-400 font-mono">{tradesToday}</div>
      </div>
    </motion.div>
  );
}
