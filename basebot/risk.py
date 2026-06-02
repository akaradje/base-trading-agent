"""กฎความเสี่ยงแบบ deterministic — บังคับเสมอ ไม่ว่าชั้น LLM จะตัดสินใจอย่างไร.

นี่คือ "ตาข่ายนิรภัย": LLM แนะนำ/กรอง/ลดขนาดได้ แต่ stop-loss, take-profit,
เพดานขนาดโพซิชัน, trailing stop และ tiered circuit breakers บังคับด้วยโค้ดล้วน

Phase 1 เพิ่ม:
- Tiered circuit breakers: NORMAL → REDUCED → HALTED → KILL
- Trailing stop: ป้องกันกำไรที่ได้แล้ว ด้วย peak price tracking
"""
from __future__ import annotations

from dataclasses import dataclass

from .portfolio import Portfolio


# ──────────────────────────────────────────────
# Risk Levels — ระดับความเสี่ยงแบบขั้นบันได
# ──────────────────────────────────────────────

class RiskLevel:
    """ระดับความเสี่ยงของพอร์ต — ใช้ตัดสินใจว่าจะเทรดแค่ไหน."""
    NORMAL = 0      # ทำงานปกติ
    REDUCED = 1     # ลด size เหลือ 50%
    HALTED = 2      # หยุดเปิดไม้ใหม่ (ขายได้เท่านั้น)
    KILL = 3        # ขายทุกอย่าง (emergency liquidation)

    _NAMES = {0: "NORMAL", 1: "REDUCED", 2: "HALTED", 3: "KILL"}

    @classmethod
    def name(cls, level: int) -> str:
        return cls._NAMES.get(level, f"UNKNOWN({level})")


# ──────────────────────────────────────────────
# Risk Parameters
# ──────────────────────────────────────────────

@dataclass
class RiskParams:
    # Position sizing
    max_position_pct: float = 0.25

    # Fixed stop-loss / take-profit (จาก entry price)
    stop_loss_pct: float = 0.05
    take_profit_pct: float = 0.12

    # Fee
    fee_pct: float = 0.003

    # Trailing stop — ป้องกันกำไรที่ได้แล้ว
    trailing_stop_pct: float = 0.03              # ลดลง 3% จาก peak → ขาย
    trailing_stop_activate_pct: float = 0.05     # เริ่ม trailing เมื่อกำไร >= 5%

    # Tiered circuit breakers — ตอบสนองแบบขั้นบันได
    drawdown_warn_pct: float = 0.10              # REDUCED: ลด size เหลือ 50%
    drawdown_halt_pct: float = 0.15              # HALTED: หยุดเปิดไม้ใหม่
    drawdown_kill_pct: float = 0.20              # KILL: ขายทุกอย่าง

    # Backward compat — เก็บไว้แต่ใช้ drawdown_kill_pct แทน
    max_drawdown_pct: float = 0.20

    @classmethod
    def from_cfg(cls, cfg: dict) -> "RiskParams":
        return cls(
            max_position_pct=float(cfg.get("max_position_pct", 0.25)),
            stop_loss_pct=float(cfg.get("stop_loss_pct", 0.05)),
            take_profit_pct=float(cfg.get("take_profit_pct", 0.12)),
            fee_pct=float(cfg.get("fee_pct", 0.003)),
            trailing_stop_pct=float(cfg.get("trailing_stop_pct", 0.03)),
            trailing_stop_activate_pct=float(cfg.get("trailing_stop_activate_pct", 0.05)),
            drawdown_warn_pct=float(cfg.get("drawdown_warn_pct", 0.10)),
            drawdown_halt_pct=float(cfg.get("drawdown_halt_pct", 0.15)),
            drawdown_kill_pct=float(cfg.get("drawdown_kill_pct", 0.20)),
            max_drawdown_pct=float(cfg.get("max_drawdown_pct", 0.20)),
        )


# ──────────────────────────────────────────────
# Risk Manager — บังคับกฎความเสี่ยงทั้งหมด
# ──────────────────────────────────────────────

class RiskManager:
    def __init__(self, params: RiskParams):
        self.p = params

    # ---- Tiered Circuit Breakers ----

    def assess_risk_level(self, pf: Portfolio, prices: dict[str, float]) -> tuple[int, str]:
        """ประเมินระดับความเสี่ยงของพอร์ตแบบขั้นบันได.

        คืน (risk_level, reason_string)
        - NORMAL: ทำงานปกติ
        - REDUCED: ลด size เหลือ 50%
        - HALTED: หยุดเปิดไม้ใหม่
        - KILL: ขายทุกอย่าง
        """
        eq = pf.equity(prices)
        pf.peak_equity = max(pf.peak_equity, eq)
        if pf.peak_equity <= 0:
            return RiskLevel.NORMAL, ""

        drawdown = (pf.peak_equity - eq) / pf.peak_equity

        # KILL — drawdown เกิน kill threshold → emergency liquidation
        if drawdown >= self.p.drawdown_kill_pct:
            return RiskLevel.KILL, f"drawdown {drawdown:.1%} >= {self.p.drawdown_kill_pct:.0%}"

        # HALTED — drawdown เกิน halt threshold → หยุดเปิดไม้ใหม่
        if drawdown >= self.p.drawdown_halt_pct:
            return RiskLevel.HALTED, f"drawdown {drawdown:.1%} >= {self.p.drawdown_halt_pct:.0%}"

        # REDUCED — drawdown เกิน warn threshold → ลด size
        if drawdown >= self.p.drawdown_warn_pct:
            return RiskLevel.REDUCED, f"drawdown {drawdown:.1%} >= {self.p.drawdown_warn_pct:.0%}"

        # ตรวจแพ้ติดต่อกัน per symbol (3 ครั้งติด → REDUCED)
        for sym in list(pf.positions.keys()):
            consecutive = self._count_consecutive_losses(pf, sym)
            if consecutive >= 3:
                return RiskLevel.REDUCED, f"{sym}: แพ้ {consecutive} ครั้งติด"

        return RiskLevel.NORMAL, ""

    def _count_consecutive_losses(self, pf: Portfolio, symbol: str) -> int:
        """นับจำนวนเทรดที่ขาดทุนติดต่อกันสำหรับเหรียญนี้."""
        count = 0
        for t in reversed(pf.trades):
            if t.symbol != symbol:
                continue
            if t.side != "sell":
                continue
            # ถ้าขายได้ราคาต่ำกว่า entry → ขาดทุน
            if hasattr(t, "entry_price") and t.entry_price > 0:
                if t.price < t.entry_price:
                    count += 1
                else:
                    break
            else:
                # fallback: ดูจาก reason
                if "loss" in t.reason.lower() or "stop" in t.reason.lower():
                    count += 1
                else:
                    break
        return count

    # ---- Trailing Stop + Stop-Loss / Take-Profit ----

    def exit_reason(self, pf: Portfolio, symbol: str, price: float) -> str | None:
        """ตรวจเงื่อนไขขาย: stop-loss, take-profit, trailing stop, ROI decay.

        ลำดับการตรวจ:
        1. Hard stop-loss (จาก entry price) — ทำงานเสมอ
        2. ROI decay (time-based profit taking) — Phase 8
        3. Take-profit ceiling — ขายเมื่อกำไรถึงเป้า
        4. Trailing stop — ขายเมื่อราคาลดลงจาก peak (เปิดใช้เมื่อกำไรถึง threshold)
        """
        pos = pf.positions.get(symbol)
        if not pos or pos.entry_price == 0:
            return None

        upnl = (price - pos.entry_price) / pos.entry_price

        # 1. Hard stop-loss (เสมอ)
        if upnl <= -self.p.stop_loss_pct:
            return f"stop_loss ({upnl:.1%})"

        # 2. Phase 8: ROI decay — time-based profit taking
        roi_reason = self._roi_decay_exit(pos, upnl)
        if roi_reason:
            return roi_reason

        # 3. Take-profit ceiling
        if upnl >= self.p.take_profit_pct:
            return f"take_profit ({upnl:.1%})"

        # 4. Trailing stop — เปิดใช้เมื่อกำไร >= activate threshold
        if pos.peak_price > 0 and upnl >= self.p.trailing_stop_activate_pct:
            trail_price = pos.peak_price * (1 - self.p.trailing_stop_pct)
            if price <= trail_price:
                drop_from_peak = (pos.peak_price - price) / pos.peak_price
                return f"trailing_stop (peak={pos.peak_price:.4f}, drop={drop_from_peak:.1%})"

        return None

    def _roi_decay_exit(self, pos, upnl: float) -> str | None:
        """Phase 8: ROI Decay — time-based profit taking.

        กำไรเป้าลดลงตามเวลาที่ถือ:
        - ทันที: กำไร 5% → ขาย
        - 30 นาที: กำไร 3% → ขาย
        - 1 ชม.: กำไร 2% → ขาย
        - 4 ชม.: กำไร 1% → ขาย
        - 24 ชม.: break-even → ขาย

        ใช้เมื่อกำไรถึงเป้าตามเวลาที่ถือ ไม่ต้องรอถึง take_profit_pct คงที่
        """
        import time
        from datetime import datetime, timezone

        if upnl <= 0:
            return None

        # คำนวณเวลาที่ถือ (ชั่วโมง)
        try:
            opened = datetime.fromisoformat(pos.opened_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            hours_held = (now - opened).total_seconds() / 3600
        except (ValueError, AttributeError):
            return None

        # ROI decay thresholds
        roi_thresholds = [
            (0.0, 0.05),     # ทันที: กำไร 5% → ขาย
            (0.5, 0.03),     # 30 นาที: กำไร 3% → ขาย
            (1.0, 0.02),     # 1 ชม.: กำไร 2% → ขาย
            (4.0, 0.01),     # 4 ชม.: กำไร 1% → ขาย
            (24.0, 0.0),     # 24 ชม.: break-even → ขาย
        ]

        for min_hours, min_pnl in roi_thresholds:
            if hours_held >= min_hours and upnl >= min_pnl:
                return f"roi_decay ({hours_held:.1f}h, {upnl:.1%})"

        return None

    # ---- Position Sizing ----

    def max_buy_usd(self, pf: Portfolio, symbol: str, prices: dict[str, float],
                    risk_level: int = RiskLevel.NORMAL,
                    atr: float | None = None,
                    atr_values: dict[str, float] | None = None) -> float:
        """เงินสูงสุดที่ลงเพิ่มในเหรียญนี้ได้.

        - ไม่ให้เกินเพดาน max_position_pct ของพอร์ต
        - ถ้า risk_level = REDUCED → ลด size เหลือ 50%
        - ถ้า risk_level >= HALTED → ห้ามเปิดไม้ใหม่ (คืน 0)
        - ถ้ามี ATR → ปรับ size ตามความผันผวน (volatility-adjusted sizing)
        """
        # HALTED หรือ KILL → ห้ามซื้อ
        if risk_level >= RiskLevel.HALTED:
            return 0.0

        eq = pf.equity(prices)
        cap = eq * self.p.max_position_pct

        # ATR-weighted sizing: เหรียญผันผวนสูง → position เล็กลง
        if atr is not None and atr > 0 and atr_values and symbol in atr_values:
            values = sorted(v for v in atr_values.values() if v > 0)
            if len(values) >= 2:
                median_atr = values[len(values) // 2]
                # ผันผวนสูงกว่า median → ลด size, ต่ำกว่า → เพิ่ม size (clamped 0.25-2.0)
                vol_mult = max(0.25, min(2.0, median_atr / atr))
                cap *= vol_mult
        held = pf.position_value(symbol, prices.get(symbol, 0.0))
        available = max(0.0, min(cap - held, pf.cash))

        # REDUCED → ลด size เหลือ 50%
        if risk_level >= RiskLevel.REDUCED:
            available *= 0.5

        return available
