# me_code_pretty_one_day

## What This Is

An offline-first local AI coding assistant built on Apple Silicon, using Qwen2.5-Coder-7B fine-tuned via MLX-LoRA and served through Ollama or mlx_lm.server. Integrates Confucius RAG for domain-specific patterns and injects SLC coding standards via system prompts. Supplements remote Claude Code (z.ai) for fast, private, offline-capable code generation.

Also includes comprehensive Rick agent updates: refreshing 4 existing Apple-specialist Ricks with WWDC25/26 platform changes and creating 4 new domain specialist Ricks (Foundation Models, Metal 4, Privacy, visionOS).

## Core Value

Ship fast local code generation that works completely offline, never phones home, and knows Bret's patterns — so simple tasks don't need remote AI.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] **LAKE-01**: Local model serving via Ollama or mlx_lm.server
- [ ] **LAKE-02**: MLX-LoRA fine-tuning pipeline for Qwen2.5-Coder-7B
- [ ] **LAKE-03**: Confucius RAG integration for domain patterns
- [ ] **LAKE-04**: SLC coding standards system prompt injection
- [ ] **LAKE-05**: Offline-first operation (zero network dependency)
- [ ] **LAKE-06**: Sub-5s inference latency for code generation
- [ ] **LAKE-07**: Training data generation (5000+ examples)
- [ ] **LAKE-08**: Benchmark and evaluation framework
- [ ] **RICK-01**: Update apple-elitist-rick with WWDC25/26 changes
- [ ] **RICK-02**: Update gamer-rick with WWDC25/26 changes
- [ ] **RICK-03**: Update swiftui-liquid-glass with WWDC25/26 changes
- [ ] **RICK-04**: Update swift-concurrency-expert with WWDC25/26 changes
- [ ] **RICK-05**: Create foundation-models-rick
- [ ] **RICK-06**: Create metal-4-rick
- [ ] **RICK-07**: Create privacy-rick
- [ ] **RICK-08**: Create visionos-rick

### Out of Scope

| Feature | Reason |
|---------|--------|
| Replacing Claude Code / z.ai | Supplements, not replaces — remote AI handles complex reasoning |
| Multi-user serving | Single-developer local tool |
| Mobile/iOS inference | Desktop-first on Apple Silicon Mac |
| Custom training from scratch | LoRA fine-tuning of proven base model |
| Web UI | CLI-first, possible terminal UI later |
| Gemma 4 PCB vision integration | Covered by kicad-agent Phase 84, separate scope |

## Context

- **Existing infrastructure**: MLX pipeline proven via kicad-agent Gemma 4 fine-tuning work
- **Confucius RAG**: Already running with 3637+ artifacts, Ollama with nomic-embed-text available
- **Claude Code as harness**: z.ai is the AI source, Claude Code is the orchestration layer
- **Apple Silicon hardware**: M-series Mac with unified memory (16-128GB)
- **WWDC25/26 research complete**: AFM framework, Liquid Glass, Metal 4, 25+ new frameworks documented
- **Rick agent system**: 23+ specialists in Council of Ricks, need currency updates

## Constraints

- **Hardware**: Apple Silicon only (M1+), unified memory limits model size
- **License**: Must use Apache 2.0 or MIT licensed models (Qwen2.5-Coder qualifies)
- **Offline**: Must function without network after initial setup
- **Latency**: <5s first token, <30 tok/s generation for 7B model
- **Memory**: Target 16GB Mac compatibility (7B Q4 model ~4GB, LoRA adapter ~50MB)
- **Existing stack**: Must integrate with Confucius (not replace), Ollama (not replace)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Qwen2.5-Coder-7B over larger models | Best code quality/size ratio for 16GB Macs | — Pending |
| MLX-LoRA over full fine-tuning | Proven in kicad-agent, low resource, fast iteration | — Pending |
| Ollama for serving | Already installed, GGUF ecosystem, simple API | — Pending |
| Confucius for RAG | Already running, nomic-embed-text available, domain patterns stored | — Pending |
| Rick updates in same project | Shared WWDC25/26 research, atomic updates | — Pending |

---
*Last updated: 2026-06-10 after initial project definition*
