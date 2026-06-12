#!/usr/bin/env python3
"""HumanEval benchmark: pass@k evaluation for base vs fine-tuned vs fine-tuned+RAG.

Runs 164 HumanEval problems through 3 model variants, generates n_samples
completions per problem, and calculates pass@k scores using the hypergeometric
distribution. Results are written to data/humaneval_results/ as JSONL files.

Variants:
  - base: Raw Ollama model, no system prompt, no RAG
  - finetuned: Ollama model with SLC system prompt, no RAG
  - rag: Ollama model with SLC system prompt + Confucius RAG context

Usage:
    python3 scripts/benchmark_humaneval.py --max-problems 2 --n-samples 2 --verbose
    python3 scripts/benchmark_humaneval.py --variants base finetuned --max-problems 10
"""

import argparse
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MODEL_PATH = os.path.join(
    PROJECT_ROOT, "models", "qwen2.5-coder-7b-instruct-4bit-mlx"
)
DEFAULT_ADAPTER_PATH = os.path.join(PROJECT_ROOT, "training", "adapters-600")
DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "humaneval_results")
SLC_SYSTEM_PATH = os.path.join(PROJECT_ROOT, "prompts", "slc_system.txt")
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5-coder:7b-instruct-q4_K_M"
OLLAMA_TIMEOUT = 120


def pass_at_k(n: int, c: int, k: int) -> float:
    """Calculate pass@k using hypergeometric distribution.

    Args:
        n: Total samples generated per problem.
        c: Number of correct samples (passing all tests).
        k: Number of samples selected for evaluation.

    Returns:
        Probability that at least one of k samples passes all tests.
    """
    if k > n:
        return 1.0 if c == n else 0.0
    if n - c < k:
        return 1.0
    return 1.0 - math.comb(n - c, k) / math.comb(n, k)


def extract_completion(prompt: str, raw_output: str) -> str:
    """Extract function body from model output, stripping markdown fences.

    HumanEval expects just the function body that completes the prompt.
    Strips markdown code fences (```python ... ```) if present.

    Args:
        prompt: The HumanEval problem prompt (function signature).
        raw_output: Raw text from the model.

    Returns:
        Cleaned completion text.
    """
    text = raw_output.strip()
    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```python or ```) and last line (```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    return text


def _load_slc_prompt() -> str:
    """Load SLC system prompt from prompts/slc_system.txt."""
    try:
        with open(SLC_SYSTEM_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def _call_ollama(
    messages: list[dict],
    max_tokens: int = 512,
    temperature: float = 0.2,
    ollama_model: str = OLLAMA_MODEL,
) -> dict:
    """Send a chat completion request to Ollama API.

    Args:
        messages: Chat messages (system, user, assistant roles).
        max_tokens: Maximum tokens to generate.
        temperature: Sampling temperature.
        ollama_model: Model name for Ollama.

    Returns:
        Response dict with content key, or None on error.
    """
    endpoint = f"{OLLAMA_BASE_URL}/v1/chat/completions"
    payload = json.dumps({
        "model": ollama_model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }).encode()

    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
            return {
                "content": data["choices"][0]["message"]["content"],
                "usage": data.get("usage", {}),
            }
    except (urllib.error.URLError, TimeoutError, KeyError, IndexError):
        return None


def generate_for_problem(
    problem: dict,
    variant: str,
    assembler: object,
    model_path: str,
    adapter_path: str | None = None,
    ollama_model: str = OLLAMA_MODEL,
    max_tokens: int = 512,
    temperature: float = 0.2,
    n_samples: int = 20,
    verbose: bool = False,
) -> list[dict]:
    """Generate n_samples completions for a single HumanEval problem.

    Args:
        problem: HumanEval problem dict with 'prompt', 'test', 'entry_point', 'task_id'.
        variant: One of "base", "finetuned", "rag".
        assembler: PromptAssembler instance (used for rag variant).
        model_path: Path to the model directory.
        adapter_path: Path to LoRA adapter (not used in Ollama mode).
        ollama_model: Ollama model name.
        max_tokens: Maximum tokens to generate per sample.
        temperature: Sampling temperature.
        n_samples: Number of completions to generate.
        verbose: If True, print progress per sample.

    Returns:
        List of {"task_id": ..., "completion": ...} dicts.
    """
    task_id = problem.get("task_id", "unknown")
    prompt = problem["prompt"]
    samples = []

    # Build messages based on variant
    if variant == "base":
        # No system prompt, no RAG -- raw prompt only
        messages = [{"role": "user", "content": prompt}]
    elif variant == "finetuned":
        # SLC system prompt, no RAG
        slc_prompt = _load_slc_prompt()
        messages = [
            {"role": "system", "content": slc_prompt},
            {"role": "user", "content": prompt},
        ]
    elif variant == "rag":
        # SLC system prompt + RAG via PromptAssembler
        messages = assembler.assemble(
            prompt, domain="python",
            max_generation_tokens=max_tokens,
            skip_rag=False,
        )
    else:
        raise ValueError(f"Unknown variant: {variant}")

    for i in range(n_samples):
        if verbose:
            print(
                f"  [{variant}] {task_id} [{i+1}/{n_samples}]",
                file=sys.stderr,
                flush=True,
            )

        response = _call_ollama(
            messages, max_tokens=max_tokens, temperature=temperature,
            ollama_model=ollama_model,
        )

        if response is not None:
            completion = extract_completion(prompt, response["content"])
        else:
            completion = ""

        samples.append({"task_id": task_id, "completion": completion})

    return samples


def run_variant(
    variant: str,
    problems: dict,
    output_dir: str,
    assembler: object,
    model_path: str,
    adapter_path: str | None = None,
    ollama_model: str = OLLAMA_MODEL,
    n_samples: int = 20,
    max_problems: int | None = None,
    max_tokens: int = 512,
    temperature: float = 0.2,
    verbose: bool = False,
) -> dict:
    """Run benchmark for one variant across all problems.

    Args:
        variant: One of "base", "finetuned", "rag".
        problems: Dict of HumanEval problems from read_problems().
        output_dir: Directory to write results JSONL files.
        assembler: PromptAssembler instance.
        model_path: Path to model directory.
        adapter_path: Path to LoRA adapter.
        ollama_model: Ollama model name.
        n_samples: Samples per problem.
        max_problems: Limit number of problems (None = all 164).
        max_tokens: Max tokens per generation.
        temperature: Sampling temperature.
        verbose: Print progress.

    Returns:
        Results dict with pass@k values and metadata.
    """
    from human_eval.data import write_jsonl
    from human_eval.evaluation import evaluate_functional_correctness

    # Slice problems if max_problems is set
    problem_items = list(problems.items())
    if max_problems is not None:
        problem_items = problem_items[:max_problems]

    all_samples = []
    total = len(problem_items)
    start_time = time.time()

    for idx, (task_id, problem) in enumerate(problem_items):
        if verbose:
            print(
                f"[{variant}] Problem {idx+1}/{total}: {task_id}",
                file=sys.stderr,
                flush=True,
            )

        samples = generate_for_problem(
            problem=problem,
            variant=variant,
            assembler=assembler,
            model_path=model_path,
            adapter_path=adapter_path,
            ollama_model=ollama_model,
            max_tokens=max_tokens,
            temperature=temperature,
            n_samples=n_samples,
            verbose=verbose,
        )
        all_samples.extend(samples)

    elapsed = time.time() - start_time

    # Write samples to JSONL
    samples_path = os.path.join(output_dir, f"{variant}_samples.jsonl")
    os.makedirs(output_dir, exist_ok=True)
    write_jsonl(samples_path, all_samples)

    if verbose:
        print(
            f"[{variant}] Wrote {len(all_samples)} samples to {samples_path}",
            file=sys.stderr,
        )

    # Evaluate functional correctness
    if verbose:
        print(f"[{variant}] Evaluating functional correctness...", file=sys.stderr)

    results = evaluate_functional_correctness(samples_path)

    # Calculate aggregate pass@k
    n = n_samples
    correct = sum(1 for v in results.values() if v)
    pass1 = pass_at_k(n, correct, 1)
    pass10 = pass_at_k(n, correct, 10)
    pass100 = pass_at_k(n, correct, 100)

    return {
        "variant": variant,
        "total_problems": total,
        "correct": correct,
        "pass@1": pass1,
        "pass@10": pass10,
        "pass@100": pass100,
        "elapsed_sec": elapsed,
        "samples_file": samples_path,
    }


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for HumanEval benchmark."""
    parser = argparse.ArgumentParser(
        description="HumanEval benchmark: base vs finetuned vs rag",
    )
    parser.add_argument(
        "--variants",
        nargs="+",
        choices=["base", "finetuned", "rag"],
        default=["base", "finetuned", "rag"],
        help="Variants to benchmark (default: all three)",
    )
    parser.add_argument(
        "--n-samples",
        type=int,
        default=20,
        help="Samples per problem per variant (default: 20)",
    )
    parser.add_argument(
        "--max-problems",
        type=int,
        default=None,
        help="Limit number of problems for development (default: all 164)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=512,
        help="Max tokens per generation (default: 512)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        help="Sampling temperature (default: 0.2)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default=DEFAULT_MODEL_PATH,
        help=f"Model directory path (default: {DEFAULT_MODEL_PATH})",
    )
    parser.add_argument(
        "--adapter-path",
        type=str,
        default=DEFAULT_ADAPTER_PATH,
        help=f"Adapter path (default: {DEFAULT_ADAPTER_PATH})",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Print progress and timing information",
    )

    args = parser.parse_args(argv)

    from human_eval.data import read_problems

    # Load problems
    problems = read_problems()
    if args.max_problems is not None:
        problems = dict(list(problems.items())[:args.max_problems])
    print(f"Loaded {len(problems)} HumanEval problems.", file=sys.stderr)

    # Initialize PromptAssembler (needed for rag variant)
    assembler = None
    if "rag" in args.variants:
        from prompt_template import PromptAssembler
        assembler = PromptAssembler(args.model_path)

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Run each variant
    all_results = []
    for variant in args.variants:
        print(f"\n=== Running variant: {variant} ===", file=sys.stderr)
        result = run_variant(
            variant=variant,
            problems=problems,
            output_dir=args.output_dir,
            assembler=assembler,
            model_path=args.model_path,
            adapter_path=args.adapter_path,
            n_samples=args.n_samples,
            max_problems=args.max_problems,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            verbose=args.verbose,
        )
        all_results.append(result)

    # Print comparison table
    print()
    print(f"{'Variant':<16} {'pass@1':>8} {'pass@10':>8} {'pass@100':>8} {'Time':>8}")
    print("-" * 50)
    for r in all_results:
        elapsed_min = r["elapsed_sec"] / 60
        print(
            f"{r['variant']:<16} {r['pass@1']:>8.3f} {r['pass@10']:>8.3f} "
            f"{r['pass@100']:>8.3f} {elapsed_min:>7.0f}m"
        )
    print()

    # Save results summary
    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "n_samples": args.n_samples,
        "max_problems": len(problems),
        "max_tokens": args.max_tokens,
        "temperature": args.temperature,
        "results": all_results,
    }
    summary_path = os.path.join(args.output_dir, "results_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Results saved to {summary_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
