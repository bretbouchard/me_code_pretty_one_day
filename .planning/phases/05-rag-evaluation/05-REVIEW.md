---
phase: 05-rag-evaluation
reviewed: 2026-06-12T00:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - prompts/domains.json
  - prompts/slc_system.txt
  - scripts/benchmark_humaneval.py
  - scripts/benchmark-latency.py
  - scripts/benchmark-throughput.py
  - scripts/generate.py
  - scripts/prompt_template.py
  - scripts/seed_patterns.py
  - scripts/test_benchmark_humaneval.py
  - scripts/test_latency_throughput.py
  - scripts/test_prompt_template.py
  - scripts/test_rag_pipeline.py
findings:
  critical: 1
  warning: 5
  info: 3
  total: 9
status: issues_found
---

# Phase 5: Code Review Report

**Reviewed:** 2026-06-12
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Reviewed 12 files implementing a RAG-augmented code generation pipeline with benchmarking infrastructure. The codebase includes prompt assembly with Confucius retrieval, Ollama API integration, HumanEval benchmarking, TTFT/throughput benchmarks, and comprehensive test coverage.

Overall the code is well-structured with good docstrings, type hints, error handling, and test coverage. However, one security concern (`trust_remote_code=True` in tokenizer loading) and several correctness/robustness issues were found.

## Critical Issues

### CR-01: `trust_remote_code=True` in AutoTokenizer.from_pretrained

**File:** `scripts/prompt_template.py:66`
**Issue:** `AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)` allows arbitrary code execution from model config files. If the model directory or tokenizer config is compromised or sourced from an untrusted origin, this enables remote code execution. The Hugging Face transformers documentation explicitly warns about this flag.

```python
self.tokenizer = AutoTokenizer.from_pretrained(
    model_path, trust_remote_code=True
)
```

**Fix:**
```python
self.tokenizer = AutoTokenizer.from_pretrained(
    model_path, trust_remote_code=False
)
```

Only use `trust_remote_code=True` if the model absolutely requires custom code in its tokenizer and the model source is trusted and verified. For standard Qwen2.5-Coder models, `trust_remote_code=False` (the default) should work correctly.

## Warnings

### WR-01: Duplicated `build_variant_messages` function across two files

**File:** `scripts/benchmark-latency.py:31-62` and `scripts/benchmark-throughput.py:31-62`
**Issue:** The `build_variant_messages` function is copy-pasted identically between `benchmark-latency.py` and `benchmark-throughput.py`. Both files also duplicate the `VALID_VARIANTS` constant, `SLC_SYSTEM_PATH`, and `MODEL_PATH`. Any bug fix or change to one must be manually replicated to the other, which is error-prone.

**Fix:** Extract the shared function into a common module (e.g., `scripts/benchmark_utils.py`) and import it in both benchmark scripts.

```python
# scripts/benchmark_utils.py
VALID_VARIANTS = {"base", "finetuned", "rag"}

def build_variant_messages(variant: str, prompt: str) -> list[dict]:
    ...
```

### WR-02: `pass_at_k` missing guard against `k > n`

**File:** `scripts/benchmark_humaneval.py:39-52`
**Issue:** The `pass_at_k` function checks `if n - c < k: return 1.0` but does not check the case where `k > n`. When `k > n`, `math.comb(n, k)` raises a `ValueError: k must be <= n`. This can occur if `n_samples` is small (e.g., `--n-samples 2`) and `pass@100` is calculated (line 298: `pass100 = pass_at_k(n, correct, 100)` where `n=2, k=100`).

```python
def pass_at_k(n: int, c: int, k: int) -> float:
    if n - c < k:
        return 1.0
    return 1.0 - math.comb(n - c, k) / math.comb(n, k)
```

**Fix:**
```python
def pass_at_k(n: int, c: int, k: int) -> float:
    if k > n:
        return 1.0  # Cannot select k from n; treat as best-effort pass
    if n - c < k:
        return 1.0
    return 1.0 - math.comb(n - c, k) / math.comb(n, k)
```

### WR-03: `generate.py` creates a new `PromptAssembler` on every call

**File:** `scripts/generate.py:57`
**Issue:** `generate_with_rag` creates a new `PromptAssembler` instance on every invocation. The constructor loads a Hugging Face tokenizer from disk (`AutoTokenizer.from_pretrained`) and reads config files. This is expensive -- repeated CLI invocations pay this cost every time. In `benchmark_humaneval.py`, the assembler is correctly created once and reused.

```python
def generate_with_rag(...) -> str | None:
    assembler = PromptAssembler(model_path)  # expensive -- tokenizer load
```

**Fix:** Accept an optional `assembler` parameter to allow reuse:

```python
def generate_with_rag(
    user_prompt: str,
    domain: str = "python",
    model_path: str = DEFAULT_MODEL_PATH,
    assembler: PromptAssembler | None = None,  # allow pre-built assembler
    ...
) -> str | None:
    if assembler is None:
        assembler = PromptAssembler(model_path)
```

### WR-04: `_sanitize_content` may truncate mid-multibyte character

**File:** `scripts/prompt_template.py:39`
**Issue:** The truncation `sanitized[:max_length]` slices by character index, which for Python 3 strings works correctly since Python strings are Unicode. However, if the result is later encoded to bytes (e.g., UTF-8), a character at position `max_length` that is a multi-byte character is fine -- the slice is character-safe. This is actually NOT a bug in Python 3. However, the real concern is that truncation mid-sentence or mid-code-block could inject malformed patterns into the prompt. The 500-character limit is a safety measure, so this is acceptable but worth noting for awareness.

**Severity adjustment:** Downgrading this to informational since Python 3 string slicing is Unicode-aware and the truncation is a safety bound, not a precision operation.

**Fix:** No fix required -- this is safe in Python 3. Consider adding a comment noting this is intentional.

### WR-05: `_load_slc_prompt` returns empty string on FileNotFoundError with no warning

**File:** `scripts/benchmark_humaneval.py:78-84`
**Issue:** When the SLC system prompt file is missing, `_load_slc_prompt` silently returns an empty string. The `finetuned` variant is then functionally identical to `base`, producing incorrect benchmark comparisons without any indication to the user. This silent degradation could lead to misleading benchmark conclusions.

```python
def _load_slc_prompt() -> str:
    try:
        with open(SLC_SYSTEM_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""  # silent -- finetuned variant silently becomes identical to base
```

**Fix:**
```python
def _load_slc_prompt() -> str:
    try:
        with open(SLC_SYSTEM_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(
            f"WARNING: SLC system prompt not found at {SLC_SYSTEM_PATH}. "
            f"Finetuned variant will run without system prompt.",
            file=sys.stderr,
        )
        return ""
```

## Info

### IN-01: Token estimation uses magic number in throughput benchmark

**File:** `scripts/benchmark-throughput.py:120`
**Issue:** Token counting uses a hardcoded estimation factor `len(content) / 3.5` with the comment "Character-based estimation: ~3.5 chars/token for code." This magic number is acceptable for a benchmark approximation but should ideally be configurable or at minimum documented with a source.

```python
token_count += len(content) / 3.5
```

**Fix:** Extract to a named constant:

```python
CHARS_PER_TOKEN_ESTIMATE = 3.5  # ~3.5 chars/token for code generation
# ...
token_count += len(content) / CHARS_PER_TOKEN_ESTIMATE
```

### IN-02: `generate.py` bare `except Exception` suppresses tokenizer errors

**File:** `scripts/generate.py:83`
**Issue:** The verbose token counting block catches bare `Exception`, which could mask unexpected errors beyond the intended tokenizer failure case.

```python
try:
    tokenized = assembler.tokenizer.apply_chat_template(
        messages, add_generation_prompt=True, tokenize=True
    )
    print(f"Prompt tokens: {len(tokenized)}", file=sys.stderr)
except Exception:
    pass
```

**Fix:** Catch the specific expected exception types:

```python
except (TypeError, ValueError, AttributeError):
    pass
```

### IN-03: `test_prompt_template.py` imports from `scripts.prompt_template` but `benchmark_humaneval.py` imports from `prompt_template`

**File:** `scripts/test_prompt_template.py:152,161,182` and `scripts/benchmark_humaneval.py:386`
**Issue:** Inconsistent import paths across test files. `test_prompt_template.py` patches `scripts.prompt_template.subprocess.run` while `benchmark_humaneval.py` imports `from prompt_template import PromptAssembler`. The tests work because `test_prompt_template.py` patches the module path and the production scripts run from the `scripts/` directory. However, the inconsistency is fragile and confusing for maintainers.

**Fix:** Standardize on one import convention. Since the production scripts use relative imports (`from prompt_template import ...`) when run from the `scripts/` directory, tests should either match or document the expectation.

---

_Reviewed: 2026-06-12_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
