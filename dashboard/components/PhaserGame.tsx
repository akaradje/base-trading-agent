"use client";

import { useEffect, useRef } from "react";
import { EventBus } from "@/lib/EventBus";

export default function PhaserGame() {
  const containerRef = useRef<HTMLDivElement>(null);
  const gameRef = useRef<any>(null);

  useEffect(() => {
    if (gameRef.current) return;

    const init = async () => {
      const PhaserLib = await import("phaser");
      const Phaser = PhaserLib.default || PhaserLib;
      const { gameConfig } = await import("@/phaser/config");

      const config = {
        ...gameConfig,
        parent: containerRef.current,
        width: containerRef.current?.clientWidth || 1200,
        height: 600,
      };

      const game = new Phaser.Game(config);
      gameRef.current = game;
      EventBus.setGame(game);
    };

    init();

    return () => {
      if (gameRef.current) {
        gameRef.current.destroy(true);
        gameRef.current = null;
        EventBus.setGame(null);
      }
    };
  }, []);

  return (
    <div
      ref={containerRef}
      id="phaser-container"
      className="w-full rounded-xl overflow-hidden border border-gray-700/50 shadow-2xl shadow-blue-500/5"
      style={{ height: 600 }}
    />
  );
}
