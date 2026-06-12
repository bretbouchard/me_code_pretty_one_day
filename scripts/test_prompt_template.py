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
    # Tests for Task 2 -- will be implemented in Task 2
    pass
