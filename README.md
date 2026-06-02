# Base Trading Agent 🤖

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/akaradje/base-trading-agent?style=social)](https://github.com/akaradje/base-trading-agent/stargazers)
[![GitHub Last Commit](https://img.shields.io/github/last-commit/akaradje/base-trading-agent)](https://github.com/akaradje/base-trading-agent/commits)
[![GitHub Issues](https://img.shields.io/github/issues/akaradje/base-trading-agent)](https://github.com/akaradje/base-trading-agent/issues)
[![Next.js 15](https://img.shields.io/badge/Next.js-15-000000?logo=next.js&logoColor=white)](https://nextjs.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](deploy/Dockerfile)
[![Supabase](https://img.shields.io/badge/Supabase-Realtime-3FCF8E?logo=supabase&logoColor=white)](https://supabase.com/)
[![Base Blockchain](https://img.shields.io/badge/Base-L2-0052FF?logo=ethereum&logoColor=white)](https://base.org/)

บอทเทรดเหรียญคริปโตบนเชน **Base** ทำงาน **24 ชม.** ออกแบบเป็น **multi-agent** (Planner–Analyst–Critic–Executor) เริ่มที่ **paper trading** (จำลอง ไม่ใช้เงินจริง) แล้วต่อ live ทีหลังได้

> ⚠️ **คำเตือน:** ซอฟต์แวร์เพื่อการศึกษา/ทดลอง ไม่ใช่คำแนะนำการลงทุน คริปโตมีความเสี่ยงสูง เริ่มที่ paper trading เสมอ และอย่าใส่เงินเกินที่รับความเสียหายได้

---

## สถาปัตยกรรม Multi-Agent

```
ราคา (CoinGecko) ─► Indicator (EMA/RSI)
                         │
   ┌─────────────────────┴───────────────────────────────┐
   │ 0. RiskManager (deterministic): kill switch,         │
   │    stop-loss / take-profit  ── บังคับเสมอ ──┐        │
   │ 1. 🧭 Strategist (Planner)  regime/ความเสี่ยงรวม      │
   │ 2. 📊 Analyst  conviction + action (จาก price action)  │
   │ 3. 🛡️ RiskCritic (Critic)  อนุมัติ/วีโต้/ลดขนาด        │
   │ 4. ⚙️ Executor  ยิงออเดอร์ (paper / Base)             │
   └──────────────────────────────────────────────────────┘
```

กฎความเสี่ยงแข็ง (stop-loss, take-profit, เพดานขนาดโพซิชัน, kill switch) บังคับด้วยโค้ด **deterministic เสมอ** — LLM ได้แค่กรองออก/ลดขนาด ไม่มีทางข้ามกฎ

### โมเดล (ผ่าน OpenRouter — เลือกชุดประหยัดสุด-คุ้มสุด)

| Agent | โมเดล | ราคา /1M (in/out) |
|---|---|---|
| 🧭 Strategist | `qwen/qwen3.7-max` | ~$0.25 / $0.38 |
| 📊 Analyst | `qwen/qwen3-coder-flash` | $0.07 / $0.26 |
| 🛡️ RiskCritic | `xiaomi/mimo-v2.5-pro` | reasoning model |

เปลี่ยนโมเดลได้ใน `config.yaml` → `agents:` (ดู slug ทั้งหมดที่ https://openrouter.ai/models)

---

## ติดตั้ง

```bash
pip install -r requirements.txt

# (ไม่บังคับ) ใส่คีย์ LLM — ไม่ใส่ก็รันได้ด้วยกลยุทธ์ deterministic
copy .env.example .env        # Windows
# แก้ .env ใส่ OPENROUTER_API_KEY
```

ตั้ง env var (PowerShell):
```powershell
$env:OPENROUTER_API_KEY = "sk-or-..."
```

---

## ใช้งาน

```bash
python run.py backtest --days 90   # ทดสอบกลยุทธ์ฐานกับข้อมูลย้อนหลังก่อน
python run.py run                  # เปิดบอท paper trading 24 ชม. (Ctrl+C หยุด)
python run.py status               # ดูสถานะพอร์ตล่าสุด
```

สถานะพอร์ตเก็บที่ `state/portfolio.json` (รันต่อจากเดิมได้หลังปิด)

---

## ตั้งค่า (`config.yaml`)

- `mode`: `paper` (จำลอง) | `live` (ยังบล็อกไว้ ต้องต่อ Base MCP ก่อน)
- `poll_interval_sec`: รอบการเช็คราคา (เริ่ม 60s)
- `symbols`: เหรียญที่เทรด (ใช้ **CoinGecko coin id**)
- `strategy`: พารามิเตอร์ EMA/RSI
- `risk`: stop-loss, take-profit, เพดานโพซิชัน, max-drawdown, ค่าธรรมเนียม
- `agents`: เปิด/ปิด + เลือกโมเดลแต่ละ agent

---

## ต่อ Live บน Base (ทำทีหลัง)

ตอนนี้ `LiveExecutor` บล็อกไว้กันยิงเงินจริงโดยไม่ตั้งใจ วิธีต่อ:

1. ติดตั้ง Base MCP: `claude mcp add --transport http base-mcp https://mcp.base.org`
2. แก้ `basebot/executor.py` → `LiveExecutor.buy/sell` ให้เรียก swap ผ่าน Base MCP
   (ETH/USDC ↔ token) ทุก write action จะมีลิงก์ให้ **approve ใน Base Account** ก่อนยืนยัน
3. ตั้ง `mode: live` ใน `config.yaml`

---

## โครงสร้าง

```
run.py                  CLI (run / backtest / status)
config.yaml             ตั้งค่าทั้งหมด
basebot/
  config.py             โหลด config
  data.py               ดึงราคา CoinGecko
  indicators.py         EMA / RSI / crossover
  portfolio.py          พอร์ตจำลอง + persistence
  risk.py               กฎความเสี่ยง deterministic
  executor.py           Paper / Live executor
  llm.py                เชื่อม OpenRouter (OpenAI-compatible)
  orchestrator.py       ประสาน agents (Planner→Analyst→Critic→Executor)
  engine.py             ลูป 24 ชม.
  backtest.py           ทดสอบย้อนหลัง
  agents/               strategist, analyst, risk_critic
```
