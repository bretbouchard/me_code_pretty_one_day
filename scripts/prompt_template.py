"""Prompt assembler: SLC system prompt + Confucius RAG retrieval + token budget management.

Assembles chat messages for code generation by combining:
1. SLC coding standards (from prompts/slc_system.txt)
2. Domain-specific patterns retrieved from Confucius CLI
3. User prompt

All within the model's context window budget (default 32768 tokens for Qwen2.5-Coder-7B).
"""

import json
import os
import re
import subprocess

from transformers import AutoTokenizer

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPTS_DIR = os.path.join(PROJECT_ROOT, "prompts")
SLC_SYSTEM_PATH = os.path.join(PROMPTS_DIR, "slc_system.txt")
DOMAINS_PATH = os.path.join(PROMPTS_DIR, "domains.json")

MAX_CONTENT_LENGTH_PER_PATTERN = 500


def load_domains_mapping() -> dict:
    """Load and return the domain-to-query mapping from prompts/domains.json."""
    with open(DOMAINS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _sanitize_content(content: str, max_length: int = MAX_CONTENT_LENGTH_PER_PATTERN) -> str:
    """Sanitize confucius output before injection into system prompt.

    Strips control characters and truncates to max_length.
    """
    # Remove control characters except newline, tab
    sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", content)
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    return sanitized.strip()


class PromptAssembler:
    """Assembles system prompts with SLC standards + RAG context within token budget.

    Token budget analysis (verified via tokenizer):
    - SLC system prompt: ~196 tokens
    - Per RAG pattern: ~32 tokens (avg content length / token ratio)
    - 5 patterns: ~160 tokens
    - User prompt: ~40 tokens (avg)
    - Chat template overhead: ~10 tokens
    - Total input: ~406 tokens
    - Context window: 32,768 tokens
    - Remaining for generation: ~32,362 tokens (no pressure)
    """

    def __init__(self, model_path: str, max_context: int = 32768):
        """Initialize assembler with tokenizer and configuration files.

        Args:
            model_path: Path to the model directory containing tokenizer config.
            max_context: Maximum context window size in tokens (default: 32768 for Qwen2.5-Coder-7B).
        """
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path, trust_remote_code=True
        )
        self.max_context = max_context
        self.slc_prompt = self._load_slc_prompt()
        self.domains = load_domains_mapping()

    def _load_slc_prompt(self) -> str:
        """Load SLC system prompt from file."""
        with open(SLC_SYSTEM_PATH, "r", encoding="utf-8") as f:
            return f.read()

    def retrieve_patterns(self, domain: str, limit: int = 5) -> list[dict]:
        """Retrieve domain-specific patterns from Confucius via CLI.

        Looks up the domain in the domains mapping to find search queries.
        Tries queries sequentially until results are found. Returns empty
        list on timeout, parse failure, or no results (graceful degradation).

        Args:
            domain: Domain tag (e.g. "swift", "python") or raw query string.
            limit: Maximum number of patterns to return.

        Returns:
            List of pattern dicts with keys: id, type, content, tags.
        """
        # Resolve domain to queries
        queries = []
        if domain in self.domains:
            queries = self.domains[domain].get("queries", [])
        if not queries:
            queries = [domain]

        # Try each query until we find results
        for query in queries:
            try:
                result = subprocess.run(
                    ["confucius", "search", query, "--limit", str(limit)],
                    capture_output=True, text=True, timeout=10,
                )

                # Parse search output: extract pattern IDs from ### headers
                pattern_ids = []
                for line in result.stdout.strip().split("\n"):
                    if line.startswith("### "):
                        pid = line[4:].rstrip("...")
                        pattern_ids.append(pid)

                if not pattern_ids:
                    continue

                # Get full content for each pattern via confucius get
                patterns = []
                for pid in pattern_ids[:limit]:
                    try:
                        get_result = subprocess.run(
                            ["confucius", "get", pid],
                            capture_output=True, text=True, timeout=10,
                        )
                        data = json.loads(get_result.stdout)
                        content = _sanitize_content(data.get("content", ""))
                        if content:
                            patterns.append({
                                "id": data.get("id", pid),
                                "type": data.get("type", "pattern"),
                                "content": content,
                                "tags": data.get("metadata", {}).get("tags", []),
                            })
                    except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError):
                        continue

                if patterns:
                    return patterns

            except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError):
                continue

        return []

    def assemble(
        self,
        user_prompt: str,
        domain: str = "python",
        max_generation_tokens: int = 2048,
        skip_rag: bool = False,
    ) -> list[dict]:
        """Build chat messages with system+RAG+user within context budget.

        Retrieves RAG patterns for the domain (unless skip_rag is True),
        combines with SLC system prompt and user prompt, then checks token
        budget. If the combined prompt exceeds the context window minus
        generation tokens, patterns are iteratively removed from the end
        until budget fits.

        Args:
            user_prompt: The user's code generation request.
            domain: Domain tag for RAG retrieval (e.g. "swift", "python").
            max_generation_tokens: Tokens reserved for model output.
            skip_rag: If True, skip Confucius retrieval and use SLC prompt only.

        Returns:
            List of message dicts with "role" and "content" keys.
            Always returns at least [system_message, user_message].
        """
        patterns = [] if skip_rag else self.retrieve_patterns(domain)

        # Build RAG section
        rag_section = ""
        if patterns:
            rag_section = "## Retrieved Patterns\n\n"
            for p in patterns:
                rag_section += f"### {p.get('type', 'pattern').title()}\n"
                rag_section += p.get("content", "") + "\n\n"

        # Combine system prompt
        system_content = self.slc_prompt + "\n\n" + rag_section

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_prompt},
        ]

        # Token budget check
        tokenized = self.tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=True
        )

        while (len(tokenized) + max_generation_tokens > self.max_context
               and patterns):
            patterns.pop()
            rag_section = ""
            if patterns:
                rag_section = "## Retrieved Patterns\n\n"
                for p in patterns:
                    rag_section += f"### {p.get('type', 'pattern').title()}\n"
                    rag_section += p.get("content", "") + "\n\n"

            system_content = self.slc_prompt + "\n\n" + rag_section
            messages = [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_prompt},
            ]
            tokenized = self.tokenizer.apply_chat_template(
                messages, add_generation_prompt=True, tokenize=True
            )

        return messages
