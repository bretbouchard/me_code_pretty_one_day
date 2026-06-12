# Plan 04-03 Summary: Serving, Deployment, and Benchmark Comparison

**Status:** Complete
**Plan:** 04-03
**Phase:** 04-fine-tuning-pipeline
**Wave:** 2

---

## What Was Built

Three scripts for fine-tuned model serving, optional Ollama deployment, and benchmark comparison.

### 1. `scripts/serve_finetuned.py` (160 lines)

Launches `mlx_lm.server` with the LoRA adapter loaded via `--adapter-path`.

- Default port 8801 (avoids conflict with base model on 8800)
- Validates both model directory and adapter directory before launching
- Follows same pattern as `serve-mlx.py`: subprocess.Popen, health polling via `/v1/models`, SIGINT/SIGTERM handlers, output streaming
- Prints model ID discovery note (mlx_lm.server uses full path as model ID)

### 2. `scripts/merge_and_deploy.py` (277 lines)

Fuses adapter into standalone model, with optional Ollama deployment.

- Disk space check: 15GB required for dequantize, warns at <20GB, 2GB for no-dequantize
- Runs `mlx_lm.fuse` (NOT `--export-gguf` which is incompatible with Qwen2)
- Reports fused model file count and total size
- Optional `--deploy-ollama` creates a Modelfile and runs `ollama create --experimental`
- Ollama failure is non-fatal: prints warning and recommends `serve_finetuned.py`

### 3. `scripts/benchmark_compare.py` (411 lines)

Compares base model (port 8800) vs fine-tuned model (port 8801) on validation prompts.

- Discovers model IDs from each server via `/v1/models`
- Loads prompts from `data/valid.jsonl` (extracts user messages)
- Runs non-streaming completions against both servers
- Code quality heuristics: syntax validation (ast.parse for Python, bracket matching for Swift), docstring detection, type hint detection
- Prints formatted comparison table with improvement percentages
- Uses `urllib.request` only (no external dependencies)

---

## Verification Results

| Check | Status |
|-------|--------|
| `serve_finetuned.py` parses | PASS |
| `serve_finetuned.py --help` shows --adapter-path, --port | PASS |
| `merge_and_deploy.py` parses | PASS |
| `merge_and_deploy.py --help` shows --deploy-ollama, --dequantize | PASS |
| `benchmark_compare.py` parses | PASS |
| `benchmark_compare.py --help` shows --base-url, --ft-url | PASS |
| No `--export-gguf` in code (comments only) | PASS |
| Line count: serve_finetuned.py >= 80 | PASS (160) |
| Line count: merge_and_deploy.py >= 80 | PASS (277) |
| Line count: benchmark_compare.py >= 120 | PASS (411) |

---

## Design Decisions

1. **Port 8801 for fine-tuned model** — Allows running both base and fine-tuned simultaneously for comparison.
2. **mlx_lm.server as PRIMARY serving path** — Per RESEARCH finding, GGUF export hardcodes llama architecture and fails for Qwen2.
3. **Non-streaming benchmark** — Simpler implementation, sufficient for comparison. Streaming could be added later for TTFT measurement.
4. **Graceful adapter-not-found handling** — Scripts check for `adapter_config.json` or `adapters.safetensors` before launching, with clear error messages pointing to training.
5. **Ollama deployment is non-fatal** --experimental flag means it may fail; the script warns and recommends the mlx_lm.server path.

---

## Usage

```bash
# Start fine-tuned model server (after training completes)
python3 scripts/serve_finetuned.py

# Fuse adapter and optionally deploy to Ollama
python3 scripts/merge_and_deploy.py --deploy-ollama

# Compare base vs fine-tuned (both servers must be running)
python3 scripts/serve-mlx.py &          # port 8800
python3 scripts/serve_finetuned.py &    # port 8801
python3 scripts/benchmark_compare.py --num-prompts 20
```

---

## Dependencies

- Plan 01 (training data generation) — provides `data/valid.jsonl` for benchmark prompts
- Plan 02 (training config) — produces adapter at `training/adapters/`
- Existing `scripts/serve-mlx.py` — pattern and base model server

## Threat Model

| ID | Threat | Mitigation |
|----|--------|------------|
| T-04-06 | Disk exhaustion from fusion | Disk check >= 15GB before dequantize; warn at < 20GB |
| T-04-07 | Ollama model name collision | Model name `qwen2.5-coder-ft` is unique, local-only |
