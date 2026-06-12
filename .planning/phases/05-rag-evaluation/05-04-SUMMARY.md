---
phase: 05-rag-evaluation
plan: 04
subsystem: benchmarking
tags: [benchmark, latency, throughput, ttft, variant, ollama, rag, finetuned, tdd]

# Dependency graph
requires:
  - phase: 05-rag-evaluation/05-01
    provides: PromptAssembler class, SLC system prompt in prompts/slc_system.txt
  - phase: 05-rag-evaluation/05-02
    provides: generate.py with variant-based generation
provides:
  - benchmark-latency.py with --variant flag (base/finetuned/rag/all) and comparison table
  - benchmark-throughput.py with --variant flag (base/finetuned/rag/all) and comparison table
  - build_variant_messages function in both scripts
  - Optional messages parameter on measure_ttft and measure_throughput (backward compatible)
  - 16 tests covering all variant behaviors, message injection, and backward compatibility
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: [variant-messaging-pattern, comparison-table-output, lazy-import-for-optional-deps]

key-files:
  created:
    - scripts/test_latency_throughput.py
  modified:
    - scripts/benchmark-latency.py
    - scripts/benchmark-throughput.py

key-decisions:
  - "Lazy import of PromptAssembler inside build_variant_messages to avoid tokenizer load overhead for non-RAG variants"
  - "Used importlib.util.spec_from_file_location in tests to handle hyphenated Python module filenames"
  - "Default variant is 'base' which preserves exact original behavior (backward compatible)"

patterns-established:
  - "Variant messaging pattern: build_variant_messages maps variant name to message structure"
  - "Comparison table: --variant all runs 3 benchmarks and prints aligned table with Mean/Min/Max"

requirements-completed: [LAKE-17]

# Metrics
started: 2026-06-12T20:33:50Z
completed: 2026-06-12T20:38:13Z
duration: 4m
duration_minutes: 4
commits: 2
files_modified: 3
---

# Phase 05 Plan 04: Latency/Throughput Variant Benchmarks Summary

**TTFT and tok/s benchmark scripts extended with --variant flag for base, finetuned, and RAG-augmented model comparison with TDD**

## Performance

- **Duration:** 4m
- **Started:** 2026-06-12T20:33:50Z
- **Completed:** 2026-06-12T20:38:13Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Commits:** 2 (test + feat)
- **Files modified:** 3

## Accomplishments
- benchmark-latency.py and benchmark-throughput.py both support `--variant base|finetuned|rag|all` flag
- `--variant base` preserves exact original behavior (user-only messages, no system prompt)
- `--variant finetuned` loads SLC system prompt from prompts/slc_system.txt and sends system+user messages
- `--variant rag` uses PromptAssembler for full RAG pipeline (SLC + retrieved patterns + user prompt)
- `--variant all` runs all 3 variants sequentially and prints aligned comparison table
- Both `measure_ttft` and `measure_throughput` accept optional `messages` parameter (backward compatible)
- 16 tests pass: help flags, variant message building, RAG mock, message injection, invalid variant, backward compat

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Add failing tests for --variant support** - `353abe2` (test)
2. **Task 1 (GREEN): Implement --variant support in both benchmark scripts** - `0150938` (feat)

_Note: No REFACTOR commit needed -- implementation was clean on first pass._

## Files Created/Modified
- `scripts/benchmark-latency.py` - Extended with --variant flag, build_variant_messages, messages param, comparison table
- `scripts/benchmark-throughput.py` - Extended with --variant flag, build_variant_messages, messages param, comparison table
- `scripts/test_latency_throughput.py` - 16 tests covering all variant behaviors and backward compatibility

## Decisions Made
- Lazy import of PromptAssembler inside `build_variant_messages` (not at module level) to avoid loading the heavy transformers tokenizer when running non-RAG variants (base/finetuned)
- Used `importlib.util.spec_from_file_location` in tests because Python can't import hyphenated filenames (`benchmark-latency.py`) directly
- Default variant is `base` which constructs `[{"role": "user", "content": prompt}]` -- identical to the original hardcoded behavior

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test import mechanism for hyphenated Python filenames**
- **Found during:** Task 1 (RED phase test execution)
- **Issue:** `import benchmark_latency` fails with `ModuleNotFoundError` because Python doesn't allow hyphens in module names. The test used `importlib.import_module("benchmark_latency")` which can't find `benchmark-latency.py`.
- **Fix:** Changed test import helper to use `importlib.util.spec_from_file_location(module_name, filepath)` which loads any file path as a module regardless of filename conventions
- **Files modified:** scripts/test_latency_throughput.py
- **Verification:** All 16 tests pass after fix
- **Committed in:** `0150938` (part of GREEN phase commit)

**2. [Rule 1 - Bug] Fixed mock patch target for lazily-imported PromptAssembler**
- **Found during:** Task 1 (GREEN phase test execution)
- **Issue:** `patch("benchmark_latency.PromptAssembler")` raised `AttributeError` because PromptAssembler is imported inside `build_variant_messages()` (lazy import), not at module level
- **Fix:** Changed patch target from `benchmark_latency.PromptAssembler` to `prompt_template.PromptAssembler` (the actual module where the class lives), which works regardless of import location
- **Files modified:** scripts/test_latency_throughput.py
- **Verification:** RAG variant tests pass with mock correctly intercepting PromptAssembler
- **Committed in:** `0150938` (part of GREEN phase commit)

---

**Total deviations:** 2 auto-fixed (2 bugs in test code)
**Impact on plan:** Both fixes were test infrastructure issues, not implementation changes. The benchmark scripts themselves followed the plan exactly. No scope creep.

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED | `353abe2` | Present -- test-only commit with 16 failing tests |
| GREEN | `0150938` | Present -- feat commit, all 16 tests pass |
| REFACTOR | N/A | Not needed |

## Issues Encountered
- Python hyphenated filenames (`benchmark-latency.py`) can't be imported with standard `import` -- resolved via `importlib.util.spec_from_file_location`
- Lazy imports require patching at the source module, not the importing module -- resolved by patching `prompt_template.PromptAssembler`

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- LAKE-17 satisfied: latency and throughput benchmarks support all 3 model variants
- Comparison tables available via `--variant all` flag
- No downstream dependencies on this plan

---
*Phase: 05-rag-evaluation*
*Completed: 2026-06-12*
