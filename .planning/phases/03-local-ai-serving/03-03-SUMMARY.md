# Plan 03-03 Summary: mlx_lm.server Serving Path (LAKE-02)

**Status:** Complete

## Model Download

- Downloaded `mlx-community/Qwen2.5-Coder-7B-Instruct-4bit` via `huggingface_hub.snapshot_download`
- Stored at `./models/qwen2.5-coder-7b-instruct-4bit-mlx/` (11 files, ~4.0 GB safetensors)
- Download completed in under 1 minute

## CLI Generation Test

- Ran `python3 -m mlx_lm.generate` with prompt `"def fibonacci(n):"`
- Model generated valid Python code with docstring and full implementation
- Performance: 4.094 tok/s prompt, 20.438 tok/s generation, 4.447 GB peak memory
- Deprecation warning: `python3 -m mlx_lm.generate` is deprecated, use `python3 -m mlx_lm generate` (dot syntax) instead

## Server Test (API Response Confirmed)

- `scripts/serve-mlx.py` successfully starts `mlx_lm.server` on configurable port (default 8800)
- `/v1/models` endpoint returns 200 with model listed
- `/v1/chat/completions` endpoint returns 200 with valid JSON response
- Chat completions test: requested palindrome function, received correct Python implementation
- Server warmup: ~25 seconds from launch to model fully loaded in memory
- SIGTERM handling confirmed: graceful shutdown kills subprocess cleanly

## Files Created

| File | Description |
|------|-------------|
| `models/qwen2.5-coder-7b-instruct-4bit-mlx/` | MLX-native model weights + tokenizer (11 files, ~4 GB) |
| `scripts/serve-mlx.py` | Server launch script (125 lines) with health polling, graceful shutdown, CLI args |

## Key Findings

1. **Model ID behavior:** `mlx_lm.server` registers the full local path as the model ID in `/v1/models`, not the HuggingFace repo name. Chat completion requests must use this full path (e.g., `/Users/bretbouchard/apps/me_code_pretty_one_day/models/qwen2.5-coder-7b-instruct-4bit-mlx`) as the `model` field. Clients should query `/v1/models` first to discover the correct ID.

2. **mlx_lm version:** 0.31.3 installed, deprecation warning on `python3 -m mlx_lm.generate` (use `python3 -m mlx_lm generate` instead).

3. **Memory usage:** ~4.5 GB peak for the 4-bit quantized 7B model. Comfortable on M2 Pro 32GB.

## Issues

None.
