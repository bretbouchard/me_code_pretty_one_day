#!/usr/bin/env python3
"""Download Qwen2.5-Coder-7B-Instruct and convert to MLX 4-bit quantization.

Uses mlx_lm.download to handle downloading from Hugging Face and converting
to MLX format in one step.

Usage:
    python scripts/download_model.py
    python scripts/download_model.py --model Qwen/Qwen2.5-Coder-7B-Instruct
    python scripts/download_model.py --output models/my-model
"""

import argparse
import os
import shutil
import subprocess
import sys


def check_mlx_lm() -> bool:
    """Check that mlx-lm is installed."""
    try:
        import mlx_lm
        return True
    except ImportError:
        return False


def check_disk_space(path: str, needed_gb: int) -> bool:
    """Check available disk space."""
    stat = shutil.disk_usage(os.path.dirname(path) or ".")
    free_gb = stat.free / (1024 ** 3)
    return free_gb >= needed_gb


def download_model(model_name: str, output_dir: str) -> None:
    """Download and convert model using mlx_lm."""
    cmd = [
        sys.executable, "-m", "mlx_lm.download",
        "--model", model_name,
        "--save-dir", output_dir,
    ]
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def verify_download(output_dir: str) -> bool:
    """Verify the downloaded model contains expected files."""
    expected = ["config.json"]
    for f in expected:
        if not os.path.exists(os.path.join(output_dir, f)):
            return False
    # Check for weight files (safetensors or npz)
    for entry in os.listdir(output_dir):
        if entry.endswith(".safetensors") or entry.endswith(".npz"):
            return True
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Download Qwen2.5-Coder-7B-Instruct as MLX 4-bit quantized model."
    )
    parser.add_argument(
        "--model",
        default="Qwen/Qwen2.5-Coder-7B-Instruct",
        help="HuggingFace model name (default: Qwen/Qwen2.5-Coder-7B-Instruct)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output directory (default: models/qwen2.5-coder-7b-instruct-4bit-mlx)",
    )
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    output_dir = args.output or os.path.join(project_root, "models", "qwen2.5-coder-7b-instruct-4bit-mlx")

    # Check mlx-lm
    if not check_mlx_lm():
        print("Error: mlx-lm is not installed.", file=sys.stderr)
        print("Install with: pip install mlx-lm", file=sys.stderr)
        sys.exit(1)

    # Check if already downloaded
    if os.path.exists(output_dir) and verify_download(output_dir):
        print(f"Model already exists at: {output_dir}")
        print("Delete the directory and re-run to re-download.")
        return

    # Check disk space (~8GB for download + conversion)
    needed_gb = 8
    print(f"Checking disk space (need ~{needed_gb}GB)...")
    if not check_disk_space(output_dir, needed_gb):
        print(f"Error: Not enough disk space. Need ~{needed_gb}GB free.", file=sys.stderr)
        sys.exit(1)
    print("  OK")

    # Download
    print(f"\nDownloading {args.model}...")
    print(f"Output: {output_dir}")
    print("(This will take a while depending on your internet speed)\n")
    download_model(args.model, output_dir)

    # Verify
    if not verify_download(output_dir):
        print(f"\nError: Download completed but model files not found in {output_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"\nModel downloaded successfully to: {output_dir}")
    print("\nNext steps:")
    print("  1. Start Ollama: ollama serve")
    print("  2. Generate code: python scripts/generate.py 'write a binary search' --no-rag")


if __name__ == "__main__":
    main()
