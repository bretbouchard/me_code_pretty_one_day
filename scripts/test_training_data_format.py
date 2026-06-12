"""Tests for training data JSONL format — structure, roles, content, no ChatML tokens."""

import json
import os

import pytest

from conftest import TRAIN_FILE, VALID_FILE

VALID_ROLES = {"system", "user", "assistant"}
CHATML_TOKENS = ["<|im_start|>", "<|im_end|>"]

SAMPLE_SIZE = 100


def _get_sample_lines(filepath: str, count: int = SAMPLE_SIZE):
    """Yield up to `count` (index, parsed_json) tuples from a JSONL file."""
    if not os.path.exists(filepath):
        pytest.skip(f"{os.path.basename(filepath)} does not exist yet")
    with open(filepath, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= count:
                break
            line = line.strip()
            if line:
                yield i, json.loads(line)


@pytest.mark.parametrize("filepath", [TRAIN_FILE, VALID_FILE])
class TestLineIsValidJSON:
    def test_each_line_valid_json(self, filepath):
        errors = []
        with open(filepath, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= SAMPLE_SIZE:
                    break
                line = line.strip()
                if line:
                    try:
                        json.loads(line)
                    except json.JSONDecodeError as e:
                        errors.append(f"Line {i}: {e}")
        assert not errors, f"Invalid JSON on {len(errors)} lines: {errors[:5]}"


@pytest.mark.parametrize("filepath", [TRAIN_FILE, VALID_FILE])
class TestMessagesStructure:
    def test_messages_key_exists(self, filepath):
        for idx, example in _get_sample_lines(filepath):
            assert "messages" in example, f"Line {idx}: missing 'messages' key"

    def test_messages_is_list(self, filepath):
        for idx, example in _get_sample_lines(filepath):
            assert isinstance(example.get("messages"), list), f"Line {idx}: messages is not a list"

    def test_message_roles_valid(self, filepath):
        for idx, example in _get_sample_lines(filepath):
            for j, msg in enumerate(example["messages"]):
                assert msg.get("role") in VALID_ROLES, (
                    f"Line {idx}, msg {j}: invalid role '{msg.get('role')}'"
                )

    def test_message_content_nonempty(self, filepath):
        for idx, example in _get_sample_lines(filepath):
            for j, msg in enumerate(example["messages"]):
                content = msg.get("content", "")
                assert isinstance(content, str) and len(content.strip()) > 0, (
                    f"Line {idx}, msg {j}: empty or non-string content"
                )

    def test_last_message_is_assistant(self, filepath):
        for idx, example in _get_sample_lines(filepath):
            last_role = example["messages"][-1].get("role")
            assert last_role == "assistant", f"Line {idx}: last message role is '{last_role}', expected 'assistant'"

    def test_system_message_present(self, filepath):
        for idx, example in _get_sample_lines(filepath):
            first_role = example["messages"][0].get("role")
            assert first_role == "system", f"Line {idx}: first message role is '{first_role}', expected 'system'"


@pytest.mark.parametrize("filepath", [TRAIN_FILE, VALID_FILE])
class TestNoRawChatMLTokens:
    def test_no_raw_chatml_tokens(self, filepath):
        violations = []
        for idx, example in _get_sample_lines(filepath):
            for j, msg in enumerate(example.get("messages", [])):
                content = str(msg.get("content", ""))
                for token in CHATML_TOKENS:
                    if token in content:
                        violations.append(f"Line {idx}, msg {j}: contains '{token}'")
        assert not violations, f"ChatML token violations: {violations[:5]}"
