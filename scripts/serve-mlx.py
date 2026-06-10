#!/usr/bin/env python3
"""
Launch script for mlx_lm.server with the local Qwen2.5-Coder model.

Starts the server, polls until healthy, and handles graceful shutdown.
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
DEFAULT_PORT = 8800

# Model path relative to project root
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "models", "qwen2.5-coder-7b-instruct-4bit-mlx")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Launch mlx_lm.server with the local Qwen2.5-Coder model"
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
        help=f"Port to bind (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--model",
        default=None,
        help=f"Override model path (default: {MODEL_DIR})",
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
    model_path = args.model if args.model else MODEL_DIR

    if not os.path.isdir(model_path):
        print(f"ERROR: Model directory not found: {model_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Starting mlx_lm.server with model: {model_path}")
    print(f"Binding to {args.host}:{args.port}")

    cmd = [
        sys.executable, "-m", "mlx_lm", "server",
        "--model", model_path,
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
        print(f"mlx_lm.server ready on http://localhost:{args.port}")
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
