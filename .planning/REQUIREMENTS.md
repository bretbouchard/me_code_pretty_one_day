# Requirements: me_code_pretty_one_day

**Defined:** 2026-06-10
**Core Value:** Ship fast local code generation that works completely offline, never phones home, and knows Bret's patterns

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Local AI — Serving

- [ ] **LAKE-01**: Qwen2.5-Coder-7B-Instruct served via Ollama with GGUF Q4_K_M quantization
- [ ] **LAKE-02**: Alternative mlx_lm.server serving path with MLX-native model format
- [ ] **LAKE-03**: Sub-5s first token latency on M-series Mac (7B model)
- [ ] **LAKE-04**: Generation throughput >= 30 tok/s for 7B model
- [ ] **LAKE-05**: Offline operation — full inference with zero network after model download

### Local AI — Fine-Tuning

- [ ] **LAKE-06**: MLX-LoRA fine-tuning pipeline (rank 16-32, QLoRA 4-bit)
- [ ] **LAKE-07**: Training data generator producing 5000+ code generation examples
- [ ] **LAKE-08**: Training data format: Qwen ChatML (`<|im_start|>role\ncontent<|im_end|>`)
- [ ] **LAKE-09**: Adapter output compatible with Ollama GGUF merging
- [ ] **LAKE-10**: Train/val split (90/10) with reproducible seed

### Local AI — RAG & Prompts

- [ ] **LAKE-11**: Confucius RAG retrieval integrated into generation pipeline
- [ ] **LAKE-12**: SLC coding standards injected via system prompt
- [ ] **LAKE-13**: Domain-specific pattern retrieval (Swift, Python, JUCE, PCB layouts)
- [ ] **LAKE-14**: Context window management for RAG + prompt + generation

### Local AI — Evaluation

- [ ] **LAKE-15**: Benchmark framework comparing base vs fine-tuned model
- [ ] **LAKE-16**: HumanEval-based code generation quality metric
- [ ] **LAKE-17**: Latency and throughput benchmarks per model size

### Rick Updates — Existing

- [ ] **RICK-01**: apple-elitist-rick updated with Foundation Models framework, Liquid Glass, Metal 4, BNNS Graph, SpeechAnalyzer, quantum crypto, iOS 26 SDK deprecations, SF Symbols 7
- [ ] **RICK-02**: gamer-rick updated with Apple Games app, Metal 4 for games, Game Center updates, visionOS spatial accessories
- [ ] **RICK-03**: swiftui-liquid-glass updated with spatial layout, WebKit for SwiftUI, SwiftUI+RealityKit, AttributedString enhancements
- [ ] **RICK-04**: swift-concurrency-expert updated with C++/Swift interop safety, Java interop, SwiftUI concurrency patterns for iOS 26

### Rick Updates — New

- [x] **RICK-05**: foundation-models-rick — AFM framework specialist (LanguageModelSession, @Generable, Tool protocol, LoRA adapters, on-device vs server, Privacy-Preserving Compute)
- [x] **RICK-06**: metal-4-rick — Metal 4 GPU framework specialist (ML+graphics convergence, WebGPU support, new shader stages, mesh shaders, ray tracing updates)
- [x] **RICK-07**: privacy-rick — Apple privacy platform specialist (quantum-safe crypto, Containerization framework, PermissionKit, App Tracking updates, PCC architecture)
- [x] **RICK-08**: visionos-rick — visionOS 26+ specialist (spatial UI, GlassEffectContainer, spatial accessories, shared space, persona rendering)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Local AI — Advanced

- **LAKE-18**: Multi-model serving (code + domain-specific models)
- **LAKE-19**: Terminal UI for interactive code generation
- **LAKE-20**: Integration with Xcode via Source Editor Extension

### Rick Updates — Maintenance

- **RICK-09**: Automated currency checking pipeline for all Ricks
- **RICK-10**: Rick agent test suite with platform API coverage verification

## Out of Scope

| Feature | Reason |
|---------|--------|
| Replacing Claude Code / z.ai | Supplements remote AI for simple/fast tasks only |
| Multi-user serving | Single-developer local tool |
| Mobile inference | Desktop Apple Silicon only |
| Full model training from scratch | LoRA fine-tuning of proven Qwen2.5-Coder base |
| Web UI / API server | CLI-first, no HTTP server needed |
| Gemma 4 PCB vision | kicad-agent Phase 84, separate project |
| Automated Rick test suite | v2 scope, needs CI infrastructure |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| LAKE-01 | Phase 3 | Pending |
| LAKE-02 | Phase 3 | Pending |
| LAKE-03 | Phase 3 | Pending |
| LAKE-04 | Phase 3 | Pending |
| LAKE-05 | Phase 3 | Pending |
| LAKE-06 | Phase 4 | Pending |
| LAKE-07 | Phase 4 | Pending |
| LAKE-08 | Phase 4 | Pending |
| LAKE-09 | Phase 4 | Pending |
| LAKE-10 | Phase 4 | Pending |
| LAKE-11 | Phase 5 | Pending |
| LAKE-12 | Phase 5 | Pending |
| LAKE-13 | Phase 5 | Pending |
| LAKE-14 | Phase 5 | Pending |
| LAKE-15 | Phase 5 | Pending |
| LAKE-16 | Phase 5 | Pending |
| LAKE-17 | Phase 5 | Pending |
| RICK-01 | Phase 1 | Complete |
| RICK-02 | Phase 1 | Complete |
| RICK-03 | Phase 1 | Complete |
| RICK-04 | Phase 1 | Complete |
| RICK-05 | Phase 2 | Complete |
| RICK-06 | Phase 2 | Complete |
| RICK-07 | Phase 2 | Complete |
| RICK-08 | Phase 2 | Complete |

**Coverage:**
- v1 requirements: 24 total
- Mapped to phases: 24
- Unmapped: 0

---
*Requirements defined: 2026-06-10*
*Last updated: 2026-06-10 after initial definition*
