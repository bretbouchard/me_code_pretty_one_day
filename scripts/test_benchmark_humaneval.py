"""Tests for HumanEval benchmark framework.

Tests pass@k math, completion extraction, and benchmark runner smoke tests.
human-eval package tests are gated behind import checks so tests work without it.
"""

import json
import math
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

# Add scripts directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from benchmark_humaneval import extract_completion, pass_at_k

# Check if human-eval is available for integration tests
try:
    from human_eval.data import read_problems, write_jsonl
    HAS_HUMAN_EVAL = True
except ImportError:
    HAS_HUMAN_EVAL = False


# --- pass_at_k tests (Tests 1-4) ---

class TestPassAtK:
    """Tests for pass@k hypergeometric distribution calculation."""

    def test_pass_at_k_basic(self) -> None:
        """Test 1: pass_at_k(5, 2, 1) returns 0.4."""
        # 1 - C(3,1)/C(5,1) = 1 - 3/5 = 0.4
        assert abs(pass_at_k(5, 2, 1) - 0.4) < 1e-9

    def test_pass_at_k_all_correct(self) -> None:
        """Test 2: pass_at_k(10, 10, 1) returns 1.0 when all samples are correct."""
        assert pass_at_k(10, 10, 1) == 1.0

    def test_pass_at_k_none_correct(self) -> None:
        """Test 3: pass_at_k(10, 0, 1) returns 0.0 when no samples are correct."""
        assert pass_at_k(10, 0, 1) == 0.0

    def test_pass_at_k_edge_case(self) -> None:
        """Test 4: pass_at_k(5, 5, 10) returns 1.0 when n-c < k."""
        assert pass_at_k(5, 5, 10) == 1.0


# --- extract_completion tests (Tests 5-6) ---

class TestExtractCompletion:
    """Tests for extracting function body from model output."""

    def test_strips_markdown_fences(self) -> None:
        """Test 5: extract_completion strips ```python fences and returns function body."""
        prompt = "def foo():\n    pass"
        raw_output = "```python\ndef foo():\n    return 1\n```"
        result = extract_completion(prompt, raw_output)
        assert result == "def foo():\n    return 1"

    def test_no_fences_passthrough(self) -> None:
        """Test 6: extract_completion passes through content without fences."""
        prompt = "def foo():\n    pass"
        raw_output = "def foo():\n    return 1"
        result = extract_completion(prompt, raw_output)
        assert result == "def foo():\n    return 1"


# --- Smoke tests (Test 7) ---

@pytest.mark.skipif(not HAS_HUMAN_EVAL, reason="human-eval package not installed")
class TestRunVariantSmoke:
    """Smoke tests using mocked Ollama API and real HumanEval problems."""

    def test_generate_for_problem_produces_samples(self) -> None:
        """Test 7: generate_for_problem with mocked Ollama produces correct sample count."""
        from benchmark_humaneval import generate_for_problem

        problems = read_problems()
        task_ids = list(problems.keys())[:2]

        # Mock assembler (not actually used in base variant)
        mock_assembler = MagicMock()

        # Mock Ollama API response
        mock_response = {
            "choices": [{"message": {"content": "    return 42"}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 5},
        }

        samples = []
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value.read.return_value = (
                json.dumps(mock_response).encode()
            )

            for task_id in task_ids[:1]:
                problem = problems[task_id]
                result = generate_for_problem(
                    problem=problem,
                    variant="base",
                    assembler=mock_assembler,
                    model_path="/fake/model",
                    n_samples=2,
                    verbose=False,
                )
                samples.extend(result)

        assert len(samples) == 2
        assert all("task_id" in s for s in samples)
        assert all("completion" in s for s in samples)

    def test_write_samples_jsonl(self) -> None:
        """Verify samples can be written to JSONL via human_eval.data.write_jsonl."""
        problems = read_problems()
        task_id = list(problems.keys())[0]

        samples = [
            {"task_id": task_id, "completion": "    return 1"},
            {"task_id": task_id, "completion": "    return 2"},
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f:
            tmp_path = f.name

        try:
            write_jsonl(tmp_path, samples)

            # Verify file was written correctly
            with open(tmp_path, "r") as f:
                lines = [json.loads(line) for line in f if line.strip()]
            assert len(lines) == 2
            assert lines[0]["task_id"] == task_id
        finally:
            os.unlink(tmp_path)
