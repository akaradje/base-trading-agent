"""พอร์ตจำลอง: เงินสด, โพซิชัน, การบันทึกเทรด, mark-to-market. มี persistence เป็น JSON."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

from .config import ROOT


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Position:
    qty: float
    entry_price: float
    opened_at: str = field(default_factory=_now)
    peak_price: float = 0.0   # ราคาสูงสุดตั้งแต่เข้า position (สำหรับ trailing stop)


@dataclass
class Trade:
    ts: str
    symbol: str
    side: str          # buy | sell
    qty: float
    price: float
    fee: float
    reason: str
    cash_after: float
    tx_hash: str = ""         # on-chain tx hash (ว่างสำหรับ paper trades)
    mode: str = "paper"       # "paper" หรือ "live" — แยกประเภทเทรด


class Portfolio:
    def __init__(self, cash: float, fee_pct: float):
        self.cash = cash
        self.start_cash = cash
        self.fee_pct = fee_pct
        self.positions: dict[str, Position] = {}
        self.trades: list[Trade] = []
        self.peak_equity = cash
        # Phase 8: Pair locking — ล็อกเหรียญหลังขาย (ป้องกัน re-entry ทันที)
        self._pair_locks: dict[str, float] = {}  # symbol -> unlock_timestamp (unix)
        self._pair_lock_hours: float = 12.0  # ล็อก 12 ชั่วโมง

    # ---- valuation ----
    def equity(self, prices: dict[str, float]) -> float:
        total = self.cash
        for sym, pos in self.positions.items():
            px = prices.get(sym, pos.entry_price)
            total += pos.qty * px
        return total

    def position_value(self, symbol: str, price: float) -> float:
        pos = self.positions.get(symbol)
        return pos.qty * price if pos else 0.0

    def unrealized_pct(self, symbol: str, price: float) -> float | None:
        pos = self.positions.get(symbol)
        if not pos or pos.entry_price == 0:
            return None
        return (price - pos.entry_price) / pos.entry_price

    # ---- pair locking ----
    def is_locked(self, symbol: str) -> bool:
        """เช็คว่าเหรียญถูกล็อกอยู่หรือไม่."""
        import time
        unlock_ts = self._pair_locks.get(symbol)
        if unlock_ts is None:
            return False
        if time.time() >= unlock_ts:
            del self._pair_locks[symbol]
            return False
        return True

    def lock_pair(self, symbol: str, hours: float | None = None) -> None:
        """ล็อกเหรียญหลังขาย — ป้องกัน re-entry ทันที."""
        import time
        h = hours if hours is not None else self._pair_lock_hours
        self._pair_locks[symbol] = time.time() + h * 3600

    def lock_remaining(self) -> dict[str, float]:
        """คืน dict ของเหรียญที่ยังล็อกอยู่ (สำหรับ logging)."""
        import time
        now = time.time()
        return {s: (ts - now) / 3600 for s, ts in self._pair_locks.items() if ts > now}

    # ---- trading ----
    def buy(self, symbol: str, usd_amount: float, price: float, reason: str, **meta) -> Trade | None:
        usd_amount = min(usd_amount, self.cash)
        if usd_amount <= 0 or price <= 0:
            return None
        fee = usd_amount * self.fee_pct
        qty = (usd_amount - fee) / price
        if qty <= 0:
            return None
        self.cash -= usd_amount
        pos = self.positions.get(symbol)
        if pos:  # ถัวเฉลี่ย
            total_qty = pos.qty + qty
            pos.entry_price = (pos.entry_price * pos.qty + price * qty) / total_qty
            pos.qty = total_qty
        else:
            self.positions[symbol] = Position(qty=qty, entry_price=price, peak_price=price)
        return self._record(symbol, "buy", qty, price, fee, reason, **meta)

    def sell(self, symbol: str, price: float, reason: str, fraction: float = 1.0, **meta) -> Trade | None:
        pos = self.positions.get(symbol)
        if not pos or price <= 0:
            return None
        qty = pos.qty * max(0.0, min(fraction, 1.0))
        if qty <= 0:
            return None
        gross = qty * price
        fee = gross * self.fee_pct
        self.cash += gross - fee
        pos.qty -= qty
        if pos.qty <= 1e-12:
            del self.positions[symbol]
            # Phase 8: ล็อกเหรียญหลังขายหมด (ไม่ล็อกถ้าขายบางส่วน)
            self.lock_pair(symbol)
        return self._record(symbol, "sell", qty, price, fee, reason, **meta)

    def _record(self, symbol, side, qty, price, fee, reason, **meta) -> Trade:
        t = Trade(
            ts=_now(), symbol=symbol, side=side, qty=qty, price=price,
            fee=fee, reason=reason, cash_after=self.cash,
            tx_hash=meta.get("tx_hash", ""),
            mode=meta.get("mode", "paper"),
        )
        self.trades.append(t)
        return t

    # ---- persistence ----
    def to_dict(self) -> dict:
        return {
            "cash": self.cash,
            "start_cash": self.start_cash,
            "fee_pct": self.fee_pct,
            "peak_equity": self.peak_equity,
            "positions": {k: asdict(v) for k, v in self.positions.items()},
            "trades": [asdict(t) for t in self.trades],
            "pair_locks": self._pair_locks,
        }

    def save(self, path: str | Path | None = None) -> None:
        path = Path(path) if path else ROOT / "state" / "portfolio.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        # เขียน .tmp แล้ว rename — ป้องกันไฟล์ corrupt ถ้า crash ระหว่างเขียน
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        tmp.replace(path)

    @classmethod
    def load(cls, cash: float, fee_pct: float, path: str | Path | None = None) -> "Portfolio":
        path = Path(path) if path else ROOT / "state" / "portfolio.json"
        if not path.exists():
            return cls(cash, fee_pct)
        d = json.loads(path.read_text(encoding="utf-8"))
        p = cls(d.get("start_cash", cash), d.get("fee_pct", fee_pct))
        p.cash = d.get("cash", cash)
        p.peak_equity = d.get("peak_equity", p.cash)
        p.positions = {k: Position(**v) for k, v in d.get("positions", {}).items()}
        p.trades = [Trade(**t) for t in d.get("trades", [])]
        p._pair_locks = d.get("pair_locks", {})
        return p
