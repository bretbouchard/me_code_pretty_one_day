#!/usr/bin/env python3
"""Generate synthetic training data for fine-tuning Qwen2.5-Coder-7B-Instruct.

Reads seed task files from data/seed_examples/, expands them into diverse
training examples, and writes standard chat JSONL format files (train.jsonl
and valid.jsonl) with a deterministic 90/10 split.

Usage:
    python3 scripts/generate_training_data.py [--output-dir DIR] [--seed N] [--target-count N] [--max-seq-tokens N]
"""

import argparse
import json
import os
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DEFAULT_SEED_DIR = os.path.join(PROJECT_ROOT, "data", "seed_examples")
DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data")

# Characters per token is a rough estimate (Qwen tokenizer)
CHARS_PER_TOKEN = 4.0
MIN_RESPONSE_LENGTH = 50

# System prompt variations for diversity
SYSTEM_VARIATIONS = [
    "You are an expert programmer. Write clean, well-documented code with type hints where applicable.",
    "You are a senior software engineer. Provide production-quality code with proper error handling.",
    "You are a coding assistant specializing in clear, efficient implementations.",
    "You are a software developer. Write code that is readable, maintainable, and correct.",
    "You are a technical interviewer helping candidates write optimal solutions.",
    "You are an expert Python developer. Write clean, well-documented code.",
    "You are an expert Swift developer. Write clean, idiomatic Swift code.",
]

# Prompt prefixes to create diverse variations
PROMPT_PREFIXES = [
    "Can you write",
    "Please implement",
    "I need you to create",
    "Help me write",
    "Could you code",
    "Write",
    "Implement",
    "Create",
    "Please code",
    "I'd like you to implement",
    "Can you implement",
    "Please help me write",
]

# Prompt suffixes for more variety
PROMPT_SUFFIXES = [
    "",
    "",
    "",
    " Make sure the code is well-tested.",
    " Include docstrings and type hints.",
    " Use clean, idiomatic code.",
    " Handle edge cases properly.",
    " Optimize for readability and correctness.",
    " Add error handling where appropriate.",
    " Follow best practices for the language.",
]

# Context framers — prepend to prompts for additional diversity
CONTEXT_FRAMERS = [
    "",
    "",
    "",
    "For a personal project, ",
    "As part of a production codebase, ",
    "For an interview question, ",
    "In a code review, ",
    "For a teaching example, ",
    "As a utility in a larger system, ",
    "For a CLI tool, ",
    "For a web application backend, ",
    "As a library function, ",
]


def load_seed_tasks(seed_dir: str) -> List[Dict[str, Any]]:
    """Load all seed task files from the seed directory.

    Returns a flat list of all seed tasks across all JSON files.
    """
    tasks: List[Dict[str, Any]] = []
    seed_path = Path(seed_dir)
    if not seed_path.exists():
        print(f"Error: seed directory not found: {seed_dir}", file=sys.stderr)
        sys.exit(1)

    for json_file in sorted(seed_path.glob("*.json")):
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            print(f"Warning: {json_file} is not a JSON array, skipping", file=sys.stderr)
            continue
        for item in data:
            if "user_prompt" in item and "response" in item:
                tasks.append(item)
            elif "user_prompt" in item and "system" in item:
                tasks.append(item)

    if not tasks:
        print(f"Error: no seed tasks found in {seed_dir}", file=sys.stderr)
        sys.exit(1)

    return tasks


def estimate_tokens(text: str) -> int:
    """Estimate token count from text length."""
    return int(len(text) / CHARS_PER_TOKEN)


def build_example(system: str, user_prompt: str, assistant_response: str) -> Dict[str, Any]:
    """Build a single training example in chat JSONL format."""
    return {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": assistant_response},
        ]
    }


def _strip_leading_verb(prompt: str) -> str:
    """Remove common leading verbs from a prompt to enable prefix variation."""
    for verb in ["Write ", "Implement ", "Create ", "Write a ", "Implement a ", "Build "]:
        if prompt.startswith(verb):
            return prompt[len(verb):]
    return prompt


def make_user_prompt(seed: Dict[str, Any], system_idx: int, prefix_idx: int,
                     suffix_idx: int, context_idx: int) -> str:
    """Build a unique user prompt from variation indices."""
    base_prompt = seed["user_prompt"]
    clean = _strip_leading_verb(base_prompt)

    prefix = PROMPT_PREFIXES[prefix_idx % len(PROMPT_PREFIXES)]
    suffix = PROMPT_SUFFIXES[suffix_idx % len(PROMPT_SUFFIXES)]
    context = CONTEXT_FRAMERS[context_idx % len(CONTEXT_FRAMERS)]

    return f"{context}{prefix} {clean}{suffix}"


def mutate_response(base_response: str, mutation_id: int) -> str:
    """Apply a minor structural mutation to a response for diversity.

    Mutations are cosmetic (comments, whitespace) — they preserve the
    semantic code so the training signal remains consistent.
    """
    mutations = mutation_id % 6

    if mutations == 0:
        # No mutation — use as-is
        return base_response
    elif mutations == 1:
        # Add a leading file-level comment
        comment_lines = [
            "# Generated solution",
            "# Optimized for readability",
            "#",
        ]
        return "\n".join(comment_lines) + "\n" + base_response
    elif mutations == 2:
        # Add a trailing usage example comment
        return base_response + "\n\n# Usage:\n# result = solution(input_data)\n"
    elif mutations == 3:
        # Wrap with a module docstring
        return '"""\nSolution module.\n"""\n\n' + base_response
    elif mutations == 4:
        # Add if __name__ guard
        if "if __name__" not in base_response and "def " in base_response:
            return base_response + "\n\nif __name__ == '__main__':\n    pass\n"
        return base_response
    elif mutations == 5:
        # Add a TODO-style header comment
        return f"# Solution (variant {mutation_id})\n\n" + base_response
    else:
        return base_response


def expand_seeds_to_examples(
    seeds: List[Dict[str, Any]],
    target_count: int,
    max_seq_tokens: int,
    rng: random.Random,
) -> List[Dict[str, Any]]:
    """Expand seed tasks into the target number of training examples.

    Strategy:
    1. For each seed, enumerate all combinations of (system, prefix, suffix, context, mutation).
    2. Deduplicate by normalized user prompt.
    3. If still short, cycle through seeds repeatedly with sequential IDs.
    """
    max_chars = max_seq_tokens * CHARS_PER_TOKEN
    examples: List[Dict[str, Any]] = []
    seen_prompts: set = set()

    seeds_with_response = [s for s in seeds if s.get("response", "")]
    if not seeds_with_response:
        print("Error: no seed tasks with responses found", file=sys.stderr)
        sys.exit(1)

    # Enumerate all (system, prefix, suffix, context, mutation) combinations
    n_systems = len(SYSTEM_VARIATIONS)
    n_prefixes = len(PROMPT_PREFIXES)
    n_suffixes = len(PROMPT_SUFFIXES)
    n_contexts = len(CONTEXT_FRAMERS)
    n_mutations = 6  # number of response mutations (0 = unchanged)
    total_combos = n_systems * n_prefixes * n_suffixes * n_contexts * n_mutations

    for seed in seeds_with_response:
        base_response = seed["response"]
        if len(base_response.strip()) < MIN_RESPONSE_LENGTH:
            continue

        for combo_idx in range(total_combos):
            if len(examples) >= target_count:
                break

            sys_idx = combo_idx % n_systems
            pre_idx = (combo_idx // n_systems) % n_prefixes
            suf_idx = (combo_idx // (n_systems * n_prefixes)) % n_suffixes
            ctx_idx = (combo_idx // (n_systems * n_prefixes * n_suffixes)) % n_contexts
            mut_idx = (combo_idx // (n_systems * n_prefixes * n_suffixes * n_contexts)) % n_mutations

            system = SYSTEM_VARIATIONS[sys_idx]
            user_prompt = make_user_prompt(seed, sys_idx, pre_idx, suf_idx, ctx_idx)
            assistant_response = mutate_response(base_response, mut_idx)

            # Token budget check
            total_chars = len(system) + len(user_prompt) + len(assistant_response)
            if total_chars > max_chars:
                continue

            # Deduplicate
            prompt_key = user_prompt.strip().lower()
            if prompt_key in seen_prompts:
                continue
            seen_prompts.add(prompt_key)

            examples.append(build_example(system, user_prompt, assistant_response))

    # If still short (unlikely with 41 seeds * 5040 combos), cycle with unique IDs
    cycle = 0
    while len(examples) < target_count:
        seed = seeds_with_response[cycle % len(seeds_with_response)]
        cycle += 1

        # Build a fully unique prompt using cycle number
        system = SYSTEM_VARIATIONS[cycle % n_systems]
        clean = _strip_leading_verb(seed["user_prompt"])
        prefix = PROMPT_PREFIXES[cycle % n_prefixes]
        context = CONTEXT_FRAMERS[cycle % n_contexts]
        user_prompt = f"{context}{prefix} {clean} (v{cycle})"
        assistant_response = mutate_response(seed["response"], cycle % n_mutations)

        total_chars = len(system) + len(user_prompt) + len(assistant_response)
        if total_chars > max_chars:
            continue

        prompt_key = user_prompt.strip().lower()
        if prompt_key in seen_prompts:
            continue
        seen_prompts.add(prompt_key)

        if len(assistant_response.strip()) < MIN_RESPONSE_LENGTH:
            continue

        examples.append(build_example(system, user_prompt, assistant_response))

    # Shuffle deterministically
    rng.shuffle(examples)

    # Trim to exact target
    examples = examples[:target_count]

    return examples


def write_jsonl(examples: List[Dict[str, Any]], filepath: str) -> None:
    """Write examples to a JSONL file, one JSON object per line."""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        for example in examples:
            f.write(json.dumps(example, ensure_ascii=False) + "\n")


def read_jsonl(filepath: str) -> List[Dict[str, Any]]:
    """Read a JSONL file and return list of parsed objects."""
    examples: List[Dict[str, Any]] = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    return examples


def validate_examples(examples: List[Dict[str, Any]]) -> List[str]:
    """Validate examples and return list of error messages."""
    errors: List[str] = []
    valid_roles = {"system", "user", "assistant"}
    for i, ex in enumerate(examples):
        if "messages" not in ex:
            errors.append(f"Example {i}: missing 'messages' key")
            continue
        msgs = ex["messages"]
        if not isinstance(msgs, list):
            errors.append(f"Example {i}: 'messages' is not a list")
            continue
        if len(msgs) != 3:
            errors.append(f"Example {i}: expected 3 messages, got {len(msgs)}")
            continue
        for j, msg in enumerate(msgs):
            if not isinstance(msg, dict):
                errors.append(f"Example {i}, message {j}: not a dict")
                continue
            role = msg.get("role")
            content = msg.get("content", "")
            if role not in valid_roles:
                errors.append(f"Example {i}, message {j}: invalid role '{role}'")
            if not isinstance(content, str) or len(content.strip()) == 0:
                errors.append(f"Example {i}, message {j}: empty or non-string content")
            if "<|im_start|>" in str(content) or "<|im_end|>" in str(content):
                errors.append(f"Example {i}, message {j}: contains raw ChatML tokens")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic training data for fine-tuning."
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for train.jsonl/valid.jsonl (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--seed-dir",
        default=DEFAULT_SEED_DIR,
        help=f"Directory containing seed JSON files (default: {DEFAULT_SEED_DIR})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible shuffling and variation (default: 42)",
    )
    parser.add_argument(
        "--target-count",
        type=int,
        default=5500,
        help="Target number of total examples to generate (default: 5500)",
    )
    parser.add_argument(
        "--max-seq-tokens",
        type=int,
        default=1800,
        help="Maximum sequence length in tokens (default: 1800)",
    )
    args = parser.parse_args()

    # Set random seed for deterministic output
    random.seed(args.seed)

    # Load seed tasks
    print(f"Loading seed tasks from: {args.seed_dir}")
    seeds = load_seed_tasks(args.seed_dir)
    print(f"  Found {len(seeds)} seed tasks")

    seeds_with_resp = sum(1 for s in seeds if s.get("response", ""))
    print(f"  With responses: {seeds_with_resp}")

    # Generate examples
    print(f"Generating {args.target_count} examples...")
    examples = expand_seeds_to_examples(
        seeds=seeds,
        target_count=args.target_count,
        max_seq_tokens=args.max_seq_tokens,
        rng=random,
    )
    print(f"  Generated {len(examples)} examples")

    # Validate
    print("Validating examples...")
    errors = validate_examples(examples)
    if errors:
        print(f"  Validation found {len(errors)} issues:", file=sys.stderr)
        for err in errors[:10]:
            print(f"    {err}", file=sys.stderr)
        if len(errors) > 10:
            print(f"    ... and {len(errors) - 10} more", file=sys.stderr)
        sys.exit(1)
    print("  All examples valid")

    # Split 90/10
    split_idx = int(len(examples) * 0.9)
    train_examples = examples[:split_idx]
    valid_examples = examples[split_idx:]

    # Write output files
    train_path = os.path.join(args.output_dir, "train.jsonl")
    valid_path = os.path.join(args.output_dir, "valid.jsonl")

    write_jsonl(train_examples, train_path)
    write_jsonl(valid_examples, valid_path)

    # Summary
    total_tokens_est = sum(
        estimate_tokens(
            " ".join(msg.get("content", "") for msg in ex.get("messages", []))
        )
        for ex in examples
    )
    avg_tokens = total_tokens_est // max(len(examples), 1)

    print("\n--- Summary ---")
    print(f"Total examples:    {len(examples)}")
    print(f"Train examples:    {len(train_examples)} ({train_path})")
    print(f"Valid examples:    {len(valid_examples)} ({valid_path})")
    print(f"Train/total ratio: {len(train_examples) / len(examples):.4f}")
    print(f"Avg tokens/ex:     {avg_tokens}")
    print("Done.")


if __name__ == "__main__":
    main()
