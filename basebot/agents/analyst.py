"""Analyst — Qwen3-Coder-Flash. รวม indicator + recent prices + regime -> conviction + action.

ประเมิน momentum/sentiment จาก price action ตรงแทนที่จะพึ่ง Sentiment agent แยก.
"""
from __future__ import annotations

import json

SYSTEM = (
    "You are the Analyst agent for a Base-chain crypto trader. You receive a token's indicators "
    "(EMA crossover, RSI, trend, ATR, Bollinger Bands), recent price history, and the Strategist's "
    "market regime. Assess momentum and short-term sentiment from the price action, then decide a "
    "trading action and a conviction in [0, 1]. Prefer BUY only when momentum (golden cross / "
    "up-trend) aligns with non-overbought RSI and the regime is not risk_off. Prefer SELL/REDUCE "
    "when momentum breaks down. Otherwise HOLD. Respond ONLY via the schema."
)

SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["buy", "sell", "reduce", "hold"]},
        "conviction": {"type": "number"},
        "rationale": {"type": "string"},
    },
    "required": ["action", "conviction", "rationale"],
    "additionalProperties": False,
}


class Analyst:
    def __init__(self, llm, cfg: dict):
        self.llm = llm
        self.cfg = cfg
        self.model = cfg.get("model", "claude-haiku-4-5")
        self.effort = cfg.get("effort")  # ปกติ Haiku ไม่มี -> None

    def assess(self, name: str, snapshot: dict, recent: list[float], regime: dict) -> dict:
        """ประเมิน action + conviction จาก indicators, recent prices, และ regime."""
        if not self.cfg.get("enabled", True) or not self.llm.available:
            return self._fallback(snapshot)
        user = (
            f"Token: {name}\n"
            f"Indicators: {json.dumps(snapshot, ensure_ascii=False)}\n"
            f"Recent prices (last 20): {json.dumps([round(p, 6) for p in recent[-20:]])}\n"
            f"Regime: {json.dumps(regime, ensure_ascii=False)}"
        )
        out = self.llm.decide(
            model=self.model, system=SYSTEM, user=user,
            schema=SCHEMA, effort=self.effort, max_tokens=400,
        )
        return out or self._fallback(snapshot)

    @staticmethod
    def _fallback(snapshot: dict) -> dict:
        """กลยุทธ์ deterministic — Confluence (หลาย indicator ต้องตรงกัน).

        Phase 8: ใช้ EMA + RSI + MACD + Bollinger Bands + ADX + Volume
        ไม่เทรดถ้า indicator ไม่เห็นตรงกัน
        """
        cross = snapshot.get("cross")
        rsi = snapshot.get("rsi")
        trend_up = snapshot.get("trend_up")
        price = snapshot.get("price")
        n_points = snapshot.get("n_points", 0)

        # ข้อมูลไม่พอ → ไม่เทรด
        if n_points < 30:
            return {"action": "hold", "conviction": 0.0, "rationale": "insufficient data"}

        # MACD
        macd_hist = snapshot.get("macd_hist")
        macd_bullish = snapshot.get("macd_bullish")

        # Bollinger Bands
        bb_upper = snapshot.get("bb_upper")
        bb_lower = snapshot.get("bb_lower")

        # ADX (trend strength)
        adx_val = snapshot.get("adx")
        adx_trend = snapshot.get("adx_trend")  # ADX > 25

        # Volume
        volume_ratio = snapshot.get("volume_ratio")  # current / average

        # Stochastic
        stoch_k = snapshot.get("stoch_k")

        # ── SELL conditions (ตรงข้อเดียวก็ขาย) ──
        if cross == "death":
            return {"action": "sell", "conviction": 0.7, "rationale": "death cross"}
        if rsi is not None and rsi > 78:
            return {"action": "sell", "conviction": 0.65, "rationale": f"RSI overbought ({rsi:.0f})"}
        if macd_hist is not None and macd_hist < 0 and snapshot.get("trend_up") is False:
            return {"action": "sell", "conviction": 0.55, "rationale": "MACD bearish + downtrend"}
        if bb_upper and price and price > bb_upper:
            return {"action": "sell", "conviction": 0.6, "rationale": "price above Bollinger upper"}
        if stoch_k is not None and stoch_k > 85 and rsi is not None and rsi > 70:
            return {"action": "sell", "conviction": 0.6, "rationale": "Stoch+RSI overbought"}

        # ── BUY conditions (ต้องมี confluence — หลายตัวเห็นตรงกัน) ──
        buy_signals = 0
        buy_reasons = []
        has_ohlc = macd_hist is not None  # มี OHLC data → indicators ทำงานครบ

        # Signal 1: EMA golden cross หรือ uptrend
        if cross == "golden":
            buy_signals += 2  # crossover มีน้ำหนักมาก
            buy_reasons.append("golden cross")
        elif trend_up:
            buy_signals += 1
            buy_reasons.append("uptrend")

        # Signal 2: RSI ไม่ overbought
        if rsi is not None and rsi < 65:
            buy_signals += 1
            buy_reasons.append(f"RSI ok ({rsi:.0f})")
        elif rsi is not None and rsi > 70:
            buy_signals -= 1  # RSI สูง = หักคะแน
            buy_reasons.append(f"RSI high ({rsi:.0f})")

        # Signal 3: MACD bullish (ต้องมี OHLC data)
        if macd_bullish:
            buy_signals += 1
            buy_reasons.append("MACD bullish")

        # Signal 4: Price near BB lower (โอกาสซื้อ)
        if bb_lower and price and price < bb_lower * 1.02:
            buy_signals += 1
            buy_reasons.append("near BB lower")

        # Signal 5: ADX confirms trend (ต้องมี OHLC data)
        if adx_trend:
            buy_signals += 1
            buy_reasons.append(f"ADX={adx_val:.0f}")

        # Signal 6: Volume confirmation (ถ้ามี)
        if volume_ratio is not None and volume_ratio > 0.8:
            buy_signals += 1
            buy_reasons.append(f"vol={volume_ratio:.1f}x")
        elif volume_ratio is not None and volume_ratio < 0.5:
            buy_signals -= 1  # volume ต่ำ = หักคะแน
            buy_reasons.append("low vol")

        # ปรับ threshold ตาม data availability:
        # - มี OHLC ครบ → ต้อง 3 สัญญาณ
        # - ไม่มี OHLC (ใช้แค่ EMA/RSI) → ต้อง 2 สัญญาณ (golden cross + RSI ok)
        min_signals = 3 if has_ohlc else 2

        if buy_signals >= min_signals:
            conv = min(0.85, 0.5 + buy_signals * 0.05)
            return {"action": "buy", "conviction": conv,
                    "rationale": f"confluence ({buy_signals}): {', '.join(buy_reasons)}"}

        # ── Standalone signals (ไม่ต้อง confluence) ──

        # MACD histogram crossover (histogram จากลบเป็นบวก = momentum เปลี่ยน)
        if has_ohlc and macd_hist is not None and macd_hist > 0 and rsi is not None and rsi < 60:
            return {"action": "buy", "conviction": 0.55,
                    "rationale": f"MACD hist flip bullish (RSI={rsi:.0f})"}

        # Oversold bounce (RSI < 30 + uptrend) — ใช้ได้ทุกกรณี
        if trend_up and rsi is not None and rsi < 30:
            return {"action": "buy", "conviction": 0.55, "rationale": f"oversold bounce (RSI={rsi:.0f})"}

        # RSI oversold + near BB lower (double oversold)
        if rsi is not None and rsi < 35 and bb_lower and price and price < bb_lower * 1.03:
            return {"action": "buy", "conviction": 0.6,
                    "rationale": f"RSI oversold ({rsi:.0f}) + near BB lower"}

        return {"action": "hold", "conviction": 0.0, "rationale": "no confluence"}
