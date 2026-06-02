"""LoRA Inference Adapter — ใช้ fine-tuned LoRA model ใน bot.

โหลด LoRA adapter ที่ train แล้ว → ใช้แทน base model สำหรับ Analyst agent
ถ้าไม่มี adapter → fallback เป็น base model (ผ่าน OpenRouter)

Usage:
  from basebot.training.inference import LoRAAdapter
  adapter = LoRAAdapter("state/training/lora_output")
  result = adapter.analyze(symbol="ETH", indicators={...}, regime={...})
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent


class LoRAAdapter:
    """LoRA inference adapter สำหรับ Analyst agent.

    ถ้ามี fine-tuned model → ใช้ locally
    ถ้าไม่มี → fallback เป็น None (ให้ bot ใช้ OpenRouter ตามปกติ)
    """

    def __init__(self, model_dir: str | Path | None = None):
        self.model_dir = Path(model_dir) if model_dir else ROOT / "state" / "training" / "lora_output"
        self._model = None
        self._tokenizer = None
        self._loaded = False
        self._config = {}

    @property
    def available(self) -> bool:
        """ตรวจสอบว่ามี fine-tuned model พร้อมใช้."""
        if not self.model_dir.exists():
            return False
        # ต้องมี adapter weights
        adapter_file = self.model_dir / "adapter_model.safetensors"
        adapter_bin = self.model_dir / "adapter_model.bin"
        return adapter_file.exists() or adapter_bin.exists()

    def load(self) -> bool:
        """โหลด LoRA model + tokenizer."""
        if self._loaded:
            return True
        if not self.available:
            return False

        try:
            import torch
            from peft import PeftModel
            from transformers import AutoModelForCausalLM, AutoTokenizer

            # โหลด training config
            config_path = self.model_dir / "training_config.json"
            if config_path.exists():
                with open(config_path) as f:
                    self._config = json.load(f)

            base_model = self._config.get("base_model", "Qwen/Qwen2.5-7B-Instruct")
            print(f"Loading base model: {base_model}...")

            # โหลด base model
            self._tokenizer = AutoTokenizer.from_pretrained(
                str(self.model_dir), trust_remote_code=True
            )
            base = AutoModelForCausalLM.from_pretrained(
                base_model,
                torch_dtype=torch.float16,
                device_map="auto",
                trust_remote_code=True,
            )

            # โหลด LoRA adapter
            print(f"Loading LoRA adapter from {self.model_dir}...")
            self._model = PeftModel.from_pretrained(base, str(self.model_dir))
            self._model.eval()
            self._loaded = True

            print("LoRA model loaded successfully")
            return True

        except Exception as exc:
            print(f"Failed to load LoRA model: {exc}")
            return False

    def analyze(self, symbol: str, indicators: dict, regime: dict,
                onchain: dict | None = None, cascade: dict | None = None,
                max_tokens: int = 300) -> dict | None:
        """วิเคราะห์ trading scenario ด้วย fine-tuned model.

        Returns:
            {"action": str, "conviction": float, "rationale": str} หรือ None ถ้า fail
        """
        if not self._loaded and not self.load():
            return None

        # สร้าง prompt
        input_data = {
            "symbol": symbol,
            "price": indicators.get("price"),
            "indicators": indicators,
            "regime": regime,
            "onchain": onchain or {},
            "cascade": cascade or {},
        }

        messages = [
            {"role": "system", "content": (
                "You are a crypto trading analyst for Base chain tokens. "
                "Analyze the following trading scenario and decide: action (buy/sell/reduce/hold), "
                "conviction (0-1), and rationale."
            )},
            {"role": "user", "content": json.dumps(input_data, ensure_ascii=False)},
        ]

        try:
            import torch

            # แปลงเป็น prompt
            prompt = self._tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            inputs = self._tokenizer(prompt, return_tensors="pt").to(self._model.device)

            # Generate
            with torch.no_grad():
                outputs = self._model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=0.1,
                    top_p=0.9,
                    do_sample=False,
                )

            # Decode
            response = self._tokenizer.decode(
                outputs[0][inputs["input_ids"].shape[1]:],
                skip_special_tokens=True,
            )

            # Parse JSON response
            return self._parse_response(response)

        except Exception as exc:
            print(f"LoRA inference error: {exc}")
            return None

    def _parse_response(self, response: str) -> dict | None:
        """Parse model response เป็น structured output."""
        # ลองหา JSON ใน response
        response = response.strip()

        # ลอง parse ทั้งหมด
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # ลองหา JSON block
        import re
        json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        return None

    def unload(self) -> None:
        """unload model เพื่อ释放 memory."""
        self._model = None
        self._tokenizer = None
        self._loaded = False
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
