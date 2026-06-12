#!/usr/bin/env python3
"""RAG generation pipeline CLI: Confucius retrieval -> prompt assembly -> Ollama inference.

Chains PromptAssembler (SLC + RAG) with Ollama's OpenAI-compatible API to
produce code generation output with domain-specific context from Confucius.

Usage:
    python3 scripts/generate.py "write a binary search" --domain python
    python3 scripts/generate.py "sort an array" --domain swift --verbose
    python3 scripts/generate.py "def add(a, b):" --no-rag
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

from prompt_template import PromptAssembler, load_domains_mapping

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MODEL_PATH = os.path.join(
    PROJECT_ROOT, "models", "qwen2.5-coder-7b-instruct-4bit-mlx"
)
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5-coder:7b-instruct-q4_K_M"
OLLAMA_TIMEOUT = 120


def generate_with_rag(
    user_prompt: str,
    domain: str = "python",
    model_path: str = DEFAULT_MODEL_PATH,
    max_tokens: int = 2048,
    temperature: float = 0.2,
    no_rag: bool = False,
    verbose: bool = False,
) -> str | None:
    """Generate code with optional RAG context from Confucius.

    Chains Confucius retrieval -> prompt assembly -> Ollama inference.

    Args:
        user_prompt: The code generation prompt.
        domain: Domain for RAG retrieval (e.g. "python", "swift").
        model_path: Path to the model directory with tokenizer config.
        max_tokens: Maximum tokens to generate.
        temperature: Sampling temperature (0.0 = deterministic).
        no_rag: If True, skip Confucius retrieval entirely.
        verbose: If True, print timing and debug information.

    Returns:
        Generated code string, or None on error.
    """
    assembler = PromptAssembler(model_path)

    # Step 1: Retrieve patterns (unless --no-rag)
    patterns = []
    if not no_rag:
        retrieval_start = time.perf_counter()
        patterns = assembler.retrieve_patterns(domain)
        retrieval_elapsed = time.perf_counter() - retrieval_start
        if verbose:
            print(
                f"Retrieved {len(patterns)} patterns in {retrieval_elapsed * 1000:.0f}ms",
                file=sys.stderr,
            )

    # Step 2: Assemble prompt
    messages = assembler.assemble(
        user_prompt, domain, max_generation_tokens=max_tokens, skip_rag=no_rag
    )

    if verbose:
        # Count approximate prompt tokens from assembled messages
        try:
            tokenized = assembler.tokenizer.apply_chat_template(
                messages, add_generation_prompt=True, tokenize=True
            )
            print(f"Prompt tokens: {len(tokenized)}", file=sys.stderr)
        except Exception:
            pass

    # Step 3: Send to Ollama API
    endpoint = f"{OLLAMA_BASE_URL}/v1/chat/completions"
    payload = json.dumps({
        "model": OLLAMA_MODEL,
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
        gen_start = time.perf_counter()
        with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
        gen_elapsed = time.perf_counter() - gen_start
    except urllib.error.URLError as e:
        print(f"Error: Ollama connection failed: {e.reason}", file=sys.stderr)
        return None
    except TimeoutError:
        print(
            f"Error: Ollama request timed out after {OLLAMA_TIMEOUT}s",
            file=sys.stderr,
        )
        return None

    # Step 4: Extract content
    try:
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        if verbose:
            prompt_tokens = usage.get("prompt_tokens", "N/A")
            completion_tokens = usage.get("completion_tokens", "N/A")
            print(f"Generation tokens: {completion_tokens}", file=sys.stderr)
            print(f"Generation time: {gen_elapsed:.1f}s", file=sys.stderr)

        return content
    except (KeyError, IndexError) as e:
        print(f"Error: Unexpected Ollama response format: {e}", file=sys.stderr)
        return None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for the generation pipeline."""
    parser = argparse.ArgumentParser(
        description="RAG-augmented code generation pipeline",
    )
    parser.add_argument(
        "prompt",
        type=str,
        help="Code generation prompt",
    )

    # Load available domains for choices
    try:
        domains = load_domains_mapping()
        domain_choices = list(domains.keys())
    except (FileNotFoundError, json.JSONDecodeError):
        domain_choices = None

    parser.add_argument(
        "--domain",
        type=str,
        default="python",
        choices=domain_choices,
        help="Domain for RAG retrieval (default: python)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=2048,
        help="Maximum tokens to generate (default: 2048)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        help="Sampling temperature (default: 0.2)",
    )
    parser.add_argument(
        "--no-rag",
        action="store_true",
        default=False,
        help="Skip Confucius RAG retrieval",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Print timing and debug information",
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default=DEFAULT_MODEL_PATH,
        help=f"Model directory path (default: {DEFAULT_MODEL_PATH})",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for the RAG generation pipeline."""
    args = parse_args(argv)

    result = generate_with_rag(
        user_prompt=args.prompt,
        domain=args.domain,
        model_path=args.model_path,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        no_rag=args.no_rag,
        verbose=args.verbose,
    )

    if result is not None:
        print(result)
    else:
        print("Generation failed.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
