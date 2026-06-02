"use client";

import { useAgents } from "@/lib/AgentContext";
import { motion } from "framer-motion";
import IsometricDesk from "./IsometricDesk";
import { DustParticles, AmbientLights, ScanLine } from "./ParticleEffects";
import { CoffeeMachine, Whiteboard, ServerRack, PixelPlant, PixelClock } from "./PixelFurniture";
import WalkingAgent from "./WalkingAgent";

// Desk positions in the isometric office (percentage-based)
const DESK_POSITIONS: Record<string, { x: number; y: number }> = {
  strategist: { x: 25, y: 20 },  // Top-left area
  analyst:    { x: 75, y: 20 },  // Top-right area
  onchain:    { x: 15, y: 55 },  // Left side
  critic:     { x: 85, y: 55 },  // Right side
  risk:       { x: 35, y: 80 },  // Bottom-left
  engine:     { x: 65, y: 80 },  // Bottom-right
};

export default function IsometricOffice() {
  const { agents } = useAgents();

  // Check if any agent is working (for sparkle effects)
  const hasWorkingAgent = Object.values(agents).some(a => a.status === "working");

  return (
    <div className="relative w-full h-[500px] overflow-hidden rounded-xl border border-gray-700 bg-gradient-to-b from-gray-900 via-gray-800 to-gray-900">
      {/* Background grid */}
      <div className="absolute inset-0 opacity-10">
        <div
          className="w-full h-full"
          style={{
            backgroundImage: `
              linear-gradient(rgba(74, 222, 128, 0.3) 1px, transparent 1px),
              linear-gradient(90deg, rgba(74, 222, 128, 0.3) 1px, transparent 1px)
            `,
            backgroundSize: "40px 40px",
          }}
        />
      </div>

      {/* Phase 9: Ambient light orbs */}
      <AmbientLights />

      {/* Phase 9: Floating dust particles */}
      <DustParticles count={15} />

      {/* Phase 9: Scan line effect */}
      <ScanLine />

      {/* Office floor (isometric) */}
      <div
        className="absolute inset-10 border border-gray-700/30 rounded-lg"
        style={{
          background: "linear-gradient(135deg, rgba(30, 41, 59, 0.5), rgba(15, 23, 42, 0.5))",
        }}
      />

      {/* Office title */}
      <motion.div
        className="absolute top-4 left-1/2 -translate-x-1/2 z-20"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="bg-gray-800/80 backdrop-blur-sm border border-gray-600 rounded-lg px-4 py-2">
          <h3 className="text-xs font-bold text-gray-300 flex items-center gap-2">
            🏢 AI Agent Virtual Office
            <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
            {hasWorkingAgent && (
              <motion.span
                className="text-yellow-400"
                animate={{ opacity: [1, 0.5, 1] }}
                transition={{ repeat: Infinity, duration: 1 }}
              >
                ⚡
              </motion.span>
            )}
          </h3>
        </div>
      </motion.div>

      {/* Desks with characters */}
      {Object.entries(DESK_POSITIONS).map(([agentId, position]) => (
        <IsometricDesk
          key={agentId}
          agentId={agentId}
          agent={agents[agentId] || { agent_id: agentId, status: "idle", avatar_mood: "neutral" }}
          position={position}
        />
      ))}

      {/* Phase 9: Pixel Art Furniture */}
      <CoffeeMachine x={48} y={45} />
      <Whiteboard x={5} y={10} />
      <ServerRack x={92} y={15} />
      <PixelPlant x={3} y={40} />
      <PixelPlant x={95} y={75} />
      <PixelClock x={50} y={5} />

      {/* Phase 9: Walking Agent (เดินไปมาใน office) */}
      <WalkingAgent
        color="#4ade80"
        name="Joe"
        startX={10}
        endX={90}
        y={60}
        speed={0.8}
        direction="right"
      />

      {/* Connection lines between agents (pipeline visualization) */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none z-10">
        {/* Strategist → Analyst */}
        <motion.line
          x1="25%" y1="25%" x2="75%" y2="25%"
          stroke="#4ade80" strokeWidth="1" strokeDasharray="4 4"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1, strokeDashoffset: [0, -8] }}
          transition={{ repeat: Infinity, duration: 2, ease: "linear" }}
        />
        {/* Analyst → Critic */}
        <motion.line
          x1="75%" y1="30%" x2="85%" y2="50%"
          stroke="#ef4444" strokeWidth="1" strokeDasharray="4 4"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1, strokeDashoffset: [0, -8] }}
          transition={{ repeat: Infinity, duration: 2, ease: "linear", delay: 0.3 }}
        />
        {/* OnChain → Analyst */}
        <motion.line
          x1="20%" y1="55%" x2="70%" y2="25%"
          stroke="#a78bfa" strokeWidth="1" strokeDasharray="4 4"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1, strokeDashoffset: [0, -8] }}
          transition={{ repeat: Infinity, duration: 2, ease: "linear", delay: 0.6 }}
        />
        {/* Risk → Engine */}
        <motion.line
          x1="40%" y1="80%" x2="60%" y2="80%"
          stroke="#facc15" strokeWidth="1" strokeDasharray="4 4"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1, strokeDashoffset: [0, -8] }}
          transition={{ repeat: Infinity, duration: 2, ease: "linear", delay: 0.9 }}
        />

        {/* Phase 9: Animated data flow particles on connection lines */}
        {hasWorkingAgent && (
          <>
            <motion.circle
              r="3" fill="#4ade80"
              animate={{
                cx: ["25%", "75%"],
                cy: ["25%", "25%"],
                opacity: [0, 1, 0],
              }}
              transition={{ repeat: Infinity, duration: 2, ease: "linear" }}
            />
            <motion.circle
              r="3" fill="#ef4444"
              animate={{
                cx: ["75%", "85%"],
                cy: ["30%", "50%"],
                opacity: [0, 1, 0],
              }}
              transition={{ repeat: Infinity, duration: 2, ease: "linear", delay: 0.3 }}
            />
          </>
        )}
      </svg>

      {/* Bottom info bar */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-20">
        <div className="bg-gray-800/80 backdrop-blur-sm border border-gray-600 rounded-lg px-4 py-2 flex items-center gap-4 text-[10px] text-gray-400">
          <span>🟢 idle</span>
          <span>💻 working</span>
          <span>🤔 thinking</span>
          <span>🔴 error</span>
          <span>😴 sleeping</span>
        </div>
      </div>
    </div>
  );
}
