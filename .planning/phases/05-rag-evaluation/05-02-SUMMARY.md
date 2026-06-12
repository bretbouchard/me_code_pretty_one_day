---
phase: 05-rag-evaluation
plan: 02
subsystem: rag
tags: [confucius, rag, ollama, qwen2.5-coder, prompt-assembly, cli, pipeline]

# Dependency graph
requires:
  - phase: 05-01-rag-foundation
    provides: PromptAssembler class, SLC system prompt, domain mapping, confucius retrieval
  - phase: 03-local-ai-serving
    provides: Ollama serving Qwen2.5-Coder-7B at localhost:11434
provides:
  - Full RAG generation pipeline CLI (generate.py)
  - generate_with_rag() function chaining confucius -> prompt assembly -> Ollama inference
  - Integration test suite with --run-integration gating
  - skip_rag parameter on PromptAssembler.assemble() for RAG-less mode
affects: [05-03-benchmark-humaneval, 05-04-pattern-seeding]

# Tech tracking
tech-stack:
  added: [urllib.request for Ollama OpenAI-compatible API calls, argparse for CLI interface]
  patterns: [graceful-degradation-on-connection-error, optional-rag-bypass, verbose-stderr-logging]

key-files:
  created:
    - scripts/generate.py
    - scripts/test_rag_pipeline.py
  modified:
    - scripts/prompt_template.py

key-decisions:
  - "Added skip_rag parameter to PromptAssembler.assemble() instead of mocking retrieval externally"
  - "Verbose output goes to stderr to keep stdout clean for piped usage"
  - "Ollama timeout set to 120 seconds per threat model T-05-06"

patterns-established:
  - "Optional RAG bypass: skip_rag flag allows running pipeline without confucius dependency"
  - "Stderr for diagnostics: verbose/timing info on stderr, generated output on stdout"

requirements-completed: [LAKE-11]

# Metrics
started: 2026-06-12T20:21:41Z
completed: 2026-06-12T20:29:18Z
duration: 8m
duration_minutes: 8
commits: 4
files_modified: 3
---

# Phase 05 Plan 02: RAG Generation Pipeline Summary

**Full RAG pipeline CLI chaining Confucius retrieval, SLC prompt assembly, and Ollama inference with graceful degradation and optional RAG bypass**

## Performance

- **Duration:** 8m
- **Started:** 2026-06-12T20:21:41Z
- **Completed:** 2026-06-12T20:29:18Z
- **Tasks:** 2
- **Commits:** 4 (atomic task commits, TDD cycle included)
- **Files modified:** 3

## Accomplishments
- `generate.py` CLI tool with `generate_with_rag()` function implementing full pipeline: confucius search -> PromptAssembler -> Ollama /v1/chat/completions
- `--no-rag` flag for RAG-less generation using only SLC system prompt
- `--verbose` flag reporting retrieval latency and token counts to stderr
- Graceful degradation on Ollama connection errors and timeouts (returns None)
- `skip_rag` parameter added to `PromptAssembler.assemble()` for clean RAG bypass
- 9 unit tests with mocked dependencies, 3 integration tests gated behind `--run-integration`
- TDD execution: RED (failing tests) -> GREEN (implementation) -> committed

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Add failing tests for RAG generation pipeline** - `92b193f` (test)
2. **Task 1 GREEN: Implement RAG generation pipeline CLI and skip_rag support** - `07b848b` (feat)
3. **Task 1 fix: Fix test mocks and assertions for GREEN phase** - `f162ff9` (test)
4. **Task 2: Add integration tests for live Ollama RAG pipeline** - `c19f78b` (test)

## Files Created/Modified
- `scripts/generate.py` - RAG pipeline CLI (155 lines): generate_with_rag(), parse_args(), main()
- `scripts/test_rag_pipeline.py` - 9 unit tests + 3 integration tests with --run-integration gating
- `scripts/prompt_template.py` - Added skip_rag parameter to PromptAssembler.assemble()

## Decisions Made
- Added `skip_rag: bool = False` parameter to `PromptAssembler.assemble()` (rather than mocking retrieval externally) for clean separation between RAG and non-RAG modes
- Verbose/diagnostic output goes to stderr so stdout can be piped to files or other tools
- Ollama timeout of 120 seconds per threat model T-05-06 mitigation

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test mock target for urllib.request.urlopen**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Tests patched `generate.urlopen` but `urlopen` is imported into generate.py's namespace via `from urllib.request import urlopen` -- the attribute doesn't exist on the generate module
- **Fix:** Changed all mock patches from `"generate.urlopen"` to `"urllib.request.urlopen"` and extracted helper functions for mock setup
- **Files modified:** scripts/test_rag_pipeline.py
- **Verification:** All 9 unit tests pass
- **Committed in:** f162ff9

**2. [Rule 1 - Bug] Fixed assemble() assertion to include skip_rag keyword**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** After adding skip_rag parameter to PromptAssembler.assemble(), test assertions didn't include the new keyword argument
- **Fix:** Updated assert_called_once_with to include `skip_rag=False` / `skip_rag=True` as appropriate
- **Files modified:** scripts/test_rag_pipeline.py
- **Committed in:** f162ff9

**3. [Rule 1 - Bug] Fixed CLI test argv to exclude script name**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** parse_args() called with explicit argv list included "generate.py" as first element, which argparse treated as an extra positional argument
- **Fix:** Removed "generate.py" from the argv list since parse_args takes the args directly (not sys.argv)
- **Files modified:** scripts/test_rag_pipeline.py
- **Committed in:** f162ff9

**4. [Rule 1 - Bug] Fixed verbose test to check stderr instead of stdout**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** generate.py writes verbose output to stderr but test asserted on captured.out
- **Fix:** Changed assertion to check captured.err
- **Files modified:** scripts/test_rag_pipeline.py
- **Committed in:** f162ff9

---

**Total deviations:** 4 auto-fixed (4 bugs in test code)
**Impact on plan:** All auto-fixes were test corrections during TDD GREEN phase. Implementation followed plan exactly. No scope creep.

## Issues Encountered
- TDD test code needed 4 rounds of fixes to match implementation details (mock targets, assertions, argv handling, stderr capture). All resolved within the GREEN phase commit.

## User Setup Required
None - no external service configuration required. Ollama must be running for live integration tests.

## Next Phase Readiness
- generate_with_rag() ready for use by benchmark_humaneval.py (Plan 03)
- Integration tests provide validation path for live Ollama testing
- PromptAssembler.skip_rag enables benchmark variants (base only, RAG-augmented)

---
*Phase: 05-rag-evaluation*
*Completed: 2026-06-12*

## Self-Check: PASSED
