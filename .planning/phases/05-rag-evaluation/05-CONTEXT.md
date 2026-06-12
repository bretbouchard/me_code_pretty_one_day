# Phase 5: RAG & Evaluation - Context

**Gathered:** 2026-06-12
**Status:** Ready for planning
**Source:** Auto-generated from roadmap scope + existing artifacts

<domain>
## Phase Boundary

Wire Confucius RAG retrieval into the local code generation pipeline, inject SLC coding standards via system prompt, and build a benchmark suite comparing base vs fine-tuned model quality. This is the final phase — it connects all prior work (serving, fine-tuning, data generation) into a usable local AI system.

Existing infrastructure to build on:
- **Serving:** Ollama running Qwen2.5-Coder-7B-Instruct (Phase 3)
- **Fine-tuning:** 3 adapter variants trained via MLX-LoRA (Phase 4)
- **Training data:** 22K examples (19.8K train, 2.2K val) in ChatML format
- **Confucius:** Pattern storage CLI (`confucius store/search/list/get`) — available for RAG retrieval

</domain>

<decisions>
## Implementation Decisions

### RAG Integration Strategy
- Confucius stores patterns as text memories — retrieve relevant ones at inference time
- Retrieval must be fast (<100ms) to not degrade user experience
- Context window budget must be managed: system prompt + RAG context + user prompt + generation

### System Prompt Design
- SLC coding standards injected as part of the system prompt
- Must include Bret's specific patterns (Apple ecosystem, Swift, Python, JUCE)
- Must be concise to leave room for generation

### Benchmark Design
- HumanEval-based code generation quality metric (LAKE-16)
- Compare 3 variants: base model, fine-tuned (best adapter), fine-tuned + RAG
- Latency and throughput benchmarks per model size (LAKE-17)
- Full pipeline must run offline end-to-end (LAKE-11 through LAKE-14)

### Architecture
- Script-based pipeline: user prompt → RAG retrieval → prompt assembly → Ollama inference → output
- No HTTP server needed (CLI-first, per project scope)
- Confucius CLI used directly for retrieval (no MCP overhead)

### Claude's Discretion
- Exact prompt template format and token budget allocation
- Number of benchmark tasks and evaluation criteria
- How to score "quality" beyond pass/fail

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 4 Artifacts (Fine-Tuning Pipeline)
- `.planning/phases/04-fine-tuning-pipeline/04-01-SUMMARY.md` — Training data generator (5K seed tasks, 22K generated)
- `.planning/phases/04-fine-tuning-pipeline/04-02-SUMMARY.md` — LoRA config and training wrapper
- `.planning/phases/04-fine-tuning-pipeline/04-03-SUMMARY.md` — Adapter serving and benchmarks
- `.planning/phases/04-fine-tuning-pipeline/04-RESEARCH.md` — Technical research

### Training Data & Config
- `training/lora_config.yaml` — Active LoRA config (rank 32, QLoRA 4-bit)
- `training/adapters/` — Base adapter (rank 32, 1000 steps)
- `training/adapters-600/` — 600-step variant
- `training/adapters-1200/` — 1200-step variant
- `training/adapters-formatting/` — Formatting-focused adapter (2000 steps)
- `data/train.jsonl` — 19,800 training examples
- `data/valid.jsonl` — 2,200 validation examples

### Requirements
- `.planning/REQUIREMENTS.md` — LAKE-11 through LAKE-17 requirement text

### Confucius CLI
- Available commands: `confucius store`, `confucius search`, `confucius list`, `confucius get`
- Pattern storage for domain knowledge retrieval

</canonical_refs>

<specifics>
## Specific Ideas

- Store Bret's coding patterns in Confucius as domain knowledge before benchmarking
- Use `ollama api generate` endpoint for inference (already running)
- Benchmark should include: task description → code generation → execution test → score
- Consider using mlx_lm.server with adapter loading as alternative serving path

</specifics>

<deferred>
## Deferred Ideas

- Terminal UI for interactive code generation (v2 scope)
- Multi-model serving (v2 scope)
- Xcode integration (v2 scope)

</deferred>

---

*Phase: 05-rag-evaluation*
*Context gathered: 2026-06-12*
