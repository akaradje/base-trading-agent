# แผนพัฒนาสถาปัตยกรรม Base Trading Agent

> ผลลัพธ์จาก deep research — 5 แกน: LLM agent architecture, Base L2 strategies, risk management, on-chain signals, production infrastructure
> บันทึกเมื่อ: 2026-05-31

---

## สารบัญ

1. [สถาปัตยกรรม Agent ที่ควรปรับปรุง](#1-สถาปัตยกรรม-agent)
2. [สัญญาณเทรดที่ควรเพิ่ม](#2-สัญญาณเทรด)
3. [การจัดการความเสี่ยง](#3-การจัดการความเสี่ยง)
4. [การปรับปรุง Execution](#4-execution)
5. [Infrastructure สำหรับ Production](#5-infrastructure)
6. [ลำดับการพัฒนา](#6-ลำดับการพัฒนา)

---

## 1. สถาปัตยกรรม Agent

### 1.1 เพิ่ม OnChain Agent (ไฟล์ใหม่: `basebot/agents/onchain.py`)

แทรกเข้าไประหว่าง Strategist กับ Sentiment ใน pipeline สัญญาณ 3 ชนิด:

**Exchange Flow Signal** — Poll Glassnode API ทุก 15 นาที
```
GET https://api.glassnode.com/v1/metrics/transactions/transfers_volume_exchanges_net?api_key=KEY&a=ETH&i=24h
```
- Net outflow = bullish (ETH ออกจาก exchange → คนสะสม)
- Net inflow = bearish (ETH เข้า exchange → พร้อมขาย)
- Normalize เป็น [-1, 1]

**Funding Rate Signal** — Poll Binance WebSocket
```
wss://fstream.binance.com/ws/ethusdt@markPrice@1s
```
- Funding > 0.1%/8h = bearish (crowded longs → อาจถูก liquidate)
- Funding < -0.05%/8h = bullish (crowded shorts → short squeeze)
- Normalize เป็น [-1, 1]

**Whale Accumulation Signal** — Poll Basescan API ทุก 30 นาที
```
GET https://api.basescan.com/api?module=action=tokentx&address=WALLET&apikey=KEY
```
- ติดตาม wallet ที่กำหนดใน config (10-20 addresses)
- ถ้า 3+ wallets สะสมเหรียญเดียวกันภายใน 48 ชม. → signal = +1

**Output Schema:**
```python
{
    "exchange_flow": float,       # -1 ถึง 1
    "funding_rate": float,        # -1 ถึง 1
    "whale_signal": float,        # -1 ถึง 1
    "on_chain_conviction": float, # 0 ถึง 1
    "composite_score": float,     # weighted average
    "summary": str,
}
```

**Config ที่ต้องเพิ่ม:**
```yaml
onchain:
  glassnode_api_key: ""         # env: GLASSNODE_API_KEY
  coinglass_api_key: ""         # env: COINGLASS_API_KEY
  basescan_api_key: ""          # env: BASESCAN_API_KEY
  whale_watchlist: []           # รายชื่อ Base addresses ที่จะติดตาม
  poll_interval_min: 15
```

### 1.2 Confidence-Weighted Consensus (แก้ orchestrator.py)

แทนที่ระบบ approve/veto แบบ binary ด้วยการคูณ conviction ของทุก agent:

```python
chain_conviction = (
    appetite                              # Strategist confidence
    * float(senti.get("score", 0))        # Sentiment (normalize [-1,1] → [0,1])
    * conv                                # Analyst conviction
    * float(verdict.get("size_factor"))   # RiskCritic confidence
    * onchain_conviction                  # OnChain agent
)
```

ถ้า `chain_conviction < min_conviction` → ข้ามเทรดนี้ ข้อดี: ถ้าทุก agent lukewarm (0.3-0.5) ผลคูณจะต่ำมาก → ไม่เทรด

### 1.3 ลบ Sentiment Agent (ประหยัด ~33% ค่า LLM)

**ปัญหา:** Sentiment agent ตอนนี้ไม่มี news feed จริง — แค่อ่านข้อมูลราคาซ้ำกับ Analyst

**ทางเลือก A (แนะนำ):** ลบ `sentiment.py` รวมข้อมูลเข้า Analyst prompt โดยตรง

**ทางเลือก B (ถ้ามีงบ):** เพิ่ม CryptoPanic API ($30/เดือน)
```
GET https://cryptopanic.com/api/v1/posts/?auth_token=KEY&currencies=ETH,AERO,DEGEN&kind=news
```

### 1.4 Model Assignment Optimization

| Agent | ปัจจุบัน | แนะนำ | เหตุผล |
|-------|----------|-------|--------|
| Strategist | `qwen/qwen3.7-max` | คงเดิม | รันทุก 30 นาที คุ้มค่า |
| Analyst | `qwen/qwen3-coder-flash` | คงเดิม | เร็ว รันถี่ |
| RiskCritic | `xiaomi/mimo-v2.5-pro` | คงเดิม | reasoning ดี สำหรับ veto |
| Sentiment | `qwen/qwen3-8b` | ลบ (รวมเข้า Analyst) | ซ้ำซ้อน |

**ระยะยาว:** หลังเก็บข้อมูล 2-3 เดือน → fine-tune LoRA adapter บน Qwen-7B ด้วย FinGPT framework
- Training data: (headline, sentiment_label, 24h_price_movement)
- LoRA rank 16, alpha 32
- Deploy บน RTX 3090 หรือ AWS g5.xlarge ($1.01/ชม.)

---

## 2. สัญญาณเทรด

### 2.1 เพิ่ม Technical Indicators (แก้ `basebot/indicators.py`)

**ATR (Average True Range) — 14 period:**
```python
def atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> list[float]:
    if len(closes) < 2:
        return []
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
        trs.append(tr)
    if len(trs) < period:
        return []
    atr_vals = [sum(trs[:period]) / period]
    for tr in trs[period:]:
        atr_vals.append((atr_vals[-1] * (period - 1) + tr) / period)
    return atr_vals
```

**Bollinger Bands (20 period, 2 std dev):**
```python
def bollinger(prices: list[float], period: int = 20, num_std: float = 2.0):
    if len(prices) < period:
        return (None, None, None)
    window = prices[-period:]
    middle = sum(window) / period
    std = (sum((p - middle) ** 2 for p in window) / period) ** 0.5
    return (middle + num_std * std, middle, middle - num_std * std)
```

**VWAP:** ต้องการ volume data จาก CoinGecko OHLC endpoint

### 2.2 อัปเกรด Data Source (แก้ `basebot/data.py`)

**CoinGecko OHLC endpoint (ฟรี):**
```
GET /coins/{id}/ohlc?vs_currency=usd&days=14
→ [[timestamp, open, high, low, close], ...]
```

**DeFiLlama (ฟรี, ไม่ต้องมี API key):**
```
GET https://coins.llama.fi/chart/coingecko:{id}?start=TIMESTAMP&span=86400&period=1d
```

**Aerodrome Subgraph (ข้อมูล DEX บน Base):**
```
https://gateway.thegraph.com/api/SUBGRAPH_KEY/subgraphs/id/aerodrome-finance-base
```
สำหรับดู pool TVL, volume, liquidity depth

**เพิ่มฟังก์ชัน:**
```python
def ohlc(coin_id: str, days: int = 14, vs: str = "usd") -> list[dict]:
    raw = _get(f"/coins/{coin_id}/ohlc", {"vs_currency": vs, "days": days})
    return [{"ts": p[0], "open": p[1], "high": p[2], "low": p[3], "close": p[4]} for p in raw]
```

### 2.3 Liquidation Cascade Detection (ไฟล์ใหม่: `basebot/liquidation.py`)

**Data source:** Coinalyze API หรือ Binance WebSocket สำหรับ Open Interest

**Signal Logic:**
```python
def detect_cascade(oi_history: list[float], price_history: list[float], threshold_pct: float = 5.0):
    if len(oi_history) < 60:
        return None
    oi_change = (oi_history[-1] - oi_history[-60]) / oi_history[-60] * 100
    price_change = (price_history[-1] - price_history[-60]) / price_history[-60] * 100

    # Long cascade: OI ลด + ราคาลง = forced long liquidations
    if oi_change < -threshold_pct and price_change < -2.0:
        return "long_cascade"   # mean-reversion long entry
    # Short cascade: OI ลด + ราคาขึ้น = forced short liquidations
    if oi_change < -threshold_pct and price_change > 2.0:
        return "short_cascade"  # mean-reversion short entry
    return None
```

---

## 3. การจัดการความเสี่ยง

### 3.1 Volatility-Adjusted Position Sizing (แก้ `basebot/risk.py`)

แทนที่ flat 25% cap ด้วย ATR-weighted sizing:

```python
def max_buy_usd(self, pf, symbol, prices, atr_values=None):
    eq = pf.equity(prices)
    base_cap = eq * self.p.max_position_pct

    if atr_values and symbol in atr_values:
        ref_atr = sorted(atr_values.values())[len(atr_values) // 2]
        asset_atr = atr_values[symbol]
        if asset_atr > 0:
            volatility_mult = max(0.25, min(2.0, ref_atr / asset_atr))
            base_cap *= volatility_mult

    held = pf.position_value(symbol, prices.get(symbol, 0.0))
    return max(0.0, min(base_cap - held, pf.cash))
```

**ผลลัพธ์:** DEGEN (ผันผวนสูง) ได้ position เล็กลง 30-50%, ETH (นิ่งกว่า) ได้ใหญ่ขึ้น

### 3.2 Trailing Stops with Time Decay (แก้ `risk.py` + `portfolio.py`)

**เพิ่ม `peak_price` ใน Position:**
```python
@dataclass
class Position:
    qty: float
    entry_price: float
    opened_at: str = field(default_factory=_now)
    peak_price: float = 0.0   # ราคาสูงสุดตั้งแต่เข้า
```

**อัปเดต peak_price ใน engine.py ทุก cycle:**
```python
for cid, px in prices.items():
    pos = self.pf.positions.get(cid)
    if pos:
        pos.peak_price = max(pos.peak_price, px)
```

**Config parameters:**
```yaml
risk:
  trailing_stop_pct: 0.03        # trailing 3% จาก peak
  trailing_stop_offset: 0.05     # เริ่ม trailing เมื่อกำไร >= 5%
  trailing_time_decay_min: 120   # tighten stop หลังถือ 2 ชม.
  trailing_time_decay_pct: 0.02  # tighten เหลือ 2%
```

**Logic ใหม่:**
```python
def exit_reason(self, pf, symbol, price):
    pos = pf.positions.get(symbol)
    if not pos or pos.entry_price == 0:
        return None

    upnl = (price - pos.entry_price) / pos.entry_price

    # Hard stop-loss (ทำงานเสมอ)
    if upnl <= -self.p.stop_loss_pct:
        return f"stop_loss ({upnl:.1%})"

    # Take-profit (เพดานสูงสุด)
    if upnl >= self.p.take_profit_pct:
        return f"take_profit ({upnl:.1%})"

    # Trailing stop (เริ่มเมื่อกำไรถึง offset)
    if pos.peak_price > 0 and upnl >= self.p.trailing_stop_offset:
        trail_pct = self.p.trailing_stop_pct

        # Time decay: tighten หลังถือนาน
        opened = datetime.fromisoformat(pos.opened_at)
        hold_min = (datetime.now(timezone.utc) - opened).total_seconds() / 60
        if hold_min > self.p.trailing_time_decay_min:
            trail_pct = self.p.trailing_time_decay_pct

        trail_price = pos.peak_price * (1 - trail_pct)
        if price <= trail_price:
            return f"trailing_stop (peak={pos.peak_price:.4f}, trail={trail_pct:.1%})"

    return None
```

### 3.3 Tiered Circuit Breakers (แก้ `basebot/risk.py`)

แทน kill switch แบบ binary ด้วย 4 ระดับ:

```python
class RiskLevel:
    NORMAL = 0      # ทำงานปกติ
    REDUCED = 1     # 50% position sizing, widen stops
    HALTED = 2      # ห้ามเปิดไม้ใหม่ เฉพาะขาย
    EMERGENCY = 3   # บังคับขายทุกอย่าง

def assess_risk_level(self, pf, prices) -> tuple[int, str]:
    eq = pf.equity(prices)
    pf.peak_equity = max(pf.peak_equity, eq)
    if pf.peak_equity <= 0:
        return RiskLevel.NORMAL, ""

    drawdown = (pf.peak_equity - eq) / pf.peak_equity

    # Rolling Sharpe ratio (20 trades ล่าสุด)
    if len(pf.trades) >= 20:
        returns = self._compute_trade_returns(pf)
        if len(returns) >= 10:
            mean_ret = sum(returns) / len(returns)
            std_ret = (sum((r - mean_ret)**2 for r in returns) / len(returns)) ** 0.5
            sharpe = (mean_ret / std_ret * (252 ** 0.5)) if std_ret > 0 else 0
            if sharpe < 0.5:
                return RiskLevel.REDUCED, f"rolling_sharpe={sharpe:.2f}"

    # แพ้ติดต่อกัน per symbol
    for sym in list(pf.positions.keys()):
        consecutive = self._count_consecutive_losses(pf, sym)
        if consecutive >= 3:
            return RiskLevel.REDUCED, f"{sym}: {consecutive} consecutive losses"

    # Drawdown tiers
    if drawdown >= self.p.max_drawdown_pct:
        return RiskLevel.EMERGENCY, f"drawdown={drawdown:.1%}"
    if drawdown >= self.p.max_drawdown_pct * 0.75:
        return RiskLevel.HALTED, f"drawdown={drawdown:.1%}"
    if drawdown >= self.p.max_drawdown_pct * 0.4:
        return RiskLevel.REDUCED, f"drawdown={drawdown:.1%}"

    return RiskLevel.NORMAL, ""
```

**ใช้ใน orchestrator.py:**
```python
risk_level, reason = self.risk.assess_risk_level(self.pf, prices)
if risk_level >= RiskLevel.EMERGENCY:
    for cid in list(self.pf.positions.keys()):
        px = prices.get(cid)
        if px:
            self.ex.sell(cid, px, f"EMERGENCY: {reason}")
    return
if risk_level >= RiskLevel.HALTED:
    self.log(f"  HALTED: {reason} — ห้ามเปิดไม้")
    return
if risk_level >= RiskLevel.REDUCED:
    budget *= 0.5
    self.log(f"  REDUCED: {reason} — 50% sizing")
```

### 3.4 Connectivity Kill Switch (แก้ `basebot/engine.py`)

ถ้า data feed นิ่ง → ขายทุกอย่าง:

```python
self._last_data_ts = time.time()
self._max_stale_seconds = cfg.poll_interval_sec * 3  # 3 cycles ที่ไม่ได้ราคา

def _cycle(self):
    try:
        prices = data.current_prices(...)
        self._last_data_ts = time.time()
    except data.DataError:
        stale = time.time() - self._last_data_ts
        if stale > self._max_stale_seconds:
            self.log(f"  DATA STALE {stale:.0f}s — ขายทุกอย่าง!")
            for cid in list(self.pf.positions.keys()):
                last_px = self.histories[cid][-1] if self.histories[cid] else None
                if last_px:
                    self.pf.sell(cid, last_px, "data_stale_kill")
            return
```

---

## 4. Execution

### 4.1 Gas-Aware Execution (แก้ `basebot/executor.py`)

ใช้ Base GasPriceOracle predeploy สำหรับค่า gas ที่แม่นกว่า:

```python
# GasPriceOracle บน Base ที่ 0x420000000000000000000000000000000000000F
GAS_ORACLE = "0x420000000000000000000000000000000000000F"

def estimate_total_fee(rpc_url, tx_bytes):
    """เรียก GasPriceOracle.getL1Fee(encoded_tx) สำหรับ L1 data cost ที่แม่น"""
    # ABI encode: getL1Fee(bytes) -> uint256
    selector = "0x939e1e40"
    # ... call via eth_call
```

### 4.2 Dynamic Slippage (แก้ `basebot/executor.py`)

ปรับ slippage ตาม pool liquidity และ trade size:

```python
def compute_dynamic_slippage(self, quote, pool_tvl):
    base_bps = int(self.slippage_config.get("default_bps", 50))
    trade_value = self._estimate_trade_value_usd(quote)

    if pool_tvl > 0:
        impact_ratio = trade_value / pool_tvl
        dynamic_bps = int(base_bps * (1 + impact_ratio * 150))
        return min(dynamic_bps, int(self.slippage_config.get("max_bps", 300)))
    return base_bps
```

### 4.3 Multicall3 for Batch Reads

รวม eth_call หลายตัวเป็น call เดียว:

```python
MULTICALL3 = "0xcA11bde05977b3631167028862bE2a173976CA11"  # บน Base

def batch_get_amounts_out(w3, router_addr, pairs):
    """Batch getAmountsOut calls เป็น eth_call เดียว"""
    # Build aggregate3 call
```

### 4.4 MEV Protection

Base sequencer มี MEV resistance ในตัวสำหรับ native swaps (ไม่มี public mempool)
สำหรับ L1 bridge operations → ใช้ Flashbots Protect RPC:

```yaml
live:
  submission_rpc:
    base_native: "https://mainnet.base.org"        # สำหรับ Base DEX swaps
    l1_bridge: "https://rpc.flashbots.net/fast"     # สำหรับ L1 operations
```

---

## 5. Infrastructure

### 5.1 Structured Logging (ไฟล์ใหม่: `basebot/logging.py`)

```python
import logging
import json
from logging.handlers import RotatingFileHandler

class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
        })

def setup_logging(log_file="state/bot.log"):
    logger = logging.getLogger("basebot")
    logger.setLevel(logging.INFO)

    # Rotating file: 10MB, 10 backups
    fh = RotatingFileHandler(log_file, maxBytes=10_000_000, backupCount=10, encoding="utf-8")
    fh.setFormatter(JsonFormatter())
    logger.addHandler(fh)

    # Console (human-readable)
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    logger.addHandler(ch)

    return logger
```

### 5.2 Process Watchdog (systemd + Docker)

**systemd service:**
```ini
# /etc/systemd/system/basebot.service
[Unit]
Description=Base Trading Agent
After=network.target

[Service]
Type=notify
ExecStart=/usr/bin/python3 /opt/basebot/run.py run
WatchdogSec=120
Restart=on-failure
RestartSec=30
EnvironmentFile=/opt/basebot/.env

[Install]
WantedBy=multi-user.target
```

**Docker healthcheck:**
```dockerfile
HEALTHCHECK --interval=120s --timeout=10s --retries=3 \
  CMD python -c "import os; exit(0 if os.path.getmtime('state/portfolio.json') > $(date -d '3 minutes ago' +%s) else 1)"
```

### 5.3 Alerting (ไฟล์ใหม่: `basebot/alerts.py`)

**Telegram Bot API (ฟรี):**
```python
import requests

def send_telegram(token, chat_id, message):
    requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
        timeout=10,
    )
```

**Alert triggers:**
- Kill switch ทำงาน (ทุกระดับ)
- Data feed นิ่ง > 3 cycles
- Emergency liquidation
- LLM agent fail > 3 ครั้งติด
- Daily P&L summary ที่ UTC midnight

**Config:**
```yaml
alerts:
  enabled: false
  telegram_token: ""       # env: TELEGRAM_BOT_TOKEN
  telegram_chat_id: ""     # env: TELEGRAM_CHAT_ID
  on_kill_switch: true
  on_data_stale: true
  on_emergency: true
  daily_summary: true
```

### 5.4 Atomic State Persistence (แก้ `basebot/portfolio.py`)

```python
def save(self, path=None):
    path = Path(path) if path else ROOT / "state" / "portfolio.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
    tmp.replace(path)  # atomic on same filesystem
```

### 5.5 Dependencies ที่ต้องเพิ่ม

```txt
# requirements.txt — เพิ่ม:
web3>=6.0.0          # for on-chain calls (GasPriceOracle, Multicall3)
sdnotify>=1.0        # systemd watchdog (Linux only)
```

---

## 6. ลำดับการพัฒนา

| Phase | สิ่งที่ทำ | ผลกระทบ | ความยาก | วันที่ (approx) |
|-------|----------|---------|---------|----------------|
| **Phase 1** | Tiered circuit breakers, trailing stops, atomic save | ลดความเสี่ยงสูง | ง่าย | 2-3 วัน |
| **Phase 2** | ATR indicator, volatility-adjusted sizing, OHLC data | ปรับปรุงผลตอบแทน | ง่าย | 2-3 วัน |
| **Phase 3** | ลบ Sentiment agent, structured logging | ประหยัดค่า LLM | ง่าย | 1 วัน |
| **Phase 4** | OnChain agent, connectivity kill switch, alerting | สัญญาณใหม่ + ปลอดภัย | กลาง | 3-4 วัน |
| **Phase 5** | Confidence-weighted consensus, gas-aware execution | คุณภาพ execution | กลาง | 2 วัน |
| **Phase 6** | Flashbots Protect, Multicall3, process watchdog | Production hardening | กลาง | 2-3 วัน |
| **Phase 7** | Liquidation cascade, LoRA fine-tuning | Alpha generation | ยาก | 1-2 สัปดาห์ |

**Phase 1-3:** ไม่ต้องเพิ่ม dependency ใหม่ ทำได้เลย
**Phase 4+:** ต้องมี API keys สำหรับ Glassnode/Basescan/CoinGlass
**Phase 7:** ต้องมี GPU สำหรับ fine-tuning

---

## Phase 3 Implementation Checklist (ลบ Sentiment + Structured Logging)

> **Status:** ✅ DONE — Phase 3 เสร็จสมบูรณ์

### Task A: ลบ Sentiment Agent ✅

- [x] A1. ลบ `basebot/agents/sentiment.py`
- [x] A2. แก้ `basebot/agents/__init__.py` — ลบ Sentiment import/export
- [x] A3. แก้ `basebot/agents/analyst.py`:
  - ลบ `sentiment: dict` param จาก `assess()`
  - เพิ่ม `recent: list[float]` param (ราคา 20 จุดล่าสุด)
  - SYSTEM prompt: ลบ "a sentiment score" — ให้ประเมินจาก price action เอง
  - user prompt: แทน `Sentiment: {...}` ด้วย `Recent prices: [...]`
- [x] A4. แก้ `basebot/orchestrator.py`:
  - ลบ `Sentiment` import + `self.sentiment` init
  - ลบ `senti = self.sentiment.score(...)` line
  - เปลี่ยน `self.analyst.assess(name, snap, senti, regime)` → `self.analyst.assess(name, snap, histories.get(cid, [])[-20:], regime)`
  - ใน proposal dict: ลบ `"sentiment": senti`
  - อัปเดต docstring (ลบ "Sentiment ->")
- [x] A5. แก้ `config.yaml` — ลบ `sentiment:` section
- [x] A6. อัปเดต docs: `CLAUDE.md`, `README.md`

### Task B: Structured Logging ✅

- [x] B1. สร้าง `basebot/logging.py`:
  - `JsonFormatter` — `{"ts", "level", "module", "message"}`
  - `setup_logging(log_file)` — RotatingFileHandler 10MB/10 backups + console
  - สร้าง `state/` dir อัตโนมัติ
- [x] B2. แก้ `run.py` — ใช้ `setup_logging()`, ส่ง logger ให้ Engine
- [x] B3. แก้ `basebot/engine.py` — ใช้ logger.info ผ่าน `log` param (ไม่ต้องแก้ engine.py เพิ่ม)
- [x] B4. อัปเดต docs: `CLAUDE.md` (ทำพร้อม A6)

### Verification ✅

- [x] `python -m compileall -q basebot run.py` — no syntax errors
- [x] `python run.py status` — loads normally
- [x] `from basebot.agents import Strategist, Analyst, RiskCritic` — works without Sentiment

---

## Phase 4 Implementation Checklist (OnChain + Connectivity Kill Switch + Alerting)

> **Status:** ✅ DONE — Phase 4 เสร็จสมบูรณ์

### Task A: OnChain Agent ✅

- [x] A1. สร้าง `basebot/agents/onchain.py`:
  - `_exchange_flow_signal()` — Glassnode API, normalize [-1, 1]
  - `_funding_rate_signal()` — Binance Futures public API, normalize [-1, 1]
  - `_whale_signal()` — Basescan API, ติดตาม wallet watchlist
  - `OnChainAgent` class — cache, weighted composite score, conviction
- [x] A2. แก้ `basebot/agents/__init__.py` — เพิ่ม OnChainAgent export
- [x] A3. แก้ `basebot/config.py` — เพิ่ม `onchain: dict` + `alerts: dict` fields
- [x] A4. แก้ `config.yaml` — เพิ่ม `onchain:` section (keys, weights, watchlist)

### Task B: Connectivity Kill Switch ✅

- [x] B1. แก้ `basebot/engine.py`:
  - เพิ่ม `_last_data_ts` + `_max_stale_sec` (3 cycles)
  - ก่อนดึงราคา: ตรวจ stale → ถ้าเกิน threshold + มี positions → ขายทุกอย่าง
  - อัปเดต `_last_data_ts` เมื่อดึงราคาสำเร็จ
  - เรียก `alerts.on_data_stale()` + `alerts.on_emergency()` เมื่อ kill switch ทำงาน

### Task C: Alert System ✅

- [x] C1. สร้าง `basebot/alerts.py`:
  - `AlertManager` class — Telegram Bot API
  - `on_kill_switch()` — แจ้งเมื่อ circuit breaker ทำงาน
  - `on_data_stale()` — แจ้งเมื่อ data feed นิ่ง
  - `on_emergency()` — แจ้งเมื่อ emergency liquidation
  - `on_daily_summary()` — สรุป P&L รายวัน
  - `on_llm_failure()` — แจ้งเมื่อ LLM fail ติดต่อกัน 3+ ครั้ง
- [x] C2. แก้ `config.yaml` — เพิ่ม `alerts:` section
- [x] C3. แก้ `.env.example` — เพิ่ม env vars สำหรับ API keys + Telegram

### Task D: Integration ✅

- [x] D1. แก้ `basebot/orchestrator.py`:
  - รับ `AlertManager` param + `OnChainAgent` init
  - เรียก `self.onchain.signals()` ทุก cycle
  - ใช้ `onchain_conviction` ใน chain conviction: `appetite × analyst_conv × onchain_conv`
  - เรียก `self.alerts.on_kill_switch()` เมื่อ circuit breaker ทำงาน
  - เรียก `self.alerts.on_emergency()` เมื่อ KILL
- [x] D2. แก้ `basebot/engine.py` — ส่ง `alerts` ให้ Orchestrator

### Verification ✅

- [x] `python -m compileall -q basebot run.py` — no syntax errors
- [x] `python run.py status` — loads normally
- [x] `from basebot.agents import Strategist, Analyst, RiskCritic, OnChainAgent` — works
- [x] `OnChainAgent({}).signals()` — ดึง funding rate จาก Binance สำเร็จ
- [x] `AlertManager({'enabled': False}).available` — False (expected)

---

## Phase 5 Implementation Checklist (Confidence-Weighted Consensus + Gas-Aware Execution)

> **Status:** ✅ DONE — Phase 5 เสร็จสมบูรณ์

### Task A: Confidence-Weighted Consensus ✅

- [x] A1. แก้ `basebot/orchestrator.py`:
  - เรียก RiskCritic ก่อนคำนวณ chain conviction (ย้ายขึ้นมาจากหลัง chain_conv check)
  - สูตรใหม่: `chain_conv = appetite × analyst_conv × onchain_conv × critic_size_factor`
  - ถ้า chain_conv < min_conviction → skip พร้อม log แสดงทุก factor
  - budget = max_buy_usd × chain_conv (clamp ไม่เกินเพดาน deterministic)
- [x] A2. อัปเดต docstring orchestrator — แสดงลำดับ pipeline ใหม่
- [x] A3. อัปเดต log format — แสดง app×ana×oc×critic breakdown

### Task B: Gas-Aware Execution ✅

- [x] B1. เพิ่ม `GasOracle` class ใน `basebot/executor.py`:
  - `_eth_call()` — raw eth_call ผ่าน JSON-RPC
  - `get_l1_fee(tx_bytes)` — เรียก GasPriceOracle.getL1Fee(bytes) สำหรับ L1 data cost
  - `get_gas_price()` — ดู L2 gas price (cache 12 วินาที)
  - `estimate_total_cost(gas_units, tx_bytes)` — รวม L2 execution + L1 data fee
- [x] B2. แก้ `TransactionBuilder.__init__()` — สร้าง GasOracle instance
- [x] B3. แก้ `TransactionBuilder.prepare_swap()` — เรียก GasOracle หลัง build_tx
- [x] B4. แก้ `LiveExecutor._format_quote_preview()` — แสดง L1/L2 breakdown
- [x] B5. แก้ `_request_user_approval()` — ส่ง tx_data ให้ preview

### Verification ✅

- [x] `python -m compileall -q basebot run.py` — no syntax errors
- [x] `python run.py status` — loads normally
- [x] `from basebot.executor import GasOracle` — imports correctly
- [x] `GasOracle().get_gas_price()` — ดึง L2 gas price จาก Base RPC สำเร็จ (1 gwei)
- [x] `GasOracle().estimate_total_cost(200000)` — คำนวณ gas cost สำเร็จ

---

## Phase 6 Implementation Checklist (Flashbots + Multicall3 + Watchdog)

> **Status:** ✅ DONE — Phase 6 เสร็จสมบูรณ์

### Task A: Flashbots Protect RPC Routing ✅

- [x] A1. แก้ `config.yaml` — เพิ่ม `live.submission_rpc` section:
  - `base_native`: "https://mainnet.base.org" (สำหรับ Base DEX swaps)
  - `l1_bridge`: "https://rpc.flashbots.net/fast" (สำหรับ L1 bridge operations)
- [x] A2. แก้ `basebot/executor.py` LiveExecutor:
  - เก็บ `_rpc_base_native` + `_rpc_l1_bridge` จาก config
  - `_submit_transaction(tx_data, operation)` — เลือก RPC ตาม operation type
  - ส่ง `rpcUrl` parameter ให้ MCP send_tx
  - buy/sell ใช้ `operation="swap"` (Base sequencer มี MEV resistance)

### Task B: Multicall3 Batch Reads ✅

- [x] B1. เพิ่ม `Multicall3Client` class ใน `basebot/executor.py`:
  - `_encode_aggregate3(calls)` — ABI encode สำหรับ aggregate3((address,bool,bytes)[])
  - `_decode_aggregate3(result, n)` — ABI decode result
  - `batch_balance_of(wallet, token_addresses)` — ดึง ERC-20 balance หลาย token ใน 1 RPC call
  - ใช้ urllib (ไม่เพิ่ม dependency)
- [x] B2. ทดสอบ — `Multicall3Client().batch_balance_of()` ทำงานสำเร็จ

### Task C: Process Watchdog ✅

- [x] C1. แก้ `basebot/engine.py`:
  - `_heartbeat(status, error)` — เขียน heartbeat JSON ทุก cycle (atomic write)
  - `check_health(path, max_age)` — static method สำหรับเช็คสถานะ
  - สถานะ: "ok" | "degraded" | "error"
  - Track cycle_count, positions, cash, error
- [x] C2. สร้าง `deploy/basebot.service` — systemd service file:
  - WatchdogSec=180 (3 นาที timeout)
  - Restart=on-failure, RestartSec=30
  - Security hardening (NoNewPrivileges, ProtectSystem)
- [x] C3. สร้าง `deploy/Dockerfile`:
  - Python 3.12-slim
  - HEALTHCHECK — เช็ค heartbeat ทุก 120s, timeout 300s
- [x] C4. สร้าง `deploy/docker-compose.yml`:
  - Volume mount สำหรับ state persistence
  - Resource limits (512MB, 0.5 CPU)
  - JSON file logging (10MB, 3 backups)
- [x] C5. เพิ่ม `health` CLI command ใน `run.py`:
  - `python run.py health` — เช็ค heartbeat status
  - exit code 0 = healthy, 1 = unhealthy
  - `--max-age` parameter

### Verification ✅

- [x] `python -m compileall -q basebot run.py` — no syntax errors
- [x] `python run.py status` — loads normally
- [x] `python run.py health` — returns "missing" (expected when bot not running)
- [x] `Multicall3Client().batch_balance_of()` — works
- [x] `Engine.check_health()` — returns correct status

---

## Phase 7 Implementation Checklist (Liquidation Cascade + LoRA Fine-tuning)

> **Status:** ✅ DONE — Phase 7 เสร็จสมบูรณ์

### Task A: Liquidation Cascade Detection ✅

- [x] A1. สร้าง `basebot/liquidation.py`:
  - `get_oi_history(symbol, period, limit)` — ดึง Open Interest history จาก Binance Futures
  - `get_current_oi(symbol)` — ดึง OI ปัจจุบัน
  - `detect_cascade(oi_history, price_history, lookback, threshold_pct)` — ตรวจ forced liquidations:
    - "long_cascade": OI ลด + ราคาลง = mean-reversion long entry
    - "short_cascade": OI ลด + ราคาขึ้น = mean-reversion short entry
  - `LiquidationDetector` class — cache, batch scan ทุกเหรียญ
- [x] A2. แก้ `basebot/orchestrator.py`:
  - Import + init `LiquidationDetector`
  - เรียก `self.liquidation.scan()` ทุก cycle
  - Cascade boost: 1.5x chain_conv เมื่อตรวจพบ cascade
  - Log cascade signals
- [x] A3. ทดสอบ — `LiquidationDetector().scan()` ดึง OI จาก Binance สำเร็จ

### Task B: LoRA Fine-tuning Infrastructure ✅

- [x] B1. สร้าง `basebot/training/collector.py`:
  - `TrainingCollector` class — บันทึก decisions + outcomes
  - `log_decision()` — บันทึก indicators, regime, onchain, cascade, action, conviction
  - `log_outcome()` — บันทึก PnL%, hold duration, exit reason
  - `get_stats()` — สถิติ training data
  - Output: JSONL files ใน `state/training/`
- [x] B2. สร้าง `basebot/training/dataset.py`:
  - `build_training_pairs()` — แปลง decisions+outcomes เป็น instruction tuning format
  - `export_for_finetune()` — ส่งออกเป็น messages JSONL สำหรับ fine-tune
  - `prepare_dataset()` — CLI entry point
  - กรองเฉพาะ profitable decisions เป็น positive examples
- [x] B3. สร้าง `basebot/training/train.py`:
  - `run_training()` — LoRA fine-tuning ด้วย Hugging Face transformers + peft
  - Support: Qwen2.5-7B-Instruct, LoRA rank 16, alpha 32
  - CLI: `python -m basebot.training.train --data ... --epochs 3`
  - Output: LoRA adapter weights + training config
- [x] B4. สร้าง `basebot/training/inference.py`:
  - `LoRAAdapter` class — โหลด fine-tuned model สำหรับ inference
  - `analyze(symbol, indicators, regime)` — ใช้ fine-tuned model วิเคราะห์
  - Fallback: ถ้าไม่มี adapter → return None (ให้ bot ใช้ OpenRouter)
  - `unload()` — 释放 GPU memory
- [x] B5. สร้าง `basebot/training/__init__.py` — package exports
- [x] B6. แก้ `basebot/engine.py` — import + init TrainingCollector

### Verification ✅

- [x] `python -m compileall -q basebot run.py` — no syntax errors
- [x] `python run.py status` — loads normally
- [x] `LiquidationDetector().scan(['ethereum'], ...)` — ดึง OI จาก Binance สำเร็จ
- [x] `TrainingCollector().log_decision()` + `log_outcome()` — บันทึกสำเร็จ
- [x] `prepare_dataset()` — สร้าง training pairs สำเร็จ

---

## ไฟล์ที่ต้องสร้าง/แก้

| ไฟล์ | การกระทำ |
|------|---------|
| `basebot/risk.py` | เขียนใหม่: trailing stops, tiered circuit breakers, ATR sizing |
| `basebot/indicators.py` | เพิ่ม ATR, Bollinger, VWAP |
| `basebot/portfolio.py` | เพิ่ม peak_price, atomic save |
| `basebot/orchestrator.py` | เพิ่ม OnChain agent, tiered risk, confidence consensus |
| `basebot/data.py` | เพิ่ม OHLC endpoint, DeFiLlama fallback |
| `basebot/engine.py` | Connectivity kill switch |
| `basebot/executor.py` | Gas-aware execution, dynamic slippage |
| `config.yaml` | เพิ่ม sections: onchain, expanded risk, alerts |
| `basebot/agents/onchain.py` | **ไฟล์ใหม่**: exchange flow + funding + whale |
| `basebot/agents/sentiment.py` | **ลบ** (รวมเข้า Analyst) |
| `basebot/alerts.py` | **ไฟล์ใหม่**: Telegram notifications |
| `basebot/logging.py` | **ไฟล์ใหม่**: structured JSON logging |
