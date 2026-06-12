"""Tests for generate_training_data.py — existence, counts, and seed files."""

import json
import os

import pytest

from conftest import SEED_DIR, TRAIN_FILE, VALID_FILE


class TestOutputFilesExist:
    def test_train_file_exists(self, train_file: str):
        assert os.path.exists(train_file), f"train.jsonl not found at {train_file}"

    def test_valid_file_exists(self, valid_file: str):
        assert os.path.exists(valid_file), f"valid.jsonl not found at {valid_file}"


class TestExampleCounts:
    def test_train_count(self, train_file: str):
        with open(train_file, "r", encoding="utf-8") as f:
            lines = [l for l in f if l.strip()]
        assert len(lines) >= 4500, f"train.jsonl has {len(lines)} lines, expected >= 4500"

    def test_valid_count(self, valid_file: str):
        with open(valid_file, "r", encoding="utf-8") as f:
            lines = [l for l in f if l.strip()]
        assert len(lines) >= 500, f"valid.jsonl has {len(lines)} lines, expected >= 500"


class TestSeedFiles:
    @pytest.fixture(params=["python_tasks.json", "swift_tasks.json", "general_tasks.json"])
    def seed_file(self, request):
        return os.path.join(SEED_DIR, request.param)

    def test_seed_files_exist(self, seed_file: str):
        assert os.path.exists(seed_file), f"Seed file not found: {seed_file}"

    def test_seed_files_valid_json(self, seed_file: str):
        with open(seed_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, list), f"{seed_file} is not a JSON array"

    def test_seed_file_min_entries(self, seed_file: str):
        with open(seed_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) >= 3, f"{seed_file} has {len(data)} entries, expected >= 3"

    def test_seed_file_has_required_fields(self, seed_file: str):
        with open(seed_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        for i, entry in enumerate(data):
            assert "user_prompt" in entry, f"{seed_file}[{i}]: missing 'user_prompt'"
            assert isinstance(entry["user_prompt"], str), f"{seed_file}[{i}]: user_prompt not a string"
            assert len(entry["user_prompt"]) > 0, f"{seed_file}[{i}]: empty user_prompt"
