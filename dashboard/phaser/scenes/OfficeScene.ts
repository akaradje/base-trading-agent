import * as Phaser from "phaser";
import { EventBus, EVENTS } from "../../lib/EventBus";
import { AGENT_COLORS, AGENT_IDS } from "./PreloadScene";

const T = 32; // tile size

// ─── Room definitions ──────────────────────────────────
interface RoomDef {
  id: string; name: string;
  x: number; y: number; w: number; h: number;
  color: number;
  spots: { x: number; y: number }[];
  doorX: number; doorY: number;
}

const ROOMS: RoomDef[] = [
  {
    id: "war", name: "War Room", x: 2, y: 2, w: 16, h: 10, color: 0x16213e,
    spots: [
      { x: 4, y: 4 }, { x: 8, y: 4 }, { x: 12, y: 4 },
      { x: 4, y: 8 }, { x: 8, y: 8 }, { x: 12, y: 8 },
    ],
    doorX: 18, doorY: 7,
  },
  {
    id: "strategy", name: "Strategy Room", x: 22, y: 2, w: 10, h: 7, color: 0x1a1a3e,
    spots: [{ x: 25, y: 5 }, { x: 28, y: 5 }],
    doorX: 22, doorY: 5,
  },
  {
    id: "risk", name: "Risk Room", x: 22, y: 12, w: 10, h: 7, color: 0x2a1a1a,
    spots: [{ x: 25, y: 15 }, { x: 28, y: 15 }],
    doorX: 22, doorY: 15,
  },
  {
    id: "datacenter", name: "Data Center", x: 2, y: 15, w: 10, h: 6, color: 0x0f1a2e,
    spots: [{ x: 5, y: 17 }, { x: 8, y: 17 }],
    doorX: 12, doorY: 17,
  },
  {
    id: "meeting", name: "Meeting Room", x: 15, y: 15, w: 6, h: 6, color: 0x1a2e1a,
    spots: [{ x: 17, y: 17 }, { x: 19, y: 17 }],
    doorX: 18, doorY: 15,
  },
];

// Agent → initial desk position in War Room (tile coords)
const DESK_LAYOUT: Record<string, { tx: number; ty: number }> = {
  strategist: { tx: 3, ty: 3 },
  analyst:    { tx: 7, ty: 3 },
  onchain:    { tx: 11, ty: 3 },
  critic:     { tx: 3, ty: 7 },
  risk:       { tx: 7, ty: 7 },
  engine:     { tx: 11, ty: 7 },
};

// Corridor nodes for pathfinding
const CORRIDORS: Record<string, { x: number; y: number; edges: string[] }> = {
  hub:        { x: 18, y: 10, edges: ["war_door", "strat_door", "risk_door", "data_door", "meet_door"] },
  war_door:   { x: 18, y: 7,  edges: ["hub"] },
  strat_door: { x: 22, y: 5,  edges: ["hub"] },
  risk_door:  { x: 22, y: 15, edges: ["hub"] },
  data_door:  { x: 12, y: 17, edges: ["hub"] },
  meet_door:  { x: 18, y: 15, edges: ["hub"] },
};

// ─── Agent state ───────────────────────────────────────
interface AgentSprite {
  id: string;
  sprite: Phaser.GameObjects.Sprite;
  label: Phaser.GameObjects.Text;
  statusBg: Phaser.GameObjects.Graphics;
  bubble: Phaser.GameObjects.Container | null;
  currentRoom: string;
  status: string;
  targetX: number;
  targetY: number;
  isMoving: boolean;
}

export class OfficeScene extends Phaser.Scene {
  private agents: Map<string, AgentSprite> = new Map();
  private decorations: Phaser.GameObjects.GameObject[] = [];
  private particleEmitters: Phaser.GameObjects.Particles.ParticleEmitter[] = [];
  private statusUpdateInterval = 0;

  constructor() {
    super({ key: "OfficeScene" });
  }

  create() {
    this.cameras.main.setBackgroundColor("#06060f");

    // Draw everything
    this.drawOffice();
    this.placeFurniture();
    this.spawnAgents();
    this.addAmbientEffects();
    this.setupCamera();
    this.setupEventBus();

    // Periodic updates
    this.time.addEvent({ delay: 300, callback: this.tick, callbackScope: this, loop: true });

    // Random agent idle behaviors
    this.time.addEvent({ delay: 5000, callback: this.randomBehavior, callbackScope: this, loop: true });

    EventBus.emit(EVENTS.SCENE_READY);
  }

  // ─── Office rendering ───────────────────────────────
  private drawOffice() {
    const g = this.add.graphics().setDepth(0);

    // Subtle grid background
    g.lineStyle(1, 0x0d1117, 0.4);
    for (let x = 0; x < 36; x++) {
      g.lineBetween(x * T, 0, x * T, 24 * T);
    }
    for (let y = 0; y < 24; y++) {
      g.lineBetween(0, y * T, 36 * T, y * T);
    }

    // Draw rooms
    ROOMS.forEach((room) => {
      const rx = room.x * T;
      const ry = room.y * T;
      const rw = room.w * T;
      const rh = room.h * T;

      // Floor
      g.fillStyle(room.color, 0.7);
      g.fillRect(rx, ry, rw, rh);

      // Floor pattern (subtle tiles)
      g.lineStyle(1, 0xffffff, 0.03);
      for (let tx = room.x; tx < room.x + room.w; tx++) {
        g.lineBetween(tx * T, ry, tx * T, ry + rh);
      }
      for (let ty = room.y; ty < room.y + room.h; ty++) {
        g.lineBetween(rx, ty * T, rx + rw, ty * T);
      }

      // Walls
      g.lineStyle(2, 0x334155, 0.9);
      g.strokeRect(rx, ry, rw, rh);

      // Door opening
      g.fillStyle(0x0a0a14, 1);
      g.fillRect(room.doorX * T, room.doorY * T, T, T);

      // Room label
      this.add.text(rx + 8, ry + 4, room.name, {
        fontSize: "9px", fontFamily: '"Press Start 2P", monospace', color: "#475569",
      }).setDepth(1);
    });

    // Corridor lines
    g.lineStyle(2, 0x1e293b, 0.4);
    Object.entries(CORRIDORS).forEach(([id, node]) => {
      node.edges.forEach((targetId) => {
        const target = CORRIDORS[targetId];
        if (target && id < targetId) {
          g.lineBetween(node.x * T + T / 2, node.y * T + T / 2, target.x * T + T / 2, target.y * T + T / 2);
        }
      });
    });
  }

  // ─── Furniture placement ────────────────────────────
  private placeFurniture() {
    const warRoom = ROOMS[0];

    // Desks with monitors in War Room
    Object.entries(DESK_LAYOUT).forEach(([agentId, pos]) => {
      const dx = (warRoom.x + pos.tx) * T;
      const dy = (warRoom.y + pos.ty) * T;
      const info = AGENT_COLORS[agentId];
      const colorHex = "#" + info.color.toString(16).padStart(6, "0");

      // Desk
      const desk = this.add.image(dx + T, dy + T / 2, "desk").setDepth(dy + 1);

      // Color accent strip on desk
      const accent = this.add.graphics().setDepth(dy + 2);
      accent.fillStyle(info.color, 0.4);
      accent.fillRect(dx + T - 2, dy + 2, 4, 4);

      // Agent name plate on desk
      this.add.text(dx + T, dy + T - 2, info.name, {
        fontSize: "7px", fontFamily: "monospace", color: colorHex,
      }).setOrigin(0.5, 0).setDepth(dy + 2);
    });

    // Coffee machine
    this.add.image(16 * T + T / 2, 4 * T + T / 2, "coffee").setDepth(4 * T);

    // Whiteboard
    this.add.image(5 * T + T, 2 * T + T / 2, "whiteboard").setDepth(2 * T - 1);

    // Server rack in Data Center
    const dc = ROOMS[3];
    this.add.image((dc.x + 2) * T, (dc.y + 2) * T, "server").setDepth((dc.y + 2) * T);
    this.add.image((dc.x + 4) * T, (dc.y + 2) * T, "server").setDepth((dc.y + 2) * T);

    // Plants
    const plantPositions = [
      [19 * T, 3 * T], [19 * T, 10 * T], [14 * T, 16 * T], [21 * T, 16 * T],
    ];
    plantPositions.forEach(([px, py]) => {
      this.add.image(px, py, "plant").setDepth(py);
    });

    // Chart screens on walls
    this.add.image(8 * T, 2 * T + 4, "chart-screen").setDepth(2 * T - 1);
    this.add.image(26 * T, 2 * T + 4, "chart-screen").setDepth(2 * T - 1);

    // Chairs
    Object.entries(DESK_LAYOUT).forEach(([, pos]) => {
      const dx = (warRoom.x + pos.tx) * T;
      const dy = (warRoom.y + pos.ty + 1) * T;
      this.add.image(dx + T, dy, "chair").setDepth(dy);
    });
  }

  // ─── Agent spawning ─────────────────────────────────
  private spawnAgents() {
    const warRoom = ROOMS[0];

    AGENT_IDS.forEach((id) => {
      const pos = DESK_LAYOUT[id];
      const info = AGENT_COLORS[id];
      const px = (warRoom.x + pos.tx + 1) * T;
      const py = (warRoom.y + pos.ty) * T + 12;
      const colorHex = "#" + info.color.toString(16).padStart(6, "0");

      // Sprite
      const sprite = this.add.sprite(px, py, `char-${id}`);
      sprite.setOrigin(0.5, 1);
      sprite.setDepth(py);
      sprite.play(`char-${id}-idle`);
      sprite.setInteractive({ useHandCursor: true, hitArea: new Phaser.Geom.Rectangle(-16, -48, 32, 48), hitAreaCallback: Phaser.Geom.Rectangle.Contains });

      // Status glow background
      const statusBg = this.add.graphics().setDepth(py - 1);
      this.drawStatusGlow(statusBg, px, py, info.color, 0);

      // Name label
      const label = this.add.text(px, py + 4, info.name, {
        fontSize: "8px", fontFamily: '"Press Start 2P", monospace',
        color: colorHex, align: "center",
      }).setOrigin(0.5, 0).setDepth(1000);

      // Interaction
      sprite.on("pointerdown", () => EventBus.emit(EVENTS.AGENT_CLICKED, id));
      sprite.on("pointerover", () => { sprite.setScale(1.1); });
      sprite.on("pointerout", () => { sprite.setScale(1); });

      this.agents.set(id, {
        id, sprite, label, statusBg, bubble: null,
        currentRoom: "War Room", status: "idle",
        targetX: px, targetY: py, isMoving: false,
      });
    });
  }

  private drawStatusGlow(g: Phaser.GameObjects.Graphics, x: number, y: number, color: number, alpha: number) {
    g.clear();
    if (alpha <= 0) return;
    g.fillStyle(color, alpha * 0.15);
    g.fillCircle(x, y - 20, 20);
    g.fillStyle(color, alpha * 0.08);
    g.fillCircle(x, y - 20, 30);
  }

  // ─── Ambient effects ────────────────────────────────
  private addAmbientEffects() {
    // Floating particles (data flow)
    const particles = this.add.particles(0, 0, undefined as any, {
      x: { min: 0, max: 36 * T },
      y: { min: 0, max: 24 * T },
      lifespan: 4000,
      speed: { min: 5, max: 15 },
      scale: { start: 0.3, end: 0 },
      alpha: { start: 0.2, end: 0 },
      tint: [0x4ade80, 0x60a5fa, 0xa78bfa],
      frequency: 200,
    });
    particles.setDepth(5000);

    // Scan line
    const scanLine = this.add.rectangle(0, 0, 36 * T, 1, 0x4ade80, 0.06).setDepth(5001);
    this.tweens.add({
      targets: scanLine,
      y: 24 * T,
      duration: 6000,
      repeat: -1,
      ease: "Linear",
    });

    // Ambient light orbs
    const orbColors = [0x4ade80, 0x60a5fa, 0xa78bfa, 0xf97316];
    for (let i = 0; i < 4; i++) {
      const orb = this.add.circle(
        200 + Math.random() * 800,
        100 + Math.random() * 500,
        40 + Math.random() * 30,
        orbColors[i], 0.03
      ).setDepth(0);
      this.tweens.add({
        targets: orb,
        alpha: { from: 0.02, to: 0.06 },
        scale: { from: 0.9, to: 1.1 },
        duration: 3000 + Math.random() * 2000,
        yoyo: true, repeat: -1,
        ease: "Sine.easeInOut",
      });
    }
  }

  // ─── Camera ─────────────────────────────────────────
  private setupCamera() {
    const cam = this.cameras.main;
    cam.setBounds(0, 0, 36 * T, 24 * T);
    cam.setZoom(1.3);
    cam.centerOn(12 * T, 8 * T);

    let isDragging = false;
    let lastX = 0;
    let lastY = 0;

    this.input.on("pointerdown", (p: Phaser.Input.Pointer) => {
      if (p.button === 0 && !this.agents.has(this.getAgentAt(p.worldX, p.worldY)?.id || "")) {
        isDragging = true;
        lastX = p.x;
        lastY = p.y;
      }
    });

    this.input.on("pointermove", (p: Phaser.Input.Pointer) => {
      if (isDragging) {
        cam.scrollX -= (p.x - lastX) / cam.zoom;
        cam.scrollY -= (p.y - lastY) / cam.zoom;
        lastX = p.x;
        lastY = p.y;
      }
    });

    this.input.on("pointerup", () => { isDragging = false; });

    this.input.on("wheel", (_p: any, _gx: any, _gy: any, _gz: any, dy: number) => {
      cam.setZoom(Phaser.Math.Clamp(cam.zoom - dy * 0.001, 0.6, 2.5));
    });
  }

  private getAgentAt(wx: number, wy: number): AgentSprite | undefined {
    let found: AgentSprite | undefined;
    this.agents.forEach((agent) => {
      if (found) return;
      const dx = Math.abs(wx - agent.sprite.x);
      const dy = Math.abs(wy - (agent.sprite.y - 24));
      if (dx < 20 && dy < 30) found = agent;
    });
    return found;
  }

  // ─── EventBus (React → Phaser) ─────────────────────
  private setupEventBus() {
    EventBus.on(EVENTS.AGENT_STATUS_CHANGED, (id: string, status: string) => {
      const agent = this.agents.get(id);
      if (!agent) return;
      agent.status = status;
      this.updateAgentVisual(agent);
    });

    EventBus.on(EVENTS.AGENT_BUBBLE, (id: string, text: string) => {
      this.showBubble(id, text);
    });

    EventBus.on(EVENTS.AGENT_MOVE, (id: string, roomName: string) => {
      this.moveAgentToRoom(id, roomName);
    });

    EventBus.on(EVENTS.CAMERA_FOCUS, (id: string) => {
      const agent = this.agents.get(id);
      if (agent) {
        this.cameras.main.pan(agent.sprite.x, agent.sprite.y - 20, 600, "Sine.easeInOut");
      }
    });
  }

  // ─── Agent visual update ────────────────────────────
  private updateAgentVisual(agent: AgentSprite) {
    const key = `char-${agent.id}`;
    const info = AGENT_COLORS[agent.id];
    const colorHex = "#" + info.color.toString(16).padStart(6, "0");

    // Play the right animation
    const animMap: Record<string, string> = {
      idle: `${key}-idle`,
      working: `${key}-work`,
      thinking: `${key}-think`,
      error: `${key}-idle`,
      celebrate: `${key}-celebrate`,
    };
    const animKey = animMap[agent.status] || `${key}-idle`;

    if (agent.sprite.anims.currentAnim?.key !== animKey) {
      agent.sprite.play(animKey, true);
    }

    // Tint based on status
    switch (agent.status) {
      case "working":
        agent.sprite.clearTint();
        agent.label.setColor("#4ade80");
        break;
      case "thinking":
        agent.sprite.setTint(0xffffdd);
        agent.label.setColor("#facc15");
        break;
      case "error":
        agent.sprite.setTint(0xffaaaa);
        agent.label.setColor("#ef4444");
        // Shake effect
        this.tweens.add({
          targets: agent.sprite,
          x: agent.sprite.x + 2,
          duration: 50, yoyo: true, repeat: 3,
          onComplete: () => { agent.sprite.x = agent.targetX; },
        });
        break;
      case "celebrate":
        agent.sprite.clearTint();
        agent.label.setColor("#a78bfa");
        break;
      default:
        agent.sprite.clearTint();
        agent.label.setColor(colorHex);
    }

    // Status glow
    const glowAlpha = agent.status === "working" ? 0.6 : agent.status === "thinking" ? 0.4 : 0.1;
    this.drawStatusGlow(agent.statusBg, agent.sprite.x, agent.sprite.y, info.color, glowAlpha);
  }

  // ─── Speech bubbles ─────────────────────────────────
  private showBubble(agentId: string, text: string) {
    const agent = this.agents.get(agentId);
    if (!agent) return;

    if (agent.bubble) { agent.bubble.destroy(); agent.bubble = null; }

    const info = AGENT_COLORS[agentId];
    const container = this.add.container(agent.sprite.x, agent.sprite.y - 58);

    const maxW = 160;
    const tObj = this.add.text(0, 0, text.slice(0, 100), {
      fontSize: "8px", fontFamily: "monospace", color: "#e2e8f0",
      wordWrap: { width: maxW - 12 },
    }).setOrigin(0.5, 0.5);

    const bw = Math.max(tObj.width + 12, 50);
    const bh = tObj.height + 10;

    const bg = this.add.graphics();
    bg.fillStyle(0x0f172a, 0.95);
    bg.fillRoundedRect(-bw / 2, -bh / 2, bw, bh, 5);
    bg.lineStyle(1, info.color, 0.7);
    bg.strokeRoundedRect(-bw / 2, -bh / 2, bw, bh, 5);

    const tail = this.add.graphics();
    tail.fillStyle(0x0f172a, 0.95);
    tail.fillTriangle(-3, bh / 2, 3, bh / 2, 0, bh / 2 + 5);

    container.add([bg, tObj, tail]);
    container.setDepth(3000).setAlpha(0);

    this.tweens.add({ targets: container, alpha: 1, y: agent.sprite.y - 62, duration: 200 });

    this.time.delayedCall(4000, () => {
      this.tweens.add({
        targets: container, alpha: 0, duration: 300,
        onComplete: () => { container.destroy(); if (agent.bubble === container) agent.bubble = null; },
      });
    });

    agent.bubble = container;
  }

  // ─── Agent movement ─────────────────────────────────
  private moveAgentToRoom(agentId: string, roomName: string) {
    const agent = this.agents.get(agentId);
    if (!agent || agent.isMoving) return;

    const room = ROOMS.find((r) => r.name === roomName);
    if (!room) return;

    // Find available spot
    const spotIdx = Math.floor(Math.random() * room.spots.length);
    const spot = room.spots[spotIdx];
    const targetX = spot.x * T + T / 2;
    const targetY = spot.y * T + 12;

    agent.isMoving = true;
    agent.targetX = targetX;
    agent.targetY = targetY;

    // Walk animation
    agent.sprite.play(`char-${agentId}-walk`, true);

    // Face direction
    if (targetX < agent.sprite.x) agent.sprite.setFlipX(true);
    else agent.sprite.setFlipX(false);

    // Calculate path via corridors
    const path = this.findPath(agent.currentRoom, roomName);
    this.walkPath(agent, path, targetX, targetY, roomName);
  }

  private findPath(fromRoom: string, toRoom: string): { x: number; y: number }[] {
    // Simple: go to war_door → hub → target_door → room
    const fromDoor = ROOMS.find((r) => r.name === fromRoom)?.doorX;
    const toDoor = ROOMS.find((r) => r.name === toRoom);
    if (!toDoor) return [];

    const hub = CORRIDORS.hub;
    return [
      { x: (fromDoor || 18) * T + T / 2, y: 7 * T + T / 2 },
      { x: hub.x * T + T / 2, y: hub.y * T + T / 2 },
      { x: toDoor.doorX * T + T / 2, y: toDoor.doorY * T + T / 2 },
    ];
  }

  private walkPath(agent: AgentSprite, path: { x: number; y: number }[], finalX: number, finalY: number, roomName: string) {
    if (path.length === 0) {
      // Walk directly to final position
      this.tweens.add({
        targets: [agent.sprite],
        x: finalX, y: finalY,
        duration: Phaser.Math.Distance.Between(agent.sprite.x, agent.sprite.y, finalX, finalY) / 0.06,
        ease: "Linear",
        onUpdate: () => {
          agent.label.x = agent.sprite.x;
          agent.label.y = agent.sprite.y + 4;
          agent.sprite.setDepth(agent.sprite.y);
          agent.label.setDepth(agent.sprite.y + 1);
        },
        onComplete: () => {
          agent.sprite.play(`char-${agent.id}-idle`, true);
          agent.sprite.setFlipX(false);
          agent.currentRoom = roomName;
          agent.isMoving = false;
        },
      });
      return;
    }

    const next = path[0];
    const remaining = path.slice(1);

    if (next.x < agent.sprite.x) agent.sprite.setFlipX(true);
    else if (next.x > agent.sprite.x) agent.sprite.setFlipX(false);

    const dist = Phaser.Math.Distance.Between(agent.sprite.x, agent.sprite.y, next.x, next.y);

    this.tweens.add({
      targets: [agent.sprite],
      x: next.x, y: next.y,
      duration: dist / 0.06,
      ease: "Linear",
      onUpdate: () => {
        agent.label.x = agent.sprite.x;
        agent.label.y = agent.sprite.y + 4;
        agent.sprite.setDepth(agent.sprite.y);
        agent.label.setDepth(agent.sprite.y + 1);
      },
      onComplete: () => {
        this.walkPath(agent, remaining, finalX, finalY, roomName);
      },
    });
  }

  // ─── Random idle behaviors ──────────────────────────
  private randomBehavior() {
    this.agents.forEach((agent) => {
      if (agent.isMoving) return;

      // Random small movement when idle
      if (agent.status === "idle" && Math.random() < 0.15) {
        const dx = (Math.random() - 0.5) * 20;
        const dy = (Math.random() - 0.5) * 10;
        this.tweens.add({
          targets: agent.sprite,
          x: agent.targetX + dx,
          y: agent.targetY + dy,
          duration: 1000,
          ease: "Sine.easeInOut",
          yoyo: true,
          onUpdate: () => {
            agent.label.x = agent.sprite.x;
            agent.label.y = agent.sprite.y + 4;
          },
          onComplete: () => {
            agent.sprite.x = agent.targetX;
            agent.sprite.y = agent.targetY;
            agent.label.x = agent.targetX;
            agent.label.y = agent.targetY + 4;
          },
        });
      }

      // Random speech bubble for working agents
      if (agent.status === "working" && Math.random() < 0.1) {
        const messages = [
          "Analyzing...", "Processing data", "Signal detected!", "Running model...",
          "Checking risk...", "Scanning chain", "Evaluating...", "Computing...",
        ];
        this.showBubble(agent.id, messages[Math.floor(Math.random() * messages.length)]);
      }
    });
  }

  // ─── Tick update ────────────────────────────────────
  private tick() {
    this.statusUpdateInterval++;

    // Depth sort every tick
    this.agents.forEach((agent) => {
      if (!agent.isMoving) {
        agent.sprite.setDepth(agent.sprite.y);
        agent.label.setDepth(agent.sprite.y + 1);
      }
      // Update status glow pulse
      if (agent.status === "working") {
        const pulse = 0.3 + Math.sin(this.statusUpdateInterval * 0.1) * 0.2;
        this.drawStatusGlow(agent.statusBg, agent.sprite.x, agent.sprite.y, AGENT_COLORS[agent.id].color, pulse);
      }
    });
  }
}
