#!/usr/bin/env python3
"""
Launch script for mlx_lm.server with the fine-tuned Qwen2.5-Coder model.

Loads the LoRA adapter via --adapter-path and starts the server on port 8801
(separate from the base model on 8800). Polls until healthy, then streams output.
"""

import argparse
import os
import signal
import subprocess
import sys
import time
import urllib.request
import urllib.error


DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8801

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_MODEL = os.path.join(PROJECT_ROOT, "models", "qwen2.5-coder-7b-instruct-4bit-mlx")
DEFAULT_ADAPTER = os.path.join(PROJECT_ROOT, "training", "adapters")


def adapter_exists(adapter_path: str) -> bool:
    """Check if the adapter directory contains the expected files."""
    if not os.path.isdir(adapter_path):
        return False
    config = os.path.join(adapter_path, "adapter_config.json")
    weights = os.path.join(adapter_path, "adapters.safetensors")
    return os.path.isfile(config) or os.path.isfile(weights)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Launch mlx_lm.server with the fine-tuned model (adapter loaded)"
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"Host to bind (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port to bind (default: {DEFAULT_PORT}, base model uses 8800)",
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
    return parser.parse_args()


def wait_for_server(host: str, port: int, timeout: int = 120) -> bool:
    """Poll /v1/models until the server returns HTTP 200 or timeout."""
    url = f"http://localhost:{port}/v1/models"
    deadline = time.time() + timeout

    while time.time() < deadline:
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, ConnectionRefusedError, OSError):
            pass
        time.sleep(1)

    return False


def main():
    args = parse_args()

    # Validate model directory
    if not os.path.isdir(args.model):
        print(f"ERROR: Model directory not found: {args.model}", file=sys.stderr)
        print("Run download script or set --model to an existing model path.", file=sys.stderr)
        sys.exit(1)

    # Validate adapter directory
    if not adapter_exists(args.adapter_path):
        print(f"ERROR: Adapter not found at: {args.adapter_path}", file=sys.stderr)
        print("Expected adapter_config.json or adapters.safetensors inside.", file=sys.stderr)
        print("Run training first: python3 scripts/train_lora.py", file=sys.stderr)
        sys.exit(1)

    adapter_abs = os.path.abspath(args.adapter_path)
    model_abs = os.path.abspath(args.model)

    print(f"Starting mlx_lm.server with fine-tuned model")
    print(f"  Base model:  {model_abs}")
    print(f"  Adapter:     {adapter_abs}")
    print(f"  Binding to:  {args.host}:{args.port}")
    print()

    cmd = [
        sys.executable, "-m", "mlx_lm", "server",
        "--model", model_abs,
        "--adapter-path", adapter_abs,
        "--host", args.host,
        "--port", str(args.port),
    ]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    def shutdown(signum, frame):
        print(f"\nReceived signal {signum}, shutting down server...")
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    print("Waiting for server to become ready...")
    if wait_for_server(args.host, args.port):
        print(f"Fine-tuned model ready on http://localhost:{args.port}")
        print()
        print("NOTE: The model ID in API calls will be the full model path.")
        print("      Query /v1/models to discover the exact model ID, e.g.:")
        print(f"      curl http://localhost:{args.port}/v1/models")
    else:
        print("ERROR: Server did not become ready within timeout", file=sys.stderr)
        proc.terminate()
        sys.exit(1)

    # Stream server output
    try:
        for line in proc.stdout:
            decoded = line.decode("utf-8", errors="replace").rstrip()
            if decoded:
                print(f"[server] {decoded}")
    except KeyboardInterrupt:
        pass
    finally:
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    main()
