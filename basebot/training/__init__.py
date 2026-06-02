"""Training package — LoRA fine-tuning infrastructure สำหรับ trading agent.

Modules:
  - collector: เก็บ trading decisions + outcomes
  - dataset: แปลงข้อมูลเป็น training format
  - train: LoRA fine-tuning script
  - inference: LoRA inference adapter
"""
from .collector import TrainingCollector
from .inference import LoRAAdapter

__all__ = ["TrainingCollector", "LoRAAdapter"]
