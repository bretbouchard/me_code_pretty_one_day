"""Shared pytest fixtures for training data pipeline tests."""

import json
import os
import random
from typing import Any, Dict, List

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
SEED_DIR = os.path.join(DATA_DIR, "seed_examples")
TRAIN_FILE = os.path.join(DATA_DIR, "train.jsonl")
VALID_FILE = os.path.join(DATA_DIR, "valid.jsonl")
MODEL_DIR = os.path.join(PROJECT_ROOT, "models", "qwen2.5-coder-7b-instruct-4bit-mlx")


@pytest.fixture
def project_root() -> str:
    return PROJECT_ROOT


@pytest.fixture
def data_dir() -> str:
    return DATA_DIR


@pytest.fixture
def seed_examples_dir() -> str:
    return SEED_DIR


@pytest.fixture
def train_file() -> str:
    return TRAIN_FILE


@pytest.fixture
def valid_file() -> str:
    return VALID_FILE


@pytest.fixture
def model_dir() -> str:
    return MODEL_DIR


def _read_jsonl(filepath: str) -> List[Dict[str, Any]]:
    """Read a JSONL file and return list of parsed dicts."""
    if not os.path.exists(filepath):
        return []
    examples = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    return examples


@pytest.fixture
def train_data(train_file: str) -> List[Dict[str, Any]]:
    return _read_jsonl(train_file)


@pytest.fixture
def valid_data(valid_file: str) -> List[Dict[str, Any]]:
    return _read_jsonl(valid_file)


@pytest.fixture
def sample_train_examples(train_file: str) -> List[Dict[str, Any]]:
    """Read a random sample of up to 100 examples from train.jsonl."""
    if not os.path.exists(train_file):
        pytest.skip("train.jsonl does not exist yet")
    all_examples = _read_jsonl(train_file)
    count = min(100, len(all_examples))
    return random.Random(42).sample(all_examples, count)


@pytest.fixture
def sample_valid_examples(valid_file: str) -> List[Dict[str, Any]]:
    """Read a random sample of up to 100 examples from valid.jsonl."""
    if not os.path.exists(valid_file):
        pytest.skip("valid.jsonl does not exist yet")
    all_examples = _read_jsonl(valid_file)
    count = min(100, len(all_examples))
    return random.Random(42).sample(all_examples, count)
