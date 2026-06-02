"""Backtest — รีเพลย์ราคาย้อนหลังผ่านกลยุทธ์ deterministic (ไม่เรียก LLM เพื่อความเร็ว/ประหยัด).

ใช้ Analyst._fallback (EMA cross + RSI) + RiskManager เพื่อประเมินกลยุทธ์ฐานก่อนเปิดบอทจริง.
"""
from __future__ import annotations

from . import data
from .agents.analyst import Analyst
from .config import Config
from .indicators import snapshot
from .portfolio import Portfolio
from .risk import RiskManager, RiskParams, RiskLevel


def run_backtest(cfg: Config, days: int = 90, log=print) -> dict:
    risk = RiskManager(RiskParams.from_cfg(cfg.risk))
    pf = Portfolio(cfg.starting_cash, float(cfg.risk.get("fee_pct", 0.003)))
    warm = max(int(cfg.strategy.get("ema_slow", 26)) + 5, 30)

    series: dict[str, list[float]] = {}
    ohlc_series: dict[str, list[dict]] = {}
    for s in cfg.symbols:
        try:
            series[s.id] = data.history(s.id, days, cfg.base_currency)
            log(f"  {s.name}: {len(series[s.id])} จุด")
        except data.DataError as exc:
            log(f"  {s.name}: โหลดล้มเหลว ({exc})")
            series[s.id] = []
        try:
            ohlc_series[s.id] = data.ohlc(s.id, days, cfg.base_currency)
        except data.DataError:
            ohlc_series[s.id] = []

    length = min((len(v) for v in series.values() if v), default=0)
    if length <= warm:
        log("ข้อมูลย้อนหลังไม่พอสำหรับ backtest")
        return {}

    name_of = {s.id: s.name for s in cfg.symbols}
    for i in range(warm, length):
        prices = {cid: v[i] for cid, v in series.items() if len(v) > i}

        # ขายตามกฎความเสี่ยง (อัปเดต peak_price ก่อน)
        for cid in list(pf.positions.keys()):
            px = prices.get(cid)
            if px:
                pos = pf.positions.get(cid)
                if pos:
                    pos.peak_price = max(pos.peak_price, px)
                if r := risk.exit_reason(pf, cid, px):
                    pf.sell(cid, px, r)
        risk_level, _ = risk.assess_risk_level(pf, prices)
        if risk_level >= RiskLevel.KILL:
            # emergency liquidation
            for cid in list(pf.positions.keys()):
                px = prices.get(cid)
                if px:
                    pf.sell(cid, px, "backtest_kill")
            continue
        if risk_level >= RiskLevel.HALTED:
            continue

        # Phase 8: คำนวณ indicators ใหม่ (MACD, ADX, Bollinger, Volume)
        for cid, v in series.items():
            if len(v) <= i:
                continue
            bars = ohlc_series.get(cid, [])
            # ตัด OHLC ให้ยาวเท่ากับ price history (CoinGecko OHLC มี fewer bars)
            if bars:
                # OHLC bars อาจน้อยกว่า price points — ใช้เท่าที่มี
                n_prices = i + 1
                n_bars = min(len(bars), n_prices)
                recent_bars = bars[:n_bars]
                highs = [b["high"] for b in recent_bars]
                lows = [b["low"] for b in recent_bars]
                volumes = [b["volume"] for b in recent_bars] if "volume" in recent_bars[0] else None
                # ตัด prices ให้ยาวเท่ากับ OHLC (สำหรับ indicator calculation)
                prices_slice = v[max(0, n_prices - n_bars):n_prices]
            else:
                highs, lows, volumes = None, None, None
                prices_slice = v[:i + 1]

            snap = snapshot(prices_slice, cfg.strategy, highs=highs, lows=lows, volumes=volumes)
            view = Analyst._fallback(snap)
            px = prices[cid]

            # Phase 8: Volume filter
            vol_ratio = snap.get("volume_ratio")
            if vol_ratio is not None and vol_ratio < 0.3:
                continue

            # Phase 8: Pair lock check
            if pf.is_locked(cid):
                continue

            if view["action"] == "buy" and view["conviction"] >= 0.5:
                atr_val = snap.get("atr")
                atr_values = {cid: atr_val} if atr_val else {}
                budget = risk.max_buy_usd(
                    pf, cid, prices, risk_level,
                    atr=atr_val, atr_values=atr_values
                ) * view["conviction"]
                if budget > 1:
                    pf.buy(cid, budget, px, view["rationale"])
            elif view["action"] == "sell" and cid in pf.positions:
                pf.sell(cid, px, view["rationale"])

    final_prices = {cid: v[length - 1] for cid, v in series.items() if len(v) >= length}
    eq = pf.equity(final_prices)
    ret = (eq - pf.start_cash) / pf.start_cash * 100
    wins = sum(1 for t in pf.trades if t.side == "sell")
    log("─" * 50)
    log(f"Backtest {days} วัน | เทรด {len(pf.trades)} ครั้ง")
    log(f"เริ่ม ${pf.start_cash:,.2f} -> จบ ${eq:,.2f}  ({ret:+.2f}%)")
    return {"equity": eq, "return_pct": ret, "trades": len(pf.trades), "sells": wins}
