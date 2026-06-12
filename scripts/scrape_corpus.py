#!/usr/bin/env python3
"""
Scrape real code files from GitHub repos to build a diverse formatting corpus.

Pulls clean, well-formatted code from popular open-source projects.
Each file becomes a training snippet for the formatting data generator.

Usage:
  python3 scripts/scrape_corpus.py --max-files 200 --output data/corpus/
  python3 scripts/scrape_corpus.py --repos "python/cpython,python/typeshed,rust-lang/rust" --output data/corpus/

Requires: pip install PyGithub (optional, falls back to raw GitHub API)
"""

import argparse
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path

try:
    from github import Github
    HAS_GITHUB = True
except ImportError:
    HAS_GITHUB = False

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_REPOS = [
    # Python
    ("python", "python/cpython", "Lib/", 50, [".py"]),
    ("python", "python/typeshed", "stdlib/", 30, [".pyi"]),
    ("python", "pallets/flask", "src/flask/", 20, [".py"]),
    ("python", "python/cpython", "Tools/", 20, [".py"]),
    ("python", "psf/black", "", 15, [".py"]),
    # JavaScript
    ("javascript", "nodejs/node", "lib/", 30, [".js"]),
    ("javascript", "lodash/lodash", "", 15, [".js"]),
    ("javascript", "expressjs/express", "lib/", 15, [".js"]),
    # TypeScript
    ("typescript", "microsoft/TypeScript", "src/", 20, [".ts"]),
    ("typescript", " DefinitelyTyped/DefinitelyTyped", "types/node/", 10, [".d.ts"]),
    # Rust
    ("rust", "rust-lang/rust", "library/std/src/", 20, [".rs"]),
    ("rust", "serde-rs/serde", "src/", 15, [".rs"]),
    ("rust", "tokio-rs/tokio", "tokio/src/", 10, [".rs"]),
]

# Language detection by extension
EXT_TO_LANG = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".d.ts": "typescript",
    ".rs": "rust",
    ".swift": "swift",
}


def get_raw_github_file(repo: str, path: str) -> str | None:
    """Fetch a single file from GitHub raw API (no auth needed)."""
    import urllib.request
    url = f"https://raw.githubusercontent.com/{repo}/main/{path}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status == 200:
                return resp.read().decode("utf-8", errors="replace")
    except Exception:
        pass
    return None


def get_github_dir_listing(repo: str, dir_path: str, max_files: int) -> list[str]:
    """Get file listing from GitHub API (unauthenticated, 100 files per page)."""
    import urllib.request
    files = []
    page = 1
    while len(files) < max_files:
        url = f"https://api.github.com/repos/{repo}/contents/{dir_path}?per_page=100&page={page}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status != 200:
                    break
                data = json.loads(resp.read().decode("utf-8"))
                if not isinstance(data, list):
                    break
                for item in data:
                    if item.get("type") == "file" and item.get("name"):
                        files.append(item["path"])
                if len(data) < 100:
                    break
                page += 1
        except Exception:
            break
    return files[:max_files]


def is_code_suitable(code: str, lang: str) -> bool:
    """Filter out unsuitable code files."""
    lines = code.splitlines()
    if len(lines) < 5:
        return False
    if len(lines) > 300:
        return False
    # Filter out auto-generated, test files, etc.
    path_heuristics = [
        "test_", "_test.", "conftest", "__init__.py", ".test.",
        "pb.go", "_pb2.py",  # protobuf
    ]
    # Check for test patterns in code
    if "def test_" in code and "unittest" in code:
        return False
    if "describe(" in code or "it(" in code and "expect(" in code:
        return False
    return True


def scrape_repo_raw(repo_name: str, subdir: str, max_files: int, extensions: list[str], output_dir: Path) -> int:
    """Scrape files from a GitHub repo using raw API (no auth needed)."""
    lang = extensions[0].lstrip(".") if extensions else "unknown"
    count = 0

    if subdir:
        listing = get_github_dir_listing(repo_name, subdir, max_files * 2)
        candidate_files = [f for f in listing if any(f.endswith(ext) for ext in extensions)]
        files_to_try = candidate_files[:max_files]
    else:
        files_to_try = []

    lang_dir = output_dir / lang
    lang_dir.mkdir(parents=True, exist_ok=True)

    for file_path in files_to_try:
        code = get_raw_github_file(repo_name, file_path)
        if code and is_code_suitable(code, lang):
            # Sanitize filename
            safe_name = file_path.replace("/", "_").replace("\\", "_")
            out_path = lang_dir / safe_name
            out_path.write_text(code, encoding="utf-8")
            count += 1

    return count


def scrape_repo_github_api(repo_name: str, subdir: str, max_files: int, extensions: list[str], output_dir: Path) -> int:
    """Scrape files using PyGithub (requires GITHUB_TOKEN)."""
    if not HAS_GITHUB:
        return scrape_repo_raw(repo_name, subdir, max_files, extensions, output_dir)

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print(f"  Skipping {repo_name} (no GITHUB_TOKEN)")
        return 0

    g = Github(token)
    lang = extensions[0].lstrip(".") if extensions else "unknown"
    count = 0

    try:
        repo = g.get_repo(repo_name)
        if subdir:
            contents = repo.get_contents(subdir)
        else:
            contents = repo.get_contents("")

        file_list = []
        if isinstance(contents, list):
            for item in contents:
                if item.type == "file" and any(item.name.endswith(ext) for ext in extensions):
                    file_list.append(item)

        lang_dir = output_dir / lang
        lang_dir.mkdir(parents=True, exist_ok=True)

        for item in file_list[:max_files]:
            try:
                code = item.decoded_content.decode("utf-8", errors="replace")
            except Exception:
                continue
            if code and is_code_suitable(code, lang):
                safe_name = item.path.replace("/", "_")
                out_path = lang_dir / safe_name
                out_path.write_text(code, encoding="utf-8")
                count += 1

    except Exception as e:
        print(f"  Error scraping {repo_name}: {e}")

    return count


def main():
    parser = argparse.ArgumentParser(description="Scrape real code from GitHub for formatting corpus")
    parser.add_argument("--max-files", type=int, default=200, help="Max files per language")
    parser.add_argument("--output", type=str, default=os.path.join(PROJECT_ROOT, "data", "corpus"), help="Output directory")
    parser.add_argument("--repos", type=str, default=None, help="Override repo list (format: 'lang/repo/subdir,max,ext')")
    parser.add_argument("--token", type=str, default=None, help="GitHub token (or set GITHUB_TOKEN)")
    args = parser.parse_args()

    output_dir = Path(args.output)

    if args.token:
        os.environ["GITHUB_TOKEN"] = args.token

    repos = DEFAULT_REPOS
    if args.repos:
        repos = []
        for entry in args.repos.split(","):
            parts = entry.strip().split(":")
            lang = parts[0] if len(parts) > 0 else "python"
            repo = parts[1] if len(parts) > 1 else parts[0]
            subdir = parts[2] if len(parts) > 2 else ""
            max_f = int(parts[3]) if len(parts) > 3 else 20
            exts = [parts[4]] if len(parts) > 4 else [".py"]
            repos.append((lang, repo, subdir, max_f, exts))

    print(f"Scraping real code from {len(repos)} repos (max {args.max_files} per language)")
    print(f"Output: {output_dir}")
    print()

    total = 0
    per_lang = {}

    for lang, repo, subdir, max_f, exts in repos:
        print(f"  [{lang}] {repo}/{subdir} (max {max_f})")
        if HAS_GITHUB and os.environ.get("GITHUB_TOKEN"):
            count = scrape_repo_github_api(repo, subdir, max_f, exts, output_dir)
        else:
            count = scrape_repo_raw(repo, subdir, max_f, exts, output_dir)
        per_lang[lang] = per_lang.get(lang, 0) + count
        total += count
        print(f"    Got {count} files")

    print(f"\nTotal: {total} files")
    for lang, count in sorted(per_lang.items()):
        print(f"  {lang}: {count}")

    # Write manifest
    manifest = {"repos": [(r[0], r[1], r[2]) for r in repos], "total": total, "per_lang": per_lang}
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest saved to {output_dir / 'manifest.json'}")


if __name__ == "__main__":
    main()
