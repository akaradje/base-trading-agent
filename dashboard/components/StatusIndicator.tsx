"use client";

import { motion } from "framer-motion";

interface StatusIndicatorProps {
  connected: boolean;
  lastUpdate: string | null;
}

export default function StatusIndicator({ connected, lastUpdate }: StatusIndicatorProps) {
  const timeAgo = lastUpdate
    ? Math.floor((Date.now() - new Date(lastUpdate).getTime()) / 1000)
    : null;

  return (
    <div className="flex items-center gap-2 text-xs">
      {/* Connection dot */}
      <motion.div
        className={`w-2 h-2 rounded-full ${connected ? "bg-green-400" : "bg-red-400"}`}
        animate={connected ? { opacity: [1, 0.5, 1] } : {}}
        transition={{ repeat: Infinity, duration: 2 }}
      />

      {/* Status text */}
      <span className={connected ? "text-green-400" : "text-red-400"}>
        {connected ? "LIVE" : "OFFLINE"}
      </span>

      {/* Last update */}
      {timeAgo !== null && (
        <span className="text-gray-500">
          ({timeAgo < 60 ? `${timeAgo}s ago` : `${Math.floor(timeAgo / 60)}m ago`})
        </span>
      )}
    </div>
  );
}
