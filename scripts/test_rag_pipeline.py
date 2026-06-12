"""Tests for the RAG generation pipeline (generate.py).

Tests generate_with_rag function: Confucius retrieval -> prompt assembly -> Ollama inference.
Integration tests (skipped by default) marked with @pytest.mark.integration.
"""

import json
import sys
import os
import unittest.mock
import urllib.error
import urllib.request

import pytest

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")

# Ensure scripts directory is importable
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

from generate import generate_with_rag, parse_args


# --- Integration test configuration ---


def pytest_addoption(parser):
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="run integration tests",
    )


def pytest_collection_modifyitems(config, items):
    """Skip integration tests unless --run-integration flag is given."""
    if config.getoption("--run-integration", default=False):
        return
    skip = pytest.mark.skip(reason="need --run-integration option to run")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)


# --- Helpers ---


def _mock_urlopen_response(response_data: dict):
    """Create a mock urlopen context manager that returns the given JSON data."""
    mock_resp = unittest.mock.MagicMock()
    mock_resp.read.return_value = json.dumps(response_data).encode()
    mock_resp.__enter__ = unittest.mock.MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = unittest.mock.MagicMock(return_value=False)
    return mock_resp


def _mock_assembler(assemble_return: list[dict] | None = None):
    """Create a mock PromptAssembler that returns given messages from assemble."""
    mock = unittest.mock.patch("generate.PromptAssembler")
    MockAssembler = mock.start()
    if assemble_return is None:
        assemble_return = [
            {"role": "system", "content": "You are an expert."},
            {"role": "user", "content": "test prompt"},
        ]
    MockAssembler.return_value.assemble.return_value = assemble_return
    return MockAssembler, mock


# --- Unit tests for generate_with_rag ---


class TestGenerateWithRAG:
    """Unit tests for generate_with_rag using mocked dependencies."""

    def test_generate_with_rag_returns_nonempty_string(self):
        """generate_with_rag returns a non-empty string when Ollama is mocked."""
        mock_response = {
            "choices": [
                {"message": {"content": "def binary_search(arr, target):\n    ..."}}
            ],
            "usage": {"prompt_tokens": 50, "completion_tokens": 100},
        }

        MockAssembler, mock_asm = _mock_assembler()
        mock_urlopen = _mock_urlopen_response(mock_response)

        with unittest.mock.patch("urllib.request.urlopen", return_value=mock_urlopen):
            result = generate_with_rag(
                "write a binary search",
                domain="python",
                model_path="/fake/model",
            )

        mock_asm.stop()
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_with_rag_works_with_empty_patterns(self):
        """generate_with_rag returns output even when retrieve_patterns returns empty list."""
        mock_response = {
            "choices": [
                {"message": {"content": "def hello():\n    return 42"}}
            ],
            "usage": {"prompt_tokens": 30, "completion_tokens": 50},
        }

        MockAssembler, mock_asm = _mock_assembler([
            {"role": "system", "content": "SLC only."},
            {"role": "user", "content": "hello world"},
        ])
        mock_urlopen = _mock_urlopen_response(mock_response)

        with unittest.mock.patch("urllib.request.urlopen", return_value=mock_urlopen):
            result = generate_with_rag(
                "hello world",
                domain="python",
                model_path="/fake/model",
            )

        mock_asm.stop()
        assert result is not None
        assert len(result) > 0

    def test_generate_with_rag_calls_assemble_with_correct_args(self):
        """generate_with_rag calls PromptAssembler.assemble with the correct user_prompt and domain."""
        mock_response = {
            "choices": [{"message": {"content": "output"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }

        MockAssembler, mock_asm = _mock_assembler()
        mock_urlopen = _mock_urlopen_response(mock_response)

        with unittest.mock.patch("urllib.request.urlopen", return_value=mock_urlopen):
            generate_with_rag(
                "write a function",
                domain="swift",
                model_path="/fake/model",
                max_tokens=1024,
            )

        mock_asm.stop()
        MockAssembler.return_value.assemble.assert_called_once_with(
            "write a function", "swift", max_generation_tokens=1024, skip_rag=False
        )

    def test_generate_with_rag_sends_to_ollama_endpoint(self):
        """generate_with_rag sends messages to Ollama API endpoint at localhost:11434/v1/chat/completions."""
        mock_response = {
            "choices": [{"message": {"content": "code here"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }

        _, mock_asm = _mock_assembler()
        mock_urlopen = _mock_urlopen_response(mock_response)

        with unittest.mock.patch("urllib.request.urlopen", return_value=mock_urlopen) as patched:
            generate_with_rag("test", domain="python", model_path="/fake/model")

            mock_asm.stop()
            # Verify the request was made to the correct endpoint
            patched.assert_called_once()
            call_arg = patched.call_args
            assert call_arg is not None
            req = call_arg[0][0]
            assert isinstance(req, urllib.request.Request)
            assert "localhost:11434/v1/chat/completions" in req.full_url

    def test_generate_with_rag_extracts_content_from_response(self):
        """generate_with_rag extracts content from response['choices'][0]['message']['content']."""
        expected_content = "def add(a, b):\n    return a + b"
        mock_response = {
            "choices": [{"message": {"content": expected_content}}],
            "usage": {"prompt_tokens": 20, "completion_tokens": 40},
        }

        _, mock_asm = _mock_assembler()
        mock_urlopen = _mock_urlopen_response(mock_response)

        with unittest.mock.patch("urllib.request.urlopen", return_value=mock_urlopen):
            result = generate_with_rag("add function", domain="python", model_path="/fake/model")

        mock_asm.stop()
        assert result == expected_content

    def test_generate_with_rag_handles_connection_error(self):
        """generate_with_rag handles Ollama connection error gracefully (returns None)."""
        _, mock_asm = _mock_assembler()

        with unittest.mock.patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("Connection refused"),
        ):
            result = generate_with_rag("test", domain="python", model_path="/fake/model")

        mock_asm.stop()
        assert result is None

    def test_cli_argument_parsing(self):
        """CLI argument parsing accepts --prompt, --domain, --max-tokens, --temperature, --no-rag flags."""
        args = parse_args([
            "write a function",
            "--domain", "swift",
            "--max-tokens", "4096",
            "--temperature", "0.5",
            "--no-rag",
        ])

        assert args.prompt == "write a function"
        assert args.domain == "swift"
        assert args.max_tokens == 4096
        assert args.temperature == 0.5
        assert args.no_rag is True

    def test_no_rag_skips_retrieve_patterns(self):
        """With --no-rag flag, generate_with_rag skips retrieve_patterns."""
        mock_response = {
            "choices": [{"message": {"content": "output"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }

        MockAssembler, mock_asm = _mock_assembler()
        mock_urlopen = _mock_urlopen_response(mock_response)

        with unittest.mock.patch("urllib.request.urlopen", return_value=mock_urlopen):
            result = generate_with_rag(
                "test prompt",
                domain="python",
                model_path="/fake/model",
                no_rag=True,
            )

        mock_asm.stop()
        # retrieve_patterns should NOT have been called
        MockAssembler.return_value.retrieve_patterns.assert_not_called()
        # assemble should have been called with skip_rag=True
        MockAssembler.return_value.assemble.assert_called_once_with(
            "test prompt", "python", max_generation_tokens=2048, skip_rag=True
        )

    def test_verbose_reports_retrieval_latency(self, capsys):
        """generate_with_rag reports retrieval latency when --verbose flag is set."""
        mock_response = {
            "choices": [{"message": {"content": "output"}}],
            "usage": {"prompt_tokens": 50, "completion_tokens": 100},
        }

        MockAssembler, mock_asm = _mock_assembler()
        MockAssembler.return_value.retrieve_patterns.return_value = [
            {"id": "p1", "type": "pattern", "content": "pattern content", "tags": ["test"]}
        ]
        mock_urlopen = _mock_urlopen_response(mock_response)

        with unittest.mock.patch("urllib.request.urlopen", return_value=mock_urlopen):
            result = generate_with_rag(
                "test",
                domain="python",
                model_path="/fake/model",
                verbose=True,
            )

        mock_asm.stop()
        captured = capsys.readouterr()
        assert "Retrieved 1 patterns" in captured.err
        assert "ms" in captured.err


# --- Integration tests (skipped by default) ---


@pytest.mark.integration
class TestRAGPipelineIntegration:
    """Integration tests against a live Ollama instance.

    These tests require Ollama to be running at localhost:11434.
    Run with: pytest scripts/test_rag_pipeline.py --run-integration -v
    """

    def test_ollama_reachable(self):
        """Check if Ollama is reachable at localhost:11434."""
        try:
            req = urllib.request.Request("http://localhost:11434/v1/models")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                assert "data" in data
        except (urllib.error.URLError, OSError):
            pytest.skip("Ollama not running")

    def test_generate_no_rag_integration(self):
        """Call generate_with_rag with --no-rag mode, simple prompt."""
        result = generate_with_rag(
            "def add(a, b):",
            domain="python",
            model_path=os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "models", "qwen2.5-coder-7b-instruct-4bit-mlx",
            ),
            no_rag=True,
            max_tokens=256,
            temperature=0.2,
        )
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
        assert "def" in result or "return" in result

    def test_generate_with_rag_integration(self):
        """Call generate_with_rag with RAG enabled for full pipeline test."""
        result = generate_with_rag(
            "Write a Swift function to sort an array",
            domain="swift",
            model_path=os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "models", "qwen2.5-coder-7b-instruct-4bit-mlx",
            ),
            no_rag=False,
            max_tokens=512,
            temperature=0.2,
        )
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
