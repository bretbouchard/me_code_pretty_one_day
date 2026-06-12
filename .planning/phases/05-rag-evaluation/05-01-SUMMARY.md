---
phase: 05-rag-evaluation
plan: 01
subsystem: rag
tags: [confucius, rag, prompt-assembly, qwen2.5-coder, token-budget, slc]

# Dependency graph
requires:
  - phase: 03-local-ai-serving
    provides: Ollama serving Qwen2.5-Coder-7B with system message support
  - phase: 04-fine-tuning-pipeline
    provides: Tokenizer at models/qwen2.5-coder-7b-instruct-4bit-mlx
provides:
  - PromptAssembler class for RAG-augmented prompt assembly
  - SLC system prompt with coding standards
  - Domain-to-confucius-query mapping (swift, python, juce, pcb)
  - Pattern seeder script for pre-populating Confucius
  - Unit test suite (29 tests) for prompt template module
affects: [05-02-generate-pipeline, 05-03-benchmark-humaneval]

# Tech tracking
tech-stack:
  added: [confucius CLI subprocess integration, transformers AutoTokenizer for token budget]
  patterns: [graceful-degradation, token-budget-truncation, sanitize-before-injection]

key-files:
  created:
    - prompts/slc_system.txt
    - prompts/domains.json
    - scripts/prompt_template.py
    - scripts/test_prompt_template.py
    - scripts/seed_patterns.py
  modified: []

key-decisions:
  - "Content sanitization: strip control characters and limit to 500 chars per pattern before injection"
  - "Graceful degradation: confucius timeout/parse failure returns empty list, pipeline continues without RAG"
  - "Used confucius search (text output) then confucius get (JSON) two-step retrieval for reliability"

patterns-established:
  - "Graceful degradation: subprocess failures never crash the pipeline"
  - "Token budget loop: iteratively pop patterns until context fits"
  - "Sanitize-before-injection: strip control chars, truncate content from untrusted CLI output"

requirements-completed: [LAKE-11, LAKE-12, LAKE-13, LAKE-14]

# Metrics
started: 2026-06-12T20:12:08Z
completed: 2026-06-12T20:18:15Z
duration: 6m
duration_minutes: 6
commits: 3
files_modified: 5
---

# Phase 05 Plan 01: RAG Foundation Summary

**SLC system prompt, domain mapping, PromptAssembler with Confucius RAG retrieval, token budget management, and pattern seeder -- 29 tests passing**

## Performance

- **Duration:** 6m
- **Started:** 2026-06-12T20:12:08Z
- **Completed:** 2026-06-12T20:18:15Z
- **Tasks:** 3
- **Commits:** 3 (atomic task commits)
- **Files modified:** 5

## Accomplishments
- SLC coding standards system prompt in prompts/slc_system.txt with immutability, error handling, sizing rules
- Domain mapping (swift, python, juce, pcb) to confucius search queries in prompts/domains.json
- PromptAssembler class that retrieves patterns from Confucius CLI, assembles system+RAG+user messages within 32768 token budget
- Token budget truncation removes patterns when context window would overflow
- Graceful degradation: timeout, parse failure, or empty results produce valid RAG-less prompts
- Content sanitization strips control characters and limits pattern length to 500 chars
- 15 seed patterns across 4 domains in seed_patterns.py for Confucius pre-population
- 29 unit tests covering SLC content, domain mapping, prompt assembly, token budget, graceful degradation

## Task Commits

Each task was committed atomically:

1. **Task 1: Create SLC system prompt and domain mapping configuration** - `60e8d7a` (test)
2. **Task 2: Build PromptAssembler with Confucius RAG retrieval and token budget management** - `9010dec` (feat)
3. **Task 3: Create domain pattern seeder for Confucius** - `bdf4b91` (feat)

## Files Created/Modified
- `prompts/slc_system.txt` - SLC coding standards system prompt (22 lines)
- `prompts/domains.json` - Domain tag to confucius search query mapping (4 domains)
- `scripts/prompt_template.py` - PromptAssembler class with retrieve_patterns and assemble methods
- `scripts/test_prompt_template.py` - 29 tests: TestSLCSystemPrompt (8), TestDomainMapping (9), TestPromptAssembler (12)
- `scripts/seed_patterns.py` - 15 seed patterns with --list, --dry-run, --domain flags

## Decisions Made
- Used two-step Confucius retrieval (search for IDs, get for JSON content) rather than parsing text output directly, for reliability (Plan specified this approach)
- Content sanitization via `_sanitize_content()` strips control characters and limits to 500 chars per pattern, addressing threat T-05-02
- Graceful degradation via try/except around all subprocess calls, returning empty list on any failure (addressing threat T-05-01)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed token budget truncation test mock strategy**
- **Found during:** Task 2 (GREEN phase)
- **Issue:** Mock tokenizer returning static token count caused test to assert incorrectly about truncation behavior -- the loop exited early because 14000 + 2048 < 32768, leaving patterns intact
- **Fix:** Changed test to use `max_context=500` (smaller than any mock return value) so the truncation loop runs until all patterns are exhausted regardless of mock tokenizer return values
- **Files modified:** scripts/test_prompt_template.py
- **Verification:** test_token_budget_truncates_patterns passes, all 29 tests green
- **Committed in:** 9010dec (part of Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug in test logic)
**Impact on plan:** Test fix only -- implementation followed plan exactly. No scope creep.

## Issues Encountered
- None -- all three tasks executed cleanly with only a test mock adjustment needed.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- PromptAssembler is ready for use by generate.py (Plan 02) and benchmark_humaneval.py (Plan 03)
- Confucius pattern seeding should be run before benchmarks: `python3 scripts/seed_patterns.py`
- Token budget management handles context window pressure automatically
- Graceful degradation ensures pipeline works even if Confucius is unavailable

---
*Phase: 05-rag-evaluation*
*Completed: 2026-06-12*
