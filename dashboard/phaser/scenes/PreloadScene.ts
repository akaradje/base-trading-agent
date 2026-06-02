import * as Phaser from "phaser";

// ─── Agent definitions ─────────────────────────────────
export const AGENT_COLORS: Record<string, { color: number; name: string; role: string; hair: number; skin: string }> = {
  strategist: { color: 0x60a5fa, name: "Jing",  role: "Strategist", hair: 0x1e1e2e, skin: "#ffd5a0" },
  analyst:    { color: 0x4ade80, name: "Joe",   role: "Analyst",    hair: 0x3d2b1f, skin: "#ffe0bd" },
  critic:     { color: 0xef4444, name: "James", role: "RiskCritic", hair: 0x1a1a2e, skin: "#ffd5a0" },
  onchain:    { color: 0xa78bfa, name: "Jade",  role: "OnChain",    hair: 0x4a2040, skin: "#ffe8cc" },
  risk:       { color: 0xfacc15, name: "Jeed",  role: "RiskMgr",    hair: 0x2d1a0e, skin: "#ffd5a0" },
  engine:     { color: 0xf97316, name: "Jai",   role: "Engine",     hair: 0x111111, skin: "#e8c090" },
};

export const AGENT_IDS = Object.keys(AGENT_COLORS);

// Frame layout: each state = 4 frames, each frame = 32x48
const FW = 32;  // frame width
const FH = 48;  // frame height
const COLS = 4; // frames per animation state
const STATES = ["idle", "walk", "work", "think", "celebrate"] as const;
const TOTAL_COLS = COLS * STATES.length; // 20 columns

export class PreloadScene extends Phaser.Scene {
  constructor() {
    super({ key: "PreloadScene" });
  }

  preload() {
    const w = this.cameras.main.width;
    const h = this.cameras.main.height;

    // Loading bar
    const bar = this.add.graphics();
    const box = this.add.graphics();
    box.fillStyle(0x111122, 0.9);
    box.fillRoundedRect(w / 2 - 162, h / 2 - 14, 324, 28, 6);
    box.lineStyle(1, 0x4ade80, 0.4);
    box.strokeRoundedRect(w / 2 - 162, h / 2 - 14, 324, 28, 6);

    const loadText = this.add.text(w / 2, h / 2 - 30, "Loading assets...", {
      fontSize: "10px", fontFamily: "monospace", color: "#4ade80",
    }).setOrigin(0.5);

    this.load.on("progress", (v: number) => {
      bar.clear();
      bar.fillStyle(0x4ade80, 1);
      bar.fillRoundedRect(w / 2 - 158, h / 2 - 10, 312 * v, 20, 4);
      loadText.setText(`Loading... ${Math.round(v * 100)}%`);
    });

    this.load.on("complete", () => { bar.destroy(); box.destroy(); loadText.destroy(); });

    // Try loading real spritesheets
    AGENT_IDS.forEach((id) => {
      this.load.spritesheet(`char-${id}`, `/assets/sprites/characters/${id}.png`, {
        frameWidth: FW, frameHeight: FH,
      });
    });
    this.load.image("office-tiles", "/assets/tilemaps/office.png");
  }

  create() {
    // Generate procedural sprites for any missing characters
    AGENT_IDS.forEach((id) => {
      if (!this.textures.exists(`char-${id}`)) {
        this.generateCharacter(id, AGENT_COLORS[id]);
      }
    });

    // Generate environment textures
    this.generateEnvironment();

    // Create all animations
    this.createAnimations();

    this.scene.start("OfficeScene");
  }

  // ─── Character sprite generator ─────────────────────
  private generateCharacter(id: string, info: typeof AGENT_COLORS[string]) {
    const tex = this.textures.createCanvas(`char-${id}`, FW * TOTAL_COLS, FH) as Phaser.Textures.CanvasTexture;
    const ctx = tex.getContext();

    const cr = (info.color >> 16) & 0xff;
    const cg = (info.color >> 8) & 0xff;
    const cb = info.color & 0xff;
    const colorStr = `rgb(${cr},${cg},${cb})`;
    const darkStr = `rgb(${Math.max(0,cr-50)},${Math.max(0,cg-50)},${Math.max(0,cb-50)})`;
    const hr = (info.hair >> 16) & 0xff;
    const hg = (info.hair >> 8) & 0xff;
    const hb = info.hair & 0xff;
    const hairStr = `rgb(${hr},${hg},${hb})`;

    for (let state = 0; state < STATES.length; state++) {
      for (let f = 0; f < COLS; f++) {
        const ox = (state * COLS + f) * FW;
        this.drawCharacterFrame(ctx, ox, f, STATES[state], colorStr, darkStr, hairStr, info.skin);
      }
    }

    tex.refresh();
    for (let c = 0; c < TOTAL_COLS; c++) {
      tex.add(c, 0, c * FW, 0, FW, FH);
    }
  }

  private drawCharacterFrame(
    ctx: CanvasRenderingContext2D, ox: number, frame: number, state: string,
    color: string, dark: string, hair: string, skin: string
  ) {
    const cx = ox + 16; // center x
    let headY = 12;
    let bodyY = 24;

    // Animation offsets
    if (state === "idle") {
      const breath = Math.sin(frame * Math.PI / 2) * 0.8;
      headY += breath;
      bodyY += breath;
    } else if (state === "walk") {
      headY += Math.sin(frame * Math.PI) * 0.5;
    } else if (state === "work") {
      headY += 1; // leaning forward
      bodyY += 1;
    } else if (state === "think") {
      headY += (frame === 2 ? -1 : 0);
    } else if (state === "celebrate") {
      headY -= Math.abs(Math.sin(frame * Math.PI / 2)) * 3;
      bodyY -= Math.abs(Math.sin(frame * Math.PI / 2)) * 2;
    }

    // ── Shadow ──
    ctx.fillStyle = "rgba(0,0,0,0.2)";
    ctx.beginPath();
    ctx.ellipse(cx, 44, 8, 3, 0, 0, Math.PI * 2);
    ctx.fill();

    // ── Legs ──
    ctx.fillStyle = "#2d3748";
    if (state === "walk") {
      const legAngle = Math.sin(frame * Math.PI / 2) * 4;
      ctx.fillRect(cx - 5, bodyY + 14, 4, 10 + legAngle);
      ctx.fillRect(cx + 1, bodyY + 14, 4, 10 - legAngle);
    } else if (state === "celebrate") {
      ctx.fillRect(cx - 5, bodyY + 14, 4, 8);
      ctx.fillRect(cx + 1, bodyY + 14, 4, 8);
    } else {
      ctx.fillRect(cx - 5, bodyY + 14, 4, 10);
      ctx.fillRect(cx + 1, bodyY + 14, 4, 10);
    }

    // Shoes
    ctx.fillStyle = "#1a202c";
    if (state === "walk") {
      const legAngle = Math.sin(frame * Math.PI / 2) * 4;
      ctx.fillRect(cx - 6, bodyY + 23 + Math.max(0, legAngle), 6, 2);
      ctx.fillRect(cx, bodyY + 23 + Math.max(0, -legAngle), 6, 2);
    } else {
      ctx.fillRect(cx - 6, bodyY + 23, 6, 2);
      ctx.fillRect(cx, bodyY + 23, 6, 2);
    }

    // ── Body (shirt) ──
    ctx.fillStyle = color;
    ctx.fillRect(cx - 7, bodyY, 14, 15);
    // Shirt collar
    ctx.fillStyle = dark;
    ctx.fillRect(cx - 3, bodyY, 6, 2);

    // ── Arms ──
    ctx.fillStyle = color;
    if (state === "work") {
      // Typing: arms forward
      const armBob = Math.sin(frame * Math.PI) * 1;
      ctx.fillRect(cx - 11, bodyY + 2 + armBob, 4, 10);
      ctx.fillRect(cx + 7, bodyY + 2 - armBob, 4, 10);
      // Hands on keyboard
      ctx.fillStyle = skin;
      ctx.fillRect(cx - 11, bodyY + 11 + armBob, 4, 3);
      ctx.fillRect(cx + 7, bodyY + 11 - armBob, 4, 3);
    } else if (state === "think") {
      // Hand on chin
      ctx.fillRect(cx - 11, bodyY + 2, 4, 8);
      ctx.fillRect(cx + 7, bodyY + 2, 4, 8);
      ctx.fillStyle = skin;
      ctx.fillRect(cx - 11, bodyY + 9, 4, 3);
      // Right hand up to chin
      ctx.fillStyle = color;
      ctx.fillRect(cx + 7, bodyY - 2, 4, 6);
      ctx.fillStyle = skin;
      ctx.fillRect(cx + 7, bodyY - 4, 4, 3);
    } else if (state === "celebrate") {
      // Arms up!
      ctx.fillRect(cx - 11, bodyY - 4, 4, 10);
      ctx.fillRect(cx + 7, bodyY - 4, 4, 10);
      ctx.fillStyle = skin;
      ctx.fillRect(cx - 11, bodyY - 6, 4, 3);
      ctx.fillRect(cx + 7, bodyY - 6, 4, 3);
    } else {
      // Idle/walk: arms down
      const armSwing = state === "walk" ? Math.sin(frame * Math.PI / 2) * 3 : 0;
      ctx.fillRect(cx - 11, bodyY + 2 + armSwing, 4, 10);
      ctx.fillRect(cx + 7, bodyY + 2 - armSwing, 4, 10);
      ctx.fillStyle = skin;
      ctx.fillRect(cx - 11, bodyY + 11 + armSwing, 4, 3);
      ctx.fillRect(cx + 7, bodyY + 11 - armSwing, 4, 3);
    }

    // ── Head ──
    // Neck
    ctx.fillStyle = skin;
    ctx.fillRect(cx - 2, headY + 8, 4, 4);

    // Head shape
    ctx.fillStyle = skin;
    ctx.beginPath();
    ctx.arc(cx, headY + 5, 8, 0, Math.PI * 2);
    ctx.fill();

    // Hair
    ctx.fillStyle = hair;
    ctx.beginPath();
    ctx.arc(cx, headY + 3, 8, Math.PI, 0);
    ctx.fill();
    ctx.fillRect(cx - 8, headY + 1, 16, 3);

    // Eyes
    const blink = (state === "think" && frame === 2) ? 1 : 3;
    ctx.fillStyle = "#1a1a2e";
    ctx.fillRect(cx - 4, headY + 4, 2, blink);
    ctx.fillRect(cx + 2, headY + 4, 2, blink);

    // Eye whites (tiny highlight)
    if (blink === 3) {
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(cx - 4, headY + 4, 1, 1);
      ctx.fillRect(cx + 2, headY + 4, 1, 1);
    }

    // Mouth
    if (state === "celebrate") {
      ctx.fillStyle = "#c0392b";
      ctx.fillRect(cx - 2, headY + 9, 4, 2);
    } else if (state === "think") {
      ctx.fillStyle = "#555";
      ctx.fillRect(cx - 1, headY + 9, 3, 1);
    } else {
      ctx.fillStyle = "#555";
      ctx.fillRect(cx - 2, headY + 9, 4, 1);
    }

    // State-specific decorations
    if (state === "work") {
      // Monitor in front
      ctx.fillStyle = "#0f172a";
      ctx.fillRect(cx - 8, bodyY - 6, 16, 10);
      ctx.fillStyle = `rgba(${Math.floor(Math.random()*100)},${Math.floor(Math.random()*200+50)},${Math.floor(Math.random()*100)},0.5)`;
      ctx.fillRect(cx - 7, bodyY - 5, 14, 8);
    }

    if (state === "celebrate") {
      // Sparkles around
      const sparkleColors = ["#ffd700", "#ff6b6b", "#4ade80", "#60a5fa"];
      for (let s = 0; s < 3; s++) {
        ctx.fillStyle = sparkleColors[(frame + s) % sparkleColors.length];
        const sx = cx - 10 + s * 10 + (frame * 2);
        const sy = headY - 4 + Math.sin(s + frame) * 4;
        ctx.fillRect(sx, sy, 2, 2);
      }
    }

    if (state === "think") {
      // Thought dots
      ctx.fillStyle = "rgba(150,150,150,0.6)";
      ctx.beginPath();
      ctx.arc(cx + 10, headY - 2, 1.5, 0, Math.PI * 2);
      ctx.fill();
      ctx.beginPath();
      ctx.arc(cx + 13, headY - 5, 2, 0, Math.PI * 2);
      ctx.fill();
      ctx.beginPath();
      ctx.arc(cx + 16, headY - 9, 2.5, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  // ─── Environment textures ───────────────────────────
  private generateEnvironment() {
    // Desk texture
    const deskTex = this.textures.createCanvas("desk", 64, 40) as Phaser.Textures.CanvasTexture;
    const dc = deskTex.getContext();
    // Desk top
    dc.fillStyle = "#475569";
    dc.fillRect(0, 0, 64, 8);
    dc.fillStyle = "#3d4a5c";
    dc.fillRect(0, 8, 64, 2);
    // Desk legs
    dc.fillStyle = "#334155";
    dc.fillRect(2, 10, 4, 28);
    dc.fillRect(58, 10, 4, 28);
    // Monitor
    dc.fillStyle = "#0f172a";
    dc.fillRect(20, -12, 24, 14);
    dc.fillStyle = "#1e3a5f";
    dc.fillRect(21, -11, 22, 12);
    // Monitor stand
    dc.fillStyle = "#334155";
    dc.fillRect(30, 2, 4, 6);
    deskTex.refresh();

    // Chair texture
    const chairTex = this.textures.createCanvas("chair", 24, 32) as Phaser.Textures.CanvasTexture;
    const cc = chairTex.getContext();
    cc.fillStyle = "#1e293b";
    cc.fillRect(4, 0, 16, 4); // top
    cc.fillStyle = "#2d3a4a";
    cc.fillRect(2, 4, 20, 10); // back
    cc.fillStyle = "#3d4a5c";
    cc.fillRect(4, 14, 16, 6); // seat
    cc.fillStyle = "#1e293b";
    cc.fillRect(6, 20, 3, 10); // legs
    cc.fillRect(15, 20, 3, 10);
    chairTex.refresh();

    // Plant texture
    const plantTex = this.textures.createCanvas("plant", 24, 36) as Phaser.Textures.CanvasTexture;
    const pc = plantTex.getContext();
    // Pot
    pc.fillStyle = "#92400e";
    pc.fillRect(4, 24, 16, 12);
    pc.fillStyle = "#78350f";
    pc.fillRect(2, 22, 20, 4);
    // Leaves
    pc.fillStyle = "#15803d";
    pc.beginPath(); pc.arc(12, 16, 8, 0, Math.PI * 2); pc.fill();
    pc.fillStyle = "#166534";
    pc.beginPath(); pc.arc(8, 12, 6, 0, Math.PI * 2); pc.fill();
    pc.fillStyle = "#22c55e";
    pc.beginPath(); pc.arc(16, 10, 5, 0, Math.PI * 2); pc.fill();
    plantTex.refresh();

    // Server rack
    const serverTex = this.textures.createCanvas("server", 32, 56) as Phaser.Textures.CanvasTexture;
    const sc = serverTex.getContext();
    sc.fillStyle = "#1e293b";
    sc.fillRect(0, 0, 32, 56);
    sc.strokeStyle = "#334155";
    sc.lineWidth = 1;
    sc.strokeRect(0, 0, 32, 56);
    // LED lights
    for (let i = 0; i < 6; i++) {
      sc.fillStyle = i % 2 === 0 ? "#4ade80" : "#22c55e";
      sc.beginPath(); sc.arc(24, 6 + i * 9, 2, 0, Math.PI * 2); sc.fill();
    }
    // Drive bays
    for (let i = 0; i < 4; i++) {
      sc.fillStyle = "#0f172a";
      sc.fillRect(4, 4 + i * 13, 14, 9);
    }
    serverTex.refresh();

    // Whiteboard
    const wbTex = this.textures.createCanvas("whiteboard", 80, 48) as Phaser.Textures.CanvasTexture;
    const wc = wbTex.getContext();
    wc.fillStyle = "#e2e8f0";
    wc.fillRect(0, 0, 80, 48);
    wc.strokeStyle = "#94a3b8";
    wc.lineWidth = 2;
    wc.strokeRect(0, 0, 80, 48);
    // Content lines
    wc.fillStyle = "#3b82f6";
    for (let i = 0; i < 4; i++) {
      wc.fillRect(8, 8 + i * 10, 30 + Math.random() * 30, 2);
    }
    // Arrows
    wc.fillStyle = "#ef4444";
    wc.fillRect(50, 12, 20, 2);
    wbTex.refresh();

    // Coffee machine
    const coffeeTex = this.textures.createCanvas("coffee", 28, 36) as Phaser.Textures.CanvasTexture;
    const cmc = coffeeTex.getContext();
    cmc.fillStyle = "#374151";
    cmc.fillRect(0, 0, 28, 36);
    cmc.fillStyle = "#1f2937";
    cmc.fillRect(4, 4, 20, 12);
    cmc.fillStyle = "#dc2626";
    cmc.beginPath(); cmc.arc(14, 10, 3, 0, Math.PI * 2); cmc.fill();
    cmc.fillStyle = "#92400e";
    cmc.fillRect(8, 20, 12, 10);
    cmc.fillStyle = "#78350f";
    cmc.fillRect(6, 18, 16, 4);
    coffeeTex.refresh();

    // Trading chart screen (wall-mounted)
    const chartTex = this.textures.createCanvas("chart-screen", 64, 40) as Phaser.Textures.CanvasTexture;
    const chrc = chartTex.getContext();
    chrc.fillStyle = "#0f172a";
    chrc.fillRect(0, 0, 64, 40);
    chrc.strokeStyle = "#1e293b";
    chrc.strokeRect(0, 0, 64, 40);
    // Candlesticks
    const colors = ["#4ade80", "#ef4444", "#4ade80", "#ef4444", "#4ade80", "#4ade80", "#ef4444"];
    for (let i = 0; i < 7; i++) {
      const x = 6 + i * 8;
      const h = 5 + Math.random() * 15;
      const y = 30 - h;
      chrc.fillStyle = colors[i];
      chrc.fillRect(x + 1, y, 4, h);
      // Wick
      chrc.fillRect(x + 2, y - 3, 2, 3 + h + 3);
    }
    chartTex.refresh();
  }

  // ─── Animations ─────────────────────────────────────
  private createAnimations() {
    AGENT_IDS.forEach((id) => {
      const key = `char-${id}`;

      // idle: frames 0-3
      this.anims.create({
        key: `${key}-idle`,
        frames: this.anims.generateFrameNumbers(key, { start: 0, end: 3 }),
        frameRate: 4, repeat: -1,
      });

      // walk: frames 4-7
      this.anims.create({
        key: `${key}-walk`,
        frames: this.anims.generateFrameNumbers(key, { start: 4, end: 7 }),
        frameRate: 8, repeat: -1,
      });

      // work: frames 8-11
      this.anims.create({
        key: `${key}-work`,
        frames: this.anims.generateFrameNumbers(key, { start: 8, end: 11 }),
        frameRate: 6, repeat: -1,
      });

      // think: frames 12-15
      this.anims.create({
        key: `${key}-think`,
        frames: this.anims.generateFrameNumbers(key, { start: 12, end: 15 }),
        frameRate: 3, repeat: -1,
      });

      // celebrate: frames 16-19
      this.anims.create({
        key: `${key}-celebrate`,
        frames: this.anims.generateFrameNumbers(key, { start: 16, end: 19 }),
        frameRate: 8, repeat: -1,
      });
    });
  }
}
