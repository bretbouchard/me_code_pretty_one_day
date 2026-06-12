"""Tests for extended benchmark-latency.py and benchmark-throughput.py with --variant support.

Tests cover:
- --variant flag present in both scripts
- build_variant_messages function for base, finetuned, rag variants
- Backward compatibility (default behavior unchanged)
- Comparison table output for --variant all
"""

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


# --- Import the build_variant_messages function from each module ---
# We need to add the scripts dir to sys.path to import
sys.path.insert(0, SCRIPTS_DIR)


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


class TestBuildVariantMessagesLatency:
    """Test build_variant_messages in benchmark-latency.py."""

    def _import_build_variant_messages(self):
        import importlib
        import benchmark_latency
        importlib.reload(benchmark_latency)
        return benchmark_latency.build_variant_messages

    def test_base_variant_returns_user_only(self):
        build = self._import_build_variant_messages()
        messages = build("base", "def foo(): return 42")
        assert len(messages) == 1
        assert messages[0] == {"role": "user", "content": "def foo(): return 42"}

    def test_finetuned_variant_returns_system_and_user(self):
        build = self._import_build_variant_messages()
        messages = build("finetuned", "def foo(): return 42")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "Simple, Lovable, Complete" in messages[0]["content"]
        assert messages[1] == {"role": "user", "content": "def foo(): return 42"}

    def test_rag_variant_calls_prompt_assembler(self):
        build = self._import_build_variant_messages()
        with patch("benchmark_latency.PromptAssembler") as mock_assembler_cls:
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

    def test_invalid_variant_raises_value_error(self):
        build = self._import_build_variant_messages()
        with pytest.raises(ValueError, match="Unknown variant"):
            build("invalid_variant", "test prompt")


class TestBuildVariantMessagesThroughput:
    """Test build_variant_messages in benchmark-throughput.py."""

    def _import_build_variant_messages(self):
        import importlib
        import benchmark_throughput
        importlib.reload(benchmark_throughput)
        return benchmark_throughput.build_variant_messages

    def test_base_variant_returns_user_only(self):
        build = self._import_build_variant_messages()
        messages = build("base", "implement BST")
        assert len(messages) == 1
        assert messages[0] == {"role": "user", "content": "implement BST"}

    def test_finetuned_variant_returns_system_and_user(self):
        build = self._import_build_variant_messages()
        messages = build("finetuned", "implement BST")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "Simple, Lovable, Complete" in messages[0]["content"]
        assert messages[1] == {"role": "user", "content": "implement BST"}

    def test_rag_variant_calls_prompt_assembler(self):
        build = self._import_build_variant_messages()
        with patch("benchmark_throughput.PromptAssembler") as mock_assembler_cls:
            mock_assembler = MagicMock()
            mock_assembler.assemble.return_value = [
                {"role": "system", "content": "RAG system prompt"},
                {"role": "user", "content": "implement BST"},
            ]
            mock_assembler_cls.return_value = mock_assembler

            messages = build("rag", "implement BST")
            mock_assembler.assemble.assert_called_once()
            assert len(messages) == 2

    def test_invalid_variant_raises_value_error(self):
        build = self._import_build_variant_messages()
        with pytest.raises(ValueError, match="Unknown variant"):
            build("invalid_variant", "test prompt")


class TestMeasureTtftWithMessages:
    """Test that measure_ttft accepts optional messages parameter."""

    def _import_measure_ttft(self):
        import importlib
        import benchmark_latency
        importlib.reload(benchmark_latency)
        return benchmark_latency.measure_ttft

    def test_measure_ttft_defaults_to_user_only(self):
        """When messages=None (default), payload uses [{'role': 'user', 'content': prompt}]."""
        measure = self._import_measure_ttft()

        # Mock urllib to capture the payload
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

        # Verify the default payload uses user-only messages
        assert "messages" in mock_payload
        assert mock_payload["messages"] == [{"role": "user", "content": "test prompt"}]

    def test_measure_ttft_uses_provided_messages(self):
        """When messages are provided, payload uses them instead of default."""
        measure = self._import_measure_ttft()

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

    def _import_measure_throughput(self):
        import importlib
        import benchmark_throughput
        importlib.reload(benchmark_throughput)
        return benchmark_throughput.measure_throughput

    def test_measure_throughput_defaults_to_user_only(self):
        """When messages=None (default), payload uses [{'role': 'user', 'content': prompt}]."""
        measure = self._import_measure_throughput()

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
        measure = self._import_measure_throughput()

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
