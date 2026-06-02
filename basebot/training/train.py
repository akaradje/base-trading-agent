"""LoRA Fine-tuning Script — fine-tune Qwen model สำหรับ trading decisions.

ใช้ Hugging Face transformers + peft (LoRA) framework
Training data: JSONL format จาก dataset.py

Requirements:
  pip install torch transformers peft datasets accelerate

Usage:
  python -m basebot.training.train --data state/training/finetune_dataset.jsonl --epochs 3

หมายเหตุ: ต้องมี GPU อย่างน้อย 16GB VRAM (RTX 3090/4090 หรือ AWS g5.xlarge)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent


def check_dependencies() -> bool:
    """ตรวจสอบว่ามี dependencies ที่จำเป็นครบ."""
    missing = []
    for pkg in ["torch", "transformers", "peft", "datasets"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"Missing dependencies: {', '.join(missing)}")
        print(f"Install with: pip install {' '.join(missing)}")
        return False
    return True


def load_dataset(path: str | Path) -> list[dict]:
    """โหลด training dataset จาก JSONL file."""
    path = Path(path)
    if not path.exists():
        print(f"Dataset not found: {path}")
        return []
    data = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return data


def format_messages(example: dict) -> str:
    """แปลง messages format เป็น single text สำหรับ training."""
    messages = example.get("messages", [])
    parts = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        parts.append(f"<|{role}|>\n{content}")
    return "\n".join(parts) + "<|end|>"


def run_training(data_path: str | Path,
                 base_model: str = "Qwen/Qwen2.5-7B-Instruct",
                 output_dir: str | Path | None = None,
                 epochs: int = 3,
                 batch_size: int = 4,
                 learning_rate: float = 2e-4,
                 lora_rank: int = 16,
                 lora_alpha: int = 32,
                 max_seq_length: int = 2048) -> dict:
    """รัน LoRA fine-tuning.

    Args:
        data_path: path ไป training dataset JSONL
        base_model: ชื่อ model จาก Hugging Face
        output_dir: ที่เก็บ fine-tuned model
        epochs: จำนวน training epochs
        batch_size: batch size ต่อ GPU
        learning_rate: learning rate
        lora_rank: LoRA rank (r)
        lora_alpha: LoRA alpha
        max_seq_length: ความยาว sequence สูงสุด

    Returns:
        {"output_dir": str, "train_samples": int, "epochs": int}
    """
    if not check_dependencies():
        sys.exit(1)

    import torch
    from datasets import Dataset
    from peft import LoraConfig, get_peft_model, TaskType
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        TrainingArguments,
        Trainer,
        DataCollatorForSeq2Seq,
    )

    data_path = Path(data_path)
    if output_dir is None:
        output_dir = ROOT / "state" / "training" / "lora_output"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # โหลด dataset
    print(f"Loading dataset from {data_path}...")
    raw_data = load_dataset(data_path)
    if not raw_data:
        print("No training data found. Run collector + dataset first.")
        return {"error": "no data"}

    print(f"Loaded {len(raw_data)} training samples")

    # โหลด model + tokenizer
    print(f"Loading base model: {base_model}...")
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )

    # LoRA config
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=lora_rank,
        lora_alpha=lora_alpha,
        lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        bias="none",
    )

    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # เตรียม dataset
    print("Preparing dataset...")

    def tokenize_fn(examples):
        texts = [format_messages(ex) for ex in examples]
        encodings = tokenizer(
            texts,
            truncation=True,
            max_length=max_seq_length,
            padding="max_length",
            return_tensors="pt",
        )
        encodings["labels"] = encodings["input_ids"].clone()
        return encodings

    dataset = Dataset.from_list(raw_data)
    tokenized = dataset.map(
        tokenize_fn,
        batched=True,
        remove_columns=dataset.column_names,
    )

    # Training arguments
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        learning_rate=learning_rate,
        weight_decay=0.01,
        warmup_ratio=0.1,
        lr_scheduler_type="cosine",
        logging_steps=10,
        save_strategy="epoch",
        fp16=True,
        gradient_accumulation_steps=4,
        report_to="none",  # ไม่ส่งไป wandb/tensorboard
    )

    # Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized,
        data_collator=DataCollatorForSeq2Seq(tokenizer, padding=True),
    )

    # เริ่ม training
    print(f"Starting LoRA fine-tuning for {epochs} epochs...")
    trainer.train()

    # บันทึก model
    print(f"Saving LoRA adapter to {output_dir}...")
    model.save_pretrained(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    # บันทึก training config
    config = {
        "base_model": base_model,
        "lora_rank": lora_rank,
        "lora_alpha": lora_alpha,
        "epochs": epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "train_samples": len(raw_data),
        "max_seq_length": max_seq_length,
    }
    with open(output_dir / "training_config.json", "w") as f:
        json.dump(config, f, indent=2)

    print("Training complete!")
    return {
        "output_dir": str(output_dir),
        "train_samples": len(raw_data),
        "epochs": epochs,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LoRA fine-tuning for trading agent")
    parser.add_argument("--data", required=True, help="Path to training dataset JSONL")
    parser.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct",
                        help="Base model name")
    parser.add_argument("--output", default=None, help="Output directory")
    parser.add_argument("--epochs", type=int, default=3, help="Training epochs")
    parser.add_argument("--batch-size", type=int, default=4, help="Batch size")
    parser.add_argument("--lr", type=float, default=2e-4, help="Learning rate")
    parser.add_argument("--lora-rank", type=int, default=16, help="LoRA rank")
    parser.add_argument("--lora-alpha", type=int, default=32, help="LoRA alpha")
    args = parser.parse_args()

    result = run_training(
        data_path=args.data,
        base_model=args.model,
        output_dir=args.output,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        lora_rank=args.lora_rank,
        lora_alpha=args.lora_alpha,
    )
    print(json.dumps(result, indent=2))
