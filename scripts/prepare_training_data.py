#!/usr/bin/env python3
"""Prepare training data by downloading Magicoder and mixing with seed examples.

Downloads Magicoder-OSS-Instruct-75K-Instruction-Response, converts to chat
JSONL format, filters for quality and length, then mixes with locally-expanded
seed examples at a configurable ratio.

Usage:
    python3 scripts/prepare_training_data.py [--magicoder-count N] [--seed-count N] [--ratio F]

Output:
    data/train.jsonl  (90% of combined dataset)
    data/valid.jsonl  (10% of combined dataset)
"""

import argparse
import json
import os
import random
import sys
from pathlib import Path
from typing import Any, Dict, List

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data")
DEFAULT_SEED_DIR = os.path.join(PROJECT_ROOT, "data", "seed_examples")

MAGICODER_DATASET = "ise-uiuc/Magicoder-OSS-Instruct-75K-Instruction-Response"

# Languages to include (prioritize what we care about, skip esoteric ones)
LANG_WHITELIST = {
    "python", "swift", "javascript", "typescript", "rust", "go",
    "cpp", "c", "java", "kotlin", "sql", "bash", "shell",
    "ruby", "php", "csharp", "dart", "scala", "r", "lua",
}

# System prompt for Magicoder examples (consistent with seed variations)
MAGICODER_SYSTEM = "You are an expert programmer. Write clean, well-documented code with type hints where applicable."

# Approximate chars per token (Qwen tokenizer)
CHARS_PER_TOKEN = 4.0
MIN_RESPONSE_LENGTH = 100
MAX_SEQ_TOKENS = 1800
MAX_SEQ_CHARS = int(MAX_SEQ_TOKENS * CHARS_PER_TOKEN)


def download_magicoder(target_count: int, seed: int) -> List[Dict[str, Any]]:
    """Download and convert Magicoder to chat JSONL format.

    Filters by language whitelist, response length, and sequence length.
    Samples deterministically up to target_count.
    """
    from datasets import load_dataset

    print(f"Downloading Magicoder dataset: {MAGICODER_DATASET}")
    ds = load_dataset(MAGICODER_DATASET, split="train")

    print(f"  Total examples in dataset: {len(ds)}")

    rng = random.Random(seed)
    examples: List[Dict[str, Any]] = []
    skipped_lang = 0
    skipped_short = 0
    skipped_long = 0
    skipped_no_code = 0

    # Shuffle indices deterministically for sampling
    indices = list(range(len(ds)))
    rng.shuffle(indices)

    for idx in indices:
        if len(examples) >= target_count:
            break

        row = ds[idx]
        lang = row.get("lang", "").lower()
        instruction = row.get("instruction", "")
        response = row.get("response", "")

        # Language filter
        if lang not in LANG_WHITELIST:
            skipped_lang += 1
            continue

        # Response quality filter
        if len(response.strip()) < MIN_RESPONSE_LENGTH:
            skipped_short += 1
            continue

        # Must contain code (has backtick fence)
        if "```" not in response:
            skipped_no_code += 1
            continue

        # Sequence length filter
        total_chars = len(MAGICODER_SYSTEM) + len(instruction) + len(response)
        if total_chars > MAX_SEQ_CHARS:
            skipped_long += 1
            continue

        examples.append({
            "messages": [
                {"role": "system", "content": MAGICODER_SYSTEM},
                {"role": "user", "content": instruction},
                {"role": "assistant", "content": response},
            ]
        })

    print(f"  Downloaded {len(examples)} Magicoder examples (of {target_count} requested)")
    print(f"  Skipped: {skipped_lang} lang, {skipped_short} short, {skipped_long} long, {skipped_no_code} no-code")

    return examples


def load_existing_seeds(seed_dir: str) -> List[Dict[str, Any]]:
    """Load seed-expanded examples from existing train.jsonl + valid.jsonl."""
    examples: List[Dict[str, Any]] = []
    for filename in ["train.jsonl", "valid.jsonl"]:
        filepath = os.path.join(seed_dir, filename)
        if not os.path.exists(filepath):
            continue
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    examples.append(json.loads(line))
    return examples


def validate_examples(examples: List[Dict[str, Any]], label: str) -> List[str]:
    """Validate examples and return error messages."""
    errors: List[str] = []
    valid_roles = {"system", "user", "assistant"}
    for i, ex in enumerate(examples[:100]):  # Check first 100
        if "messages" not in ex:
            errors.append(f"[{label}] Example {i}: missing 'messages'")
            continue
        msgs = ex["messages"]
        if not isinstance(msgs, list) or len(msgs) != 3:
            errors.append(f"[{label}] Example {i}: bad messages structure")
            continue
        for j, msg in enumerate(msgs):
            if not isinstance(msg, dict) or msg.get("role") not in valid_roles:
                errors.append(f"[{label}] Example {i}, msg {j}: invalid role")
            if not isinstance(msg.get("content", ""), str) or not msg["content"].strip():
                errors.append(f"[{label}] Example {i}, msg {j}: empty content")
    return errors


def write_jsonl(examples: List[Dict[str, Any]], filepath: str) -> None:
    """Write examples to a JSONL file."""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        for example in examples:
            f.write(json.dumps(example, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download Magicoder and mix with seed examples for training."
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory for train.jsonl/valid.jsonl (default: data/)",
    )
    parser.add_argument(
        "--magicoder-count",
        type=int,
        default=10000,
        help="Number of Magicoder examples to download (default: 10000)",
    )
    parser.add_argument(
        "--seed-count",
        type=int,
        default=2000,
        help="Number of seed-expanded examples to include (default: 2000)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    parser.add_argument(
        "--magicoder-only",
        action="store_true",
        help="Use only Magicoder data, skip seed examples",
    )
    parser.add_argument(
        "--seeds-only",
        action="store_true",
        help="Use only seed examples, skip Magicoder download",
    )
    args = parser.parse_args()

    random.seed(args.seed)

    # --- Step 1: Load existing seed examples ---
    all_examples: List[Dict[str, Any]] = []

    if not args.magicoder_only:
        print("Loading existing seed-expanded examples...")
        seed_examples = load_existing_seeds(args.output_dir)
        print(f"  Found {len(seed_examples)} existing seed examples")

        # Subsample if requested count is less than available
        if len(seed_examples) > args.seed_count:
            rng = random.Random(args.seed + 1)
            rng.shuffle(seed_examples)
            seed_examples = seed_examples[:args.seed_count]
            print(f"  Subsampled to {args.seed_count} seed examples")

        all_examples.extend(seed_examples)

    # --- Step 2: Download Magicoder ---
    if not args.seeds_only:
        magicoder_examples = download_magicoder(
            target_count=args.magicoder_count,
            seed=args.seed + 2,
        )
        all_examples.extend(magicoder_examples)

    # --- Step 3: Deduplicate by user prompt ---
    seen_prompts = set()
    deduped_examples = []
    for ex in all_examples:
        msgs = ex.get("messages", [])
        user_msgs = [m["content"].strip() for m in msgs if m.get("role") == "user"]
        if user_msgs and user_msgs[0] not in seen_prompts:
            seen_prompts.add(user_msgs[0])
            deduped_examples.append(ex)
    dup_count = len(all_examples) - len(deduped_examples)
    all_examples = deduped_examples
    if dup_count:
        print(f"  Deduplicated: removed {dup_count} duplicate prompts")

    # --- Step 4: Shuffle and split ---
    print(f"\nTotal examples: {len(all_examples)}")
    rng = random.Random(args.seed + 3)
    rng.shuffle(all_examples)

    split_idx = int(len(all_examples) * 0.9)
    train_examples = all_examples[:split_idx]
    valid_examples = all_examples[split_idx:]

    # --- Step 4: Validate ---
    print("Validating...")
    errors = validate_examples(train_examples, "train")
    errors.extend(validate_examples(valid_examples, "valid"))
    if errors:
        print(f"  Validation found {len(errors)} issues:", file=sys.stderr)
        for err in errors[:10]:
            print(f"    {err}", file=sys.stderr)
        sys.exit(1)
    print("  All examples valid")

    # --- Step 5: Write output ---
    train_path = os.path.join(args.output_dir, "train.jsonl")
    valid_path = os.path.join(args.output_dir, "valid.jsonl")

    write_jsonl(train_examples, train_path)
    write_jsonl(valid_examples, valid_path)

    # --- Summary ---
    seed_count_actual = len(seed_examples) if not args.magicoder_only else 0
    magicoder_count_actual = len(magicoder_examples) if not args.seeds_only else 0
    print("\n--- Summary ---")
    if not args.magicoder_only:
        print(f"Seed examples:    {seed_count_actual}")
    if not args.seeds_only:
        print(f"Magicoder:        {magicoder_count_actual}")
    print(f"Total examples:   {len(all_examples)}")
    print(f"Train examples:   {len(train_examples)} ({train_path})")
    print(f"Valid examples:   {len(valid_examples)} ({valid_path})")
    print(f"Train/total:      {len(train_examples) / len(all_examples):.4f}")
    print("Done.")


if __name__ == "__main__":
    main()
