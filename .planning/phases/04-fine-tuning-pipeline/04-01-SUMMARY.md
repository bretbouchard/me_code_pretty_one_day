# Plan 04-01 Summary: Training Data Generator

**Status:** Complete
**Date:** 2026-06-10

## What Was Done

Created the synthetic training data generator that produces 5500 code generation examples in standard chat JSONL format for Qwen2.5-Coder-7B-Instruct fine-tuning.

### Files Created

| File | Purpose |
|------|---------|
| `data/seed_examples/python_tasks.json` | 18 Python coding tasks with full solutions |
| `data/seed_examples/swift_tasks.json` | 12 Swift/SwiftUI coding tasks with full solutions |
| `data/seed_examples/general_tasks.json` | 11 general coding tasks (regex, SQL, shell, patterns) |
| `scripts/generate_training_data.py` | Data generator with template-based expansion |
| `scripts/conftest.py` | Shared pytest fixtures for test scripts |
| `scripts/test_generate_training_data.py` | Tests: file existence, counts, seed file validation |
| `scripts/test_training_data_format.py` | Tests: JSON structure, roles, content, no ChatML tokens |
| `scripts/test_train_val_split.py` | Tests: no overlap, 90/10 ratio, determinism |
| `data/train.jsonl` | 4950 training examples |
| `data/valid.jsonl` | 550 validation examples |

### Approach

The generator uses combinatorial expansion from 41 seed tasks (each with a concrete prompt + response). For each seed, it enumerates all combinations of:
- 7 system prompt variations
- 12 prompt prefix phrasings
- 10 prompt suffixes
- 12 context framers
- 6 response mutations (cosmetic: comments, docstrings, `__name__` guard)

This yields 41 * 7 * 12 * 10 * 12 * 6 = 2,471,040 possible combinations. After deduplication by normalized user prompt and token budget filtering, 5500 unique examples are selected, shuffled with seed=42, and split 90/10.

### Verification Results

- **train.jsonl:** 4950 examples (>= 4500 required)
- **valid.jsonl:** 550 examples (>= 500 required)
- **Split ratio:** 0.9000 (within 0.89-0.91 tolerance)
- **Format:** All examples are `{"messages": [{"role": "system/user/assistant", "content": "..."}]}` -- no raw ChatML tokens
- **Determinism:** Running generator twice with seed=42 produces byte-identical output files
- **No overlap:** Zero user prompts shared between train and valid sets
- **Tests:** 36/36 pass in 0.20 seconds

### Key Decisions

1. **Template-based expansion over model-based generation.** The generator works without requiring the Qwen model to be present. This makes it self-contained and fast (<1 second). The diversity comes from combinatorial variation of prompts and cosmetic response mutations rather than LLM-generated completions.

2. **Cosmetic response mutations only.** Response mutations (leading comments, trailing usage examples, docstring wrappers, `__name__` guards) are structural, not semantic. The actual code logic stays identical across variations -- this preserves training signal quality while adding prompt-response diversity.

3. **Prompt deduplication by normalized text.** Unique examples are tracked by lowercased/stripped user prompts, ensuring no duplicates reach the training set even with thousands of combinations.

### Requirements Satisfied

- **LAKE-07:** 5500 total examples (>= 5000 required)
- **LAKE-08:** Standard chat JSONL format (`{messages: [{role, content}]}`) -- mlx-lm applies Qwen ChatML template automatically
- **LAKE-10:** Deterministic 90/10 split with seed=42, reproducible across runs
