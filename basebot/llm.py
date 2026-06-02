"""ชั้นเชื่อม LLM ผ่าน OpenRouter (OpenAI-compatible) — ตัวเดียวที่ทุก agent ใช้ร่วมกัน.

- ใช้ OpenAI SDK ชี้ base_url ไป OpenRouter -> เข้าถึง DeepSeek / Qwen / Gemini ฯลฯ ในที่เดียว
- บังคับ JSON ด้วย response_format=json_object + แนบ schema ในระบบ prompt แล้ว parse แบบกันพลาด
- degrade ได้: ถ้าไม่มี key / SDK / error -> คืน None ให้ orchestrator fallback เป็น deterministic
"""
from __future__ import annotations

import json
import os
from typing import Any

try:
    from openai import OpenAI
except Exception:  # SDK ยังไม่ติดตั้ง
    OpenAI = None

OPENROUTER_BASE = "https://openrouter.ai/api/v1"


def _extract_json(text: str) -> dict | None:
    """ดึง JSON object ก้อนแรกจากข้อความ (เผื่อโมเดลห่อด้วย ```json หรือมีคำอธิบายนำ)."""
    if not text:
        return None
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1] if text.count("```") >= 2 else text.strip("`")
        if text.lstrip().startswith("json"):
            text = text.lstrip()[4:]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


class LLMClient:
    def __init__(self, log=print):
        self.log = log
        self._client = None
        self.usage = {"prompt": 0, "completion": 0, "calls": 0}
        key = os.environ.get("OPENROUTER_API_KEY")
        if OpenAI and key:
            try:
                self._client = OpenAI(
                    base_url=OPENROUTER_BASE,
                    api_key=key,
                    default_headers={  # OpenRouter ใช้ระบุแอป (ไม่บังคับ)
                        "HTTP-Referer": "https://localhost/base-trading-agent",
                        "X-Title": "Base Trading Agent",
                    },
                )
            except Exception as exc:  # noqa: BLE001
                self.log(f"[llm] init failed: {exc}")

    @property
    def available(self) -> bool:
        return self._client is not None

    def decide(
        self,
        *,
        model: str,
        system: str,
        user: str,
        schema: dict[str, Any],
        effort: str | None = None,  # คงไว้เพื่อ compat — OpenRouter ไม่ใช้
        max_tokens: int = 1200,
    ) -> dict | None:
        """เรียกโมเดลให้คืน JSON ตาม schema. คืน dict หรือ None ถ้าล้มเหลว."""
        if not self._client:
            return None

        # แนบ schema เข้าไปใน system เพื่อบังคับรูปแบบ (รองรับทุกโมเดลบน OpenRouter)
        sys_full = (
            f"{system}\n\nคืนค่าเป็น JSON object เดียวที่ตรงตาม JSON schema นี้ "
            f"(ห้ามมีข้อความอื่นนอก JSON):\n{json.dumps(schema, ensure_ascii=False)}"
        )
        try:
            resp = self._client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": sys_full},
                    {"role": "user", "content": user},
                ],
            )
        except Exception as exc:  # noqa: BLE001
            self.log(f"[llm] {model} error: {exc}")
            return None

        try:
            u = resp.usage
            self.usage["prompt"] += getattr(u, "prompt_tokens", 0) or 0
            self.usage["completion"] += getattr(u, "completion_tokens", 0) or 0
            self.usage["calls"] += 1
        except Exception:  # noqa: BLE001
            pass

        try:
            content = resp.choices[0].message.content
        except (AttributeError, IndexError):
            return None
        return _extract_json(content or "")
