#!/usr/bin/env python3
"""Scrape local repositories for training corpus and instruction-response pairs.

Walks local code directories, filters for quality, and produces:
1. Raw code files in data/corpus-local/{lang}/ for formatting training
2. Instruction-response pairs in data/local_pairs.jsonl for main training

Usage:
    python scripts/scrape_local.py                           # Default repos
    python scripts/scrape_local.py --repos ~/apps/kicad-agent  # Single repo
    python scripts/scrape_local.py --all                     # All detected repos
    python scripts/scrape_local.py --dry-run                 # Preview without writing
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data")

# Language mapping
EXT_TO_LANG = {
    ".swift": "swift",
    ".py": "python",
    ".pyi": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".h": "cpp",  # Treat headers with cpp code as cpp
    ".hpp": "cpp",
    ".rs": "rust",
    ".dart": "dart",
    ".c": "c",
}

# Directories to always skip
SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".pytest_cache",
    "build", "dist", ".gradle", ".idea", ".vscode",
    "venv", ".venv", "env", ".env", ".mypy_cache",
    ".next", ".nuxt", "target", "out", "bin", "obj",
    ".terraform", ".serverless", "coverage",
    "DerivedData", ".build", ".swiftpm",
    ".hg", ".svn", "Pods", "Carthage",
    ".planning", ".claude",
}

# File patterns to skip (tests, generated, config)
SKIP_PATTERNS = re.compile(
    r"(/|^)"
    r"(test_|_test\.|tests?/|spec_|_spec\.|conftest\.|__init__\.py"
    r"|mock_|stub_|fixture"
    r"|\.test\.|\.spec\."
    r"|\.generated\.|\.g\.|pb2\.|pb\.go"
    r"|package-lock\.|yarn\.lock"
    r"|\.config\.|rc$"
    r"|\.pbxproj$|\.xcworkspacedata$|\.xcscheme$"
    r"|gradlew$|gradle\.bat$"
    r"|\.gz$|\.zip$|\.tar$"
    r"|migration\d*\.|seed\.|dump\.|snapshot"
    r")",
    re.IGNORECASE,
)

# Code must have minimum substance
MIN_LINES = 8
MAX_LINES = 500

# Domain mapping: customize this to map your repos to training domains.
# Domains are used for RAG retrieval via Confucius. Add entries for your
# repos to get domain-specific pattern retrieval during generation.
# Domains can be anything — common choices: swift, python, juce, pcb, rust
REPO_DOMAIN_MAP = {
    # "my-ios-app": "swift",
    # "my-python-service": "python",
    # "my-audio-plugin": "juce",
}


def find_code_files(root_dir: str) -> List[Tuple[str, str]]:
    """Walk directory tree and find code files with their languages."""
    files = []
    root = Path(root_dir)
    if not root.exists():
        return files

    for dirpath, dirnames, filenames in os.walk(root):
        # Prune skipped directories in-place
        dirnames[:] = [
            d for d in dirnames
            if d not in SKIP_DIRS and not d.startswith(".")
        ]

        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            ext = os.path.splitext(filename)[1].lower()

            if ext not in EXT_TO_LANG:
                continue
            if SKIP_PATTERNS.search(filepath):
                continue

            lang = EXT_TO_LANG[ext]
            files.append((filepath, lang))

    return files


def is_code_quality(code: str) -> bool:
    """Check if code meets quality thresholds."""
    lines = code.splitlines()
    if len(lines) < MIN_LINES:
        return False
    if len(lines) > MAX_LINES:
        return False
    # Must have some substance (not just imports/comments)
    non_blank = [l for l in lines if l.strip() and not l.strip().startswith(("#", "//", "/*", "*", "\"\"\""))]
    return len(non_blank) >= 5


def extract_instruction_response(code: str, filepath: str, lang: str) -> Optional[Dict]:
    """Extract instruction-response pair from code using docstrings/signatures.

    Returns a JSONL-formatted dict or None if no good pair can be extracted.
    """
    lines = code.splitlines()

    if lang == "python":
        return _extract_python_pair(code, lines, filepath)
    elif lang == "swift":
        return _extract_swift_pair(code, lines, filepath)
    elif lang in ("typescript", "javascript"):
        return _extract_ts_pair(code, lines, filepath)
    elif lang == "cpp":
        return _extract_cpp_pair(code, lines, filepath)
    elif lang == "rust":
        return _extract_rust_pair(code, lines, filepath)

    return None


def _extract_python_pair(code: str, lines: List[str], filepath: str) -> Optional[Dict]:
    """Extract pair from Python code using docstrings."""
    # Look for module-level or class/function docstrings
    docstring_pattern = re.compile(r'^(\s*(?:class |def |async def )\w[^\n:]+:)\s*\n(\s*(?:"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'))', re.MULTILINE)
    matches = docstring_pattern.findall(code)

    if matches:
        sig, doc = matches[0]
        instruction = f"Implement the following with proper Python patterns:\n{doc.strip()}"
        # Find the body after the docstring
        sig_start = code.find(sig)
        if sig_start >= 0:
            response = code[sig_start:]
            if len(response) > 50:
                return _make_pair(instruction, response, "python")

    # Fallback: use the whole file with a generated prompt
    filename = os.path.basename(filepath)
    if _has_substantial_functions(code):
        return _make_pair(
            f"Write Python code for {filename} with proper type hints and error handling",
            code,
            "python",
        )

    return None


def _extract_swift_pair(code: str, lines: List[str], filepath: str) -> Optional[Dict]:
    """Extract pair from Swift code using doc comments."""
    # Look for /// doc comments followed by declarations
    doc_pattern = re.compile(r'((?:///[^\n]+\n)+)\s*(public\s+|private\s+|internal\s+|fileprivate\s+)?(func|class|struct|enum|protocol)\s+(\w+)', re.MULTILINE)
    matches = doc_pattern.findall(code)

    if matches:
        doc, access, keyword, name = matches[0]
        instruction = f"Implement a Swift {keyword} named `{name}`:\n{doc.strip()}"
        return _make_pair(instruction, code, "swift")

    filename = os.path.basename(filepath)
    if _has_substantial_functions(code, swift=True):
        return _make_pair(
            f"Write Swift code for {filename} following Swift 6 strict concurrency",
            code,
            "swift",
        )

    return None


def _extract_ts_pair(code: str, lines: List[str], filepath: str) -> Optional[Dict]:
    """Extract pair from TypeScript code using JSDoc."""
    jsdoc_pattern = re.compile(r'((?:\*\s*[^\n]+\n)+)\s*(export\s+)?(async\s+)?(function|class|interface|const|type)\s+(\w+)', re.MULTILINE)
    matches = jsdoc_pattern.findall(code)

    if matches:
        doc, _, async_, keyword, name = matches[0]
        instruction = f"Implement a TypeScript {keyword} named `{name}`:\n{doc.strip()}"
        return _make_pair(instruction, code, "typescript")

    filename = os.path.basename(filepath)
    return _make_pair(
        f"Write TypeScript code for {filename} with proper types",
        code,
        "typescript",
    )


def _extract_cpp_pair(code: str, lines: List[str], filepath: str) -> Optional[Dict]:
    """Extract pair from C++ code using Doxygen or block comments."""
    # Skip pure header files that are just declarations
    if code.count(";") > len(lines) * 0.5 and code.count("{") < 3:
        return None

    filename = os.path.basename(filepath)
    return _make_pair(
        f"Write C++ code for {filename} following JUCE conventions",
        code,
        "cpp",
    )


def _extract_rust_pair(code: str, lines: List[str], filepath: str) -> Optional[Dict]:
    """Extract pair from Rust code using doc comments."""
    doc_pattern = re.compile(r'((?:///[^\n]+\n)+)\s*(pub\s+)?(async\s+)?fn\s+(\w+)', re.MULTILINE)
    matches = doc_pattern.findall(code)

    if matches:
        doc, _, async_, name = matches[0]
        instruction = f"Implement a Rust function `{name}`:\n{doc.strip()}"
        return _make_pair(instruction, code, "rust")

    filename = os.path.basename(filepath)
    return _make_pair(
        f"Write Rust code for {filename} with proper error handling",
        code,
        "rust",
    )


def _has_substantial_functions(code: str, swift: bool = False) -> bool:
    """Check if code has substantial function/class definitions."""
    if swift:
        return bool(re.search(r'\b(func|class|struct|enum|protocol|extension)\b', code))
    return bool(re.search(r'\b(def |class |async def )', code))


def _make_pair(instruction: str, response: str, lang: str) -> Dict:
    """Create a training pair with system prompt."""
    system = "You are an expert programmer. Write clean, well-documented code following SLC principles (Simple, Lovable, Complete)."

    # Trim response if too long
    response_lines = response.splitlines()
    if len(response_lines) > 400:
        response = "\n".join(response_lines[:400])

    return {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": instruction},
            {"role": "assistant", "content": response},
        ]
    }


def infer_domain(repo_name: str, lang: str) -> Optional[str]:
    """Infer domain tag from repo name and language."""
    for pattern, domain in REPO_DOMAIN_MAP.items():
        if pattern.lower() in repo_name.lower():
            return domain
    # Fallback: language-based
    lang_to_domain = {"swift": "swift", "python": "python", "cpp": "juce", "rust": "rust"}
    return lang_to_domain.get(lang)


def main():
    parser = argparse.ArgumentParser(
        description="Scrape local repos for training corpus and instruction-response pairs."
    )
    parser.add_argument(
        "--repos",
        nargs="+",
        default=None,
        help="Specific repo directories to scrape (required unless --all)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Scan all repos in ~/apps/",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory (default: data/)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be scraped without writing files",
    )
    parser.add_argument(
        "--max-files-per-lang",
        type=int,
        default=500,
        help="Max corpus files per language (default: 500)",
    )
    parser.add_argument(
        "--max-pairs",
        type=int,
        default=2000,
        help="Max instruction-response pairs to generate (default: 2000)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    corpus_dir = output_dir / "corpus-local"

    # --- Determine repos to scan ---
    if args.all:
        apps_dir = Path(os.path.expanduser("~/apps"))
        repos = [str(d) for d in apps_dir.iterdir() if d.is_dir()]
    elif args.repos:
        repos = [os.path.expanduser(r) for r in args.repos]
    else:
        print("No repos specified. Use --repos to point to your code directories.")
        print()
        print("Examples:")
        print("  python scripts/scrape_local.py --repos ~/projects/my-app")
        print("  python scripts/scrape_local.py --repos ~/projects/app1 ~/projects/app2")
        print("  python scripts/scrape_local.py --all")
        print()
        print("Use --dry-run to preview what would be scraped without writing files.")
        sys.exit(0)

    # Filter to existing directories
    repos = [r for r in repos if os.path.isdir(r)]
    if not repos:
        print("No valid repo directories found.")
        sys.exit(1)

    print(f"Scanning {len(repos)} repos for training data...")
    print(f"Max corpus files per language: {args.max_files_per_lang}")
    print(f"Max instruction-response pairs: {args.max_pairs}")
    print()

    # --- Scan repos ---
    corpus_files: Dict[str, List[Tuple[str, str]]] = {}  # lang -> [(filepath, repo_name)]
    all_pairs: List[Dict] = []
    skipped = {"quality": 0, "length": 0, "pattern": 0}
    per_repo: Dict[str, int] = {}

    for repo_path in sorted(repos):
        repo_name = os.path.basename(repo_path)
        code_files = find_code_files(repo_path)

        if not code_files:
            continue

        repo_count = 0
        for filepath, lang in code_files:
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    code = f.read()
            except (OSError, PermissionError):
                skipped["quality"] += 1
                continue

            if not is_code_quality(code):
                skipped["quality"] += 1
                continue

            # Corpus file
            if lang not in corpus_files:
                corpus_files[lang] = []
            if len(corpus_files[lang]) < args.max_files_per_lang:
                corpus_files[lang].append((filepath, repo_name))

            # Instruction-response pair
            if len(all_pairs) < args.max_pairs:
                pair = extract_instruction_response(code, filepath, lang)
                if pair:
                    pair["_source"] = f"{repo_name}/{os.path.relpath(filepath, repo_path)}"
                    pair["_domain"] = infer_domain(repo_name, lang) or "general"
                    pair["_lang"] = lang
                    all_pairs.append(pair)

            repo_count += 1

        if repo_count > 0:
            per_repo[repo_name] = repo_count
            print(f"  {repo_name}: {repo_count} quality files")

    print()

    # --- Summary ---
    total_corpus = sum(len(v) for v in corpus_files.values())
    print(f"Corpus files: {total_corpus}")
    for lang in sorted(corpus_files.keys()):
        repos_repr = set(r for _, r in corpus_files[lang])
        print(f"  {lang}: {len(corpus_files[lang])} files from {len(repos_repr)} repos")

    print(f"\nInstruction-response pairs: {len(all_pairs)}")
    print(f"Skipped: {skipped['quality']} quality, {skipped['length']} length, {skipped['pattern']} pattern")

    # --- Dry run: stop here ---
    if args.dry_run:
        print("\n[DRY RUN] No files written.")
        return

    # --- Write corpus files ---
    for lang, file_list in corpus_files.items():
        lang_dir = corpus_dir / lang
        lang_dir.mkdir(parents=True, exist_ok=True)

        for filepath, repo_name in file_list:
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    code = f.read()
            except (OSError, PermissionError):
                continue

            # Sanitize filename: repo_name + relative path
            rel = os.path.relpath(filepath, os.path.dirname(filepath).rsplit(repo_name, 1)[0])
            safe_name = rel.replace("/", "__").replace("\\", "__")
            out_path = lang_dir / safe_name

            # Handle duplicate names
            if out_path.exists():
                stem = out_path.stem
                counter = 1
                while out_path.exists():
                    out_path = lang_dir / f"{stem}_{counter}{out_path.suffix}"
                    counter += 1

            out_path.write_text(code, encoding="utf-8")

    print(f"\nCorpus written to: {corpus_dir}")

    # --- Write instruction-response pairs ---
    pairs_path = output_dir / "local_pairs.jsonl"
    with open(pairs_path, "w", encoding="utf-8") as f:
        for pair in all_pairs:
            # Strip metadata before writing (training format doesn't need it)
            clean = {"messages": pair["messages"]}
            f.write(json.dumps(clean, ensure_ascii=False) + "\n")

    print(f"Pairs written to: {pairs_path}")

    # --- Write manifest ---
    manifest = {
        "source": "local_repos",
        "repos_scanned": per_repo,
        "corpus_total": total_corpus,
        "corpus_per_lang": {lang: len(v) for lang, v in corpus_files.items()},
        "pairs_total": len(all_pairs),
        "pairs_per_lang": {},
        "skipped": skipped,
    }

    # Count pairs per language
    for pair in all_pairs:
        lang = pair.get("_lang", "unknown")
        manifest["pairs_per_lang"][lang] = manifest["pairs_per_lang"].get(lang, 0) + 1

    manifest_path = corpus_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Manifest written to: {manifest_path}")
    print("\nDone.")


if __name__ == "__main__":
    main()
