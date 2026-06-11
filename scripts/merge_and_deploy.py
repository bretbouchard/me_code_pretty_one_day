#!/usr/bin/env python3
"""
Fuse LoRA adapter into base model and optionally deploy to Ollama.

PRIMARY path: mlx_lm.server with native --adapter-path (recommended).
SECONDARY: Fuse adapter into standalone model, optionally import to Ollama.

NOTE: mlx_lm.fuse --export-gguf does NOT support Qwen2 (hardcodes llama arch).
This script uses mlx_lm.fuse without --export-gguf, producing a safetensors
model that Ollama can import via --experimental safetensors support.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_MODEL = os.path.join(PROJECT_ROOT, "models", "qwen2.5-coder-7b-instruct-4bit-mlx")
DEFAULT_ADAPTER = os.path.join(PROJECT_ROOT, "training", "adapters")
DEFAULT_OUTPUT = os.path.join(PROJECT_ROOT, "training", "fused_model")
OLLAMA_MODEL_NAME = "qwen2.5-coder-ft"


def adapter_exists(adapter_path: str) -> bool:
    """Check if the adapter directory contains the expected files."""
    if not os.path.isdir(adapter_path):
        return False
    config = os.path.join(adapter_path, "adapter_config.json")
    weights = os.path.join(adapter_path, "adapters.safetensors")
    return os.path.isfile(config) or os.path.isfile(weights)


def check_disk_space(required_gb: float, path: str = "/") -> tuple[int, bool]:
    """Return free space in GB and whether it meets the requirement."""
    usage = shutil.disk_usage(path)
    free_gb = usage.free / (1024 ** 3)
    return free_gb, free_gb >= required_gb


def parse_args():
    parser = argparse.ArgumentParser(
        description="Fuse LoRA adapter into base model and optionally deploy to Ollama"
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Base model path (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--adapter-path",
        default=DEFAULT_ADAPTER,
        help=f"LoRA adapter directory (default: {DEFAULT_ADAPTER})",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Fused model output path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--deploy-ollama",
        action="store_true",
        help="Attempt Ollama import after fusion (experimental)",
    )
    parser.add_argument(
        "--dequantize",
        action="store_true",
        default=True,
        help="Dequantize to bf16 during fusion (default: True)",
    )
    parser.add_argument(
        "--no-dequantize",
        action="store_true",
        help="Keep quantization during fusion (smaller output, less disk)",
    )
    parser.add_argument(
        "--skip-disk-check",
        action="store_true",
        help="Skip disk space check before fusion",
    )
    return parser.parse_args()


def run_fuse(model: str, adapter: str, output: str, dequantize: bool) -> bool:
    """Run mlx_lm.fuse to merge adapter into the base model."""
    cmd = [
        sys.executable, "-m", "mlx_lm", "fuse",
        "--model", model,
        "--adapter-path", adapter,
        "--save-path", output,
    ]
    if dequantize:
        cmd.append("--dequantize")

    print(f"Running: {' '.join(cmd)}")
    print()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        if result.returncode != 0:
            print(f"ERROR: mlx_lm.fuse failed with exit code {result.returncode}", file=sys.stderr)
            return False

        return True
    except subprocess.TimeoutExpired:
        print("ERROR: mlx_lm.fuse timed out (600s)", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("ERROR: mlx_lm not found. Install with: pip install mlx-lm", file=sys.stderr)
        return False


def report_fused_model(output: str) -> None:
    """Print summary of the fused model output."""
    if not os.path.isdir(output):
        print(f"WARNING: Output directory not found: {output}", file=sys.stderr)
        return

    file_count = 0
    total_size = 0
    for f in os.listdir(output):
        fp = os.path.join(output, f)
        if os.path.isfile(fp):
            file_count += 1
            total_size += os.path.getsize(fp)

    total_gb = total_size / (1024 ** 3)
    print()
    print(f"Fused model saved to: {output}")
    print(f"  Files: {file_count}")
    print(f"  Total size: {total_gb:.2f} GB")


def deploy_to_ollama(fused_path: str, model_name: str) -> bool:
    """Attempt to import the fused model into Ollama."""
    if not shutil.which("ollama"):
        print("WARNING: ollama CLI not found. Skipping Ollama deployment.", file=sys.stderr)
        print("         Install from https://ollama.com or use python3 scripts/serve_finetuned.py", file=sys.stderr)
        return False

    # Create a temporary Modelfile
    modelfile_content = f"""FROM {os.path.abspath(fused_path)}
PARAMETER temperature 0.7
PARAMETER num_ctx 4096
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".Modelfile", delete=False) as mf:
        mf.write(modelfile_content)
        modelfile_path = mf.name

    try:
        cmd = [
            "ollama", "create", model_name,
            "--experimental",
            "-f", modelfile_path,
        ]
        print(f"Running: {' '.join(cmd)}")
        print()

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        if result.returncode != 0:
            print(f"WARNING: Ollama import failed (exit {result.returncode})", file=sys.stderr)
            print("         This is expected — Ollama safetensors import is experimental.", file=sys.stderr)
            print("         Recommended path: python3 scripts/serve_finetuned.py", file=sys.stderr)
            return False

        print()
        print(f"SUCCESS: Model imported to Ollama as '{model_name}'")
        print(f"  Test with: ollama run {model_name} \"Write a Python function to find prime numbers\"")
        return True

    except subprocess.TimeoutExpired:
        print("WARNING: Ollama import timed out (300s)", file=sys.stderr)
        print("         Recommended path: python3 scripts/serve_finetuned.py", file=sys.stderr)
        return False
    except Exception as e:
        print(f"WARNING: Ollama import error: {e}", file=sys.stderr)
        print("         Recommended path: python3 scripts/serve_finetuned.py", file=sys.stderr)
        return False
    finally:
        if os.path.exists(modelfile_path):
            os.unlink(modelfile_path)


def main():
    args = parse_args()

    # Handle --no-dequantize flag
    dequantize = args.dequantize and not args.no_dequantize

    # Validate model
    if not os.path.isdir(args.model):
        print(f"ERROR: Model directory not found: {args.model}", file=sys.stderr)
        sys.exit(1)

    # Validate adapter
    if not adapter_exists(args.adapter_path):
        print(f"ERROR: Adapter not found at: {args.adapter_path}", file=sys.stderr)
        print("Expected adapter_config.json or adapters.safetensors inside.", file=sys.stderr)
        print("Run training first: python3 scripts/train_lora.py", file=sys.stderr)
        sys.exit(1)

    # Disk space check
    if not args.skip_disk_check:
        if dequantize:
            required = 15.0
            warn_threshold = 20.0
        else:
            required = 2.0
            warn_threshold = 5.0

        free_gb, has_space = check_disk_space(required)
        if not has_space:
            print(f"ERROR: Insufficient disk space. Need {required:.0f}GB, have {free_gb:.1f}GB free.", file=sys.stderr)
            if dequantize:
                print("       Try --no-dequantize to keep quantization (needs ~2GB).", file=sys.stderr)
            sys.exit(1)
        free_gb, _ = check_disk_space(warn_threshold)
        if not _ and dequantize:
            print(f"WARNING: Disk space is tight ({free_gb:.1f}GB free). Recommend >= 20GB for dequantize.", file=sys.stderr)

    print(f"=== Fuse Adapter into Base Model ===")
    print(f"  Base model:    {args.model}")
    print(f"  Adapter:       {args.adapter_path}")
    print(f"  Output:        {args.output}")
    print(f"  Dequantize:     {dequantize}")
    print(f"  Deploy Ollama: {args.deploy_ollama}")
    print()

    # Run fusion
    if not run_fuse(args.model, args.adapter_path, args.output, dequantize):
        sys.exit(1)

    report_fused_model(args.output)

    # Optional Ollama deployment
    if args.deploy_ollama:
        print()
        print("=== Ollama Deployment (Experimental) ===")
        deploy_to_ollama(args.output, OLLAMA_MODEL_NAME)
        print()
        print("NOTE: If Ollama deployment fails, use mlx_lm.server instead:")
        print("      python3 scripts/serve_finetuned.py")

    print()
    print("Done. The fused model can also be served directly:")
    print(f"  python3 -m mlx_lm.server --model {args.output} --port 8801")


if __name__ == "__main__":
    main()
