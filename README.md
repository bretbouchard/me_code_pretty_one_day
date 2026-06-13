# me_code_pretty_one_day

Fine-tune Qwen2.5-Coder-7B on **your** code, offline, on Apple Silicon.

- Trains a 7B code model on your local repositories via MLX-LoRA
- Serves through Ollama — fully offline after initial model download
- Optional RAG layer injects domain patterns at inference time
- Benchmark suite measures quality (HumanEval pass@k, latency, throughput)

## Prerequisites

- **Apple Silicon Mac** (M1/M2/M3/M4) — MLX framework requires it
- **10GB free disk space** — base model is ~4GB, training generates adapter weights
- **Python 3.10+**
- **Ollama** — [ollama.com](https://ollama.com) or `brew install ollama`
- **MLX** — installed automatically with `pip install -r requirements.txt`

## Quick Start

Generate code from the base model in under 5 minutes:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Download the base model (~4GB)
make download

# 3. Start Ollama in a separate terminal
ollama serve

# 4. Generate code
python scripts/generate.py "write a binary search tree" --no-rag
```

No training required — the base Qwen2.5-Coder-7B works out of the box. Training on your code makes it better at your specific patterns and domains.

## Train on Your Code

```bash
# 1. Scrape your local repos for training data
python scripts/scrape_local.py --repos ~/projects/my-app ~/projects/my-other-app --dry-run

# 2. Generate training data (instruction-response pairs)
python scripts/scrape_local.py --repos ~/projects/my-app
python scripts/prepare_training_data.py --seeds-only

# 3. Fine-tune with MLX-LoRA
make train

# 4. Generate with your fine-tuned model
python scripts/generate.py "implement a SwiftUI list with search" --no-rag
```

The `scrape_local.py` script walks your code directories, filters for quality, and produces:
- **Corpus files** (`data/corpus-local/`) — raw code for formatting training
- **Instruction-response pairs** (`data/local_pairs.jsonl`) — for main model training

## Architecture

```
Your Code
    |
    v
scrape_local.py  -->  local_pairs.jsonl  -->  train_lora.py  -->  adapter weights
                                                                   |
                                                                   v
generate.py  <--  PromptAssembler  <--  Confucius (optional RAG)
    |
    v
Ollama (localhost:11434)
    |
    v
Generated code
```

The pipeline has two modes:
- **Base mode** (`--no-rag`): System prompt + your prompt → Ollama → output
- **RAG mode** (default): System prompt + Confucius patterns + your prompt → Ollama → output

RAG requires [Confucius](https://github.com/bretbouchard/Confucius) CLI installed. Use `--no-rag` if you don't have it.

## Project Structure

```
scripts/
  scrape_local.py          # Scrape YOUR repos for training data
  prepare_training_data.py # Convert scraped data to training format
  train_lora.py            # MLX-LoRA fine-tuning wrapper
  download_model.py        # Download base model from HuggingFace
  prompt_template.py       # PromptAssembler — RAG pipeline core
  generate.py              # Generation CLI (user-facing)
  seed_patterns.py         # Seed domain patterns into Confucius
  benchmark_humaneval.py    # HumanEval pass@k evaluation
  benchmark_latency.py     # Latency benchmarks
  benchmark-throughput.py  # Throughput benchmarks
  benchmark_utils.py       # Shared benchmark utilities
prompts/
  slc_system.txt           # SLC coding standards system prompt
  domains.json             # Domain tag → Confucius query mapping
training/
  lora_config.yaml         # LoRA hyperparameters (rank 16, default)
  lora_config_formatting.yaml # Formatting-only training config
```

## Make Targets

```
make download         Download base model (~4GB)
make train            Fine-tune with MLX-LoRA
make serve            Start Ollama
make generate         Generate code (with RAG, requires Confucius)
make generate-no-rag  Generate code (without RAG)
make benchmark        Run all benchmark suites
make seed             Seed Confucius patterns (requires Confucius CLI)
make scrape-local     Scrape YOUR local repos
make test             Run unit tests
make clean            Remove cached files
```

## Benchmarks

Evaluate model quality across three dimensions:

```bash
# HumanEval — code correctness (pass@k with k=1,2,4)
python scripts/benchmark_humaneval.py --variant rag --max-problems 20

# Latency — time to first token, tokens/sec
python scripts/benchmark-latency.py --variant all

# Throughput — sustained generation speed
python scripts/benchmark-throughput.py --variant all
```

All benchmarks support `--variant base|finetuned|rag|all` for comparing configurations.

## Customizing

### Domain mapping

Edit `prompts/domains.json` to map domain tags to Confucius search queries:

```json
{
  "swift": {"query": "Swift UI patterns, SwiftUI, GRDB", "tags": ["swift", "ios"]},
  "python": {"query": "Python data pipelines, testing, DSP", "tags": ["python"]}
}
```

### Training parameters

Edit `training/lora_config.yaml`:
- `lora_rank`: 8 (fast), 16 (balanced), 32 (complex patterns)
- `learning_rate`: 1e-5 (conservative), 2e-5 (aggressive)
- `num_iterations`: 600 (quick), 1200 (thorough)

### SLC system prompt

Edit `prompts/slc_system.txt` to change the coding standards injected into every generation. Default enforces: immutability, small functions (<50 lines), small files (<800 lines), comprehensive error handling.

## What's Included

- Training pipeline scripts (scrape, prep, train, serve, evaluate)
- LoRA config templates
- SLC system prompt and domain mapping
- Benchmark suite (HumanEval, latency, throughput)
- 99 unit tests
- Demo corpus from open-source projects

## What's NOT Included (generated when you run the pipeline)

- Base model weights (~4GB) — download via `make download`
- Training data (train.jsonl, valid.jsonl) — generate from your repos
- LoRA adapter weights — generated by training

## Troubleshooting

**Ollama not running:** Start with `ollama serve` in a separate terminal.

**Out of memory during training:** Reduce `lora_rank` to 8 and `batch_size` to 2 in `training/lora_config.yaml`.

**Model not found:** Run `make download` to get the base model, then import into Ollama.

**Slow generation:** Ensure you're on Apple Silicon (MLX uses Metal Performance Shaders). Check with `sysctl -a | grep -i apple`.

## License

MIT — see [LICENSE](LICENSE).
