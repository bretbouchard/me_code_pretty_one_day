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

**Plans:**
| Plan | Description |
|------|-------------|
| 1.1 | Update apple-elitist-rick with Foundation Models, Liquid Glass, Metal 4, new frameworks, deprecations |
| 1.2 | Update gamer-rick with Apple Games app, Metal 4 game features, Game Center, visionOS gaming |
| 1.3 | Update swiftui-liquid-glass with spatial layout, WebKit for SwiftUI, new modifiers |
| 1.4 | Update swift-concurrency-expert with C++/Swift interop, Java interop, new patterns |

**Success Criteria:**
- [ ] Each Rick agent file includes all WWDC25/26 framework additions
- [ ] Deprecated APIs documented with migration paths
- [ ] New API types and protocols referenced with correct signatures
- [ ] No stale pre-WWDC25 information remains uncorrected

## Phase 2: New Domain Ricks

**Goal:** Create 4 new specialist Ricks for domains uncovered by WWDC25/26

**Requirements:** RICK-05, RICK-06, RICK-07, RICK-08

**Plans:**
| Plan | Description |
|------|-------------|
| 2.1 | Create foundation-models-rick (AFM framework, on-device/server, LoRA, @Generable) |
| 2.2 | Create metal-4-rick (ML+graphics convergence, WebGPU, mesh shaders) |
| 2.3 | Create privacy-rick (quantum crypto, Containerization, PermissionKit, PCC) |
| 2.4 | Create visionos-rick (spatial UI, GlassEffectContainer, spatial accessories) |

**Success Criteria:**
- [ ] Each new Rick follows established agent definition format
- [ ] Registered in Council of Ricks wave routing
- [ ] Covers all relevant WWDC25/26 sessions for its domain
- [ ] Tools list matches domain (Read, Write, Edit, Bash, Grep, Glob, WebSearch, WebFetch)

## Phase 3: Local AI Serving

**Goal:** Qwen2.5-Coder-7B running locally with sub-5s latency, fully offline

**Requirements:** LAKE-01 to LAKE-05

**Plans:**
| Plan | Description |
|------|-------------|
| 3.1 | Download and verify Qwen2.5-Coder-7B-Instruct Q4_K_M model |
| 3.2 | Configure Ollama serving with model and test latency/throughput |
| 3.3 | Configure mlx_lm.server alternative serving path |
| 3.4 | Offline verification — disconnect network, verify full inference |
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
| 4.1 | Training data generator (code tasks with Q+A+ground truth, 5000+ examples) |
| 4.2 | MLX-LoRA training script (rank 16-32, QLoRA 4-bit, lr=5e-6) |
| 4.3 | Adapter export and Ollama GGUF merge pipeline |
| 4.4 | Train/val split validation |
| 4.5 | Base vs fine-tuned comparison benchmark |

**Success Criteria:**
- [ ] 5000+ training examples in Qwen ChatML format
- [ ] LoRA adapter trains successfully via mlx-lm
- [ ] Adapter merges into GGUF for Ollama serving
- [ ] Fine-tuned model shows measurable improvement over base

## Phase 5: RAG & Evaluation

**Goal:** Confucius RAG provides domain context, SLC standards injected, full benchmark suite

**Requirements:** LAKE-11 to LAKE-17

**Plans:**
| Plan | Description |
|------|-------------|
| 5.1 | Confucius RAG retrieval integrated into prompt assembly |
| 5.2 | SLC coding standards system prompt template |
| 5.3 | Domain-specific retrieval (Swift, Python, JUCE, PCB patterns) |
| 5.4 | Context window budget management (RAG + prompt + generation) |
| 5.5 | HumanEval-based benchmark comparing base/fine-tuned/RAG variants |
| 5.6 | Final latency and quality report |

**Success Criteria:**
- [ ] RAG retrieval returns relevant domain patterns in <100ms
- [ ] System prompt enforces SLC standards in generated code
- [ ] Benchmark report shows base vs fine-tuned vs RAG quality comparison
- [ ] Full pipeline runs offline end-to-end

## Dependencies

```
Phase 1 (Rick Updates) ────────────────────────────┐
Phase 2 (New Ricks) ───────────────────────────────┤
                                                    ├──→ (Independent tracks)
Phase 3 (Serving) ──→ Phase 4 (Fine-Tuning) ──→ Phase 5 (RAG & Eval)
```

Phase 1 and 2 (Rick work) are independent from Phase 3-5 (Local AI work).

---
*Roadmap created: 2026-06-10*
*Last updated: 2026-06-10 after initial definition*
