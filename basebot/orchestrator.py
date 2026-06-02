"""Orchestrator — ประสานทุก agent เป็นลูป Planner -> Analyst -> Critic -> Executor.

ลำดับการตัดสินใจต่อ 1 รอบ:
  0. RiskManager: kill switch + ตรวจ stop-loss/take-profit ของโพซิชันที่ถือ (deterministic, มาก่อนเสมอ)
  1. Strategist (Planner): มุมมองตลาดรวม (cache ตาม refresh_min)
  2. OnChain Agent: สัญญาณ on-chain (exchange flow, funding rate, whale)
  3. Liquidation Cascade Detection: ตรวจ forced liquidations (mean-reversion signal)
  4. ต่อเหรียญ: Analyst -> RiskCritic -> Confidence-weighted consensus
  5. RiskManager clamp ขนาดอีกชั้น แล้วส่งให้ Executor

Phase 5: Confidence-weighted consensus — chain_conv = appetite × analyst × onchain × critic_size
Phase 7: Cascade boost — 1.5x เมื่อตรวจพบ liquidation cascade
"""
from __future__ import annotations

from .alerts import AlertManager
from .agents import Strategist, Analyst, RiskCritic
from .agents.onchain import OnChainAgent
from .broadcaster import AgentBroadcaster
from .executor import Executor
from .liquidation import LiquidationDetector
from .portfolio import Portfolio
from .risk import RiskManager, RiskLevel
from .training.collector import TrainingCollector


class Orchestrator:
    def __init__(self, cfg, llm, portfolio: Portfolio, executor: Executor,
                 risk: RiskManager, log=print, alerts: AlertManager | None = None):
        self.cfg = cfg
        self.pf = portfolio
        self.ex = executor
        self.risk = risk
        self.log = log
        self.alerts = alerts or AlertManager({})
        self.broadcast = AgentBroadcaster(cfg.raw.get("dashboard", {}))
        self.strategist = Strategist(llm, cfg.agent("strategist"))
        self.analyst = Analyst(llm, cfg.agent("analyst"))
        self.critic = RiskCritic(llm, cfg.agent("risk_critic"))
        self.onchain = OnChainAgent(cfg.onchain)
        self.liquidation = LiquidationDetector(cfg.raw.get("liquidation", {}))
        self.collector = TrainingCollector()
        self.min_conviction = float(cfg.agent("risk_critic").get("min_conviction", 0.40))

    def step(self, snapshots: dict[str, dict], histories: dict[str, list[float]],
             prices: dict[str, float], name_of: dict[str, str]) -> None:
        # 0) อัปเดต peak_price แล้วขายตามกฎความเสี่ยง (ไม่สนสัญญาณ LLM)
        for cid in list(self.pf.positions.keys()):
            px = prices.get(cid)
            if px is None:
                continue
            # อัปเดตราคาสูงสุดสำหรับ trailing stop
            pos = self.pf.positions.get(cid)
            if pos:
                pos.peak_price = max(pos.peak_price, px)
            reason = self.risk.exit_reason(self.pf, cid, px)
            if reason:
                try:
                    t = self.ex.sell(cid, px, reason)
                    if t:
                        self.log(f"  🔻 SELL {name_of.get(cid, cid)} @ {px:.4f} — {reason}")
                except Exception as exc:
                    self.log(f"  ⚠️ SELL {name_of.get(cid, cid)} ล้มเหลว: {exc}")

        # 1) Tiered circuit breakers — ประเมินระดับความเสี่ยง
        self.broadcast.set_working("risk", "Assessing portfolio risk level...")
        risk_level, risk_reason = self.risk.assess_risk_level(self.pf, prices)
        self.broadcast.set_idle("risk", f"Risk: {RiskLevel.name(risk_level)}")
        if risk_level >= RiskLevel.KILL:
            self.log(f"  🚨 KILL: {risk_reason} — ขายทุกอย่าง!")
            sold = []
            for cid in list(self.pf.positions.keys()):
                px = prices.get(cid)
                if px:
                    try:
                        t = self.ex.sell(cid, px, f"EMERGENCY: {risk_reason}")
                        if t:
                            sold.append(name_of.get(cid, cid))
                    except Exception as exc:
                        self.log(f"  ⚠️ emergency sell {cid} ล้มเหลว: {exc}")
            self.alerts.on_kill_switch("KILL", risk_reason, len(sold))
            self.alerts.on_emergency(risk_reason, sold)
            return
        if risk_level >= RiskLevel.HALTED:
            self.log(f"  🛑 HALTED: {risk_reason} — หยุดเปิดไม้ใหม่")
            self.alerts.on_kill_switch("HALTED", risk_reason, len(self.pf.positions))
            return
        if risk_level >= RiskLevel.REDUCED:
            self.log(f"  ⚠️ REDUCED: {risk_reason} — ลด size 50%")
            self.alerts.on_kill_switch("REDUCED", risk_reason, len(self.pf.positions))

        # 2) Planner
        self.broadcast.set_working("strategist", "Analyzing market regime...")
        regime = self.strategist.view(snapshots)
        allowed = set(regime.get("allowed_symbols") or [])  # ว่าง = อนุญาตทุกเหรียญ
        appetite = float(regime.get("risk_appetite", 0.5))
        if regime.get("regime") == "risk_off" or appetite <= 0:
            self.log(f"  🧭 regime={regime.get('regime')} appetite={appetite:.2f} — Planner สั่งงดเปิดไม้")
            self.broadcast.set_sleeping("strategist", f"Regime: {regime.get('regime')} — งดเปิดไม้")
            self.broadcast.set_sleeping("analyst", "รอสัญญาณจาก Strategist")
            self.broadcast.set_sleeping("critic", "ไม่มีออเดอร์ให้ตรวจ")
            return
        self.broadcast.set_idle("strategist", f"Regime: {regime['regime']} ({appetite:.0%})")

        # 2.5) On-chain signals — ดึง once ต่อ cycle
        self.broadcast.set_working("onchain", "Scanning blockchain signals...")
        onchain = self.onchain.signals()
        onchain_conviction = max(0.0, onchain.get("conviction", 0.0))
        onchain_composite = onchain.get("composite_score", 0.0)
        if onchain.get("summary") and onchain_composite != 0:
            self.log(f"  🔗 on-chain: {onchain['summary']} (composite={onchain_composite:+.2f})")
        self.broadcast.set_idle("onchain", onchain.get("summary", "No data"))

        # 2.6) Liquidation Cascade Detection — ตรวจ forced liquidations
        cascade_signals = self.liquidation.scan(list(snapshots.keys()), histories)
        for cid, sig in cascade_signals.items():
            if sig.get("cascade"):
                self.log(f"  💥 CASCADE {name_of.get(cid, cid)}: {sig['summary']}")

        # 3) รวบรวม ATR values ทุกเหรียญ (สำหรับ volatility-adjusted sizing)
        atr_values = {cid: snap.get("atr", 0) for cid, snap in snapshots.items() if snap.get("atr")}

        for cid, snap in snapshots.items():
            name = name_of.get(cid, cid)
            px = prices.get(cid)
            if px is None:
                continue
            if allowed and name not in allowed and cid not in allowed:
                continue

            # Phase 8: Volume filter — ข้ามถ้า volume ต่ำเกินไป
            volume_ratio = snap.get("volume_ratio")
            if volume_ratio is not None and volume_ratio < 0.3:
                self.broadcast.set_idle("analyst", f"{name}: low vol ({volume_ratio:.1f}x)")
                continue

            # Phase 8: Pair lock check — ข้ามถ้าเหรียญถูกล็อก
            if self.pf.is_locked(cid):
                locked = self.pf.lock_remaining()
                hours = locked.get(cid, 0)
                self.broadcast.set_idle("analyst", f"{name}: locked ({hours:.1f}h)")
                continue

            # Phase 8: Daily trend filter — ถ้า daily trend = down → ไม่ BUY
            daily_trend = snap.get("daily_trend", "neutral")

            recent = histories.get(cid, [])[-20:]
            self.broadcast.set_working("analyst", f"Analyzing {name}...")
            view = self.analyst.assess(name, snap, recent, regime)
            action = view.get("action", "hold")
            conv = float(view.get("conviction", 0.0))
            self.broadcast.set_idle("analyst", f"{name}: {action} ({conv:.0%})")

            # บันทึก training data ทุก decision (สำหรับ LoRA fine-tuning)
            self.collector.log_decision(
                symbol=name, price=px, action=action, conviction=conv,
                rationale=view.get("rationale", ""),
                indicators=snap, regime=regime,
                onchain={"composite": onchain_composite, "conviction": onchain_conviction},
                cascade=cascade_signals.get(cid, {}),
                analyst_output=view,
            )

            # ขาย/ลดตามคำแนะนำ analyst (ถ้ามีของถือ)
            if action in ("sell", "reduce") and cid in self.pf.positions:
                frac = 1.0 if action == "sell" else 0.5
                try:
                    self.broadcast.set_working("engine", f"Executing {action.upper()} {name}...")
                    t = self.ex.sell(cid, px, f"analyst:{view.get('rationale','')[:40]}", fraction=frac)
                    if t:
                        self.log(f"  🔻 {action.upper()} {name} @ {px:.4f} — conv={conv:.2f}")
                        self.broadcast.broadcast_trade(name, action, px, t.qty, view.get("rationale", ""))
                        self.broadcast.set_idle("engine", f"{action.upper()} {name} @ {px:.4f}")
                except Exception as exc:
                    self.log(f"  ⚠️ {action.upper()} {name} ล้มเหลว: {exc}")
                    self.broadcast.set_error("engine", f"{action.upper()} {name} failed")
                continue

            if action != "buy" or conv < self.min_conviction:
                continue

            # Phase 8: Daily trend filter — ถ้า daily trend = down → ลด conviction 50%
            if daily_trend == "down":
                conv *= 0.5
                self.log(f"  📉 {name} daily trend DOWN — ลด conviction เหลือ {conv:.2f}")
                if conv < self.min_conviction:
                    continue

            # 4) RiskCritic — เรียกก่อน chain conviction เพื่อเอา size_factor
            max_budget = self.risk.max_buy_usd(
                self.pf, cid, prices, risk_level,
                atr=snap.get("atr"), atr_values=atr_values
            )
            proposal = {
                "symbol": name, "price": px, "proposed_usd": round(max_budget, 2),
                "conviction": conv, "analyst": view,
                "indicators": snap, "regime": regime,
                "portfolio": {"cash": round(self.pf.cash, 2),
                              "equity": round(self.pf.equity(prices), 2)},
            }
            self.broadcast.set_working("critic", f"Reviewing {name} order...")
            verdict = self.critic.review(proposal)
            if not verdict.get("approved"):
                self.log(f"  🛡️ VETO {name} — {verdict.get('reason','')[:60]}")
                self.broadcast.set_thinking("critic", f"VETO {name}: {verdict.get('reason','')[:40]}")
                continue
            critic_size = float(verdict.get("size_factor", 0.5))
            self.broadcast.set_idle("critic", f"{name}: Approved ({critic_size:.0%})")

            # 5) Confidence-weighted consensus:
            #    chain_conv = analyst_conv × critic_size × appetite_boost × onchain_boost × cascade_boost
            #    Phase 8: appetite/on-chain เป็น boost (0.5-1.5) ไม่ใช่ multiplier ตรงๆ
            #    ถ้า neutral → 1.0 (ไม่กระทบ), ถ้า bullish → >1.0, ถ้า bearish → <1.0
            appetite_boost = 0.5 + appetite  # appetite 0-1 → boost 0.5-1.5
            oc_boost = 1.0
            if onchain_composite > 0.1:
                oc_boost = 1.0 + onchain_composite  # bullish → boost
            elif onchain_composite < -0.1:
                oc_boost = max(0.5, 1.0 + onchain_composite)  # bearish → reduce (min 0.5)
            # Cascade boost: ถ้ามี liquidation cascade → เพิ่ม conviction 1.5x (mean-reversion opportunity)
            cascade_data = cascade_signals.get(cid, {})
            cascade_boost = 1.5 if cascade_data.get("cascade") else 1.0
            chain_conv = conv * critic_size * appetite_boost * oc_boost * cascade_boost
            if chain_conv < self.min_conviction:
                self.log(f"  ⏭️ {name} — chain_conv={chain_conv:.2f} ต่ำกว่า min {self.min_conviction} "
                         f"(ana={conv:.2f}×critic={critic_size:.2f}×app_boost={appetite_boost:.2f}"
                         f"×oc_boost={oc_boost:.2f}{'×cascade=1.50' if cascade_boost > 1 else ''})")
                continue

            # 6) คำนวณขนาด position จาก chain conviction
            budget = max_budget * chain_conv
            usd = min(budget, max_budget)  # clamp ไม่ให้เกินเพดาน deterministic
            if usd <= 1:
                continue
            try:
                self.broadcast.set_working("engine", f"Executing BUY {name}...")
                t = self.ex.buy(cid, usd, px, f"approved conv={conv:.2f}")
                if t:
                    self.log(f"  🟢 BUY {name} ${usd:.2f} @ {px:.4f} — "
                             f"chain={chain_conv:.2f} (app×ana×oc×critic)")
                    self.broadcast.broadcast_trade(name, "buy", px, usd / px, f"conv={conv:.2f}")
                    self.broadcast.set_idle("engine", f"BUY {name} ${usd:.2f} executed")
            except Exception as exc:
                self.log(f"  ⚠️ BUY {name} ล้มเหลว: {exc}")
                self.broadcast.set_error("engine", f"BUY {name} failed: {exc}")
