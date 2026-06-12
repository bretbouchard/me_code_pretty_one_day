#!/usr/bin/env python3
"""Benchmark generation throughput (tokens/second) for local LLM serving.

Measures sustained generation speed by streaming 512+ tokens
and calculating tok/s excluding initial TTFT.

Supports three model variants:
- base: Default behavior, user prompt only (no system prompt)
- finetuned: SLC system prompt + user prompt
- rag: Full RAG assembly via PromptAssembler (SLC + retrieved patterns + user prompt)
- all: Runs all three variants and prints comparison table
"""

import argparse
import json
import os
import statistics
import sys
import time

import urllib.request
import urllib.error

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SLC_SYSTEM_PATH = os.path.join(PROJECT_ROOT, "prompts", "slc_system.txt")
MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "qwen2.5-coder-7b-instruct-4bit-mlx")

VALID_VARIANTS = {"base", "finetuned", "rag"}


def build_variant_messages(variant: str, prompt: str) -> list[dict]:
    """Build chat messages for the specified benchmark variant.

    Args:
        variant: One of "base", "finetuned", "rag".
        prompt: The user prompt content.

    Returns:
        List of message dicts with "role" and "content" keys.

    Raises:
        ValueError: If variant is not recognized.
    """
    if variant not in VALID_VARIANTS:
        raise ValueError(f"Unknown variant: {variant}. Must be one of {sorted(VALID_VARIANTS)}")

    if variant == "base":
        return [{"role": "user", "content": prompt}]

    if variant == "finetuned":
        with open(SLC_SYSTEM_PATH, "r", encoding="utf-8") as f:
            slc_text = f.read()
        return [
            {"role": "system", "content": slc_text},
            {"role": "user", "content": prompt},
        ]

    # variant == "rag" -- use PromptAssembler for full RAG pipeline
    from prompt_template import PromptAssembler

    assembler = PromptAssembler(MODEL_PATH)
    return assembler.assemble(prompt, domain="python", max_generation_tokens=512)


def measure_throughput(
    base_url: str = "http://localhost:11434",
    model: str = "qwen2.5-coder:7b-instruct-q4_K_M",
    prompt: str = (
        "Implement a complete binary search tree in Python with insert, "
        "search, delete, and traversal methods. Include docstrings."
    ),
    max_tokens: int = 512,
    iterations: int = 3,
    messages: list[dict] | None = None,
) -> list[dict]:
    """Measure throughput for each iteration. Returns list of result dicts."""
    results = []
    endpoint = f"{base_url}/v1/chat/completions"

    # Use provided messages or construct default
    if messages is None:
        messages = [{"role": "user", "content": prompt}]

    for i in range(iterations):
        payload = json.dumps({
            "model": model,
            "messages": messages,
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


def print_comparison_table(
    all_results: dict[str, list[dict]],
    prompt: str,
) -> None:
    """Print comparison table of throughput results across variants.

    Args:
        all_results: Dict mapping variant name to list of result dicts.
        prompt: The prompt that was benchmarked.
    """
    print()
    print(f"{'Variant':<14} {'Mean tok/s':>11} {'Total tokens':>13} {'Time':>8}")
    print("-" * 50)

    for variant in ["base", "finetuned", "rag"]:
        variant_results = all_results.get(variant, [])
        valid = [r for r in variant_results if not r.get("error")]
        if valid:
            mean_tps = statistics.mean([r["tokens_per_sec"] for r in valid])
            avg_tokens = statistics.mean([r["total_tokens"] for r in valid])
            avg_elapsed = statistics.mean([r["elapsed_sec"] for r in valid])
            print(
                f"{variant:<14} {mean_tps:>10.1f} "
                f"{avg_tokens:>12.0f} {avg_elapsed:>7.1f}s"
            )
        else:
            print(f"{variant:<14} {'ERROR':>11} {'---':>13} {'---':>8}")

    print()


def main():
    parser = argparse.ArgumentParser(description="Measure generation throughput (tok/s)")
    parser.add_argument("--base-url", default="http://localhost:11434")
    parser.add_argument("--model", default="qwen2.5-coder:7b-instruct-q4_K_M")
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument(
        "--variant",
        choices=["base", "finetuned", "rag", "all"],
        default="base",
        help="Model variant to benchmark (default: base). 'all' runs all three.",
    )
    args = parser.parse_args()

    prompt = (
        "Implement a complete binary search tree in Python with insert, "
        "search, delete, and traversal methods. Include docstrings."
    )

    if args.variant == "all":
        print(f"=== Throughput Benchmark (all variants) ===")
        print(f"Server: {args.base_url}")
        print(f"Model:  {args.model}")
        print(f"Iterations: {args.iterations} per variant")
        print(f"Max tokens: {args.max_tokens}")
        print()

        all_results = {}
        for variant in ["base", "finetuned", "rag"]:
            print(f"--- Running {variant} variant ---")
            messages = build_variant_messages(variant, prompt)
            variant_results = measure_throughput(
                base_url=args.base_url,
                model=args.model,
                prompt=prompt,
                iterations=args.iterations,
                max_tokens=args.max_tokens,
                messages=messages,
            )
            all_results[variant] = variant_results

        print_comparison_table(all_results, prompt)
    else:
        messages = build_variant_messages(args.variant, prompt)
        print(f"=== Throughput Benchmark ({args.variant} variant) ===")
        print(f"Server: {args.base_url}")
        print(f"Model:  {args.model}")
        print(f"Iterations: {args.iterations}")
        print(f"Max tokens: {args.max_tokens}")
        print()

        results = measure_throughput(
            base_url=args.base_url,
            model=args.model,
            prompt=prompt,
            iterations=args.iterations,
            max_tokens=args.max_tokens,
            messages=messages,
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
