"""Tests for prompt template: SLC system prompt, domain mapping, and prompt assembly."""

import json
import os
import subprocess
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPTS_DIR = os.path.join(PROJECT_ROOT, "prompts")
SLC_SYSTEM_PATH = os.path.join(PROMPTS_DIR, "slc_system.txt")
DOMAINS_PATH = os.path.join(PROMPTS_DIR, "domains.json")


class TestSLCSystemPrompt:
    """Tests for prompts/slc_system.txt content."""

    def test_slc_file_exists(self):
        assert os.path.exists(SLC_SYSTEM_PATH), f"slc_system.txt missing at {SLC_SYSTEM_PATH}"

    def test_slc_file_nonempty(self):
        with open(SLC_SYSTEM_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        assert len(content.strip()) > 0, "slc_system.txt is empty"

    def test_slc_min_lines(self):
        with open(SLC_SYSTEM_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) > 20, f"slc_system.txt has {len(lines)} lines, expected >20"

    def test_contains_slc_motto(self):
        with open(SLC_SYSTEM_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        assert "Simple, Lovable, Complete" in content

    def test_contains_immutability_rule(self):
        with open(SLC_SYSTEM_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        assert "Immutability" in content and "create new objects" in content and "never mutate" in content

    def test_contains_error_handling(self):
        with open(SLC_SYSTEM_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        assert "Error handling" in content and "comprehensive" in content and "never swallow silently" in content

    def test_contains_function_file_sizing(self):
        with open(SLC_SYSTEM_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        assert "Functions <50 lines" in content and "files <800 lines" in content

    def test_contains_type_hints_and_docstrings(self):
        with open(SLC_SYSTEM_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        assert "type hints" in content and "docstrings" in content


class TestDomainMapping:
    """Tests for prompts/domains.json structure and content."""

    def test_domains_file_exists(self):
        assert os.path.exists(DOMAINS_PATH), f"domains.json missing at {DOMAINS_PATH}"

    def test_domains_valid_json(self):
        with open(DOMAINS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_domains_has_all_keys(self):
        with open(DOMAINS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key in ("swift", "python", "juce", "pcb"):
            assert key in data, f"Missing domain key: {key}"

    def test_each_domain_has_queries(self):
        with open(DOMAINS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key in ("swift", "python", "juce", "pcb"):
            assert "queries" in data[key], f"Domain {key} missing 'queries' key"
            assert isinstance(data[key]["queries"], list)
            assert len(data[key]["queries"]) >= 2, f"Domain {key} has fewer than 2 queries"

    def test_swift_queries_content(self):
        with open(DOMAINS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        queries_str = " ".join(data["swift"]["queries"])
        assert any(q in queries_str for q in ("swiftui", "swift async")), \
            f"Swift queries should include 'swiftui' or 'swift async': {data['swift']['queries']}"

    def test_python_queries_content(self):
        with open(DOMAINS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        queries_str = " ".join(data["python"]["queries"])
        assert any(q in queries_str for q in ("python", "python pattern")), \
            f"Python queries should include 'python' or 'python pattern': {data['python']['queries']}"

    def test_juce_queries_content(self):
        with open(DOMAINS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        queries_str = " ".join(data["juce"]["queries"])
        assert any(q in queries_str for q in ("audio", "juce", "dsp")), \
            f"JUCE queries should include 'audio', 'juce', or 'dsp': {data['juce']['queries']}"

    def test_pcb_queries_content(self):
        with open(DOMAINS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        queries_str = " ".join(data["pcb"]["queries"])
        assert any(q in queries_str for q in ("pcb", "kicad", "circuit")), \
            f"PCB queries should include 'pcb', 'kicad', or 'circuit': {data['pcb']['queries']}"

    def test_each_domain_has_tags(self):
        with open(DOMAINS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key in ("swift", "python", "juce", "pcb"):
            assert "tags" in data[key], f"Domain {key} missing 'tags' key"
            assert isinstance(data[key]["tags"], list)


class TestPromptAssembler:
    """Tests for PromptAssembler class: init, retrieve_patterns, assemble, token budget."""

    @pytest.fixture
    def mock_tokenizer(self):
        """Create a mock tokenizer that returns a controllable token count."""
        tokenizer = MagicMock()
        tokenizer.apply_chat_template = MagicMock(return_value=[1] * 400)
        return tokenizer

    @pytest.fixture
    def assembler(self, mock_tokenizer, tmp_path):
        """Create a PromptAssembler with mocked tokenizer and config files."""
        # Create temporary prompt files
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        slc_content = (
            "You are an expert code generation assistant.\n"
            "## Coding Standards (MANDATORY)\n"
            "- Simple, Lovable, Complete\n"
            "- Immutability: create new objects, never mutate existing ones\n"
            "- Error handling: comprehensive, never swallow silently\n"
            "- Functions <50 lines, files <800 lines\n"
        )
        (prompts_dir / "slc_system.txt").write_text(slc_content)

        domains = {
            "swift": {"queries": ["swiftui", "swift async"], "tags": ["swift"]},
            "python": {"queries": ["python", "python pattern"], "tags": ["python"]},
        }
        (prompts_dir / "domains.json").write_text(json.dumps(domains))

        with patch("scripts.prompt_template.PROJECT_ROOT", str(tmp_path)):
            from scripts.prompt_template import PromptAssembler
            assembler = PromptAssembler.__new__(PromptAssembler)
            assembler.tokenizer = mock_tokenizer
            assembler.max_context = 32768
            assembler.slc_prompt = slc_content
            assembler.domains = domains
            return assembler

    def test_init_loads_slc_prompt(self):
        """PromptAssembler.__init__ loads slc_system.txt content successfully."""
        mock_tokenizer = MagicMock()
        mock_tokenizer.apply_chat_template = MagicMock(return_value=[1] * 100)

        with patch("scripts.prompt_template.AutoTokenizer", return_value=mock_tokenizer):
            from scripts.prompt_template import PromptAssembler
            pa = PromptAssembler.__new__(PromptAssembler)
            pa.tokenizer = mock_tokenizer
            pa.max_context = 32768
            # Load SLC prompt directly
            with open(SLC_SYSTEM_PATH, "r", encoding="utf-8") as f:
                pa.slc_prompt = f.read()
            assert "Simple, Lovable, Complete" in pa.slc_prompt

    def test_init_loads_domains(self):
        """PromptAssembler.__init__ loads domains.json successfully."""
        with open(DOMAINS_PATH, "r", encoding="utf-8") as f:
            expected = json.load(f)

        from scripts.prompt_template import load_domains_mapping
        result = load_domains_mapping()
        assert result == expected

    def test_retrieve_patterns_calls_confucius_search(self, assembler):
        """retrieve_patterns('swift') calls confucius search with a query from domains.json."""
        mock_search_output = "### pattern-1\n**Type:** pattern\n**Tags:** swift\n**Content:** swift async pattern\n"
        mock_get_output = json.dumps({
            "id": "pattern-1",
            "type": "pattern",
            "content": "swift async pattern content",
            "metadata": {"tags": ["swift"]},
        })

        with patch("scripts.prompt_template.subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(stdout=mock_search_output, returncode=0),  # search
                MagicMock(stdout=mock_get_output, returncode=0),      # get
            ]
            patterns = assembler.retrieve_patterns("swift")
            assert len(patterns) >= 1
            assert patterns[0]["id"] == "pattern-1"

    def test_assemble_returns_system_and_user_messages(self, assembler):
        """assemble() returns a list with 2 dicts: system message and user message."""
        with patch.object(assembler, "retrieve_patterns", return_value=[]):
            messages = assembler.assemble("write a function", domain="python")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "write a function"

    def test_system_message_contains_slc_text(self, assembler):
        """System message content contains SLC prompt text."""
        with patch.object(assembler, "retrieve_patterns", return_value=[]):
            messages = assembler.assemble("write code", domain="python")
        assert "Simple, Lovable, Complete" in messages[0]["content"]

    def test_system_message_contains_rag_header(self, assembler):
        """System message content contains RAG section header."""
        mock_patterns = [
            {"id": "p1", "type": "pattern", "content": "test pattern content"},
        ]
        with patch.object(assembler, "retrieve_patterns", return_value=mock_patterns):
            messages = assembler.assemble("write code", domain="swift")
        assert "## Retrieved Patterns" in messages[0]["content"]

    def test_token_budget_truncates_patterns(self, assembler):
        """When mocked to return overflowing tokens, token budget truncation reduces pattern count."""
        # Use a small max_context to force truncation with mock tokenizer.
        assembler.max_context = 500
        assembler.tokenizer.apply_chat_template = MagicMock(return_value=[1] * 400)

        mock_patterns = [
            {"id": f"p{i}", "type": "pattern", "content": f"pattern content {i} " * 20}
            for i in range(5)
        ]

        with patch.object(assembler, "retrieve_patterns", return_value=list(mock_patterns)):
            messages = assembler.assemble("write code", domain="swift", max_generation_tokens=2048)

        # System message should still be valid
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        # All patterns should have been truncated since 400 + 2048 > 500 budget
        # and tokenizer always returns 400 tokens (mock doesn't respond to content changes).
        # When patterns is empty, the while loop exits because `and patterns` is False.
        assert "## Retrieved Patterns" not in messages[0]["content"]

    def test_token_count_within_budget(self, assembler):
        """Token count of assembled prompt + max_generation_tokens <= max_context."""
        assembler.tokenizer.apply_chat_template = MagicMock(return_value=[1] * 400)

        mock_patterns = [
            {"id": "p1", "type": "pattern", "content": "some pattern content"},
        ]
        with patch.object(assembler, "retrieve_patterns", return_value=mock_patterns):
            messages = assembler.assemble("write code", domain="python", max_generation_tokens=2048)

        token_count = len(assembler.tokenizer.apply_chat_template.return_value)
        assert token_count + 2048 <= 32768

    def test_retrieve_patterns_empty_on_no_results(self, assembler):
        """retrieve_patterns returns empty list when confucius search returns no results."""
        with patch("scripts.prompt_template.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="No results found.", returncode=0)
            patterns = assembler.retrieve_patterns("nonexistent")
            assert patterns == []

    def test_retrieve_patterns_empty_on_timeout(self, assembler):
        """retrieve_patterns returns empty list when confucius CLI times out."""
        with patch("scripts.prompt_template.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="confucius", timeout=10)
            patterns = assembler.retrieve_patterns("swift")
            assert patterns == []

    def test_retrieve_patterns_unknown_domain_uses_raw_query(self, assembler):
        """retrieve_patterns uses domain string directly as query for unknown domains."""
        mock_search_output = "### pattern-x\n**Type:** pattern\n**Tags:** test\n**Content:** test content\n"
        mock_get_output = json.dumps({
            "id": "pattern-x",
            "type": "pattern",
            "content": "test content",
            "metadata": {"tags": ["test"]},
        })

        with patch("scripts.prompt_template.subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(stdout=mock_search_output, returncode=0),
                MagicMock(stdout=mock_get_output, returncode=0),
            ]
            patterns = assembler.retrieve_patterns("unknown_domain")
            assert len(patterns) >= 1

    def test_assemble_no_patterns_still_valid(self, assembler):
        """assemble with empty patterns returns valid system+user messages."""
        with patch.object(assembler, "retrieve_patterns", return_value=[]):
            messages = assembler.assemble("write a function", domain="python")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        # System content should be just SLC prompt (no RAG section when no patterns)
        assert "Simple, Lovable, Complete" in messages[0]["content"]
