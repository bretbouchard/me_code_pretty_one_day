#!/usr/bin/env python3
"""Benchmark generation throughput (tokens/second) for local LLM serving.

Measures sustained generation speed by streaming 512+ tokens
and calculating tok/s excluding initial TTFT.
"""

import argparse
import json
import statistics
import sys
import time

import urllib.request
import urllib.error


def measure_throughput(
    base_url: str = "http://localhost:11434",
    model: str = "qwen2.5-coder:7b-instruct-q4_K_M",
    prompt: str = (
        "Implement a complete binary search tree in Python with insert, "
        "search, delete, and traversal methods. Include docstrings."
    ),
    max_tokens: int = 512,
    iterations: int = 3,
) -> list[dict]:
    """Measure throughput for each iteration. Returns list of result dicts."""
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
                        content = delta.get("content", "")
                        if content:
                            if first_token_time is None:
                                first_token_time = time.perf_counter()
                            # Character-based estimation: ~3.5 chars/token for code
                            # Word splitting undercounts (operators, punctuation, indentation)
                            token_count += len(content) / 3.5
                    except json.JSONDecodeError:
                        continue
        except urllib.error.URLError as e:
            print(f"iteration={i+1} ERROR: {e.reason}", file=sys.stderr)
            results.append({"iteration": i + 1, "error": True})
            continue

        end = time.perf_counter()

        if first_token_time is not None and token_count > 0:
            gen_time = end - first_token_time
            elapsed = end - start
            tok_per_s = token_count / gen_time if gen_time > 0 else 0

            token_count_int = int(round(token_count))
            result = {
                "iteration": i + 1,
                "total_tokens": token_count_int,
                "elapsed_sec": round(elapsed, 3),
                "gen_time_sec": round(gen_time, 3),
                "tokens_per_sec": round(tok_per_s, 1),
            }
            results.append(result)
            print(
                f"iteration={i+1} tokens={token_count_int} "
                f"elapsed={elapsed:.3f}s gen_time={gen_time:.3f}s "
                f"tok/s={tok_per_s:.1f}"
            )
        else:
            print(f"iteration={i+1} ERROR: no tokens received", file=sys.stderr)
            results.append({"iteration": i + 1, "error": True})

    return results


def main():
    parser = argparse.ArgumentParser(description="Measure generation throughput (tok/s)")
    parser.add_argument("--base-url", default="http://localhost:11434")
    parser.add_argument("--model", default="qwen2.5-coder:7b-instruct-q4_K_M")
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--max-tokens", type=int, default=512)
    args = parser.parse_args()

    print(f"=== Throughput Benchmark ===")
    print(f"Server: {args.base_url}")
    print(f"Model:  {args.model}")
    print(f"Iterations: {args.iterations}")
    print(f"Max tokens: {args.max_tokens}")
    print()

    results = measure_throughput(
        base_url=args.base_url,
        model=args.model,
        iterations=args.iterations,
        max_tokens=args.max_tokens,
    )

    valid = [r for r in results if not r.get("error")]
    if not valid:
        print("ERROR: No successful measurements", file=sys.stderr)
        sys.exit(1)

    throughputs = [r["tokens_per_sec"] for r in valid]
    mean_tps = statistics.mean(throughputs)
    min_tps = min(throughputs)
    max_tps = max(throughputs)
    avg_tokens = statistics.mean([r["total_tokens"] for r in valid])

    print()
    print(f"=== Results ===")
    print(f"Successful:     {len(valid)}/{args.iterations}")
    print(f"Avg tokens:     {avg_tokens:.0f}")
    print(f"Mean throughput: {mean_tps:.1f} tok/s")
    print(f"Min throughput:  {min_tps:.1f} tok/s")
    print(f"Max throughput:  {max_tps:.1f} tok/s")
    print(f"Target:          >=30.0 tok/s")
    print(f"Status:          {'PASS' if mean_tps >= 30.0 else 'FAIL'}")

    sys.exit(0 if mean_tps >= 30.0 else 1)


if __name__ == "__main__":
    main()
