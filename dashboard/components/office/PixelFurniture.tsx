"use client";

import { motion } from "framer-motion";

// ──────────────────────────────────────────────
// Pixel Art Coffee Machine
// ──────────────────────────────────────────────

function CoffeeMachine({ x, y }: { x: number; y: number }) {
  return (
    <div className="absolute" style={{ left: `${x}%`, top: `${y}%` }}>
      <div className="relative w-6 h-8">
        {/* Machine body */}
        <div className="w-6 h-6 bg-gray-600 rounded-sm border border-gray-500">
          {/* Screen */}
          <motion.div
            className="absolute top-1 left-1 w-4 h-2 bg-green-900 rounded-sm"
            animate={{ opacity: [0.5, 1, 0.5] }}
            transition={{ repeat: Infinity, duration: 2 }}
          />
          {/* Cup slot */}
          <div className="absolute bottom-1 left-1.5 w-3 h-2 bg-gray-800 rounded-sm" />
        </div>
        {/* Steam */}
        <motion.div
          className="absolute -top-2 left-2 w-0.5 h-2 bg-white/30 rounded-full"
          animate={{ y: [0, -4, 0], opacity: [0.3, 0.6, 0.3] }}
          transition={{ repeat: Infinity, duration: 2 }}
        />
        <motion.div
          className="absolute -top-3 left-3 w-0.5 h-2 bg-white/20 rounded-full"
          animate={{ y: [0, -4, 0], opacity: [0.2, 0.4, 0.2] }}
          transition={{ repeat: Infinity, duration: 2, delay: 0.3 }}
        />
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────
// Pixel Art Whiteboard
// ──────────────────────────────────────────────

function Whiteboard({ x, y }: { x: number; y: number }) {
  return (
    <div className="absolute" style={{ left: `${x}%`, top: `${y}%` }}>
      <div className="relative w-12 h-8">
        {/* Board */}
        <div className="w-12 h-8 bg-white rounded-sm border-2 border-gray-400">
          {/* Content */}
          <div className="p-1">
            <motion.div
              className="w-6 h-0.5 bg-blue-400 rounded mb-0.5"
              animate={{ width: ["40%", "70%", "40%"] }}
              transition={{ repeat: Infinity, duration: 3 }}
            />
            <motion.div
              className="w-4 h-0.5 bg-red-400 rounded mb-0.5"
              animate={{ width: ["30%", "60%", "30%"] }}
              transition={{ repeat: Infinity, duration: 4 }}
            />
            <div className="w-8 h-0.5 bg-green-400 rounded" />
          </div>
        </div>
        {/* Marker tray */}
        <div className="absolute -bottom-1 left-2 right-2 h-1 bg-gray-500 rounded-sm">
          <div className="absolute left-1 w-1 h-0.5 bg-red-500 rounded" />
          <div className="absolute left-3 w-1 h-0.5 bg-blue-500 rounded" />
        </div>
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────
// Pixel Art Server Rack
// ──────────────────────────────────────────────

function ServerRack({ x, y }: { x: number; y: number }) {
  return (
    <div className="absolute" style={{ left: `${x}%`, top: `${y}%` }}>
      <div className="relative w-4 h-10">
        {/* Rack body */}
        <div className="w-4 h-10 bg-gray-700 rounded-sm border border-gray-600">
          {/* Server units */}
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="relative h-2 mx-0.5 mt-0.5 bg-gray-800 rounded-sm">
              {/* LEDs */}
              <motion.div
                className="absolute left-0.5 top-0.5 w-1 h-1 bg-green-400 rounded-full"
                animate={{ opacity: [1, 0.3, 1] }}
                transition={{ repeat: Infinity, duration: 1.5, delay: i * 0.3 }}
              />
              <motion.div
                className="absolute right-0.5 top-0.5 w-1 h-1 bg-blue-400 rounded-full"
                animate={{ opacity: [0.5, 1, 0.5] }}
                transition={{ repeat: Infinity, duration: 2, delay: i * 0.2 }}
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────
// Pixel Art Plant
// ──────────────────────────────────────────────

function PixelPlant({ x, y }: { x: number; y: number }) {
  return (
    <div className="absolute" style={{ left: `${x}%`, top: `${y}%` }}>
      <div className="relative w-4 h-8">
        {/* Pot */}
        <div className="absolute bottom-0 left-0.5 w-3 h-2 bg-amber-700 rounded-sm" />
        {/* Plant */}
        <motion.div
          className="absolute bottom-2 left-1 w-2 h-4"
          animate={{ rotate: [-2, 2, -2] }}
          transition={{ repeat: Infinity, duration: 4, ease: "easeInOut" }}
        >
          <div className="w-2 h-3 bg-green-500 rounded-full" />
          <div className="absolute -left-1 top-1 w-2 h-2 bg-green-400 rounded-full" />
          <div className="absolute -right-1 top-2 w-2 h-2 bg-green-600 rounded-full" />
        </motion.div>
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────
// Pixel Art Clock
// ──────────────────────────────────────────────

function PixelClock({ x, y }: { x: number; y: number }) {
  return (
    <div className="absolute" style={{ left: `${x}%`, top: `${y}%` }}>
      <div className="relative w-6 h-6">
        {/* Clock face */}
        <div className="w-6 h-6 bg-gray-800 rounded-full border-2 border-gray-600 flex items-center justify-center">
          {/* Hour markers */}
          {[0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330].map((deg) => (
            <div
              key={deg}
              className="absolute w-0.5 h-1 bg-gray-500"
              style={{
                transform: `rotate(${deg}deg)`,
                transformOrigin: "50% 12px",
                top: "2px",
              }}
            />
          ))}
          {/* Hour hand */}
          <motion.div
            className="absolute w-0.5 h-2 bg-white rounded-full origin-bottom"
            style={{ bottom: "50%", left: "calc(50% - 1px)" }}
            animate={{ rotate: [0, 360] }}
            transition={{ repeat: Infinity, duration: 43200, ease: "linear" }}
          />
          {/* Minute hand */}
          <motion.div
            className="absolute w-px h-2.5 bg-white/80 rounded-full origin-bottom"
            style={{ bottom: "50%", left: "calc(50% - 0.5px)" }}
            animate={{ rotate: [0, 360] }}
            transition={{ repeat: Infinity, duration: 3600, ease: "linear" }}
          />
          {/* Center dot */}
          <div className="absolute w-1 h-1 bg-red-500 rounded-full" />
        </div>
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────
// Export
// ──────────────────────────────────────────────

export { CoffeeMachine, Whiteboard, ServerRack, PixelPlant, PixelClock };
