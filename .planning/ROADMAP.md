# Roadmap: me_code_pretty_one_day

**Created:** 2026-06-10
**Phases:** 5

## Phase Overview

| Phase | Name | Requirements | Focus |
|-------|------|-------------|-------|
| 1 | Rick Currency Updates | RICK-01 to RICK-04 | Update 4 existing Apple-specialist Ricks with WWDC25/26 |
| 2 | New Domain Ricks | RICK-05 to RICK-08 | Create 4 new specialist Ricks |
| 3 | Local AI Serving | LAKE-01 to LAKE-05 | Model download, serving via Ollama/mlx_lm.server |
| 4 | Fine-Tuning Pipeline | LAKE-06 to LAKE-10 | MLX-LoRA training pipeline and data generation |
| 5 | RAG & Evaluation | LAKE-11 to LAKE-17 | Confucius RAG integration, SLC prompts, benchmarks |

## Phase 1: Rick Currency Updates

**Goal:** All existing Apple-specialist Ricks reflect WWDC25/26 platform changes

**Requirements:** RICK-01, RICK-02, RICK-03, RICK-04

**Plans:** 4 plans

Plans: 4 plans (4 complete)

- [x] 01-01-PLAN.md -- Update apple-elitist-rick with WWDC26 (SiriKit deprecation, App Intents, UISceneDelegate, Swift 6.4, Xcode 27, cross-references to new Ricks)
- [x] 01-02-PLAN.md -- Update gamer-rick with WWDC26 (Logitech Muse, MetalFX, frame interpolation, Liquid Glass intensity, cross-references to metal-4-rick and visionos-rick)
- [x] 01-03-PLAN.md -- Update swiftui-liquid-glass with WWDC26 (Liquid Glass intensity switch, TextEditor rich text, spatial layout refinements, Swift 6.4 concurrency, cross-reference to visionos-rick)
- [x] 01-04-PLAN.md -- Update swift-concurrency-expert with WWDC26 (Swift 6.4 ergonomics, auto-generated C++ bindings, `sending` convention, module-level default isolation, Java interop updates)

**Success Criteria:**
- [x] Each Rick agent file includes all WWDC25/26 framework additions
- [x] Deprecated APIs documented with migration paths
- [x] New API types and protocols referenced with correct signatures
- [x] No stale pre-WWDC25 information remains uncorrected

**Completed:** 2026-06-12

## Phase 2: New Domain Ricks

**Goal:** Create 4 new specialist Ricks for domains uncovered by WWDC25/26

**Requirements:** RICK-05, RICK-06, RICK-07, RICK-08

**Plans:** 4 plans (pre-existing — files created in prior session)

| Plan | Description |
|------|-------------|
| 2.1 | Create foundation-models-rick (AFM framework, on-device/server, LoRA, @Generable) |
| 2.2 | Create metal-4-rick (ML+graphics convergence, WebGPU, mesh shaders) |
| 2.3 | Create privacy-rick (quantum crypto, Containerization, PermissionKit, PCC) |
| 2.4 | Create visionos-rick (spatial UI, GlassEffectContainer, spatial accessories) |

**Success Criteria:**
- [x] Each new Rick follows established agent definition format
- [x] Registered in Council of Ricks wave routing
- [x] Covers all relevant WWDC25/26 sessions for its domain
- [x] Tools list matches domain (Read, Write, Edit, Bash, Grep, Glob, WebSearch, WebFetch)

**Completed:** 2026-06-12 (verified — 4 files exist at ~/.claude/agents/, 800-975 lines each)

## Phase 3: Local AI Serving

**Goal:** Qwen2.5-Coder-7B running locally with sub-5s latency, fully offline

**Requirements:** LAKE-01 to LAKE-05

**Plans:**
| Plan | Description |
|------|-------------|
| 3.1 | Download and verify Qwen2.5-Coder-7B-Instruct Q4_K_M model |
| 3.2 | Configure Ollama serving with model and test latency/throughput |
| 3.3 | Configure mlx_lm.server alternative serving path |
| 3.4 | Offline verification -- disconnect network, verify full inference |
| 3.5 | Benchmark latency (TTFT) and throughput (tok/s) |

**Success Criteria:**
- [ ] Model loads and generates code via Ollama API
- [ ] First token <5s on M-series Mac
- [ ] Generation >= 30 tok/s for 7B model
- [ ] Works offline with zero network dependency

## Phase 4: Fine-Tuning Pipeline

**Goal:** MLX-LoRA fine-tuning pipeline producing domain-adapted adapter

**Requirements:** LAKE-06 to LAKE-10

**Plans:**
| Plan | Description |
|------|-------------|
| 4.1 | Training data generator + seed tasks + train/val split + tests (LAKE-07, LAKE-08, LAKE-10) |
| 4.2 | LoRA training config + wrapper script with disk check (LAKE-06) |
| 4.3 | Adapter serving (mlx_lm.server native) + Ollama deploy + benchmark comparison (LAKE-09) |

Plans:
- [ ] 04-01-PLAN.md -- Training data generator with seed tasks, train/val split, and unit tests
- [ ] 04-02-PLAN.md -- LoRA config YAML and training wrapper script
- [ ] 04-03-PLAN.md -- Fine-tuned model serving, Ollama deploy, base vs fine-tuned benchmark

**Success Criteria:**
- [ ] 5000+ training examples in standard chat JSONL format (mlx-lm applies ChatML automatically)
- [ ] LoRA adapter trains successfully via mlx-lm with QLoRA 4-bit, rank 16
- [ ] Fine-tuned model serves via mlx_lm.server with native adapter loading
- [ ] Optional Ollama deployment via experimental safetensors import (GGUF not supported for Qwen2)
- [ ] Fine-tuned model shows measurable improvement over base in benchmark comparison

## Phase 5: RAG & Evaluation

**Goal:** Confucius RAG provides domain context, SLC standards injected, full benchmark suite

**Requirements:** LAKE-11 to LAKE-17

**Plans:** 4 plans

Plans:
- [ ] 05-01-PLAN.md -- RAG foundation: SLC system prompt, domain mapping, PromptAssembler with token budget, Confucius pattern seeder (LAKE-11, LAKE-12, LAKE-13, LAKE-14)
- [ ] 05-02-PLAN.md -- Generation pipeline: generate.py CLI chaining confucius -> prompt assembly -> Ollama inference (LAKE-11)
- [ ] 05-03-PLAN.md -- HumanEval benchmark: pass@k evaluation comparing base/finetuned/RAG variants (LAKE-15, LAKE-16)
- [ ] 05-04-PLAN.md -- Latency/throughput per variant: extend existing benchmark scripts with --variant flag (LAKE-17)

**Success Criteria:**
- [ ] RAG retrieval returns relevant domain patterns in <100ms
- [ ] System prompt enforces SLC standards in generated code
- [ ] Benchmark report shows base vs fine-tuned vs RAG quality comparison
- [ ] Full pipeline runs offline end-to-end

## Dependencies

```
Phase 1 (Rick Updates) ────────────────────────────┐
Phase 2 (New Ricks) ───────────────────────────────┤
                                                    ├──> (Independent tracks)
Phase 3 (Serving) ──> Phase 4 (Fine-Tuning) ──> Phase 5 (RAG & Eval)
```

Phase 1 and 2 (Rick work) are independent from Phase 3-5 (Local AI work).

---
*Roadmap created: 2026-06-10*
*Last updated: 2026-06-12 after Phase 5 planning*
