#!/usr/bin/env python3
"""Pre-populate Confucius with domain-specific coding patterns.

Seeds Confucius memory with patterns for 4 domains: swift, python, juce, pcb.
These patterns improve RAG retrieval quality for the code generation pipeline.

Usage:
    python3 scripts/seed_patterns.py --list              # Show available patterns
    python3 scripts/seed_patterns.py --dry-run           # Show what would be stored
    python3 scripts/seed_patterns.py --domain swift      # Seed only swift patterns
    python3 scripts/seed_patterns.py                     # Seed all domains
"""

import argparse
import subprocess
import sys

SEED_PATTERNS: dict[str, list[dict]] = {
    "swift": [
        {
            "id": "swift-async-pattern",
            "type": "pattern",
            "tags": "swift,async,concurrency",
            "content": (
                "Swift async/await pattern: Use structured concurrency with TaskGroup "
                "for parallel work. Always handle cancellation with Task.isCancelled. "
                "Use 'sending' keyword for transferred values in Swift 6.4."
            ),
        },
        {
            "id": "swift-swiftui-view",
            "type": "pattern",
            "tags": "swift,swiftui,view",
            "content": (
                "SwiftUI view pattern: Keep views as structs with small bodies. "
                "Extract subviews for readability. Use @State for local state, "
                "@Binding for parent-child communication. "
                "Prefer @Observable over ObservableObject in iOS 26."
            ),
        },
        {
            "id": "swift-error-handling",
            "type": "pattern",
            "tags": "swift,error,handling",
            "content": (
                "Swift error handling: Use typed throws in Swift 6.4 for specific error "
                "types. Create custom Error enums. Never force-try in production. "
                "Use defer for cleanup. Propagate errors rather than silently catching."
            ),
        },
        {
            "id": "swift-immutability",
            "type": "pattern",
            "tags": "swift,immutability,value-types",
            "content": (
                "Swift immutability: Prefer let over var. Use value types (struct) "
                "over reference types (class) by default. Create new instances instead "
                "of mutating. Use .map/.filter/.reduce instead of mutating loops."
            ),
        },
        {
            "id": "swift-liquid-glass",
            "type": "pattern",
            "tags": "swift,swiftui,liquid-glass,wwdc26",
            "content": (
                "Liquid Glass pattern (iOS 26): Use .glassEffect() modifier for "
                "translucent surfaces. Control intensity with GlassEffectIntensity. "
                "Use GlassEffectContainer for coordinated glass effects. "
                "Combine with standard SwiftUI modifiers."
            ),
        },
    ],
    "python": [
        {
            "id": "python-immutability",
            "type": "pattern",
            "tags": "python,immutability,pattern",
            "content": (
                "Python immutability: Use frozen dataclasses (@dataclass(frozen=True)) "
                "for immutable data. Return new objects instead of mutating. "
                "Use tuple instead of list for fixed collections. "
                "Prefer comprehensions over in-place mutations."
            ),
        },
        {
            "id": "python-error-handling",
            "type": "pattern",
            "tags": "python,error,handling",
            "content": (
                "Python error handling: Define custom exception classes inheriting "
                "from Exception. Always include error context in messages. "
                "Never use bare except. Use contextlib for resource cleanup. "
                "Validate at function boundaries."
            ),
        },
        {
            "id": "python-type-hints",
            "type": "pattern",
            "tags": "python,typing,pattern",
            "content": (
                "Python type hints: Use type hints on all function signatures. "
                "Use typing module for generics (list[str] not List[str] in Python 3.11+). "
                "Use Protocol for interfaces. Use TypeVar for generics. "
                "Run mypy in CI."
            ),
        },
        {
            "id": "python-file-organization",
            "type": "pattern",
            "tags": "python,organization,pattern",
            "content": (
                "Python file organization: One class per file for large classes. "
                "Group related utilities in modules. Keep files under 400 lines. "
                "Use __init__.py for public API exports. "
                "Separate concerns into packages."
            ),
        },
    ],
    "juce": [
        {
            "id": "juce-plugin-structure",
            "type": "pattern",
            "tags": "audio,juce,plugin",
            "content": (
                "JUCE plugin structure: Inherit from juce::AudioProcessor. "
                "Implement prepareToPlay, processBlock, releaseResources. "
                "Use AudioProcessorValueTreeState for parameters. "
                "Keep DSP logic separate from GUI code."
            ),
        },
        {
            "id": "juce-dsp-pattern",
            "type": "pattern",
            "tags": "audio,juce,dsp",
            "content": (
                "JUCE DSP pattern: Use juce::dsp::ProcessorChain for signal flow. "
                "Use AudioBlock for buffer access. Use FIRFilter/Coefficients for "
                "filter design. Process in fixed-size blocks for consistent performance."
            ),
        },
        {
            "id": "juce-state-management",
            "type": "pattern",
            "tags": "audio,juce,state",
            "content": (
                "JUCE state management: Use ValueTree for hierarchical state. "
                "Use AudioProcessorValueTreeState for plugin parameters. "
                "Implement getStateInformation/setStateInformation for preset save/load. "
                "Use Attach classes for parameter-UI binding."
            ),
        },
    ],
    "pcb": [
        {
            "id": "pcb-layout-basics",
            "type": "pattern",
            "tags": "pcb,layout,design",
            "content": (
                "PCB layout basics: Keep high-speed traces short and direct. "
                "Use ground planes for signal integrity. "
                "Place decoupling capacitors close to ICs. "
                "Route differential pairs together with matched lengths."
            ),
        },
        {
            "id": "kicad-schematic-pattern",
            "type": "pattern",
            "tags": "pcb,kicad,schematic",
            "content": (
                "KiCad schematic pattern: Use hierarchical sheets for subsystem "
                "organization. Label nets consistently (e.g., VCC_3V3, GND). "
                "Use power flags for power nets. Run ERC before layout."
            ),
        },
        {
            "id": "pcb-design-rules",
            "type": "pattern",
            "tags": "pcb,design,rules",
            "content": (
                "PCB design rules: Minimum trace width 6mil for signal, 20mil for power. "
                "Via size 0.6mm drill minimum. Keep copper fill clearance consistent. "
                "Run DRC before manufacturing."
            ),
        },
    ],
}


def seed_domain(domain: str, patterns: list[dict], dry_run: bool = False) -> int:
    """Seed Confucius with patterns for a given domain.

    Args:
        domain: Domain name (e.g. "swift", "python").
        patterns: List of pattern dicts with id, type, tags, content.
        dry_run: If True, print what would be stored without calling confucius.

    Returns:
        Number of patterns successfully stored (or would be stored in dry_run).
    """
    stored = 0
    for pattern in patterns:
        pattern_id = pattern["id"]
        pattern_type = pattern["type"]
        tags = pattern["tags"]
        content = pattern["content"]

        if dry_run:
            print(f"  [{domain}] {pattern_id} ({pattern_type}, tags: {tags})")
            stored += 1
            continue

        try:
            cmd = [
                "confucius", "store", content,
                "--type", pattern_type,
                "--tags", tags,
                "--id", pattern_id,
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                stored += 1
            else:
                print(
                    f"  WARNING: Failed to store {pattern_id}: {result.stderr.strip()}",
                    file=sys.stderr,
                )
        except subprocess.TimeoutExpired:
            print(
                f"  WARNING: Timeout storing {pattern_id}",
                file=sys.stderr,
            )
        except Exception as e:
            print(
                f"  WARNING: Error storing {pattern_id}: {e}",
                file=sys.stderr,
            )

    return stored


def main() -> None:
    """Parse arguments and seed Confucius with domain patterns."""
    parser = argparse.ArgumentParser(
        description="Pre-populate Confucius with domain-specific coding patterns.",
    )
    parser.add_argument(
        "--domain",
        type=str,
        default="all",
        help="Domain to seed (swift, python, juce, pcb, or all). Default: all.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be stored without calling confucius.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available patterns grouped by domain.",
    )
    args = parser.parse_args()

    if args.list:
        total = 0
        print("Available seed patterns:\n")
        for domain, patterns in SEED_PATTERNS.items():
            print(f"  {domain} ({len(patterns)} patterns):")
            for p in patterns:
                print(f"    - {p['id']} [{p['type']}] tags: {p['tags']}")
                print(f"      {p['content'][:80]}...")
            print()
            total += len(patterns)
        print(f"  Total: {total} patterns across {len(SEED_PATTERNS)} domains")
        return

    domains_to_seed: list[str]
    if args.domain == "all":
        domains_to_seed = sorted(SEED_PATTERNS.keys())
    elif args.domain in SEED_PATTERNS:
        domains_to_seed = [args.domain]
    else:
        print(
            f"Unknown domain: {args.domain}. "
            f"Available: {', '.join(sorted(SEED_PATTERNS.keys()))}, all",
            file=sys.stderr,
        )
        sys.exit(1)

    prefix = "[DRY RUN] " if args.dry_run else ""
    print(f"{prefix}Seeding {len(domains_to_seed)} domain(s)...\n")

    total_stored = 0
    for domain in domains_to_seed:
        patterns = SEED_PATTERNS[domain]
        count = seed_domain(domain, patterns, dry_run=args.dry_run)
        print(f"  {domain}: {count} patterns {'listed' if args.dry_run else 'stored'}")
        total_stored += count

    print(f"\n{prefix}Total: {total_stored} patterns across {len(domains_to_seed)} domain(s)")


if __name__ == "__main__":
    main()
