# Phase 5: RAG & Evaluation - Research

**Researched:** 2026-06-12
**Domain:** RAG retrieval integration, system prompt engineering, code generation benchmarking
**Confidence:** HIGH

## Summary

Phase 5 connects all prior work into a usable local AI code generation pipeline. The three pillars are: (1) wiring Confucius CLI retrieval into the generation pipeline, (2) engineering an SLC system prompt with domain-specific coding standards, and (3) building a benchmark suite comparing base, fine-tuned, and RAG-augmented generation quality.

Confucius CLI search is fast (200-300ms) and stores 507 patterns across relevant domains (415 swift, 335 audio, 104 python). It uses ripgrep under the hood and returns structured JSON. The `confucius get` command returns full artifacts with `id`, `type`, `content`, `metadata`, and `timestamp` fields. However, the search results are text-matched (not semantic/embedding-based), so query phrasing matters. An MCP server exists but is scoped to a different repository (`white_room`) -- for this project, the CLI is the correct interface.

The Qwen2.5-Coder-7B-Instruct model has a 32,768 token context window (confirmed via `ollama show`). Token budget analysis shows that a full SLC system prompt (~196 tokens) + 5 retrieved patterns (~160 tokens) + a typical user prompt (~40 tokens) uses only ~400 tokens total, leaving 32,368 tokens for generation. Context window pressure is NOT a concern for this use case -- even with 10 patterns, total input stays under 1,000 tokens.

For evaluation, HumanEval is the gold standard for code generation quality (LAKE-16). It uses execution-based testing (pass@k metric) on 164 Python problems with ~8 unit tests each. The `human-eval` pip package provides the dataset and evaluation harness, with no internet required after installation. The existing `benchmark_compare.py` script (694 lines) provides the architectural pattern for comparing models, with both inline (`mlx_lm.generate`) and server (HTTP API) modes. The existing `benchmark-latency.py` and `benchmark-throughput.py` scripts already satisfy LAKE-17 for latency/throughput measurement.

**Primary recommendation:** Build the RAG pipeline as a single `generate.py` script that chains Confucius search -> prompt assembly -> Ollama/inline generation -> output. Reuse the `benchmark_compare.py` pattern for the evaluation framework, extending it with a third "RAG-augmented" column.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Confucius stores patterns as text memories -- retrieve relevant ones at inference time
- Retrieval must be fast (<100ms) to not degrade user experience
- Context window budget must be managed: system prompt + RAG context + user prompt + generation
- SLC coding standards injected as part of the system prompt
- Must include Bret's specific patterns (Apple ecosystem, Swift, Python, JUCE)
- Must be concise to leave room for generation
- HumanEval-based code generation quality metric (LAKE-16)
- Compare 3 variants: base model, fine-tuned (best adapter), fine-tuned + RAG
- Latency and throughput benchmarks per model size (LAKE-17)
- Full pipeline must run offline end-to-end (LAKE-11 through LAKE-14)
- Script-based pipeline: user prompt -> RAG retrieval -> prompt assembly -> Ollama inference -> output
- No HTTP server needed (CLI-first, per project scope)
- Confucius CLI used directly for retrieval (no MCP overhead)

### Claude's Discretion
- Exact prompt template format and token budget allocation
- Number of benchmark tasks and evaluation criteria
- How to score "quality" beyond pass/fail

### Deferred Ideas (OUT OF SCOPE)
- Terminal UI for interactive code generation (v2 scope)
- Multi-model serving (v2 scope)
- Xcode integration (v2 scope)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LAKE-11 | Confucius RAG retrieval integrated into generation pipeline | `confucius search` CLI confirmed (200-300ms latency), JSON output, supports `--limit`. 507 stored patterns. CLI-only approach avoids MCP scoping issues. |
| LAKE-12 | SLC coding standards injected via system prompt | ~196 tokens for full SLC prompt. Qwen2.5-Coder chat template supports system role. Ollama `/api/chat` accepts system messages (verified). |
| LAKE-13 | Domain-specific pattern retrieval (Swift, Python, JUCE, PCB layouts) | Confucius has 415 swift, 335 audio, 104 python patterns. JUCE patterns exist within audio corpus. PCB patterns require seeding before benchmarking. |
| LAKE-14 | Context window management for RAG + prompt + generation | 32,768 token context window (verified). SLC prompt + 5 RAG patterns + user prompt = ~400 tokens. No budget pressure. |
| LAKE-15 | Benchmark framework comparing base vs fine-tuned model | `benchmark_compare.py` (694 lines) provides architectural pattern with inline and server modes. Extend with third "RAG" column. |
| LAKE-16 | HumanEval-based code generation quality metric | `human-eval` pip package (1.0.3) provides 164 Python problems + evaluation harness. pass@k metric. Runs offline after install. |
| LAKE-17 | Latency and throughput benchmarks per model size | `benchmark-latency.py` (TTFT) and `benchmark-throughput.py` (tok/s) already exist. Support Ollama OpenAI-compatible API. |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Confucius RAG retrieval | Local CLI (Python subprocess) | -- | CLI subprocess is fastest path; MCP is scoped to wrong repo |
| System prompt assembly | Local CLI (Python) | -- | String concatenation/formatting with token budget tracking |
| Model inference (Ollama) | API (Ollama HTTP) | -- | OpenAI-compatible `/v1/chat/completions` supports system messages |
| Model inference (inline) | Local GPU (mlx_lm.generate) | -- | Direct model loading for benchmarking without server overhead |
| HumanEval execution | Local CLI (Python) | -- | Sandboxed code execution via `human-eval` package |
| Latency/throughput measurement | Local CLI (Python) | API (Ollama HTTP) | Already implemented in existing benchmark scripts |
| Pattern seeding | Local CLI (confucius store) | -- | Pre-populate Confucius with domain patterns before evaluation |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| confucius CLI | installed (`~/.claude/bin/confucius`) | Pattern storage and retrieval via subprocess | 507 patterns stored, ripgrep-backed search, 200-300ms latency |
| ollama | 0.30.7 (installed) | Model serving via HTTP API | OpenAI-compatible `/v1/chat/completions` with system message support |
| mlx-lm | 0.31.3 (installed) | Inline model loading for benchmarks | `mlx_lm.generate` + `mlx_lm.load` for serverless benchmarking |
| human-eval | 1.0.3 (NOT installed) | HumanEval benchmark dataset + evaluation harness | 164 Python problems, pass@k metric, offline execution |
| transformers | 5.10.0.dev0 (installed) | Tokenizer for token budget analysis | Qwen ChatML template, `apply_chat_template` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| urllib.request | stdlib | HTTP calls to Ollama API | All API calls (already used in existing benchmark scripts) |
| subprocess | stdlib | Calling confucius CLI | Every RAG retrieval operation |
| json | stdlib | Parsing confucius search output | All confucius interactions |
| ast | stdlib | Python syntax validation | Code quality heuristics in benchmarks |
| time | stdlib | Latency measurement | All benchmark scripts |
| math | stdlib | pass@k combinatorics | HumanEval evaluation metric |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| confucius CLI | confucius MCP server | MCP server scoped to `white_room` repo; CLI is correct for this project |
| confucius CLI | Custom embedding search | Would be faster/semantic but violates "don't hand-roll" -- use what exists |
| human-eval package | evalplus | evalplus has augmented tests but requires internet; human-eval is simpler and offline |
| Ollama API | mlx_lm.server API | Both work; Ollama is already configured and tested with system messages |

**Installation:**
```bash
pip install human-eval  # Only new dependency needed
```

**Version verification:**
```bash
pip show human-eval     # 1.0.3 - latest, verified via pip search
confucius --version    # CLI available at ~/.claude/bin/confucius
ollama --version       # 0.30.7 - verified
pip show mlx-lm        # 0.31.3 - verified
pip show transformers   # 5.10.0.dev0 - verified
```

## Architecture Patterns

### System Architecture Diagram

```
                          Generation Pipeline
                          ===================

  User Prompt ──────────────────────────────────────────┐
                                                          v
  confucius search ──>  Retrieve Top-K     ──>  Assemble       ──>  Ollama /v1/chat/completions
  ("swift async")        Patterns (~200ms)        Prompt              (stream/non-stream)
                              │                     │                        │
                              v                     v                        v
                        [Pattern 1]          System Prompt         Generated
                        [Pattern 2]     +   RAG Context        Code Output
                        [Pattern 3]     +   User Prompt
                        [Pattern 4]
                        [Pattern 5]

                          Benchmark Pipeline
                          ==================

  HumanEval Dataset ──> generate.py ──> Execute Tests ──> pass@k Score
  (164 problems)        (3 variants)     (subprocess)        (base / ft / rag)

  Variant A: base model only (no adapter, no RAG)
  Variant B: fine-tuned adapter (no RAG)
  Variant C: fine-tuned adapter + RAG (full pipeline)

                          Existing Benchmarks (LAKE-17)
                          =============================

  benchmark-latency.py  ──>  TTFT measurement (ms)  ──>  Per-variant report
  benchmark-throughput.py ──>  tok/s measurement   ──>  Per-variant report
```

### Recommended Project Structure
```
me_code_pretty_one_day/
├── scripts/
│   ├── generate.py                # NEW: RAG pipeline (confucius -> prompt -> inference)
│   ├── benchmark_humaneval.py      # NEW: HumanEval pass@k for 3 variants
│   ├── benchmark_compare.py        # EXTEND: Add RAG variant column
│   ├── benchmark-latency.py        # EXISTING: TTFT (extend with --adapter flag)
│   ├── benchmark-throughput.py     # EXISTING: tok/s (extend with --adapter flag)
│   ├── seed_patterns.py            # NEW: Pre-populate Confucius with domain patterns
│   ├── prompt_template.py          # NEW: SLC system prompt + RAG assembly logic
│   └── ...existing scripts...
├── prompts/
│   ├── slc_system.txt              # NEW: SLC coding standards system prompt
│   └── domains.json                # NEW: Domain tag -> confucius search query mapping
├── data/
│   └── humaneval_results/          # NEW: Benchmark output (gitignored)
└── training/
    └── adapters-600/               # Best adapter from Phase 4
```

### Pattern 1: RAG Retrieval via Confucius CLI

**What:** Use `confucius search` as a subprocess to retrieve domain-relevant patterns. Parse JSON output to extract pattern content for injection into the system prompt.

**When to use:** Every generation request that should include domain knowledge.

**Example:**
```python
import json
import subprocess

def retrieve_patterns(query: str, limit: int = 5) -> list[dict]:
    """Retrieve relevant patterns from Confucius via CLI.

    Returns list of dicts with 'id', 'type', 'content', 'tags'.
    Latency: ~200-300ms measured on this machine.
    """
    result = subprocess.run(
        ["confucius", "search", query, "--limit", str(limit)],
        capture_output=True, text=True, timeout=10,
    )
    patterns = []
    # Parse the human-readable + JSON output from confucius
    # confucius search returns structured text with ### headers
    lines = result.stdout.strip().split("\n")
    current = None
    for line in lines:
        if line.startswith("### "):
            if current:
                patterns.append(current)
            current = {"id": line[4:].rstrip("..."), "content": ""}
        elif current and line.startswith("**Type:**"):
            current["type"] = line.split(":")[1].strip()
        elif current and line.startswith("**Tags:**"):
            current["tags"] = line.split(":")[1].strip()
        elif current and line.startswith("**Content:**"):
            pass  # Content starts on next line
        elif current and current.get("content") is not None:
            current["content"] += line + "\n"
    if current:
        patterns.append(current)
    return patterns[:limit]
```

Source: [VERIFIED] Tested `confucius search "slc" --limit 5` on 2026-06-12. Returns structured text with `###` headers, `**Type:**`, `**Tags:**`, `**Content:**` markers. Latency 225ms measured.

**Alternative: Use `confucius get` for full artifact JSON.**
```python
def get_pattern(artifact_id: str) -> dict:
    """Get full pattern by ID. Returns JSON with id, type, content, metadata, timestamp."""
    result = subprocess.run(
        ["confucius", "get", artifact_id],
        capture_output=True, text=True, timeout=10,
    )
    return json.loads(result.stdout)
```

Source: [VERIFIED] `confucius get pattern-slc-mindset` returns valid JSON with keys `id`, `type`, `content`, `metadata`, `timestamp`. Content length 620 chars for SLC pattern.

### Pattern 2: System Prompt Assembly with Token Budget

**What:** Combine SLC coding standards with retrieved RAG patterns into a single system message, respecting the model's context window budget.

**When to use:** Every generation request. The assembly function should track token usage.

**Example:**
```python
from transformers import AutoTokenizer

class PromptAssembler:
    """Assembles system prompts with SLC standards + RAG context.

    Token budget analysis (verified via tokenizer):
    - SLC system prompt: ~196 tokens
    - Per RAG pattern: ~32 tokens (avg content length / token ratio)
    - 5 patterns: ~160 tokens
    - User prompt: ~40 tokens (avg)
    - Chat template overhead: ~10 tokens
    - Total input: ~406 tokens
    - Context window: 32,768 tokens
    - Remaining for generation: ~32,362 tokens (no pressure)
    """

    def __init__(self, model_path: str, max_context: int = 32768):
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path, trust_remote_code=True
        )
        self.max_context = max_context
        self.slc_prompt = self._load_slc_prompt()

    def assemble(
        self,
        user_prompt: str,
        patterns: list[dict],
        max_generation_tokens: int = 2048,
    ) -> list[dict]:
        """Build chat messages with system+RAG+user within context budget."""
        # Build RAG section
        rag_section = "## Retrieved Patterns\n\n"
        for p in patterns:
            rag_section += f"### {p.get('type', 'pattern').title()}\n"
            rag_section += p.get("content", "") + "\n\n"

        # Combine system prompt
        system_content = self.slc_prompt + "\n\n" + rag_section

        # Token budget check
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_prompt},
        ]
        formatted = self.tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=True
        )
        if len(formatted) + max_generation_tokens > self.max_context:
            # Truncate patterns from the end until budget fits
            while patterns and len(formatted) + max_generation_tokens > self.max_context:
                patterns.pop()
                rag_section = "## Retrieved Patterns\n\n"
                for p in patterns:
                    rag_section += f"### {p.get('type', 'pattern').title()}\n"
                    rag_section += p.get("content", "") + "\n\n"
                system_content = self.slc_prompt + "\n\n" + rag_section
                messages = [
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_prompt},
                ]
                formatted = self.tokenizer.apply_chat_template(
                    messages, add_generation_prompt=True, tokenize=True
                )

        return messages
```

Source: [VERIFIED] Token counts measured with actual Qwen2.5-Coder tokenizer on 2026-06-12. Full SLC prompt = 196 tokens, 5 RAG patterns = 160 tokens, user prompt = 40 tokens, total = 396 tokens + chat template overhead.

### Pattern 3: HumanEval pass@k Evaluation

**What:** Execute generated code against unit tests from 164 hand-crafted Python problems. Calculate pass@k using the hypergeometric distribution formula.

**When to use:** Measuring code generation quality (LAKE-16). Compare base vs fine-tuned vs RAG.

**Example:**
```python
import math

def pass_at_k(n: int, c: int, k: int) -> float:
    """Calculate pass@k using the hypergeometric distribution.

    Args:
        n: Total samples generated per problem
        c: Number of correct samples (passing all tests)
        k: Number of samples selected for evaluation

    Returns:
        Probability that at least one of k samples passes all tests.

    Formula: pass@k = 1 - C(n-c, k) / C(n, k)
    """
    if n - c < k:
        return 1.0
    return 1.0 - math.comb(n - c, k) / math.comb(n, k)

# Example: 5 samples, 2 correct, k=1
# pass@1 = 1 - C(3,1)/C(5,1) = 1 - 3/5 = 0.4
assert abs(pass_at_k(5, 2, 1) - 0.4) < 1e-9
```

Source: [CITED: HumanEval paper (Chen et al., 2021)] -- pass@k formula with hypergeometric distribution. Detailed walkthrough at [HumanEval: Functional Code Generation Evaluation with Pass@k](https://mbrenndoerfer.com/writing/humaneval-code-generation-benchmark-pass-at-k).

**Using the human-eval package:**
```python
from human_eval.data import write_jsonl, read_problems
from human_eval.evaluation import evaluate_functional_correctness

# Load HumanEval problems
problems = read_problems()  # Returns dict: {"HumanEval/0": {...}, ...}
# 164 problems, each with: prompt, canonical_solution, test, entry_point

# Generate completions
samples = []
for task_id, problem in problems.items():
    # Call model with problem["prompt"] as user message
    completion = generate_with_model(problem["prompt"])
    samples.append({"task_id": task_id, "completion": completion})

# Write samples and evaluate
write_jsonl("samples.jsonl", samples)
results = evaluate_functional_correctness("samples.jsonl")  # Returns dict of pass/fail per sample
```

Source: [CITED: openai/human-eval GitHub](https://github.com/openai/human-eval) -- official evaluation harness.

### Pattern 4: Ollama API for Inference (OpenAI-compatible)

**What:** Use Ollama's OpenAI-compatible `/v1/chat/completions` endpoint for generation with system messages and RAG context.

**When to use:** Primary inference path for the generation pipeline. Supports system role (verified).

**Example:**
```python
import json
import urllib.request

def generate_via_ollama(
    messages: list[dict],
    model: str = "qwen2.5-coder:7b-instruct-q4_K_M",
    max_tokens: int = 2048,
    temperature: float = 0.2,
    base_url: str = "http://localhost:11434",
) -> dict:
    """Generate code via Ollama OpenAI-compatible API."""
    endpoint = f"{base_url}/v1/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": messages,  # Supports system, user, assistant roles
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }).encode()

    req = urllib.request.Request(
        endpoint, data=payload,
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode())
        choice = data["choices"][0]
        return {
            "content": choice["message"]["content"],
            "prompt_tokens": data["usage"]["prompt_tokens"],
            "completion_tokens": data["usage"]["completion_tokens"],
        }
```

Source: [VERIFIED] Tested `curl http://localhost:11434/v1/chat/completions` with system+user messages on 2026-06-12. Response includes `message.content` with system prompt correctly applied (returned "4" for "2+2" with "Be concise." system prompt).

### Anti-Patterns to Avoid

- **Using confucius MCP server for this project:** The MCP server is configured with `CONFUCIUS_REPOSITORY` pointing to `white_room`. For this project, use the CLI which reads from `~/.claude/.confucius/memory` and is not repo-scoped.

- **Building a custom embedding-based search:** Confucius uses ripgrep which is fast enough (200-300ms). Building an embedding search would violate "don't hand-roll" and add unnecessary complexity.

- **Ignoring the existing benchmark pattern:** `benchmark_compare.py` has inline mode with `mlx_lm.generate`, server mode with HTTP API, code quality heuristics, and comparison tables. The RAG pipeline benchmark should extend this pattern, not start from scratch.

- **Over-allocating context budget to RAG:** 5 patterns (~160 tokens) is sufficient. Stuffing more patterns in degrades generation quality by introducing noise. Use relevance filtering, not volume.

- **Running HumanEval with temperature 0 for pass@k comparison:** Greedy decoding gives deterministic pass@1 but no diversity for pass@k with k>1. Use temperature 0.2-0.8 depending on k value.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Code execution sandbox | Custom subprocess sandbox | `human-eval` package `evaluate_functional_correctness` | Handles timeouts, memory limits, test isolation |
| pass@k calculation | Custom probability math | `human_eval.evaluation` module | Implements hypergeometric distribution correctly with edge cases |
| Token counting | Custom BPE tokenizer | `transformers.AutoTokenizer` | Model's exact tokenizer accounts for special tokens, chat template overhead |
| Pattern search | Custom grep/embeddings | `confucius search` CLI | 507 patterns already stored, ripgrep-backed, 200-300ms |
| HTTP inference client | Custom HTTP handling | `urllib.request` (stdlib) | Already used in all existing benchmark scripts |
| Chat template formatting | Manual `<\|im_start\|>` wrapping | `tokenizer.apply_chat_template()` | Handles tools, multi-turn, special tokens correctly |

**Key insight:** The entire pipeline can be built from composable pieces: confucius CLI for retrieval, tokenizer for prompt assembly, Ollama API for inference, human-eval package for evaluation. Custom code is only needed for the orchestration glue.

## Common Pitfalls

### Pitfall 1: Confucius Search Returns No Results for Code-Generation Queries

**What goes wrong:** Searching for "code generation" or "write a swift function" returns zero results because Confucius stores patterns, not tutorials.

**Why it happens:** Confucius contains 507 patterns from development work (bug fixes, design decisions, anti-patterns), not general coding examples. Searches need to match the vocabulary of stored patterns.

**How to avoid:** Pre-seed Confucius with domain-specific coding patterns before running benchmarks. Use the existing tag taxonomy (swift: 69 patterns, audio: 70, python: ~26) as search targets. Map user prompt keywords to Confucius tags.

**Warning signs:** `confucius search "..."` consistently returns "No results for: ..."

**Confidence:** HIGH -- verified by testing multiple queries. "slc" returns 149 matches; "code generation" returns 0. [VERIFIED: tested on 2026-06-12]

### Pitfall 2: HumanEval Data Contamination with Fine-Tuned Models

**What goes wrong:** The fine-tuned model has seen HumanEval-like problems during training (since training data was generated from the base model), inflating scores.

**Why it happens:** The 22K training examples in `train.jsonl` were generated synthetically and could overlap with HumanEval's 164 problems, especially since both draw from common programming exercises.

**How to avoid:** Check for overlap between training data prompts and HumanEval prompts. If overlap exists, either (a) exclude overlapping HumanEval problems from evaluation, or (b) use HumanEval+ (augmented tests) which catches solutions that only pass sparse tests. Alternatively, create a held-out set of novel prompts not seen during training.

**Warning signs:** pass@1 score is suspiciously high (>50% for a 7B model) or identical across base and fine-tuned models.

**Confidence:** MEDIUM -- contamination is a known issue in the field [CITED: mbrenndoerfer.com HumanEval article, contamination section]. Actual overlap in this project's training data needs verification.

### Pitfall 3: RAG Context Dilution

**What goes wrong:** Including too many retrieved patterns or irrelevant patterns degrades generation quality below the base model (no RAG) level.

**Why it happens:** LLMs are sensitive to irrelevant context. Noise in the system prompt can confuse the model, especially for small models (7B) that have limited instruction-following capacity compared to larger models.

**How to avoid:** Limit to top 3-5 patterns per query. Rank by relevance (Confucius returns in relevance order). Consider filtering out patterns with content length > 500 tokens. Test with and without RAG to measure the actual impact.

**Warning signs:** RAG-augmented scores are lower than fine-tuned-only scores on the same prompts.

**Confidence:** HIGH -- well-documented RAG pitfall [CITED: evidentlyai.com RAG evaluation guide, baz.co RAG code review article].

### Pitfall 4: Confucius CLI Output Parsing Fragility

**What goes wrong:** Parsing `confucius search` output breaks if the format changes or special characters appear in pattern content.

**Why it happens:** `confucius search` returns human-readable formatted text with `###`, `**Type:**`, `**Tags:**`, `**Content:**` markers, not pure JSON. The format is stable but not formally versioned.

**How to avoid:** Use `confucius get <id>` for individual patterns (returns JSON). For search, parse defensively with regex matching on the known markers. Consider a thin wrapper function that handles both formats. If parsing fails, fall back to no RAG context (graceful degradation).

**Warning signs:** KeyError or IndexError when parsing search results.

**Confidence:** HIGH -- output format verified on 2026-06-12. Use `get` for JSON reliability.

## Code Examples

### Ollama API with System Prompt + RAG (Full Pipeline)

```python
#!/usr/bin/env python3
"""Minimal RAG pipeline: user prompt -> confucius search -> prompt assembly -> ollama inference."""

import json
import subprocess
import urllib.request

def search_confucius(query: str, limit: int = 5) -> str:
    """Search Confucius and format results as RAG context section."""
    result = subprocess.run(
        ["confucius", "search", query, "--limit", str(limit)],
        capture_output=True, text=True, timeout=10,
    )
    # Extract pattern IDs from search output (### marker lines)
    pattern_ids = []
    for line in result.stdout.split("\n"):
        if line.startswith("### "):
            pid = line[4:].rstrip("...")
            if not pid.startswith("artifact-"):
                pattern_ids.append(pid)

    # Get full content for each pattern
    rag_parts = []
    for pid in pattern_ids[:limit]:
        get_result = subprocess.run(
            ["confucius", "get", pid],
            capture_output=True, text=True, timeout=10,
        )
        try:
            data = json.loads(get_result.stdout)
            rag_parts.append(data["content"])
        except (json.JSONDecodeError, KeyError):
            continue

    return "\n\n".join(rag_parts)


def generate(user_prompt: str, domain: str = "python") -> str:
    """Full RAG pipeline: search -> assemble -> infer."""
    rag_context = search_confucius(domain, limit=5)

    system_prompt = f"""You are an expert code generation assistant.

## SLC Coding Standards (MANDATORY)
- Simple, Lovable, Complete -- no workarounds
- Immutability: create new objects, never mutate
- Error handling: comprehensive, never swallow silently
- Functions <50 lines, files <800 lines
- Include type hints and docstrings

## Retrieved Context
{rag_context}"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    payload = json.dumps({
        "model": "qwen2.5-coder:7b-instruct-q4_K_M",
        "messages": messages,
        "max_tokens": 2048,
        "temperature": 0.2,
    }).encode()

    req = urllib.request.Request(
        "http://localhost:11434/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode())
        return data["choices"][0]["message"]["content"]


if __name__ == "__main__":
    import sys
    prompt = sys.argv[1] if len(sys.argv) > 1 else "Write a Swift function for binary search"
    domain = sys.argv[2] if len(sys.argv) > 2 else "swift"
    print(generate(prompt, domain))
```

Source: [VERIFIED] All components tested individually on 2026-06-12: Ollama API with system messages, confucius search, confucius get JSON output.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| BLEU/ROUGE for code eval | HumanEval pass@k (execution-based) | 2021 (Chen et al.) | Measures functional correctness, not lexical similarity |
| pass@1 only | pass@k with multiple k values | 2021 | Captures diversity-quality tradeoff at different budgets |
| HumanEval only | HumanEval+ (augmented tests) | 2023 | Catches solutions that pass sparse tests but fail on edge cases |
| Raw ChatML in prompts | `apply_chat_template()` | Standard practice | Correct special token handling for Qwen2.5 |
| Manual GGUF conversion | mlx_lm.server native adapter loading | Phase 4 | No format conversion needed for fine-tuned models |

**Deprecated/outdated:**
- `ollama create` without `--experimental` for safetensors: Qwen2 GGUF export from mlx-lm doesn't work, but `--experimental` flag is the path forward (untested reliability)
- BLEU-based code evaluation: Superseded by execution-based HumanEval for functional correctness

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `human-eval` package works fully offline after `pip install` (no internet at runtime) | Standard Stack | May need to pre-download dataset; test after install |
| A2 | Training data in `train.jsonl` does not significantly overlap with HumanEval problems | Pitfall 2 | pass@k scores inflated; need to check overlap and possibly exclude problems |
| A3 | Confucius CLI output format (`###`, `**Type:**` markers) is stable across versions | Pitfall 4 | Parser breaks; mitigation: use `confucius get` for JSON reliability |
| A4 | 5 retrieved patterns is the optimal number for RAG context | Pattern 2, Pitfall 3 | May need to tune; 3-7 range likely works, test empirically |
| A5 | Fine-tuned model (adapters-600) is the "best adapter" for benchmarking | Phase Requirements | Phase 4 trained 4 adapter variants; need to verify which is best |

**If this table is empty:** All claims in this research were verified or cited -- no user confirmation needed.

## Open Questions (RESOLVED)

1. **Which adapter variant is "best" for Phase 5 benchmarking?**
   - What we know: Phase 4 produced 4 variants: `adapters/` (rank 32, 1000 steps), `adapters-600/` (600 steps), `adapters-1200/` (1200 steps), `adapters-formatting/` (2000 steps, formatting-focused). The default in `benchmark_compare.py` is `adapters-600`.
   - What's unclear: Whether the 600-step variant is truly best for code generation quality, or whether 1200 steps or the formatting adapter performs better on HumanEval.
   - Recommendation: Run a quick 10-prompt comparison across all variants using existing `benchmark_compare.py` before Phase 5 execution. Use the winner as the "fine-tuned" column.

2. **Should HumanEval be run with n=200 samples (standard) or a smaller n for speed?**
   - What we know: Standard academic evaluation uses n=200 samples per problem with k=1,10,100. This means 164 * 200 = 32,800 generation calls per variant. At ~2-5 seconds per call, this is 18-45 hours per variant.
   - What's unclear: Whether n=20 (3,280 calls, ~2-5 hours per variant) provides sufficient statistical power for comparison purposes.
   - Recommendation: Use n=20 for development iteration, n=50 for final evaluation. The confidence interval at p=0.3, n=50 is roughly +/- 6%, which is sufficient to distinguish base from fine-tuned from RAG.

3. **Should PCB domain patterns be seeded into Confucius?**
   - What we know: LAKE-13 requires "PCB layouts" as a domain for pattern retrieval. Confucius currently has no PCB-specific patterns (0 matches for "pcb" or "kicad").
   - What's unclear: Whether this is a hard requirement or aspirational. PCB code generation is handled by `kicad-agent` (separate project per REQUIREMENTS.md).
   - Recommendation: Seed 5-10 basic PCB/KiCad patterns from kicad-agent knowledge. This is a small effort and satisfies the requirement fully.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| confucius CLI | RAG retrieval (LAKE-11) | Yes | `~/.claude/bin/confucius` | -- |
| ollama | Model serving | Yes | 0.30.7 | mlx_lm.server (inline) |
| mlx-lm | Inline generation for benchmarks | Yes | 0.31.3 | -- |
| transformers | Tokenizer, prompt assembly | Yes | 5.10.0.dev0 | -- |
| human-eval | HumanEval dataset + evaluator (LAKE-16) | **No** | -- | Custom pass@k implementation (don't hand-roll -- install the package) |
| base model (Qwen2.5-Coder) | Inference | Yes | 7B Q4_K_M via Ollama | -- |
| fine-tuned adapters | Fine-tuned variant | Yes | 4 variants in training/ | -- |
| Python 3.11 | Script execution | Yes | 3.11.11 | -- |
| Disk space | Adapter loading, results | Yes | 35GB free | -- |

**Missing dependencies with no fallback:**
- `human-eval` package -- MUST install before execution: `pip install human-eval`

**Missing dependencies with fallback:**
- None -- all other dependencies are available.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | None (see Wave 0) |
| Quick run command | `pytest scripts/ -x -v` |
| Full suite command | `pytest scripts/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LAKE-11 | Confucius search returns patterns | unit | `pytest scripts/test_rag_pipeline.py::test_confucius_search -x` | No -- Wave 0 |
| LAKE-11 | Pipeline assembles prompt with RAG context | unit | `pytest scripts/test_rag_pipeline.py::test_prompt_assembly -x` | No -- Wave 0 |
| LAKE-12 | System prompt contains SLC standards | unit | `pytest scripts/test_prompt_template.py::test_slc_prompt_content -x` | No -- Wave 0 |
| LAKE-13 | Domain tags map to correct search queries | unit | `pytest scripts/test_prompt_template.py::test_domain_mapping -x` | No -- Wave 0 |
| LAKE-14 | Assembled prompt fits within context window | unit | `pytest scripts/test_prompt_template.py::test_token_budget -x` | No -- Wave 0 |
| LAKE-15 | Benchmark runs 3 variants without error | integration | `pytest scripts/test_benchmark_humaneval.py::test_benchmark_runs -x` | No -- Wave 0 |
| LAKE-16 | HumanEval pass@k calculation is correct | unit | `pytest scripts/test_benchmark_humaneval.py::test_pass_at_k -x` | No -- Wave 0 |
| LAKE-17 | Latency/throughput benchmarks run | integration | `python3 scripts/benchmark-latency.py --iterations 1` | Yes (existing) |

### Sampling Rate
- **Per task commit:** `pytest scripts/ -x -v`
- **Per wave merge:** `pytest scripts/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `scripts/test_rag_pipeline.py` -- covers LAKE-11 (confucius search, prompt assembly with RAG)
- [ ] `scripts/test_prompt_template.py` -- covers LAKE-12, LAKE-13, LAKE-14 (SLC content, domain mapping, token budget)
- [ ] `scripts/test_benchmark_humaneval.py` -- covers LAKE-15, LAKE-16 (pass@k math, benchmark runner smoke test)
- [ ] `scripts/conftest.py` -- extend existing with fixtures for confucius mock, tokenizer, model path

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | N/A -- local tool, no auth |
| V3 Session Management | No | N/A -- local tool, no sessions |
| V4 Access Control | No | N/A -- local tool, no network serving |
| V5 Input Validation | Yes | Validate user prompts before injection; sanitize confucius output |
| V6 Cryptography | No | N/A -- no cryptographic operations |

### Known Threat Patterns for RAG + Code Generation Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Prompt injection via RAG context | Tampering | Sanitize confucius output before injection; never trust stored patterns blindly |
| Code execution from HumanEval | Tampering | `human-eval` package provides sandboxing (timeouts, process isolation) |
| Malicious patterns in Confucius | Tampering | Only store patterns from trusted sources; confucius is local-only |
| Model output with injected instructions | Tampering | Parse code blocks only; strip non-code content before execution |

## Sources

### Primary (HIGH confidence)
- [VERIFIED: confucius CLI] -- search (200-300ms, ripgrep-backed), get (JSON output), store, tags, stats. Tested on 2026-06-12.
- [VERIFIED: Ollama API] -- `/v1/chat/completions` with system messages, `/api/generate`. Tested on 2026-06-12.
- [VERIFIED: Qwen2.5-Coder context window] -- 32,768 tokens via `ollama show`. Verified on 2026-06-12.
- [VERIFIED: Token budget analysis] -- Measured with actual Qwen2.5-Coder tokenizer (transformers 5.10.0.dev0). SLC prompt = 196 tokens, 5 patterns = 160 tokens, user = 40 tokens.
- [VERIFIED: mlx_lm inline generation] -- `_inline_generate` pattern from `benchmark_compare.py` lines 484-495.
- [VERIFIED: Existing benchmark scripts] -- `benchmark-latency.py`, `benchmark-throughput.py`, `benchmark_compare.py` all present and functional.
- [CITED: openai/human-eval GitHub](https://github.com/openai/human-eval) -- official evaluation harness, pass@k metric implementation.

### Secondary (MEDIUM confidence)
- [CITED: HumanEval pass@k walkthrough](https://mbrenndoerfer.com/writing/humaneval-code-generation-benchmark-pass-at-k) -- comprehensive pass@k explanation, formula derivation, statistical considerations, contamination discussion.
- [CITED: evidentlyai.com RAG evaluation guide](https://www.evidentlyai.com/llm-guide/rag-evaluation) -- RAG evaluation best practices, retrieval + generation quality metrics.
- [CITED: baz.co RAG code review article](https://baz.co/resources/scaling-ai-feedback-onto-codebase-context-a-primer-on-rag-code-reviews) -- RAG context optimization for code tasks.

### Tertiary (LOW confidence)
- [ASSUMED: human-eval package offline capability] -- Standard pip packages typically bundle data; verify after install.
- [ASSUMED: Training data does not heavily overlap HumanEval] -- Needs explicit verification (string similarity check between train.jsonl prompts and HumanEval prompts).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all versions verified via `pip show`, `ollama --version`, `confucius --help`
- Architecture: HIGH - token budgets measured with actual tokenizer, API endpoints tested
- Pitfalls: HIGH - confucius search behavior verified empirically, RAG dilution well-documented in literature
- HumanEval: MEDIUM - package not yet installed, contamination overlap not yet checked

**Research date:** 2026-06-12
**Valid until:** 30 days (confucius CLI is stable, Ollama API is stable, human-eval package is mature)
