import * as Phaser from "phaser";
import { BootScene } from "./scenes/BootScene";
import { PreloadScene } from "./scenes/PreloadScene";
import { OfficeScene } from "./scenes/OfficeScene";

export const TILE_SIZE = 32;

export const gameConfig: Phaser.Types.Core.GameConfig = {
  type: Phaser.AUTO,
  width: 1400,
  height: 600,
  parent: "phaser-container",
  pixelArt: true,
  roundPixels: true,
  backgroundColor: "#06060f",
  scale: {
    mode: Phaser.Scale.RESIZE,
    autoCenter: Phaser.Scale.CENTER_BOTH,
  },
  scene: [BootScene, PreloadScene, OfficeScene],
};
