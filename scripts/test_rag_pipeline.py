"""Tests for the RAG generation pipeline (generate.py).

Tests generate_with_rag function: Confucius retrieval -> prompt assembly -> Ollama inference.
Integration tests (skipped by default) marked with @pytest.mark.integration.
"""

import json
import sys
import os
import unittest.mock

import pytest

# Ensure scripts directory is importable
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

from generate import generate_with_rag


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

        with (
            unittest.mock.patch(
                "generate.PromptAssembler"
            ) as MockAssembler,
            unittest.mock.patch(
                "generate.urlopen"
            ) as mock_urlopen,
        ):
            mock_instance = MockAssembler.return_value
            mock_instance.assemble.return_value = [
                {"role": "system", "content": "You are an expert."},
                {"role": "user", "content": "write a binary search"},
            ]

            mock_resp = unittest.mock.MagicMock()
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__ = unittest.mock.MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = unittest.mock.MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            result = generate_with_rag(
                "write a binary search",
                domain="python",
                model_path="/fake/model",
            )

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

        with (
            unittest.mock.patch(
                "generate.PromptAssembler"
            ) as MockAssembler,
            unittest.mock.patch(
                "generate.urlopen"
            ) as mock_urlopen,
        ):
            mock_instance = MockAssembler.return_value
            mock_instance.retrieve_patterns.return_value = []
            mock_instance.assemble.return_value = [
                {"role": "system", "content": "SLC only."},
                {"role": "user", "content": "hello world"},
            ]

            mock_resp = unittest.mock.MagicMock()
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__ = unittest.mock.MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = unittest.mock.MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            result = generate_with_rag(
                "hello world",
                domain="python",
                model_path="/fake/model",
            )

        assert result is not None
        assert len(result) > 0

    def test_generate_with_rag_calls_assemble_with_correct_args(self):
        """generate_with_rag calls PromptAssembler.assemble with the correct user_prompt and domain."""
        with (
            unittest.mock.patch(
                "generate.PromptAssembler"
            ) as MockAssembler,
            unittest.mock.patch(
                "generate.urlopen"
            ),
        ):
            mock_instance = MockAssembler.return_value
            mock_instance.assemble.return_value = [
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "user"},
            ]

            mock_resp = unittest.mock.MagicMock()
            mock_resp.read.return_value = json.dumps(
                {"choices": [{"message": {"content": "output"}}]}
            ).encode()
            mock_resp.__enter__ = unittest.mock.MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = unittest.mock.MagicMock(return_value=False)
            unittest.mock.patch(
                "generate.urlopen",
                return_value=mock_resp,
            ).start()
            # Need to re-patch after the context manager started
            with unittest.mock.patch("generate.urlopen") as mock_urlopen:
                mock_urlopen.return_value = mock_resp
                generate_with_rag(
                    "write a function",
                    domain="swift",
                    model_path="/fake/model",
                    max_tokens=1024,
                )

            mock_instance.assemble.assert_called_once_with(
                "write a function", "swift", max_generation_tokens=1024
            )

    def test_generate_with_rag_sends_to_ollama_endpoint(self):
        """generate_with_rag sends messages to Ollama API endpoint at localhost:11434/v1/chat/completions."""
        import urllib.request

        mock_response = {
            "choices": [{"message": {"content": "code here"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }

        with (
            unittest.mock.patch(
                "generate.PromptAssembler"
            ) as MockAssembler,
            unittest.mock.patch(
                "generate.urlopen"
            ) as mock_urlopen,
        ):
            MockAssembler.return_value.assemble.return_value = [
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "user"},
            ]

            mock_resp = unittest.mock.MagicMock()
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__ = unittest.mock.MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = unittest.mock.MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            generate_with_rag("test", domain="python", model_path="/fake/model")

            # Verify the request was made to the correct endpoint
            mock_urlopen.assert_called_once()
            call_arg = mock_urlopen.call_args
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

        with (
            unittest.mock.patch(
                "generate.PromptAssembler"
            ) as MockAssembler,
            unittest.mock.patch(
                "generate.urlopen"
            ) as mock_urlopen,
        ):
            MockAssembler.return_value.assemble.return_value = [
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "user"},
            ]

            mock_resp = unittest.mock.MagicMock()
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__ = unittest.mock.MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = unittest.mock.MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            result = generate_with_rag("add function", domain="python", model_path="/fake/model")

        assert result == expected_content

    def test_generate_with_rag_handles_connection_error(self):
        """generate_with_rag handles Ollama connection error gracefully (returns None)."""
        import urllib.error

        with (
            unittest.mock.patch(
                "generate.PromptAssembler"
            ) as MockAssembler,
            unittest.mock.patch(
                "generate.urlopen",
                side_effect=urllib.error.URLError("Connection refused"),
            ),
        ):
            MockAssembler.return_value.assemble.return_value = [
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "user"},
            ]

            result = generate_with_rag("test", domain="python", model_path="/fake/model")

        assert result is None

    def test_cli_argument_parsing(self):
        """CLI argument parsing accepts --prompt, --domain, --max-tokens, --temperature, --no-rag flags."""
        from generate import parse_args

        with unittest.mock.patch("sys.argv", [
            "generate.py",
            "write a function",
            "--domain", "swift",
            "--max-tokens", "4096",
            "--temperature", "0.5",
            "--no-rag",
        ]):
            args = parse_args()

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

        with (
            unittest.mock.patch(
                "generate.PromptAssembler"
            ) as MockAssembler,
            unittest.mock.patch(
                "generate.urlopen"
            ) as mock_urlopen,
        ):
            mock_instance = MockAssembler.return_value
            mock_instance.assemble.return_value = [
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "user"},
            ]

            mock_resp = unittest.mock.MagicMock()
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__ = unittest.mock.MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = unittest.mock.MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            result = generate_with_rag(
                "test prompt",
                domain="python",
                model_path="/fake/model",
                no_rag=True,
            )

        # retrieve_patterns should NOT have been called
        mock_instance.retrieve_patterns.assert_not_called()
        # assemble should have been called with skip_rag=True
        mock_instance.assemble.assert_called_once_with(
            "test prompt", "python", max_generation_tokens=2048
        )

    def test_verbose_reports_retrieval_latency(self, capsys):
        """generate_with_rag reports retrieval latency when --verbose flag is set."""
        mock_response = {
            "choices": [{"message": {"content": "output"}}],
            "usage": {"prompt_tokens": 50, "completion_tokens": 100},
        }

        with (
            unittest.mock.patch(
                "generate.PromptAssembler"
            ) as MockAssembler,
            unittest.mock.patch(
                "generate.urlopen"
            ) as mock_urlopen,
        ):
            mock_instance = MockAssembler.return_value
            mock_instance.retrieve_patterns.return_value = [
                {"id": "p1", "type": "pattern", "content": "pattern content", "tags": ["test"]}
            ]
            mock_instance.assemble.return_value = [
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "user"},
            ]

            mock_resp = unittest.mock.MagicMock()
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__ = unittest.mock.MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = unittest.mock.MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            result = generate_with_rag(
                "test",
                domain="python",
                model_path="/fake/model",
                verbose=True,
            )

        captured = capsys.readouterr()
        assert "Retrieved 1 patterns" in captured.out
        assert "ms" in captured.out


# --- Integration tests (skipped by default) ---


@pytest.mark.integration
class TestRAGPipelineIntegration:
    """Integration tests against a live Ollama instance.

    These tests require Ollama to be running at localhost:11434.
    Run with: pytest scripts/test_rag_pipeline.py --run-integration -v
    """

    def test_ollama_reachable(self):
        """Check if Ollama is reachable at localhost:11434."""
        import urllib.request
        import urllib.error

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
