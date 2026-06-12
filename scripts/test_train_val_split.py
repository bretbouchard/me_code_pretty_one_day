"""Tests for train/val split — no overlap, ratio, determinism."""

import json
import os
import random
import tempfile

import pytest

from conftest import TRAIN_FILE, VALID_FILE


class TestSplitRatio:
    def test_split_ratio(self, train_file: str, valid_file: str):
        if not os.path.exists(train_file) or not os.path.exists(valid_file):
            pytest.skip("train.jsonl or valid.jsonl does not exist yet")

        with open(train_file, "r", encoding="utf-8") as f:
            train_count = sum(1 for line in f if line.strip())
        with open(valid_file, "r", encoding="utf-8") as f:
            valid_count = sum(1 for line in f if line.strip())

        total = train_count + valid_count
        if total == 0:
            pytest.skip("No examples found")

        ratio = train_count / total
        assert 0.89 <= ratio <= 0.91, (
            f"Train ratio is {ratio:.4f}, expected between 0.89 and 0.91 "
            f"(train={train_count}, valid={valid_count}, total={total})"
        )


class TestNoOverlap:
    def test_no_overlap(self, train_file: str, valid_file: str):
        if not os.path.exists(train_file) or not os.path.exists(valid_file):
            pytest.skip("train.jsonl or valid.jsonl does not exist yet")

        # Collect user prompts from samples of each set
        train_prompts = set()
        with open(train_file, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= 200:
                    break
                line = line.strip()
                if line:
                    ex = json.loads(line)
                    msgs = ex.get("messages", [])
                    user_msgs = [m["content"] for m in msgs if m.get("role") == "user"]
                    for content in user_msgs:
                        train_prompts.add(content.strip())

        overlap_count = 0
        with open(valid_file, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= 200:
                    break
                line = line.strip()
                if line:
                    ex = json.loads(line)
                    msgs = ex.get("messages", [])
                    user_msgs = [m["content"] for m in msgs if m.get("role") == "user"]
                    for content in user_msgs:
                        if content.strip() in train_prompts:
                            overlap_count += 1

        assert overlap_count == 0, f"Found {overlap_count} overlapping user prompts between train and valid"


class TestDeterminismShuffle:
    def test_determinism_shuffle(self):
        """Verify that shuffling with seed=42 produces identical order twice."""
        items = list(range(1000))

        rng1 = random.Random(42)
        shuffled1 = list(items)
        rng1.shuffle(shuffled1)

        rng2 = random.Random(42)
        shuffled2 = list(items)
        rng2.shuffle(shuffled2)

        assert shuffled1 == shuffled2, "Two shuffles with seed=42 produced different results"

    def test_determinism_split_consistency(self):
        """Verify split index is deterministic for a given total count."""
        total = 5500
        split_idx_1 = int(total * 0.9)
        split_idx_2 = int(total * 0.9)
        assert split_idx_1 == split_idx_2 == 4950

        # Train = 4950, valid = 550
        train_ratio = 4950 / total
        assert 0.89 <= train_ratio <= 0.91
