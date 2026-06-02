"""ชั้น Multi-Agent: Strategist (Planner), Analyst, RiskCritic (Critic), OnChainAgent.

ทุกตัว degrade ได้: ถ้า LLM ไม่พร้อม -> orchestrator ใช้ค่า default/deterministic แทน.
OnChainAgent ไม่ใช้ LLM — ดึงสัญญาณจาก API แล้วคำนวณ deterministic ทั้งหมด.
"""
from .strategist import Strategist
from .analyst import Analyst
from .risk_critic import RiskCritic
from .onchain import OnChainAgent

__all__ = ["Strategist", "Analyst", "RiskCritic", "OnChainAgent"]
