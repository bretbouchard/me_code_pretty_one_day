# me_code_pretty_one_day

Offline-first local AI code generation assistant. Fine-tuned Qwen2.5-Coder-7B via MLX-LoRA, served through Ollama, with Confucius RAG for domain patterns.

## Quick Start
```bash
# Serve model (requires Ollama running)
ollama run qwen2.5-coder:7b-instruct-q4_K_M

# Generate code with RAG
python scripts/generate.py "write a binary search" --domain python --verbose

# Generate code without RAG
python scripts/generate.py "write a binary search" --no-rag

# Run benchmarks
make benchmark
```

## Project Structure
- `scripts/` — All Python scripts (training, generation, benchmarking)
- `data/` — Training data (JSONL format), corpus files, seed examples
- `models/` — Base model (MLX 4-bit quantized)
- `training/` — LoRA adapter checkpoints and training logs
- `prompts/` — SLC system prompt, domain mapping config
- `.planning/` — GSD project lifecycle (ROADMAP, STATE, phases/)

## Architecture
- **PromptAssembler** (`scripts/prompt_template.py`): Loads SLC prompt, retrieves Confucius patterns, assembles messages within token budget
- **generate.py** (`scripts/generate.py`): CLI chaining Confucius -> PromptAssembler -> Ollama inference
- **benchmark_humaneval.py**: HumanEval pass@k comparing base/finetuned/RAG variants
- **benchmark-latency.py` / **benchmark-throughput.py**: Performance benchmarks with --variant flag
- **benchmark_utils.py**: Shared `build_variant_messages()` for benchmark scripts

## Key Files
| File | Purpose |
|------|---------|
| `scripts/prompt_template.py` | PromptAssembler class — core RAG pipeline |
| `scripts/generate.py` | Generation CLI — user-facing tool |
| `scripts/seed_patterns.py` | Confucius domain pattern seeder (15 patterns, 4 domains) |
| `scripts/benchmark_humaneval.py` | HumanEval benchmark with pass@k |
| `scripts/benchmark_utils.py` | Shared benchmark utilities |
| `prompts/slc_system.txt` | SLC coding standards system prompt |
| `prompts/domains.json` | Domain tag -> confucius query mapping |

## Available Domains
swift, python, juce, pcb

## Tests
```bash
# Run all unit tests
python -m pytest scripts/ -v -x -k "not integration"

# Run with integration tests (requires Ollama)
python -m pytest scripts/ -v -x --run-integration
```

## Model
- Base: `qwen2.5-coder-7b-instruct` (4-bit MLX quantization)
- Adapters: `training/adapters-600/` (recommended for quality/speed balance)
- Serving: Ollama at localhost:11434
- Context: 32,768 tokens
