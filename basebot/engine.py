"""Engine — ลูปเทรด 24 ชม. ดึงราคา -> คำนวณ indicator -> orchestrator -> บันทึก -> sleep.

Phase 4: เพิ่ม connectivity kill switch (data stale detection) + alert integration
Phase 6: เพิ่ม heartbeat healthcheck สำหรับ process watchdog (systemd/Docker)
"""
from __future__ import annotations

import json
import signal
import time
from datetime import datetime, timezone
from pathlib import Path

from . import data
from .alerts import AlertManager
from .config import Config
from .indicators import snapshot
from .llm import LLMClient
from .orchestrator import Orchestrator
from .portfolio import Portfolio
from .executor import PaperExecutor, LiveExecutor, LiveExecutionError
from .risk import RiskManager, RiskParams
from .training.collector import TrainingCollector


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class Engine:
    def __init__(self, cfg: Config, log=print):
        self.cfg = cfg
        self.log = log
        self.ids = [s.id for s in cfg.symbols]
        self.name_of = {s.id: s.name for s in cfg.symbols}
        # ประวัติราคาในหน่วยความจำ (ต่อเหรียญ) — warmup จาก history ตอนเริ่ม
        self.histories: dict[str, list[float]] = {cid: [] for cid in self.ids}
        self.ohlc_histories: dict[str, list[dict]] = {cid: [] for cid in self.ids}
        # Phase 8: Daily trend data สำหรับ multi-timeframe
        self.daily_trends: dict[str, str] = {}  # coin_id -> "up" | "down" | "neutral"

        self.pf = Portfolio.load(cfg.starting_cash, float(cfg.risk.get("fee_pct", 0.003)))
        self.risk = RiskManager(RiskParams.from_cfg(cfg.risk))
        if cfg.mode == "live":
            self.ex = LiveExecutor(self.pf, cfg.live, log=log)
        else:
            self.ex = PaperExecutor(self.pf)
        self.llm = LLMClient(log=log)
        self.alerts = AlertManager(cfg.alerts)
        self.orch = Orchestrator(cfg, self.llm, self.pf, self.ex, self.risk, log=log, alerts=self.alerts)
        # Phase 7: Training data collection สำหรับ LoRA fine-tuning
        self.collector = TrainingCollector()
        self._running = True

        # Connectivity kill switch — ติดตาม data freshness
        self._last_data_ts: float = time.time()
        self._max_stale_sec: float = float(cfg.poll_interval_sec) * 3

        # Phase 6: Heartbeat healthcheck — เขียนไฟล์ทุก cycle ให้ systemd/Docker เช็ค
        self._heartbeat_path = Path(cfg.raw.get("heartbeat_path", "state/heartbeat.json"))
        self._heartbeat_interval = int(cfg.poll_interval_sec)  # เขียนทุกรอบ
        self._last_heartbeat_ts: float = 0
        self._cycle_count: int = 0
        self._last_error: str = ""

    def _heartbeat(self, status: str = "ok", error: str = "") -> None:
        """เขียน heartbeat file สำหรับ process watchdog.

        systemd/Docker สามารถเช็คไฟล์นี้เพื่อยืนยันว่า bot ยังทำงานอยู่
        ถ้าไฟล์เก่าเกิน threshold → process ถือว่า unhealthy

        สถานะ: "ok" | "degraded" (มี error แต่ยังทำงาน) | "error" (หยุดรอบ)
        """
        now = time.time()
        if now - self._last_heartbeat_ts < self._heartbeat_interval:
            return  # ยังไม่ถึงเวลาเขียน

        self._last_heartbeat_ts = now
        if error:
            self._last_error = error

        heartbeat = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "unix_ts": now,
            "status": status,
            "cycle_count": self._cycle_count,
            "positions": len(self.pf.positions),
            "cash": round(self.pf.cash, 2),
            "error": self._last_error if status != "ok" else "",
        }

        try:
            self._heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._heartbeat_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(heartbeat, indent=2), encoding="utf-8")
            tmp.replace(self._heartbeat_path)  # atomic write
        except OSError:
            pass  # heartbeat failure ไม่ควรหยุด bot

    @staticmethod
    def check_health(heartbeat_path: str = "state/heartbeat.json",
                     max_age_sec: int = 300) -> dict:
        """เช็คสถานะ health ของ bot — ใช้โดย systemd/Docker healthcheck.

        คืน dict:
        {
            "healthy": bool,
            "status": str,        # "ok" | "stale" | "missing" | "error"
            "age_sec": float,     # อายุ heartbeat (วินาที)
            "cycle_count": int,
            "message": str,
        }
        """
        path = Path(heartbeat_path)
        if not path.exists():
            return {
                "healthy": False, "status": "missing", "age_sec": float("inf"),
                "cycle_count": 0, "message": "heartbeat file not found",
            }

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {
                "healthy": False, "status": "error", "age_sec": float("inf"),
                "cycle_count": 0, "message": "heartbeat file corrupt",
            }

        age = time.time() - data.get("unix_ts", 0)
        status = data.get("status", "unknown")
        cycle = data.get("cycle_count", 0)

        if age > max_age_sec:
            return {
                "healthy": False, "status": "stale", "age_sec": age,
                "cycle_count": cycle,
                "message": f"heartbeat stale ({age:.0f}s > {max_age_sec}s)",
            }

        if status == "error":
            return {
                "healthy": False, "status": "error", "age_sec": age,
                "cycle_count": cycle,
                "message": f"bot reports error: {data.get('error', 'unknown')}",
            }

        return {
            "healthy": True, "status": status, "age_sec": age,
            "cycle_count": cycle, "message": "bot is running",
        }

    def _update_daily_trends(self) -> None:
        """Phase 8: ดึง daily klines เพื่อคำนวณ daily trend (multi-timeframe).

        Daily trend = EMA 20 > EMA 50 ของ daily close prices
        ถ้า daily trend = up → อนุญาต BUY, ถ้า down → อนุญาตเฉพาะ SELL
        """
        from .indicators import ema as calc_ema
        for cid in self.ids:
            sym = data._COINGECKO_TO_BINANCE.get(cid)
            if not sym:
                continue
            try:
                daily_klines = data._binance_klines(sym, "1d", 60)
                if len(daily_klines) < 50:
                    self.daily_trends[cid] = "neutral"
                    continue
                closes = [k["close"] for k in daily_klines]
                fast_ema = calc_ema(closes, 20)
                slow_ema = calc_ema(closes, 50)
                if fast_ema[-1] > slow_ema[-1]:
                    self.daily_trends[cid] = "up"
                else:
                    self.daily_trends[cid] = "down"
                self.log(f"  {self.name_of[cid]} daily trend: {self.daily_trends[cid]}")
            except Exception:
                self.daily_trends[cid] = "neutral"

    def _warmup(self) -> None:
        self.log(f"[{_ts()}] warmup: ดึงราคาย้อนหลัง {self.cfg.warmup_days} วัน...")
        for cid in self.ids:
            try:
                self.histories[cid] = data.history(cid, self.cfg.warmup_days, self.cfg.base_currency)
                self.log(f"  {self.name_of[cid]}: {len(self.histories[cid])} จุด")
            except data.DataError as exc:
                self.log(f"  {self.name_of[cid]}: warmup ล้มเหลว ({exc})")

        # Phase 8: ดึง OHLC + volume จาก Binance สำหรับ indicators ใหม่
        self.log(f"  ดึง OHLC + volume จาก Binance...")
        for cid in self.ids:
            try:
                ohlc_data = data.ohlc(cid, max(self.cfg.warmup_days, 30), self.cfg.base_currency)
                if ohlc_data:
                    self.ohlc_histories[cid] = ohlc_data
                    self.log(f"  {self.name_of[cid]} OHLC: {len(ohlc_data)} bars")
            except data.DataError:
                self.log(f"  {self.name_of[cid]} OHLC: ข้าม")

        # Phase 8: ดึง daily trend สำหรับ multi-timeframe
        self._update_daily_trends()

    def _cycle(self) -> None:
        self._cycle_count += 1
        cycle_error = ""

        # ── Connectivity Kill Switch ──
        # ถ้า data feed นิ่งเกิน threshold → ขายทุกอย่างแล้วหยุดรอบ
        stale_sec = time.time() - self._last_data_ts
        if stale_sec > self._max_stale_sec and self.pf.positions:
            self.log(f"[{_ts()}] 🚨 DATA STALE {stale_sec:.0f}s — ขายทุกอย่าง!")
            sold = []
            for cid in list(self.pf.positions.keys()):
                px = self.histories[cid][-1] if self.histories[cid] else None
                if px:
                    t = self.pf.sell(cid, px, "data_stale_kill")
                    if t:
                        sold.append(self.name_of.get(cid, cid))
                        self.log(f"  🔻 SELL {self.name_of.get(cid, cid)} @ {px:.4f} — data_stale")
            self.alerts.on_data_stale(stale_sec, len(sold))
            self.alerts.on_emergency("data_stale", sold)
            self.pf.save()
            self._heartbeat(status="error", error=f"data_stale_{stale_sec:.0f}s")
            return

        try:
            prices = data.current_prices(self.ids, self.cfg.base_currency)
            self._last_data_ts = time.time()  # อัปเดต timestamp เมื่อดึงราคาสำเร็จ
        except data.DataError as exc:
            cycle_error = str(exc)
            self.log(f"[{_ts()}] ดึงราคาล้มเหลว: {exc}")
            self._heartbeat(status="error", error=cycle_error)
            return
        if not prices:
            self.log(f"[{_ts()}] ไม่ได้ราคาเลย ข้ามรอบ")
            self._heartbeat(status="degraded", error="no_prices")
            return

        snapshots: dict[str, dict] = {}
        for cid, px in prices.items():
            self.histories[cid].append(px)
            self.histories[cid] = self.histories[cid][-500:]  # จำกัดหน่วยความจำ

            # Phase 8: ดึง OHLC data (highs, lows, volumes) สำหรับ indicators ใหม่
            ohlc_data = self.ohlc_histories.get(cid, [])
            highs = [b["high"] for b in ohlc_data] if ohlc_data else None
            lows = [b["low"] for b in ohlc_data] if ohlc_data else None
            volumes = [b["volume"] for b in ohlc_data] if ohlc_data and "volume" in ohlc_data[0] else None

            snap = snapshot(self.histories[cid], self.cfg.strategy,
                            highs=highs, lows=lows, volumes=volumes)
            snap["name"] = self.name_of[cid]

            # Phase 8: เพิ่ม daily trend
            snap["daily_trend"] = self.daily_trends.get(cid, "neutral")

            snapshots[cid] = snap

        try:
            self.orch.step(snapshots, self.histories, prices, self.name_of)
        except LiveExecutionError as exc:
            cycle_error = str(exc)
            self.log(f"[{_ts()}] live execution error (ข้ามรอบ): {exc}")
        except Exception as exc:
            cycle_error = str(exc)
            self.log(f"[{_ts()}] orchestrator error (ข้ามรอบ): {exc}")

        eq = self.pf.equity(prices)
        pnl = (eq - self.pf.start_cash) / self.pf.start_cash * 100
        held = ", ".join(self.name_of[c] for c in self.pf.positions) or "-"
        self.log(f"[{_ts()}] equity=${eq:,.2f} ({pnl:+.2f}%) | cash=${self.pf.cash:,.2f} | ถือ: {held}")

        # Broadcast portfolio state to dashboard (non-blocking)
        self.orch.broadcast.broadcast_portfolio(
            equity=eq, cash=self.pf.cash, pnl_pct=pnl / 100,
            positions=len(self.pf.positions), trades_today=len(self.pf.trades)
        )
        self.pf.save()

        # Phase 6: เขียน heartbeat ทุก cycle
        self._heartbeat(status="ok" if not cycle_error else "degraded", error=cycle_error)

    def run(self) -> None:
        def _stop(*_):
            self.log("\nกำลังหยุด... บันทึกพอร์ต")
            self._running = False
        signal.signal(signal.SIGINT, _stop)
        signal.signal(signal.SIGTERM, _stop)

        if self.cfg.mode == "live":
            dry = self.cfg.live.get("dry_run", True)
            mode = "LIVE-DRY (จำลองธุรกรรม)" if dry else "LIVE (เงินจริง!)"
        else:
            mode = "PAPER (จำลอง)"
        llm_on = "ON" if self.llm.available else "OFF (deterministic)"
        self.log(f"=== Base Trading Agent | mode={mode} | LLM={llm_on} | "
                 f"{len(self.ids)} เหรียญ | ทุก {self.cfg.poll_interval_sec}s ===")
        self._warmup()

        while self._running:
            self._cycle()
            for _ in range(self.cfg.poll_interval_sec):
                if not self._running:
                    break
                time.sleep(1)

        self.pf.save()
        u = self.llm.usage
        if u["calls"]:
            self.log(f"LLM calls={u['calls']} prompt_tok={u['prompt']} completion_tok={u['completion']}")
        self.log("บันทึกแล้ว ลาก่อน 👋")
