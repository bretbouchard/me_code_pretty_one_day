#!/usr/bin/env python3
"""Benchmark Time To First Token (TTFT) for local LLM serving.

Measures wall-clock time from request send to first token received
in a streaming response. Reports mean/min/max across iterations.

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
    return assembler.assemble(prompt, domain="python", max_generation_tokens=200)


def measure_ttft(
    base_url: str = "http://localhost:11434",
    model: str = "qwen2.5-coder:7b-instruct-q4_K_M",
    prompt: str = 'def quicksort(arr):\n    """Sort array using quicksort algorithm."""',
    max_tokens: int = 200,
    iterations: int = 5,
    messages: list[dict] | None = None,
) -> list[float]:
    """Measure TTFT for each iteration. Returns list of TTFT values in seconds."""
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


def print_comparison_table(
    all_results: dict[str, list[float]],
    prompt: str,
) -> None:
    """Print comparison table of TTFT results across variants.

    Args:
        all_results: Dict mapping variant name to list of TTFT values.
        prompt: The prompt that was benchmarked.
    """
    print()
    print(f"{'Variant':<14} {'Mean TTFT':>10} {'Min TTFT':>10} {'Max TTFT':>10}")
    print("-" * 48)

    for variant in ["base", "finetuned", "rag"]:
        ttfts = all_results.get(variant, [])
        valid = [t for t in ttfts if t != float("inf")]
        if valid:
            mean_val = statistics.mean(valid)
            min_val = min(valid)
            max_val = max(valid)
            print(f"{variant:<14} {mean_val:>9.2f}s {min_val:>9.2f}s {max_val:>9.2f}s")
        else:
            print(f"{variant:<14} {'ERROR':>10} {'---':>10} {'---':>10}")

    print()


def main():
    parser = argparse.ArgumentParser(description="Measure Time To First Token (TTFT)")
    parser.add_argument("--base-url", default="http://localhost:11434")
    parser.add_argument("--model", default="qwen2.5-coder:7b-instruct-q4_K_M")
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--max-tokens", type=int, default=200)
    parser.add_argument(
        "--variant",
        choices=["base", "finetuned", "rag", "all"],
        default="base",
        help="Model variant to benchmark (default: base). 'all' runs all three.",
    )
    args = parser.parse_args()

    prompt = 'def quicksort(arr):\n    """Sort array using quicksort algorithm."""'

    if args.variant == "all":
        print(f"=== TTFT Benchmark (all variants) ===")
        print(f"Server: {args.base_url}")
        print(f"Model:  {args.model}")
        print(f"Iterations: {args.iterations} per variant")
        print(f"Max tokens: {args.max_tokens}")
        print()

        all_results = {}
        for variant in ["base", "finetuned", "rag"]:
            print(f"--- Running {variant} variant ---")
            messages = build_variant_messages(variant, prompt)
            ttfts = measure_ttft(
                base_url=args.base_url,
                model=args.model,
                prompt=prompt,
                iterations=args.iterations,
                max_tokens=args.max_tokens,
                messages=messages,
            )
            all_results[variant] = ttfts

        print_comparison_table(all_results, prompt)
    else:
        messages = build_variant_messages(args.variant, prompt)
        print(f"=== TTFT Benchmark ({args.variant} variant) ===")
        print(f"Server: {args.base_url}")
        print(f"Model:  {args.model}")
        print(f"Iterations: {args.iterations}")
        print(f"Max tokens: {args.max_tokens}")
        print()

        results = measure_ttft(
            base_url=args.base_url,
            model=args.model,
            prompt=prompt,
            iterations=args.iterations,
            max_tokens=args.max_tokens,
            messages=messages,
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
