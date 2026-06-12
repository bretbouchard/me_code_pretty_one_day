"""Shared utilities for benchmark scripts (latency, throughput, humaneval).

Centralizes constants and the build_variant_messages function that was
duplicated across benchmark-latency.py and benchmark-throughput.py.

Import conventions:
  - Benchmark scripts import this module directly: from benchmark_utils import ...
  - Tests that patch references in this module use: patch("benchmark_utils.subprocess.run")
  - The scripts/ directory must be on sys.path for these imports to resolve.
"""

import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SLC_SYSTEM_PATH = os.path.join(PROJECT_ROOT, "prompts", "slc_system.txt")
MODEL_PATH = os.path.join(
    PROJECT_ROOT, "models", "qwen2.5-coder-7b-instruct-4bit-mlx"
)

VALID_VARIANTS = {"base", "finetuned", "rag"}


def build_variant_messages(
    variant: str,
    prompt: str,
    max_generation_tokens: int = 512,
) -> list[dict]:
    """Build chat messages for the specified benchmark variant.

    Args:
        variant: One of "base", "finetuned", "rag".
        prompt: The user prompt content.
        max_generation_tokens: Tokens reserved for generation (default 512).
            Only used by the "rag" variant when calling PromptAssembler.

    Returns:
        List of message dicts with "role" and "content" keys.

    Raises:
        ValueError: If variant is not recognized.
    """
    if variant not in VALID_VARIANTS:
        raise ValueError(
            f"Unknown variant: {variant}. Must be one of {sorted(VALID_VARIANTS)}"
        )

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
    return assembler.assemble(
        prompt, domain="python", max_generation_tokens=max_generation_tokens
    )
