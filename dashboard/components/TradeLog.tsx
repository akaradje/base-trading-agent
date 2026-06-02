"use client";

import { useTrades } from "@/lib/AgentContext";
import { motion, AnimatePresence } from "framer-motion";

export default function TradeLog() {
  const trades = useTrades();

  return (
    <div className="bg-gray-900/40 backdrop-blur-sm rounded-xl border border-gray-700/30 p-4 h-full overflow-hidden">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-bold text-gray-300 flex items-center gap-2 font-mono">
          📋 Recent Trades
        </h3>
        <span className="text-[9px] text-gray-500 bg-gray-800/50 px-2 py-0.5 rounded-full">
          {trades.length}
        </span>
      </div>

      <div className="space-y-1.5 overflow-y-auto max-h-[400px]">
        <AnimatePresence>
          {trades.length === 0 ? (
            <div className="text-[10px] text-gray-500 text-center py-12">
              <div className="text-2xl mb-2 opacity-30">📊</div>
              <div>No trades yet</div>
              <div className="text-gray-600 mt-1">Waiting for signals...</div>
            </div>
          ) : (
            trades.slice(0, 20).map((trade, i) => (
              <motion.div
                key={trade.id || `${trade.ts}-${i}`}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0 }}
                transition={{ delay: i * 0.03 }}
                className="flex items-center gap-2 text-[10px] p-2 rounded-lg bg-gray-800/30 hover:bg-gray-800/50 transition-colors group"
              >
                {/* Side indicator */}
                <div
                  className={`w-1.5 h-6 rounded-full ${
                    trade.side === "buy" ? "bg-green-400" : "bg-red-400"
                  }`}
                />

                {/* Symbol + Side */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="font-bold text-white">{trade.symbol}</span>
                    <span
                      className={`text-[8px] px-1 py-0.5 rounded ${
                        trade.side === "buy"
                          ? "bg-green-500/15 text-green-400"
                          : "bg-red-500/15 text-red-400"
                      }`}
                    >
                      {trade.side.toUpperCase()}
                    </span>
                  </div>
                  <div className="text-gray-500 text-[8px] truncate mt-0.5" title={trade.reason}>
                    {trade.reason}
                  </div>
                </div>

                {/* Price + Qty */}
                <div className="text-right">
                  <div className="text-gray-200 font-mono">
                    ${trade.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })}
                  </div>
                  <div className="text-gray-500 text-[8px]">
                    {trade.qty.toFixed(4)}
                  </div>
                </div>
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
