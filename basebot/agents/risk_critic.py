"""RiskCritic (Critic) — Sonnet 4.6. ตรวจ/วีโต้ทุกออเดอร์ก่อนส่งให้ Executor.

สำคัญ: critic นี้ "ลดขนาด/ปฏิเสธ" ได้เท่านั้น — เพิ่มขนาดเกินเพดาน deterministic ไม่ได้
(orchestrator จะ clamp ด้วย RiskManager อีกชั้นเสมอ).
"""
from __future__ import annotations

import json

SYSTEM = (
    "You are the Risk Critic, the final gate before any order executes in a Base-chain trader. "
    "You receive a proposed order with the Analyst's reasoning and current portfolio context. "
    "Approve only if the trade is prudent given trend, RSI extremes, sentiment, and concentration. "
    "You may shrink position size (size_factor in [0,1]) but never enlarge it. Veto (approve=false) "
    "anything that looks like chasing a pump, catching a falling knife, or over-concentrating. "
    "Respond ONLY via the schema."
)

SCHEMA = {
    "type": "object",
    "properties": {
        "approved": {"type": "boolean"},
        "size_factor": {"type": "number", "description": "0..1 สัดส่วนของขนาดที่เสนอ"},
        "reason": {"type": "string"},
    },
    "required": ["approved", "size_factor", "reason"],
    "additionalProperties": False,
}


class RiskCritic:
    def __init__(self, llm, cfg: dict):
        self.llm = llm
        self.cfg = cfg
        self.model = cfg.get("model", "claude-sonnet-4-6")
        self.effort = cfg.get("effort", "medium")
        self.min_conviction = float(cfg.get("min_conviction", 0.55))

    def review(self, proposal: dict) -> dict:
        # Phase 8: ถ้า LLM ไม่พร้อม -> อนุมัติ 80% (ให้ deterministic risk คุมต่อ)
        if not self.cfg.get("enabled", True) or not self.llm.available:
            return {"approved": True, "size_factor": 0.8, "reason": "no-critic fallback"}
        user = "Proposed order + context:\n" + json.dumps(proposal, ensure_ascii=False, indent=2)
        out = self.llm.decide(
            model=self.model, system=SYSTEM, user=user,
            schema=SCHEMA, effort=self.effort, max_tokens=400,
        )
        if not out:
            return {"approved": True, "size_factor": 0.8, "reason": "critic error -> cautious"}
        # บังคับ size_factor อยู่ใน [0,1]
        out["size_factor"] = max(0.0, min(1.0, float(out.get("size_factor", 0.0))))
        return out
