# Plan 04-02 Summary: LoRA Training Config & Wrapper Script

**Status:** Complete
**Date:** 2026-06-10

## What Was Done

Created MLX-LoRA training configuration and wrapper script for Qwen2.5-Coder-7B-Instruct fine-tuning.

## Files Created

| File | Purpose |
|------|---------|
| `training/lora_config.yaml` | QLoRA training hyperparameters for mlx_lm.lora |
| `scripts/train_lora.py` | Wrapper with disk check, path validation, --mask-prompt, signal handling |
| `training/adapters/` | Output directory for adapter weights |

## Key Configuration Decisions

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| rank | 16 | LAKE-06 requirement (16-32 range), proven in kicad-agent |
| learning_rate | 5e-6 | LAKE-06 requirement |
| num_layers | 16 | Last 16 of 28 layers, memory efficient |
| grad_checkpoint | true | Critical for 32GB Mac memory |
| max_seq_length | 2048 | Memory management |
| scale | 32.0 | 2x rank (standard LoRA scaling) |
| dropout | 0.0 | No dropout for code generation |
| lr_schedule | cosine_decay | 100-step warmup, smooth decay |
| mask-prompt | CLI flag | Assistant-only loss (CLI-only, not YAML) |

## Validation Results

- Config YAML: all assertions passed (model, lr, rank, seed, grad_checkpoint, max_seq_length, scale, dropout, keys)
- Script syntax: no parse errors
- `--help` flag: works correctly

## Notes

- `5e-6` scientific notation in YAML was parsed as string by PyYAML; used `0.000005` explicit float notation instead
- `--mask-prompt` is CLI-only (not a YAML config option) — the wrapper passes it on the command line
- Training data files (train.jsonl, valid.jsonl) are verified by the wrapper at launch but not created by this plan (Plan 04-01 responsibility)
- Actual training execution is deferred — this plan creates the config and launcher only

## How to Train

```bash
cd ~/apps/me_code_pretty_one_day
python3 scripts/train_lora.py
```

## Threat Mitigations Applied

| Threat | Mitigation |
|--------|------------|
| T-04-04: Disk exhaustion | Disk check >= 10GB free, warns < 15GB, save_every: 200 limits checkpoint count |
| T-04-05: OOM | grad_checkpoint, batch_size 4, max_seq_length 2048, grad_accumulation_steps 2 |
