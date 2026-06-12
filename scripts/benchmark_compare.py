#!/usr/bin/env python3
"""
Benchmark comparison: base model vs fine-tuned model.

Runs validation or formatting prompts against both models, measures generation
time, response length, and code quality heuristics (syntax, docstrings, type hints,
formatting quality). Produces a comparison table with improvement percentages.

Two modes:
  Server mode (default): Requires both servers running.
    - Base model:     python3 scripts/serve-mlx.py           (port 8800)
    - Fine-tuned:      python3 scripts/serve_finetuned.py      (port 8801)
  Inline mode (--inline): Uses mlx_lm.generate directly, no servers needed.
    Recommended when Ollama proxy conflicts with server ports.

Prompt sets:
  --prompts-file data/valid.jsonl          Coding problems (default)
  --prompts-file data/formatting_test_prompts.jsonl  Formatting tasks
"""

import argparse
import ast
import json
import os
import statistics
import subprocess
import sys
import time
import urllib.request
import urllib.error

try:
    import mlx_lm
except ImportError:
    mlx_lm = None


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_BASE_URL = "http://localhost:8800"
DEFAULT_FT_URL = "http://localhost:8801"
DEFAULT_PROMPTS_FILE = os.path.join(PROJECT_ROOT, "data", "valid.jsonl")
DEFAULT_FORMATTING_FILE = os.path.join(PROJECT_ROOT, "data", "formatting_test_prompts.jsonl")
DEFAULT_MODEL = os.path.join(PROJECT_ROOT, "models", "qwen2.5-coder-7b-instruct-4bit-mlx")
DEFAULT_ADAPTER = os.path.join(PROJECT_ROOT, "training", "adapters-600")
DEFAULT_NUM_PROMPTS = 20
DEFAULT_MAX_TOKENS = 256


def discover_model_id(base_url: str) -> str | None:
    """Query /v1/models to discover the model ID used by mlx_lm.server.

    mlx_lm.server uses the full model path as the model ID in API calls.
    """
    try:
        url = f"{base_url}/v1/models"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode())
                models = data.get("data", [])
                if models:
                    return models[0].get("id")
    except (urllib.error.URLError, ConnectionRefusedError, OSError, json.JSONDecodeError):
        pass
    return None


def load_prompts(prompts_file: str, num_prompts: int) -> list[str]:
    """Load user messages from validation JSONL file."""
    prompts = []
    if not os.path.isfile(prompts_file):
        print(f"ERROR: Prompts file not found: {prompts_file}", file=sys.stderr)
        print("Run training data generation first: python3 scripts/generate_training_data.py", file=sys.stderr)
        sys.exit(1)

    with open(prompts_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                messages = record.get("messages", [])
                for msg in messages:
                    if msg.get("role") == "user":
                        prompts.append(msg["content"])
                        break
            except json.JSONDecodeError:
                continue
            if len(prompts) >= num_prompts:
                break

    if not prompts:
        print(f"ERROR: No user prompts found in {prompts_file}", file=sys.stderr)
        sys.exit(1)

    return prompts[:num_prompts]


def generate(base_url: str, model_id: str, prompt: str, max_tokens: int) -> dict:
    """Send a non-streaming completion request and return timing + content."""
    endpoint = f"{base_url}/v1/chat/completions"
    payload = json.dumps({
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "stream": False,
    }).encode()

    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            elapsed = time.perf_counter() - start
            data = json.loads(resp.read().decode())
            choice = data.get("choices", [{}])[0]
            content = choice.get("message", {}).get("content", "")
            usage = data.get("usage", {})
            return {
                "content": content,
                "elapsed_sec": elapsed,
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "error": False,
            }
    except (urllib.error.URLError, ConnectionRefusedError, OSError) as e:
        elapsed = time.perf_counter() - start
        return {
            "content": "",
            "elapsed_sec": elapsed,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "error": True,
            "error_msg": str(e),
        }


def extract_code_blocks(content: str) -> list[str]:
    """Extract code from markdown code blocks in the response."""
    blocks = []
    in_block = False
    current = []
    for line in content.split("\n"):
        if line.strip().startswith("```"):
            if in_block:
                blocks.append("\n".join(current))
                current = []
                in_block = False
            else:
                in_block = True
        elif in_block:
            current.append(line)
    return blocks


def check_python_syntax(code: str) -> bool:
    """Check if Python code can be parsed by ast.parse."""
    try:
        ast.parse(code)
        return True
    except (SyntaxError, ValueError):
        return False


def check_swift_syntax(code: str) -> bool:
    """Basic bracket/brace matching check for Swift code."""
    stack = []
    pairs = {"(": ")", "[": "]", "{": "}"}
    for ch in code:
        if ch in pairs:
            stack.append(ch)
        elif ch in pairs.values():
            if not stack:
                return False
            expected_open = [k for k, v in pairs.items() if v == ch][0]
            if stack[-1] != expected_open:
                return False
            stack.pop()
    return len(stack) == 0


def has_docstrings(code: str) -> bool:
    """Check if code contains a docstring (triple quotes)."""
    return '"""' in code or "'''" in code


def has_type_hints(code: str) -> bool:
    """Check if code contains type hints (colon annotations)."""
    return ": " in code and ("int" in code or "str" in code or "float" in code
           or "bool" in code or "list" in code or "dict" in code
           or "tuple" in code or "Any" in code or "Optional" in code)


def evaluate_quality(content: str) -> dict:
    """Evaluate code quality heuristics on the response."""
    code_blocks = extract_code_blocks(content)
    if not code_blocks:
        # No code blocks — evaluate the entire response
        code_blocks = [content]

    # Use the longest code block for evaluation
    primary_code = max(code_blocks, key=len)

    # Detect language
    is_python = "def " in primary_code or "import " in primary_code or "from " in primary_code
    is_swift = "func " in primary_code or "var " in primary_code or "let " in primary_code

    syntax_ok = False
    if is_python:
        syntax_ok = check_python_syntax(primary_code)
    elif is_swift:
        syntax_ok = check_swift_syntax(primary_code)

    return {
        "syntax_ok": syntax_ok,
        "has_docstrings": has_docstrings(primary_code),
        "has_type_hints": has_type_hints(primary_code),
        "response_length": len(content),
    }


def print_comparison_table(
    base_results: list[dict],
    ft_results: list[dict],
    base_times: list[float],
    ft_times: list[float],
    base_tokens: list[int],
    ft_tokens: list[int],
) -> None:
    """Print the comparison table and improvement summary."""
    # Quality metrics
    base_syntax = sum(1 for r in base_results if r["quality"]["syntax_ok"])
    ft_syntax = sum(1 for r in ft_results if r["quality"]["syntax_ok"])
    base_docs = sum(1 for r in base_results if r["quality"]["has_docstrings"])
    ft_docs = sum(1 for r in ft_results if r["quality"]["has_docstrings"])
    base_types = sum(1 for r in base_results if r["quality"]["has_type_hints"])
    ft_types = sum(1 for r in ft_results if r["quality"]["has_type_hints"])

    n = len(base_results)
    if n == 0:
        print("ERROR: No results to compare.", file=sys.stderr)
        return

    base_avg_time = statistics.mean(base_times) if base_times else 0
    ft_avg_time = statistics.mean(ft_times) if ft_times else 0
    base_avg_tokens = statistics.mean(base_tokens) if base_tokens else 0
    ft_avg_tokens = statistics.mean(ft_tokens) if ft_tokens else 0

    base_syntax_pct = (base_syntax / n) * 100
    ft_syntax_pct = (ft_syntax / n) * 100
    base_docs_pct = (base_docs / n) * 100
    ft_docs_pct = (ft_docs / n) * 100
    base_types_pct = (base_types / n) * 100
    ft_types_pct = (ft_types / n) * 100

    # Format accuracy (diff-based)
    base_fmt_accs = [r["format_accuracy"]["accuracy"] for r in base_results if "format_accuracy" in r]
    ft_fmt_accs = [r["format_accuracy"]["accuracy"] for r in ft_results if "format_accuracy" in r]
    base_fmt_exact = sum(1 for r in base_results if r.get("format_accuracy", {}).get("exact", False))
    ft_fmt_exact = sum(1 for r in ft_results if r.get("format_accuracy", {}).get("exact", False))
    base_fmt_avg = statistics.mean(base_fmt_accs) if base_fmt_accs else 0
    ft_fmt_avg = statistics.mean(ft_fmt_accs) if ft_fmt_accs else 0
    base_fmt_exact_pct = (base_fmt_exact / n) * 100
    ft_fmt_exact_pct = (ft_fmt_exact / n) * 100

    print()
    print(f"{'='*60}")
    print("  Base vs Fine-Tuned Comparison")
    print(f"{'='*60}")
    print()
    print(f"{'Model':<16} | {'Avg Time':>8} | {'Avg Tokens':>10} | {'Syntax OK':>9} | {'Fmt Acc':>8} | {'Exact':>6} | {'Has Docs':>9} | {'Has Types':>10}")
    print(f"{'-'*16}-+-{'-'*8}-+-{'-'*10}-+-{'-'*9}-+-{'-'*8}-+-{'-'*6}-+-{'-'*9}-+-{'-'*10}")
    print(f"{'base':<16} | {base_avg_time:>7.1f}s | {base_avg_tokens:>10.0f} | {base_syntax_pct:>8.0f}% | {base_fmt_avg:>7.0%} | {base_fmt_exact_pct:>5.0f}% | {base_docs_pct:>8.0f}% | {base_types_pct:>9.0f}%")
    print(f"{'fine-tuned':<16} | {ft_avg_time:>7.1f}s | {ft_avg_tokens:>10.0f} | {ft_syntax_pct:>8.0f}% | {ft_fmt_avg:>7.0%} | {ft_fmt_exact_pct:>5.0f}% | {ft_docs_pct:>8.0f}% | {ft_types_pct:>9.0f}%")
    print()

    # Improvement percentages
    print("Improvement (fine-tuned relative to base):")
    improvements = []

    if base_avg_time > 0:
        time_change = ((base_avg_time - ft_avg_time) / base_avg_time) * 100
        direction = "faster" if time_change > 0 else "slower"
        improvements.append(f"  Time:      {abs(time_change):+.1f}% ({direction})")

    if base_avg_tokens > 0:
        token_change = ((ft_avg_tokens - base_avg_tokens) / base_avg_tokens) * 100
        direction = "more" if token_change > 0 else "fewer"
        improvements.append(f"  Tokens:    {abs(token_change):+.1f}% ({direction} tokens)")

    if base_syntax_pct > 0:
        syntax_change = ft_syntax_pct - base_syntax_pct
        improvements.append(f"  Syntax OK: {syntax_change:+.1f}pp")

    if base_docs_pct > 0:
        docs_change = ft_docs_pct - base_docs_pct
        improvements.append(f"  Docs:      {docs_change:+.1f}pp")

    if base_types_pct > 0:
        types_change = ft_types_pct - base_types_pct
        improvements.append(f"  Types:     {types_change:+.1f}pp")

    if base_fmt_accs or ft_fmt_accs:
        fmt_change = (ft_fmt_avg - base_fmt_avg) * 100
        improvements.append(f"  Fmt Acc:   {fmt_change:+.1f}pp")
        improvements.append(f"  Exact:     {ft_fmt_exact_pct - base_fmt_exact_pct:+.0f}pp")

    for line in improvements:
        print(line)

    print()
    print(f"Prompts evaluated: {n}")


# --- Inline mode (no server required) ---

def _detect_language(code: str) -> str:
    """Detect programming language from code content."""
    if any(k in code for k in ["fn ", "pub ", "impl ", "struct ", "enum ", "use ", "#[derive"]):
        return "rust"
    if any(k in code for k in ["func ", "var ", "let ", "protocol ", "extension ", "struct "]):
        return "swift"
    if any(k in code for k in ["interface ", ": string", ": number", ": boolean", "=>", "<T>", "as Error"]):
        return "typescript"
    if any(k in code for k in ["const ", "function ", "class ", "async function", "module.exports", "=>"]):
        return "javascript"
    if any(k in code for k in ["def ", "import ", "from ", "@dataclass", "class ", "self."]):
        return "python"
    return "unknown"


def _format_code(code: str, lang: str) -> str:
    """Format code using the appropriate real formatter. Returns original on failure."""
    try:
        if lang == "python":
            proc = subprocess.run(
                ["black", "-", "--quiet", "--line-length=88"],
                input=code.encode("utf-8"), capture_output=True, timeout=10,
            )
            if proc.returncode == 0:
                return proc.stdout.decode("utf-8")
        elif lang in ("javascript", "typescript"):
            parser = "typescript" if lang == "typescript" else "babel"
            proc = subprocess.run(
                ["prettier", "--parser", parser, "--single-quote"],
                input=code.encode("utf-8"), capture_output=True, timeout=10,
            )
            if proc.returncode == 0:
                return proc.stdout.decode("utf-8")
        elif lang == "rust":
            proc = subprocess.run(
                ["rustfmt"], input=code.encode("utf-8"), capture_output=True, timeout=10,
            )
            if proc.returncode == 0:
                return proc.stdout.decode("utf-8")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return code


def _format_accuracy(content: str) -> dict:
    """Measure how closely model output matches real formatter output.

    Returns dict with:
      - accuracy: 0.0-1.0 (fraction of characters matching after normalization)
      - exact: bool (perfect match)
      - language: detected language
    """
    blocks = extract_code_blocks(content)
    if not blocks:
        return {"accuracy": 0.0, "exact": False, "language": "unknown"}
    code = max(blocks, key=len)
    lang = _detect_language(code)

    if lang == "unknown":
        return {"accuracy": 0.0, "exact": False, "language": lang}

    # Normalize model output (strip trailing whitespace per line)
    model_lines = [l.rstrip() for l in code.strip().splitlines()]

    # Get canonical formatting
    canonical = _format_code(code, lang)
    canonical_lines = [l.rstrip() for l in canonical.strip().splitlines()]

    # If model output is empty or canonical is empty
    if not model_lines or not canonical_lines:
        return {"accuracy": 0.0, "exact": False, "language": lang}

    # Compare line by line (handles different lengths gracefully)
    matching_chars = 0
    total_chars = 0
    for i in range(max(len(canonical_lines), len(model_lines))):
        canon_line = canonical_lines[i] if i < len(canonical_lines) else ""
        model_line = model_lines[i] if i < len(model_lines) else ""
        # Count matching characters
        for a, b in zip(canon_line, model_line):
            total_chars += 1
            if a == b:
                matching_chars += 1
        # Count extra chars as mismatches
        total_chars += abs(len(canon_line) - len(model_line))

    accuracy = matching_chars / total_chars if total_chars > 0 else 0.0
    exact = code.strip() == canonical.strip()

    return {"accuracy": accuracy, "exact": exact, "language": lang}


def _is_rust(code: str) -> bool:
    return any(k in code for k in ["fn ", "pub ", "impl ", "struct ", "enum ", "use ", "#[derive"])

def _is_js_like(code: str) -> bool:
    return any(k in code for k in ["const ", "function ", "class ", "async function", "module.exports", "=>"])

def _is_swift(code: str) -> bool:
    return any(k in code for k in ["func ", "var ", "let ", "protocol ", "enum ", "extension ", "struct "])

def _evaluate_inline(content: str) -> dict:
    """Evaluate code quality heuristics for inline mode (no server)."""
    blocks = extract_code_blocks(content)
    if not blocks:
        return {"syntax_ok": False, "has_docstrings": False, "has_type_hints": False, "response_length": len(content)}
    code = max(blocks, key=len)
    is_py = any(k in code for k in ["def ", "import ", "from ", "@dataclass", "class "])
    is_sw = _is_swift(code)
    is_js = _is_js_like(code)
    is_rs = _is_rust(code)
    syn = False
    if is_py:
        try:
            import ast; ast.parse(code); syn = True
        except Exception:
            pass
    elif is_rs:
        syn = True
    elif is_sw or is_js:
        stk, pairs, ok = [], {"(": ")", "[": "]", "{": "}"}, True
        for c in code:
            if c in pairs:
                stk.append(c)
            elif c in pairs.values():
                if not stk:
                    ok = False; break
                expected = [k for k, v in pairs.items() if v == c]
                if stk and stk[-1] == expected[0]:
                    stk.pop()
        syn = ok and len(stk) == 0
    docs = '"""' in code or "'''" in code or "/**" in code
    types = ": " in code and any(t in code for t in
        ["int", "str", "float", "bool", "list", "dict", "Optional", "Any",
         "string", "number", "boolean", "Result", ": u16", ": usize"])
    return {"syntax_ok": syn, "has_docstrings": docs, "has_type_hints": types, "response_length": len(content)}


def _load_inline_prompts(prompts_file: str, num_prompts: int) -> list[dict]:
    """Load full message records from JSONL (inline mode needs system+user)."""
    records = []
    if not os.path.isfile(prompts_file):
        print(f"ERROR: Prompts file not found: {prompts_file}", file=sys.stderr)
        sys.exit(1)
    with open(prompts_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
            if len(records) >= num_prompts:
                break
    if not records:
        print(f"ERROR: No prompts found in {prompts_file}", file=sys.stderr)
        sys.exit(1)
    return records[:num_prompts]


def _inline_generate(model, tokenizer, messages: list[dict], max_tokens: int) -> dict:
    """Generate using mlx_lm.generate (no server)."""
    prompt = tokenizer.apply_chat_template(
        messages, add_generation_prompt=True, tokenize=False, add_special_tokens=False,
    )
    start = time.perf_counter()
    chunks = []
    for chunk in mlx_lm.generate(model, tokenizer, prompt, max_tokens=max_tokens):
        chunks.append(chunk)
    elapsed = time.perf_counter() - start
    text = "".join(chunks)
    return {"content": text, "elapsed_sec": elapsed, "completion_tokens": len(tokenizer.encode(text)), "error": False}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compare base model vs fine-tuned model on validation or formatting prompts"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--inline",
        action="store_true",
        help="Use mlx_lm.generate directly (no servers needed). Recommended.",
    )
    mode.add_argument(
        "--server",
        action="store_true",
        help="Use server mode (default). Requires both servers running.",
    )
    parser.add_argument(
        "--formatting",
        action="store_true",
        help="Use formatting test prompts instead of coding problems.",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Base model server URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--ft-url",
        default=DEFAULT_FT_URL,
        help=f"Fine-tuned model server URL (default: {DEFAULT_FT_URL})",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Model path for inline mode (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--adapter-path",
        default=DEFAULT_ADAPTER,
        help=f"Adapter path for inline mode (default: {DEFAULT_ADAPTER})",
    )
    parser.add_argument(
        "--prompts-file",
        default=None,
        help="Override prompts JSONL file (default: valid.jsonl or formatting_test_prompts.jsonl)",
    )
    parser.add_argument(
        "--num-prompts",
        type=int,
        default=DEFAULT_NUM_PROMPTS,
        help=f"Number of prompts to evaluate (default: {DEFAULT_NUM_PROMPTS})",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help=f"Max tokens per generation (default: {DEFAULT_MAX_TOKENS})",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Resolve prompts file
    prompts_file = args.prompts_file
    if prompts_file is None:
        prompts_file = DEFAULT_FORMATTING_FILE if args.formatting else DEFAULT_PROMPTS_FILE

    if args.inline:
        # --- Inline mode ---
        if mlx_lm is None:
            sys.exit("Error: mlx_lm not installed. Run: pip install mlx-lm")

        print(f"=== Benchmark Comparison (inline mode) ===")
        print(f"  Model:    {args.model}")
        print(f"  Adapter:  {args.adapter_path}")
        print(f"  Prompts:   {prompts_file} ({args.num_prompts} max)")
        print(f"  Max tok:   {args.max_tokens}")
        print()

        print("Loading models...")
        base_model, base_tokenizer = mlx_lm.load(args.model)
        ft_model, ft_tokenizer = mlx_lm.load(args.model, adapter_path=args.adapter_path)
        print("Ready.\n")

        records = _load_inline_prompts(prompts_file, args.num_prompts)
        print(f"Loaded {len(records)} prompts.")

        base_results, ft_results = [], []
        base_times, ft_times = [], []
        base_tokens, ft_tokens = [], []

        for i, record in enumerate(records):
            messages = record.get("messages", [])
            user_msgs = [m["content"] for m in messages if m.get("role") == "user"]
            short = user_msgs[0][:60] + "..." if user_msgs and len(user_msgs[0]) > 60 else str(i)
            print(f"[{i+1}/{len(records)}] {short}")

            # Base
            b_resp = _inline_generate(base_model, base_tokenizer, messages, args.max_tokens)
            b_q = _evaluate_inline(b_resp["content"])
            b_fmt = _format_accuracy(b_resp["content"])
            base_results.append({**b_resp, "quality": b_q, "format_accuracy": b_fmt})
            if not b_resp["error"]:
                base_times.append(b_resp["elapsed_sec"])
                base_tokens.append(b_resp["completion_tokens"])

            # Fine-tuned
            f_resp = _inline_generate(ft_model, ft_tokenizer, messages, args.max_tokens)
            f_q = _evaluate_inline(f_resp["content"])
            f_fmt = _format_accuracy(f_resp["content"])
            ft_results.append({**f_resp, "quality": f_q, "format_accuracy": f_fmt})
            if not f_resp["error"]:
                ft_times.append(f_resp["elapsed_sec"])
                ft_tokens.append(f_resp["completion_tokens"])

            b_s = "OK" if not b_resp["error"] else "ERR"
            f_s = "OK" if not f_resp["error"] else "ERR"
            b_t = f"{b_resp['elapsed_sec']:.1f}s" if not b_resp["error"] else "n/a"
            f_t = f"{f_resp['elapsed_sec']:.1f}s" if not f_resp["error"] else "n/a"
            print(f"  base={b_s} ({b_t})  ft={f_s} ({f_t})")

    else:
        # --- Server mode ---
        print(f"=== Benchmark Comparison ===")
        print(f"  Base model:  {args.base_url}")
        print(f"  Fine-tuned:  {args.ft_url}")
        print(f"  Prompts:     {prompts_file} ({args.num_prompts} max)")
        print(f"  Max tokens:  {args.max_tokens}")
        print()

        print("Discovering model IDs...")
        base_model_id = discover_model_id(args.base_url)
        ft_model_id = discover_model_id(args.ft_url)

        if not base_model_id:
            print(f"ERROR: Cannot reach base model server at {args.base_url}", file=sys.stderr)
            print("Start it with: python3 scripts/serve-mlx.py", file=sys.stderr)
            sys.exit(1)

        if not ft_model_id:
            print(f"ERROR: Cannot reach fine-tuned server at {args.ft_url}", file=sys.stderr)
            print("Start it with: python3 scripts/serve_finetuned.py", file=sys.stderr)
            sys.exit(1)

        print(f"  Base model ID:  {base_model_id}")
        print(f"  FT model ID:   {ft_model_id}")
        print()

        prompts = load_prompts(prompts_file, args.num_prompts)
        print(f"Loaded {len(prompts)} prompts.")
        print()

        base_results, ft_results = [], []
        base_times, ft_times = [], []
        base_tokens, ft_tokens = [], []

        for i, prompt in enumerate(prompts):
            short_prompt = prompt[:60] + "..." if len(prompt) > 60 else prompt
            print(f"[{i+1}/{len(prompts)}] {short_prompt}")

            base_resp = generate(args.base_url, base_model_id, prompt, args.max_tokens)
            base_quality = evaluate_quality(base_resp["content"])
            base_results.append({**base_resp, "quality": base_quality})
            if not base_resp["error"]:
                base_times.append(base_resp["elapsed_sec"])
                base_tokens.append(base_resp["completion_tokens"])

            ft_resp = generate(args.ft_url, ft_model_id, prompt, args.max_tokens)
            ft_quality = evaluate_quality(ft_resp["content"])
            ft_results.append({**ft_resp, "quality": ft_quality})
            if not ft_resp["error"]:
                ft_times.append(ft_resp["elapsed_sec"])
                ft_tokens.append(ft_resp["completion_tokens"])

            b_s = "OK" if not base_resp["error"] else "ERR"
            f_s = "OK" if not ft_resp["error"] else "ERR"
            b_t = f"{base_resp['elapsed_sec']:.1f}s" if not base_resp["error"] else "n/a"
            f_t = f"{ft_resp['elapsed_sec']:.1f}s" if not ft_resp["error"] else "n/a"
            print(f"  base={b_s} ({b_t})  ft={f_s} ({f_t})")

    # Print comparison
    print_comparison_table(
        base_results, ft_results,
        base_times, ft_times,
        base_tokens, ft_tokens,
    )

    base_errors = sum(1 for r in base_results if r["error"])
    ft_errors = sum(1 for r in ft_results if r["error"])
    if base_errors > 0 or ft_errors > 0:
        print()
        print(f"Errors: base={base_errors}/{len(base_results)} fine-tuned={ft_errors}/{len(ft_results)}")


if __name__ == "__main__":
    main()
