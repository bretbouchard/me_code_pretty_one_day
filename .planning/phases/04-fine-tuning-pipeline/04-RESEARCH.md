# Phase 4: Fine-Tuning Pipeline - Research

**Researched:** 2026-06-10
**Domain:** MLX-LoRA fine-tuning, training data generation, adapter export
**Confidence:** HIGH

## Summary

MLX-LoRA fine-tuning for Qwen2.5-Coder-7B is well-supported by `mlx-lm 0.31.3` (installed and verified). Since the base model is already quantized (4-bit), training automatically uses QLoRA. The primary challenge is the adapter-to-Ollama deployment pipeline: `mlx_lm.fuse --export-gguf` is hardcoded to "llama" architecture metadata and will NOT produce a correct GGUF for Qwen2. However, two viable alternatives exist: (1) `ollama create --experimental` safetensors support (untested for Qwen2), and (2) the simpler mlx_lm.server serving path with native adapter loading (confirmed working). Training data must use the `chat` JSONL format with standard `{role, content}` messages -- mlx-lm applies the Qwen ChatML template automatically. Disk space is critically tight at 27GB free, which constrains fused model creation.

**Primary recommendation:** Use mlx_lm.server with native `--adapter-path` as the primary serving path for fine-tuned models. For Ollama deployment, attempt `ollama create --experimental` with the fused safetensors model; fall back to mlx_lm.server if experimental path fails.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LAKE-06 | MLX-LoRA fine-tuning pipeline (rank 16-32, QLoRA 4-bit) | mlx_lm.lora CLI confirmed working with 4-bit Qwen2.5-Coder-7B. QLoRA automatic when model is quantized. Rank 16 proven in kicad-agent. |
| LAKE-07 | Training data generator producing 5000+ code generation examples | Script must produce chat-format JSONL. Data generation via synthetic code tasks using existing model + seed examples. |
| LAKE-08 | Training data format: Qwen ChatML (`<|im_start|>role\ncontent<|im_end|>`) | mlx-lm applies chat template automatically from `{"messages": [...]}` format. Raw ChatML NOT needed -- use standard message format. |
| LAKE-09 | Adapter output compatible with Ollama GGUF merging | GGUF export from mlx_lm does NOT support Qwen2 (hardcoded "llama" arch). Alternative: ollama --experimental safetensors or mlx_lm.server native adapter loading. |
| LAKE-10 | Train/val split (90/10) with reproducible seed | mlx-lm supports `--seed` flag and separate train.jsonl/valid.jsonl files. Python random.seed(42) in generator script. |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Training data generation | Local CLI (Python) | -- | Synthetic data generation is an offline batch process, not serving |
| LoRA adapter training | Local GPU (MLX) | -- | Model training runs on Apple Silicon GPU via MLX framework |
| Adapter inference serving | Frontend Server (mlx_lm.server) | API (Ollama) | Both are local serving paths; mlx_lm.server has native adapter support |
| Adapter-to-GGUF conversion | Local CLI (mlx_lm.fuse) | -- | File conversion is an offline batch process |
| Train/val split | Local CLI (Python) | -- | Data preparation is an offline batch process |
| Benchmark comparison | Local CLI (Python) | API (Ollama/mlx_lm) | Benchmark scripts call serving endpoints |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| mlx-lm | 0.31.3 (installed) | LoRA/QLoRA fine-tuning, fuse, generate | Official Apple ML framework for LLM fine-tuning on Apple Silicon |
| mlx | 0.31.2 (installed) | ML compute backend | Required by mlx-lm |
| transformers | 5.10.0.dev0 (installed) | Tokenizer, chat templates | HuggingFace tokenizer for Qwen ChatML format |
| datasets | 4.8.5 (installed) | HuggingFace dataset loading | Required for HF dataset access |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| gguf | 0.19.0 (installed) | GGUF file format handling | Only if doing manual GGUF inspection/repair |
| jsonlines | stdlib | Training data JSONL files | For reading/writing training data |
| ollama CLI | 0.30.6 (installed) | Model serving and experimental import | For deploying fine-tuned model via `ollama create --experimental` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| mlx-lm QLoRA | Unsloth | Unsloth not available on Apple Silicon |
| mlx_lm.server serving | Ollama GGUF | Ollama requires format conversion for Qwen2; mlx_lm.server loads adapters natively |
| Synthetic data generation | HF datasets (bigcode/self-instruct) | HF datasets are generic; synthetic generation gives domain-specific control |

**Installation:**
```bash
pip install "mlx-lm[train]"  # Already installed
pip install gguf              # Already installed
```

**Version verification:**
```bash
pip show mlx-lm    # 0.31.3 - latest available
pip show mlx       # 0.31.2
pip show transformers  # 5.10.0.dev0
```

## Architecture Patterns

### System Architecture Diagram

```
                        Training Data Pipeline
                        =====================
Seed Examples  -->  Data Generator Script  -->  train.jsonl (90%)
(Qwen prompts)      (scripts/generate        -->  valid.jsonl (10%)
                    _training_data.py)            (seed=42)

                        Training Pipeline
                        =================
train.jsonl  -->  mlx_lm.lora          -->  adapters/
valid.jsonl      --model models/qwen2.5/      adapter_config.json
                 --train                    adapters.safetensors
                 --config lora_config.yaml
                 (QLoRA automatic)

                        Serving Pipeline
                        =================
                    +-- Path A: mlx_lm.server (NATIVE, no conversion)
                    |   mlx_lm.server
adapters/           |     --model models/qwen2.5/
   |                |     --adapter-path adapters/
   |                |   --> OpenAI-compatible API (localhost:8800)
   |                |
   +-- Path B: Ollama (requires conversion)
       mlx_lm.fuse  -->  fused_model/     -->  ollama create --experimental
         --model ...     (safetensors)         --file Modelfile
         --dequantize                          qwen2.5-coder-ft:latest
       (bf16, ~14GB on disk)

                        Evaluation Pipeline
                        ====================
base model    -->  benchmark_compare.py  -->  comparison report
fine-tuned     -->  (scripts/benchmark        (latency, quality,
                    _compare.py)               pass@k)
```

### Recommended Project Structure
```
me_code_pretty_one_day/
├── models/
│   └── qwen2.5-coder-7b-instruct-4bit-mlx/  # Base model (4GB, existing)
├── scripts/
│   ├── generate_training_data.py    # NEW: Training data generator
│   ├── train_lora.py                # NEW: Wrapper for mlx_lm.lora
│   ├── merge_and_deploy.py          # NEW: Fuse + Ollama import
│   ├── benchmark_compare.py          # NEW: Base vs fine-tuned comparison
│   ├── benchmark-latency.py          # Existing
│   ├── benchmark-throughput.py       # Existing
│   ├── serve-mlx.py                 # Existing
│   └── verify-offline.py             # Existing
├── data/
│   ├── train.jsonl                  # NEW: Training examples (4500+)
│   ├── valid.jsonl                  # NEW: Validation examples (500+)
│   └── seed_examples/                # NEW: Seed code tasks for generation
│       ├── python_tasks.json        # Python code generation tasks
│       ├── swift_tasks.json         # Swift code generation tasks
│       └── general_tasks.json       # General code tasks
├── training/
│   ├── lora_config.yaml             # NEW: Training configuration
│   ├── adapters/                     # Training output (gitignored)
│   └── fused_model/                  # Fused output (gitignored)
└── .planning/phases/04-fine-tuning-pipeline/
    └── 04-RESEARCH.md               # This file
```

### Pattern 1: QLoRA Training with mlx-lm

**What:** Use `mlx_lm.lora` with a quantized (4-bit) base model. QLoRA is automatic when the model is quantized -- no special configuration needed.

**When to use:** Standard fine-tuning with memory-constrained hardware (32GB Mac).

**Example:**
```yaml
# training/lora_config.yaml
model: "models/qwen2.5-coder-7b-instruct-4bit-mlx"
train: true
fine_tune_type: lora

# Dataset
data: "data"

# Training hyperparameters
seed: 42
num_layers: 16          # Fine-tune last 16 layers (of 28 total)
batch_size: 4          # Safe for 32GB Mac
iters: 1000             # Start with 1000, increase if loss still decreasing
learning_rate: 5e-6     # Per requirement LAKE-06
grad_accumulation_steps: 2  # Effective batch size = 8

# Validation
val_batches: 25
steps_per_report: 10
steps_per_eval: 100
save_every: 200

# Adapter output
adapter_path: "training/adapters"

# LoRA parameters (ONLY in config file, not CLI)
lora_parameters:
  keys: ["self_attn.q_proj", "self_attn.k_proj", "self_attn.v_proj", "self_attn.o_proj"]
  rank: 16              # Start with 16, try 32 if quality insufficient
  scale: 32.0           # scale = 2 * rank (standard)
  dropout: 0.0          # No dropout for code tasks

# Learning rate schedule
lr_schedule:
  name: cosine_decay
  warmup: 100           # Warm up over first 100 iterations
  warmup_init: 1e-7     # Start from very small LR
  arguments: [5e-6, 1000, 1e-7]  # [peak_lr, total_iters, min_lr]

# Memory optimization
grad_checkpoint: true  # Trade compute for memory
max_seq_length: 2048    # Cap sequence length to manage memory
```

Source: [mlx-lm LORA.md](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/LORA.md) -- verified 2026-06-10

**CLI command:**
```bash
mlx_lm.lora --config training/lora_config.yaml
```

### Pattern 2: Chat Format Training Data

**What:** Use the `chat` JSONL format with standard `{messages: [{role, content}]}` structure. mlx-lm applies the model's chat template (Qwen ChatML) automatically.

**When to use:** All conversational/instruction fine-tuning with Qwen models.

**Example:**
```jsonl
{"messages": [{"role": "system", "content": "You are an expert Python developer. Write clean, efficient code."}, {"role": "user", "content": "Write a function that finds all duplicate files in a directory tree using SHA-256 hashing."}, {"role": "assistant", "content": "import os\nimport hashlib\nfrom pathlib import Path\nfrom collections import defaultdict\n\ndef find_duplicates(root_dir):\n    \"\"\"Find all duplicate files in a directory tree.\n    \n    Args:\n        root_dir: Path to the root directory to search.\n        \n    Returns:\n        dict: Mapping of hash to list of duplicate file paths.\n    \"\"\"\n    hashes = defaultdict(list)\n    \n    for filepath in Path(root_dir).rglob('*'):\n        if not filepath.is_file():\n            continue\n        file_hash = hashlib.sha256(filepath.read_bytes()).hexdigest()\n        hashes[file_hash].append(str(filepath))\n    \n    return {h: paths for h, paths in hashes.items() if len(paths) > 1}"}]}
```

**Verified output:** When mlx-lm processes this, it becomes:
```
<|im_start|>system
You are an expert Python developer. Write clean, efficient code.<|im_end|>
<|im_start|>user
Write a function that finds all duplicate files in a directory tree using SHA-256 hashing.<|im_end|>
<|im_start|>assistant
import os
import hashlib
...<|im_end|>
```

Source: [VERIFIED] Tested with actual model tokenizer on 2026-06-10. The model at `models/qwen2.5-coder-7b-instruct-4bit-mlx` has the correct chat template built into `tokenizer_config.json`.

**Key formatting rules:**
- Each example must be on a single line (no newlines within a JSON object)
- Use `--mask-prompt` to only compute loss on assistant responses (recommended for instruction tuning)
- Last message in `messages` array is treated as the completion when `--mask-prompt` is used

### Pattern 3: Adapter Serving via mlx_lm.server

**What:** Serve a fine-tuned model with LoRA adapter loaded natively -- no format conversion needed.

**When to use:** Primary serving path for fine-tuned models. No GGUF conversion required.

**Example:**
```bash
mlx_lm.server \
    --model models/qwen2.5-coder-7b-instruct-4bit-mlx \
    --adapter-path training/adapters
```

Source: [VERIFIED via `mlx_lm.server --help`] -- `--adapter-path` flag confirmed available.

### Pattern 4: Train/Val Split with Reproducible Seed

**What:** Generate train.jsonl and valid.jsonl from a single dataset with a fixed random seed for reproducibility.

**When to use:** Every training run must use the same split for comparable results.

**Example:**
```python
import json
import random

random.seed(42)  # LAKE-10: reproducible seed

with open("data/all_examples.jsonl") as f:
    examples = [json.loads(line) for line in f]

random.shuffle(examples)
split_idx = int(len(examples) * 0.9)  # 90/10 split

with open("data/train.jsonl", "w") as f:
    for ex in examples[:split_idx]:
        f.write(json.dumps(ex) + "\n")

with open("data/valid.jsonl", "w") as f:
    for ex in examples[split_idx:]:
        f.write(json.dumps(ex) + "\n")
```

### Anti-Patterns to Avoid

- **Raw ChatML tokens in JSONL:** Do NOT write `<|im_start|>` tokens directly into training data. Use the `chat` format with `{messages: [{role, content}]}` and let mlx-lm apply the template automatically. The template is complex (handles tools, multi-turn) and manual encoding will produce incorrect training data.

- **Too many LoRA layers:** `num_layers: 28` (all layers) uses significantly more memory. Start with 16 (default) and increase only if quality demands it.

- **Learning rate too high for code:** 1e-4 is too aggressive for QLoRA on code tasks. Use 5e-6 per requirements, with cosine decay.

- **Not using mask-prompt:** Without `--mask-prompt`, loss is computed on both the prompt and the response. This wastes capacity learning to reproduce the input rather than improving generation quality.

- **Forgetting gradient checkpointing:** With 32GB Mac, batch_size=4, and seq_length=2048, gradient checkpointing is strongly recommended to avoid OOM.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LoRA training loop | Custom PyTorch training loop | `mlx_lm.lora` | Handles QLoRA, gradient accumulation, learning rate schedules, checkpointing, adapter saving |
| Chat template application | Manual `<|im_start|>` wrapping | `tokenizer.apply_chat_template()` or let mlx-lm handle it | Qwen2.5-Coder chat template is complex (tools, multi-turn) |
| LoRA adapter fusion | Manual weight addition | `mlx_lm.fuse` | Handles dequantization, weight merging, format output |
| GGUF conversion | Manual weight serialization | `mlx_lm.fuse --export-gguf` (for Llama) or llama.cpp convert (for Qwen) | GGUF format has specific tensor naming and metadata requirements |
| Train/val splitting | Ad-hoc shuffle | Python `random.seed(42)` + `shuffle` | Simple, reproducible, no external deps |

**Key insight:** The mlx-lm package covers the entire LoRA lifecycle -- training, evaluation, generation, fusion, and serving. Custom code is only needed for data generation and benchmarking.

## Common Pitfalls

### Pitfall 1: GGUF Export Does NOT Support Qwen2

**What goes wrong:** Running `mlx_lm.fuse --model ... --export-gguf` on a Qwen2.5-Coder model produces a GGUF file with `general.architecture: "llama"` metadata hardcoded, which is incorrect for Qwen2 (`model_type: "qwen2"`). Ollama may fail to load or produce incorrect outputs.

**Why it happens:** The `gguf.py` module in mlx-lm 0.31.3 hardcodes `"general.architecture": "llama"` and `"general.name": "llama"` in the metadata preparation function (line 228). The weight name translation also uses Llama-style tensor names (`blk.N.attn_q` etc.), not Qwen conventions.

**How to avoid:** Use one of these alternatives:
1. **Preferred:** Use `mlx_lm.server --adapter-path` for serving (native, no conversion needed)
2. **Experimental:** Use `ollama create --experimental` to import the fused safetensors model directly
3. **Manual:** Fuse with `--dequantize`, then use llama.cpp's official `convert_hf_to_gguf.py` which properly handles Qwen2 architecture

**Warning signs:** Ollama loads the GGUF but produces gibberish, or reports "model architecture not recognized."

**Confidence:** HIGH -- verified by reading `mlx_lm/gguf.py` source code and `mlx_lm/fuse.py` line 93-100.

### Pitfall 2: Disk Space Exhaustion During Fusion

**What goes wrong:** `mlx_lm.fuse --dequantize` produces a bf16 model (~14GB for 7B). With only 27GB free on disk, this can exhaust storage, especially if training artifacts (checkpoints, intermediate saves) accumulate.

**Why it happens:** The fused model at bf16 precision is roughly 3.5x the size of the 4-bit quantized model (~4GB). Training with `save_every: 200` also produces intermediate adapter checkpoints.

**How to avoid:**
- Clean up intermediate adapter checkpoints after training completes (keep only final)
- Only run fusion when needed for Ollama deployment
- Monitor disk space before fusion: `df -h /path/to/project`
- Consider using `mlx_lm.server` path exclusively to avoid fusion entirely
- Add `training/adapters/` and `training/fused_model/` to `.gitignore`

**Warning signs:** System warnings about low disk space, failed writes during training.

### Pitfall 3: Training Data Quality Over Quantity

**What goes wrong:** Generating 5000+ low-quality synthetic examples produces a model that regresses compared to the base model.

**Why it happens:** The base model (Qwen2.5-Coder-7B-Instruct) is already well-trained on code. Poor quality or repetitive training data can cause catastrophic forgetting, where the model loses its general coding ability.

**How to avoid:**
- Use diverse code tasks across multiple languages and difficulty levels
- Include high-quality seed examples from known-good code
- Validate a sample of generated training data before training
- Monitor validation loss during training -- if it increases, data quality is the issue
- Consider starting with a smaller dataset (1000-2000 examples) and scaling up
- Use `--mask-prompt` so loss is only on assistant responses

**Warning signs:** Validation loss increases over training iterations, or model generates worse code than base on held-out examples.

### Pitfall 4: Sequence Length Memory Explosion

**What goes wrong:** Training examples with long code snippets (>2048 tokens) cause out-of-memory errors on 32GB Mac.

**Why it happens:** Memory usage scales quadratically with sequence length for attention computation. A single 4096-token example with batch_size=4 can exceed available memory.

**How to avoid:**
- Set `max_seq_length: 2048` in config (or lower to 1024 if needed)
- Filter training data to exclude examples exceeding the limit
- Use `grad_checkpoint: true` to trade compute for memory
- Reduce `batch_size` to 1 or 2 if memory is tight
- Use `--grad-accumulation-steps 4` to maintain effective batch size

**Warning signs:** `mx.core.memory` errors, kernel panics, or system memory pressure warnings.

## Code Examples

### Complete Training Command

```bash
# Train with config file (recommended)
mlx_lm.lora --config training/lora_config.yaml

# Equivalent CLI command
mlx_lm.lora \
    --model models/qwen2.5-coder-7b-instruct-4bit-mlx \
    --train \
    --data data \
    --adapter-path training/adapters \
    --batch-size 4 \
    --num-layers 16 \
    --learning-rate 5e-6 \
    --iters 1000 \
    --grad-accumulation-steps 2 \
    --steps-per-report 10 \
    --steps-per-eval 100 \
    --save-every 200 \
    --val-batches 25 \
    --seed 42 \
    --grad-checkpoint \
    --max-seq-length 2048 \
    --mask-prompt
```

Source: [VERIFIED via `mlx_lm.lora --help`] -- all flags confirmed available in mlx-lm 0.31.3.

### Evaluate Trained Adapter

```bash
# Evaluate on test set
mlx_lm.lora \
    --model models/qwen2.5-coder-7b-instruct-4bit-mlx \
    --adapter-path training/adapters \
    --data data \
    --test \
    --test-batches -1  # Use entire test set
```

Source: [CITED: mlx-lm LORA.md](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/LORA.md)

### Generate with Trained Adapter

```bash
# Quick generation test
mlx_lm.generate \
    --model models/qwen2.5-coder-7b-instruct-4bit-mlx \
    --adapter-path training/adapters \
    --prompt "Write a Python function that merges two sorted lists."
```

### Fuse Adapter into Base Model

```bash
# Fuse without dequantization (keeps 4-bit, smaller output)
mlx_lm.fuse \
    --model models/qwen2.5-coder-7b-instruct-4bit-mlx \
    --adapter-path training/adapters \
    --save-path training/fused_model

# Fuse WITH dequantization (bf16, needed for GGUF or Ollama experimental)
mlx_lm.fuse \
    --model models/qwen2.5-coder-7b-instruct-4bit-mlx \
    --adapter-path training/adapters \
    --save-path training/fused_model \
    --dequantize
```

### Ollama Import (Experimental)

```bash
# Create a Modelfile pointing to the fused safetensors model
cat > /tmp/Modelfile.qwen-ft << 'EOF'
FROM /Users/bretbouchard/apps/me_code_pretty_one_day/training/fused_model
PARAMETER temperature 0.7
PARAMETER num_ctx 4096
EOF

# Create Ollama model (experimental safetensors support)
ollama create qwen2.5-coder-ft --experimental -f /tmp/Modelfile.qwen-ft

# Test the fine-tuned model
ollama run qwen2.5-coder-ft "Write a Swift struct for a binary search tree"
```

**Note:** The `--experimental` flag for safetensors import in Ollama 0.30.6 has NOT been tested with Qwen2 models in this research. This is a [MEDIUM confidence] path that requires validation during execution.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual LoRA implementation | `mlx_lm.lora` with YAML config | mlx-lm 0.10+ | No custom training code needed |
| Full fine-tuning | QLoRA (4-bit quantized base) | Standard practice | 4x memory reduction, same quality |
| Separate GGUF conversion | mlx_lm.fuse --export-gguf | mlx-lm 0.15+ | One-command export (Llama/Mistral only) |
| llama.cpp convert_hf_to_gguf | Still needed for Qwen2 | Current | mlx-lm GGUF export doesn't support Qwen2 |

**Deprecated/outdated:**
- `mlx_lm.convert` with `--upload-repo`: Still works but `mlx_lm.fuse --upload-repo` is preferred for fused models
- LoRA keys limited to q_proj/v_proj: Modern practice includes all attention projections (q, k, v, o) for better quality

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `ollama create --experimental` can import fused Qwen2.5-Coder safetensors | Pattern 4 (Ollama Import) | Falls back to mlx_lm.server serving only; no Ollama path for fine-tuned model |
| A2 | 5000 synthetic code examples from the base model will improve domain performance | Pitfall 3 | Quality may regress; need to start with smaller dataset and validate |
| A3 | Disk space (27GB free) is sufficient for training + one fusion cycle | Pitfall 2 | May need to clean up first, or skip fusion entirely |
| A4 | `--mask-prompt` correctly handles the `chat` format for Qwen2.5-Coder | Pattern 2 | Loss computed on wrong tokens, wasting training capacity |

**If this table is empty:** All claims in this research were verified or cited -- no user confirmation needed.

## Open Questions

1. **Ollama experimental safetensors support for Qwen2**
   - What we know: Ollama 0.30.6 has `--experimental` flag for safetensors model creation. The base model was originally imported to Ollama via HuggingFace GGUF (not safetensors).
   - What's unclear: Whether `--experimental` works with Qwen2 architecture specifically, or only Llama-based models.
   - Recommendation: Test with a small fused model first. If it fails, use mlx_lm.server as the primary serving path.

2. **Training data quality validation approach**
   - What we know: Need 5000+ examples in chat format. Data generated synthetically from seed examples.
   - What's unclear: What validation methodology to use before training (human review? automated quality check? sample evaluation?).
   - Recommendation: Generate data, manually review 50 random samples, then run base model on 100 validation prompts to establish baseline, then train.

3. **Optimal LoRA rank for code tasks**
   - What we know: Requirement says rank 16-32. kicad-agent used rank 16 successfully.
   - What's unclear: Whether rank 16 or 32 gives better results for code generation specifically on Qwen2.5-Coder-7B.
   - Recommendation: Start with rank 16 (proven, lower memory). Train and evaluate. If quality is insufficient, retrain with rank 32.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| mlx-lm | LoRA/QLoRA training | Yes | 0.31.3 | -- |
| mlx | ML compute backend | Yes | 0.31.2 | -- |
| transformers | Tokenizer, chat template | Yes | 5.10.0.dev0 | -- |
| datasets | HF dataset loading | Yes | 4.8.5 | -- |
| gguf | GGUF format handling | Yes | 0.19.0 | -- |
| ollama CLI | Model serving | Yes | 0.30.6 | -- |
| Python 3.11 | Script execution | Yes | 3.11.11 | -- |
| Base model (4-bit) | QLoRA training | Yes | ~4GB | -- |
| Apple M2 Pro 32GB | GPU training | Yes | 32GB unified | Reduce batch_size, grad_checkpoint |
| llama.cpp convert | Qwen2 GGUF conversion | No | -- | Use mlx_lm.server or ollama --experimental |

**Missing dependencies with no fallback:**
- None critical. The llama.cpp converter is only needed as a last-resort alternative for Ollama deployment.

**Missing dependencies with fallback:**
- `llama.cpp convert_hf_to_gguf.py`: Not installed, but only needed if both mlx_lm.server and ollama --experimental fail. Low probability.

**Disk constraint:**
- 27GB free is tight. Fused bf16 model is ~14GB. Training artifacts (adapters ~50MB, checkpoints ~200MB total) are manageable. Recommend cleaning up before fusion.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | None yet -- see Wave 0 |
| Quick run command | `pytest scripts/ -x -v` |
| Full suite command | `pytest scripts/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LAKE-06 | LoRA adapter trains and loss decreases | integration | `python3 -c "import mlx_lm; print('OK')"` + manual training run | N/A -- manual validation |
| LAKE-07 | Training data generator produces 5000+ examples | unit | `pytest scripts/test_generate_training_data.py -x` | No -- Wave 0 |
| LAKE-08 | Training data is valid chat format | unit | `pytest scripts/test_training_data_format.py -x` | No -- Wave 0 |
| LAKE-09 | Adapter works with Ollama or mlx_lm.server | integration | `python3 scripts/test_adapter_serving.py` | No -- Wave 0 |
| LAKE-10 | Train/val split is deterministic | unit | `pytest scripts/test_train_val_split.py -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -c "import mlx_lm; from transformers import AutoTokenizer; print('deps OK')"`
- **Per wave merge:** `pytest scripts/ -x -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `scripts/test_generate_training_data.py` -- covers LAKE-07 (data count, format validation)
- [ ] `scripts/test_training_data_format.py` -- covers LAKE-08 (ChatML template correctness)
- [ ] `scripts/test_train_val_split.py` -- covers LAKE-10 (determinism, ratio)
- [ ] `scripts/conftest.py` -- shared fixtures (model path, tokenizer, sample data)

Note: Many tests for this phase require actual model training runs, which are expensive (minutes per iteration). Unit tests should focus on data pipeline correctness. Integration tests for the training pipeline itself should be manual or marked with `@pytest.mark.slow`.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | N/A -- local tool, no auth |
| V3 Session Management | No | N/A -- local tool, no sessions |
| V4 Access Control | No | N/A -- local tool, no network serving |
| V5 Input Validation | Yes | Validate training data JSONL format before training |
| V6 Cryptography | No | N/A -- no cryptographic operations |

### Known Threat Patterns for ML Fine-Tuning Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Training data poisoning | Tampering | Validate all synthetic examples, manual review of samples |
| Model degradation (catastrophic forgetting) | Tampering | Monitor validation loss, keep base model as fallback |
| Prompt injection in training data | Tampering | Sanitize seed examples, avoid user-generated content in training |

## Sources

### Primary (HIGH confidence)
- [VERIFIED: mlx-lm 0.31.3 installed and tested] -- CLI flags, fuse behavior, GGUF limitations
- [VERIFIED: mlx_lm/gguf.py source code] -- hardcoded "llama" architecture at line 228, weight translation at lines 103-130
- [VERIFIED: mlx_lm/fuse.py source code] -- dequantize and export-gguf flow at lines 69-100
- [VERIFIED: Qwen2.5-Coder tokenizer chat template] -- tested with actual model, confirmed `<|im_start|>` format output
- [VERIFIED: mlx_lm.server --help] -- confirmed `--adapter-path` support
- [CITED: mlx-lm LORA.md](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/LORA.md) -- official fine-tuning documentation
- [CITED: mlx-lm lora_config.yaml example](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/examples/lora_config.yaml) -- official config example

### Secondary (MEDIUM confidence)
- [Context7: /ml-explore/mlx-lm] -- fine-tuning patterns, dataset formats, LoRA parameters

### Tertiary (LOW confidence)
- None -- all claims verified or cited from primary sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all versions verified via `pip show` and `mlx_lm.lora --help`
- Architecture: HIGH - verified via source code reading and actual CLI testing
- Pitfalls: HIGH - GGUF limitation confirmed via source code; disk space confirmed via `df -h`

**Research date:** 2026-06-10
**Valid until:** 30 days (mlx-lm releases frequently, but core LoRA API is stable)
