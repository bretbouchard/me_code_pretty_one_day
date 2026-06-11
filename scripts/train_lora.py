#!/usr/bin/env python3
"""Wrapper script for MLX-LoRA fine-tuning with pre-flight checks.

Launches mlx_lm.lora with the training configuration, enforcing:
- Disk space check (>= 10GB free required, warns if < 15GB)
- Model directory existence check
- Training data file checks
- --mask-prompt flag (assistant-only loss, CLI-only option)
- Graceful signal handling

Usage:
    python3 scripts/train_lora.py
    python3 scripts/train_lora.py --config training/lora_config.yaml
    python3 scripts/train_lora.py --skip-disk-check
"""

import argparse
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MIN_DISK_GB = 10
WARN_DISK_GB = 15


def check_disk_space(path: Path, skip: bool) -> None:
    """Verify sufficient disk space for training artifacts."""
    if skip:
        print("[DISK CHECK] Skipped (--skip-disk-check)")
        return

    usage = shutil.disk_usage(str(path))
    free_gb = usage.free / (1024 ** 3)

    if free_gb < MIN_DISK_GB:
        print(f"[DISK CHECK] FAIL: {free_gb:.1f}GB free — need >= {MIN_DISK_GB}GB")
        sys.exit(1)

    if free_gb < WARN_DISK_GB:
        print(f"[DISK CHECK] WARNING: {free_gb:.1f}GB free — recommended >= {WARN_DISK_GB}GB")

    print(f"[DISK CHECK] OK: {free_gb:.1f}GB free")


def load_config(config_path: Path) -> dict:
    """Load YAML config and return as dict for validation."""
    import yaml
    with open(config_path) as f:
        return yaml.safe_load(f)


def verify_paths(config: dict) -> None:
    """Verify model directory and training data files exist."""
    model_path = PROJECT_ROOT / config["model"]
    if not model_path.is_dir():
        print(f"[VERIFY] FAIL: Model directory not found: {model_path}")
        sys.exit(1)
    print(f"[VERIFY] OK: Model directory: {model_path}")

    data_dir = PROJECT_ROOT / config["data"]
    for filename in ("train.jsonl", "valid.jsonl"):
        data_path = data_dir / filename
        if not data_path.is_file():
            print(f"[VERIFY] FAIL: Data file not found: {data_path}")
            sys.exit(1)
        print(f"[VERIFY] OK: Data file: {data_path}")


def ensure_adapter_dir(config: dict) -> None:
    """Create adapter output directory if it doesn't exist."""
    adapter_path = PROJECT_ROOT / config["adapter_path"]
    adapter_path.mkdir(parents=True, exist_ok=True)
    print(f"[PREP] Adapter output: {adapter_path}")


def run_training(config_path: Path) -> int:
    """Launch mlx_lm.lora with --mask-prompt flag."""
    cmd = [
        sys.executable, "-m", "mlx_lm", "lora",
        "--config", str(config_path),
        "--mask-prompt",
    ]

    print(f"[TRAIN] Launching: {' '.join(cmd)}")
    print("=" * 60)

    proc = subprocess.Popen(
        cmd,
        cwd=str(PROJECT_ROOT),
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    def handle_signal(signum, frame):
        print(f"\n[TRAIN] Caught signal {signum}, terminating training...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        sys.exit(1)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    proc.wait()
    return proc.returncode


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MLX-LoRA training wrapper with pre-flight checks",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "training" / "lora_config.yaml",
        help="Path to lora_config.yaml (default: training/lora_config.yaml)",
    )
    parser.add_argument(
        "--skip-disk-check",
        action="store_true",
        help="Skip the disk space requirement check",
    )
    args = parser.parse_args()

    config_path = args.config.resolve()
    if not config_path.is_file():
        print(f"[ERROR] Config not found: {config_path}")
        sys.exit(1)

    print(f"[CONFIG] {config_path}")

    # Pre-flight checks
    check_disk_space(PROJECT_ROOT, args.skip_disk_check)

    config = load_config(config_path)
    verify_paths(config)
    ensure_adapter_dir(config)

    # Summary before training
    print("=" * 60)
    print("[PRE-FLIGHT] All checks passed. Starting training.")
    print(f"  Model:    {config['model']}")
    print(f"  Rank:     {config['lora_parameters']['rank']}")
    print(f"  LR:       {config['learning_rate']}")
    print(f"  Iters:    {config['iters']}")
    print(f"  Adapter:  {config['adapter_path']}")
    print(f"  mask-prompt: enabled (CLI flag)")
    print("=" * 60)

    # Run training
    returncode = run_training(config_path)

    if returncode == 0:
        adapter_path = PROJECT_ROOT / config["adapter_path"]
        print("=" * 60)
        print(f"[DONE] Training complete. Adapter saved to: {adapter_path}")
        print(f"[DONE] Load with: mlx_lm.generate --model {adapter_path} --adapter-path {adapter_path}")
        print("=" * 60)
    else:
        print(f"[FAIL] Training exited with code {returncode}")
        sys.exit(1)


if __name__ == "__main__":
    main()
