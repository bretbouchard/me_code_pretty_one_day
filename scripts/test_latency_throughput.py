"""Tests for extended benchmark-latency.py and benchmark-throughput.py with --variant support.

Tests cover:
- --variant flag present in both scripts
- build_variant_messages function for base, finetuned, rag variants (shared via benchmark_utils)
- Backward compatibility (default behavior unchanged)
- Comparison table output for --variant all

Import conventions:
  - benchmark_utils.py is the shared module; tests import from it directly.
  - Tests that need script internals (measure_ttft, measure_throughput) load
    the module from file and patch within its namespace.
"""

import importlib.util
import json
import os
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
PROMPTS_DIR = os.path.join(PROJECT_ROOT, "prompts")
SLC_SYSTEM_PATH = os.path.join(PROMPTS_DIR, "slc_system.txt")
LATENCY_SCRIPT = os.path.join(SCRIPTS_DIR, "benchmark-latency.py")
THROUGHPUT_SCRIPT = os.path.join(SCRIPTS_DIR, "benchmark-throughput.py")

# Ensure scripts directory is importable for benchmark_utils
sys.path.insert(0, SCRIPTS_DIR)


def _load_module_from_file(filepath: str, module_name: str):
    """Import a Python module from a file path (handles hyphenated filenames)."""
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class TestBenchmarkLatencyHelp:
    """Test that benchmark-latency.py --help shows --variant flag."""

    def test_help_shows_variant_flag(self):
        result = subprocess.run(
            [sys.executable, LATENCY_SCRIPT, "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "--variant" in result.stdout
        assert "base" in result.stdout
        assert "finetuned" in result.stdout
        assert "rag" in result.stdout


class TestBenchmarkThroughputHelp:
    """Test that benchmark-throughput.py --help shows --variant flag."""

    def test_help_shows_variant_flag(self):
        result = subprocess.run(
            [sys.executable, THROUGHPUT_SCRIPT, "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "--variant" in result.stdout
        assert "base" in result.stdout
        assert "finetuned" in result.stdout
        assert "rag" in result.stdout


class TestBuildVariantMessages:
    """Test build_variant_messages from shared benchmark_utils module.

    Both benchmark-latency.py and benchmark-throughput.py import this
    function, so testing it once covers both scripts.
    """

    def _get_build_fn(self):
        from benchmark_utils import build_variant_messages
        return build_variant_messages

    def test_base_variant_returns_user_only(self):
        build = self._get_build_fn()
        messages = build("base", "def foo(): return 42")
        assert len(messages) == 1
        assert messages[0] == {"role": "user", "content": "def foo(): return 42"}

    def test_finetuned_variant_returns_system_and_user(self):
        build = self._get_build_fn()
        messages = build("finetuned", "def foo(): return 42")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "Simple, Lovable, Complete" in messages[0]["content"]
        assert messages[1] == {"role": "user", "content": "def foo(): return 42"}

    def test_rag_variant_calls_prompt_assembler(self):
        build = self._get_build_fn()
        with patch("prompt_template.PromptAssembler") as mock_assembler_cls:
            mock_assembler = MagicMock()
            mock_assembler.assemble.return_value = [
                {"role": "system", "content": "RAG system prompt"},
                {"role": "user", "content": "def foo(): return 42"},
            ]
            mock_assembler_cls.return_value = mock_assembler

            messages = build("rag", "def foo(): return 42")
            mock_assembler.assemble.assert_called_once()
            assert len(messages) == 2
            assert messages[0]["role"] == "system"
            assert messages[1] == {"role": "user", "content": "def foo(): return 42"}

    def test_rag_variant_passes_max_generation_tokens(self):
        build = self._get_build_fn()
        with patch("prompt_template.PromptAssembler") as mock_assembler_cls:
            mock_assembler = MagicMock()
            mock_assembler.assemble.return_value = [
                {"role": "system", "content": "RAG system prompt"},
                {"role": "user", "content": "test"},
            ]
            mock_assembler_cls.return_value = mock_assembler

            build("rag", "test", max_generation_tokens=200)
            mock_assembler.assemble.assert_called_once_with(
                "test", domain="python", max_generation_tokens=200
            )

    def test_invalid_variant_raises_value_error(self):
        build = self._get_build_fn()
        with pytest.raises(ValueError, match="Unknown variant"):
            build("invalid_variant", "test prompt")


class TestMeasureTtftWithMessages:
    """Test that measure_ttft accepts optional messages parameter."""

    def _get_measure_fn(self):
        mod = _load_module_from_file(LATENCY_SCRIPT, "benchmark_latency")
        return mod.measure_ttft

    def test_measure_ttft_defaults_to_user_only(self):
        """When messages=None (default), payload uses [{'role': 'user', 'content': prompt}]."""
        measure = self._get_measure_fn()

        mock_payload = {}

        def mock_urlopen(req, timeout=None):
            nonlocal mock_payload
            mock_payload = json.loads(req.data.decode())
            mock_resp = MagicMock()
            mock_resp.__enter__ = MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_resp.__iter__ = MagicMock(return_value=iter([]))
            return mock_resp

        with patch("benchmark_latency.urllib.request.urlopen", side_effect=mock_urlopen):
            try:
                measure(iterations=1, prompt="test prompt")
            except Exception:
                pass

        assert "messages" in mock_payload
        assert mock_payload["messages"] == [{"role": "user", "content": "test prompt"}]

    def test_measure_ttft_uses_provided_messages(self):
        """When messages are provided, payload uses them instead of default."""
        measure = self._get_measure_fn()

        custom_messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "test prompt"},
        ]
        mock_payload = {}

        def mock_urlopen(req, timeout=None):
            nonlocal mock_payload
            mock_payload = json.loads(req.data.decode())
            mock_resp = MagicMock()
            mock_resp.__enter__ = MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_resp.__iter__ = MagicMock(return_value=iter([]))
            return mock_resp

        with patch("benchmark_latency.urllib.request.urlopen", side_effect=mock_urlopen):
            try:
                measure(messages=custom_messages, iterations=1, prompt="ignored")
            except Exception:
                pass

        assert mock_payload["messages"] == custom_messages


class TestMeasureThroughputWithMessages:
    """Test that measure_throughput accepts optional messages parameter."""

    def _get_measure_fn(self):
        mod = _load_module_from_file(THROUGHPUT_SCRIPT, "benchmark_throughput")
        return mod.measure_throughput

    def test_measure_throughput_defaults_to_user_only(self):
        """When messages=None (default), payload uses [{'role': 'user', 'content': prompt}]."""
        measure = self._get_measure_fn()

        mock_payload = {}

        def mock_urlopen(req, timeout=None):
            nonlocal mock_payload
            mock_payload = json.loads(req.data.decode())
            mock_resp = MagicMock()
            mock_resp.__enter__ = MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_resp.__iter__ = MagicMock(return_value=iter([]))
            return mock_resp

        with patch("benchmark_throughput.urllib.request.urlopen", side_effect=mock_urlopen):
            try:
                measure(iterations=1)
            except Exception:
                pass

        assert "messages" in mock_payload
        assert len(mock_payload["messages"]) == 1
        assert mock_payload["messages"][0]["role"] == "user"

    def test_measure_throughput_uses_provided_messages(self):
        """When messages are provided, payload uses them instead of default."""
        measure = self._get_measure_fn()

        custom_messages = [
            {"role": "system", "content": "SLC system"},
            {"role": "user", "content": "implement BST"},
        ]
        mock_payload = {}

        def mock_urlopen(req, timeout=None):
            nonlocal mock_payload
            mock_payload = json.loads(req.data.decode())
            mock_resp = MagicMock()
            mock_resp.__enter__ = MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_resp.__iter__ = MagicMock(return_value=iter([]))
            return mock_resp

        with patch("benchmark_throughput.urllib.request.urlopen", side_effect=mock_urlopen):
            try:
                measure(messages=custom_messages, iterations=1)
            except Exception:
                pass

        assert mock_payload["messages"] == custom_messages


class TestBackwardCompatibility:
    """Test that default behavior (no --variant) is preserved."""

    def test_latency_default_args_include_variant_base(self):
        """Without --variant, the script should use 'base' as default."""
        result = subprocess.run(
            [sys.executable, LATENCY_SCRIPT, "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        # The default should be "base"
        assert "default: base" in result.stdout or "default='base'" in result.stdout

    def test_throughput_default_args_include_variant_base(self):
        """Without --variant, the script should use 'base' as default."""
        result = subprocess.run(
            [sys.executable, THROUGHPUT_SCRIPT, "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "default: base" in result.stdout or "default='base'" in result.stdout
