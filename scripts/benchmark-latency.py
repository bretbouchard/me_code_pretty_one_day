#!/usr/bin/env python3
"""Benchmark Time To First Token (TTFT) for local LLM serving.

Measures wall-clock time from request send to first token received
in a streaming response. Reports mean/min/max across iterations.
"""

import argparse
import json
import statistics
import sys
import time

import urllib.request
import urllib.error


def measure_ttft(
    base_url: str = "http://localhost:11434",
    model: str = "qwen2.5-coder:7b-instruct-q4_K_M",
    prompt: str = 'def quicksort(arr):\n    """Sort array using quicksort algorithm."""',
    max_tokens: int = 200,
    iterations: int = 5,
) -> list[float]:
    """Measure TTFT for each iteration. Returns list of TTFT values in seconds."""
    results = []
    endpoint = f"{base_url}/v1/chat/completions"

    for i in range(iterations):
        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "stream": True,
        }).encode()

        req = urllib.request.Request(
            endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
        )

        start = time.perf_counter()
        first_token_time = None
        token_count = 0

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                for line in resp:
                    line = line.decode().strip()
                    if not line or not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        if delta.get("content"):
                            if first_token_time is None:
                                first_token_time = time.perf_counter()
                            token_count += 1
                    except json.JSONDecodeError:
                        continue
        except urllib.error.URLError as e:
            print(f"iteration={i+1} ERROR: {e.reason}", file=sys.stderr)
            results.append(float("inf"))
            continue

        if first_token_time is not None:
            ttft = first_token_time - start
            results.append(ttft)
            print(f"iteration={i+1} ttft={ttft:.3f}s tokens={token_count}")
        else:
            print(f"iteration={i+1} ERROR: no tokens received", file=sys.stderr)
            results.append(float("inf"))

    return results


def main():
    parser = argparse.ArgumentParser(description="Measure Time To First Token (TTFT)")
    parser.add_argument("--base-url", default="http://localhost:11434")
    parser.add_argument("--model", default="qwen2.5-coder:7b-instruct-q4_K_M")
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--max-tokens", type=int, default=200)
    args = parser.parse_args()

    print(f"=== TTFT Benchmark ===")
    print(f"Server: {args.base_url}")
    print(f"Model:  {args.model}")
    print(f"Iterations: {args.iterations}")
    print(f"Max tokens: {args.max_tokens}")
    print()

    results = measure_ttft(
        base_url=args.base_url,
        model=args.model,
        iterations=args.iterations,
        max_tokens=args.max_tokens,
    )

    valid = [r for r in results if r != float("inf")]
    if not valid:
        print("ERROR: No successful measurements", file=sys.stderr)
        sys.exit(1)

    mean_ttft = statistics.mean(valid)
    min_ttft = min(valid)
    max_ttft = max(valid)

    print()
    print(f"=== Results ===")
    print(f"Successful:  {len(valid)}/{args.iterations}")
    print(f"Mean TTFT:   {mean_ttft:.3f}s")
    print(f"Min TTFT:    {min_ttft:.3f}s")
    print(f"Max TTFT:    {max_ttft:.3f}s")
    print(f"Target:      <5.000s")
    print(f"Status:      {'PASS' if mean_ttft < 5.0 else 'FAIL'}")

    sys.exit(0 if mean_ttft < 5.0 else 1)


if __name__ == "__main__":
    main()
