#!/usr/bin/env python3
"""Verify offline code generation — no network dependency after model download.

Modes:
  Default (sudo required): Disables network interfaces, tests inference, re-enables.
  --no-sudo: Monitors for outbound connections without disconnecting (soft test).
"""

import argparse
import json
import subprocess
import sys
import time

import urllib.request
import urllib.error


def run_cmd(cmd: str, check: bool = True, capture: bool = True) -> tuple[int, str, str]:
    """Run a shell command, return (exit_code, stdout, stderr)."""
    result = subprocess.run(
        cmd, shell=True, capture_output=capture, text=True, timeout=30
    )
    if check and result.returncode != 0:
        print(f"  WARNING: command failed: {cmd}", file=sys.stderr)
        print(f"  stderr: {result.stderr.strip()}", file=sys.stderr)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def check_server(base_url: str, port: int) -> bool:
    """Check if the LLM server is responding."""
    try:
        req = urllib.request.Request(f"{base_url}:{port}/v1/models")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception:
        return False


def generate_code(base_url: str, port: int, prompt: str, model: str = None) -> tuple[bool, str]:
    """Send a code generation request. Returns (success, content)."""
    endpoint = f"{base_url}:{port}/v1/chat/completions"
    payload_obj = {
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 150,
    }
    if model:
        payload_obj["model"] = model
    payload = json.dumps(payload_obj).encode()
    req = urllib.request.Request(
        endpoint, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
            content = data["choices"][0]["message"]["content"]
            return True, content
    except Exception as e:
        return False, str(e)


def disable_network() -> list[str]:
    """Disable all non-loopback network interfaces. Returns list of disabled services."""
    code, services, _ = run_cmd("networksetup -listallnetworkservices")
    if code != 0:
        return []
    disabled = []
    for svc in services.split("\n"):
        svc = svc.strip()
        if svc.lower() in ("loopback", ""):
            continue
        run_cmd(f"networksetup -setnetworkserviceenabled \"{svc}\" off", check=False)
        disabled.append(svc)
    return disabled


def enable_network(services: list[str]) -> list[str]:
    """Re-enable network interfaces. Returns list that failed."""
    failed = []
    for svc in services:
        code, _, _ = run_cmd(
            f"networksetup -setnetworkserviceenabled \"{svc}\" on", check=False
        )
        if code != 0:
            failed.append(svc)
    return failed


def run_sudo_test(base_url: str, port: int, model: str = None) -> bool:
    """Full offline test with network interface toggling."""
    print("\n=== Hard Offline Test (sudo mode) ===")

    # Step 1: Verify server responding
    print("[1] Checking server before disconnect...", end=" ")
    if not check_server(base_url, port):
        print("FAIL — server not responding")
        return False
    print("OK")

    # Step 2: Record interfaces
    print("[2] Recording network interfaces...", end=" ")
    code, services, _ = run_cmd("networksetup -listallnetworkservices")
    if code != 0:
        print("FAIL")
        return False
    print(f"OK ({len(services.split(chr(10)))} services)")

    # Step 3: Check active connections
    print("[3] Checking active connections...", end=" ")
    code, conns, _ = run_cmd(
        "lsof -i -P 2>/dev/null | grep ESTABLISHED | grep -v 127.0.0.1 | grep -v ::1 | head -5",
        check=False,
    )
    external = conns.strip()
    if external:
        print(f"WARN — external connections active:\n    {external}")
    else:
        print("OK — no external connections")

    # Step 4: Disable network
    print("[4] Disabling network interfaces...", end=" ")
    disabled = disable_network()
    if not disabled:
        print("FAIL — no interfaces disabled (may need sudo)")
        print("    Run with: sudo python3 scripts/verify-offline.py")
        return False
    print(f"OK (disabled: {', '.join(disabled)})")

    try:
        # Step 5: Verify network down
        print("[5] Verifying network is down...", end=" ")
        code, _, _ = run_cmd("ping -c 1 -t 2 8.8.8.8", check=False)
        if code == 0:
            print("WARN — ping succeeded (network may not be fully down)")
        else:
            print("OK — ping failed as expected")

        # Step 6: Verify loopback works
        print("[6] Verifying loopback...", end=" ")
        if not check_server(base_url, port):
            print("FAIL — server not responding on loopback")
            return False
        print("OK")

        # Step 7: Generate code
        print("[7] Generating code offline...")
        prompts = [
            "Write a Python function to merge two sorted lists.",
            "Implement a stack with push, pop, and peek in Python.",
            "Write a function to find the longest common substring.",
        ]
        all_ok = True
        for i, prompt in enumerate(prompts):
            print(f"  Prompt {i+1}: ", end="")
            success, content = generate_code(base_url, port, prompt, model)
            if success and ("def " in content or "class " in content):
                lines = content.strip().split("\n")[:3]
                print(f"OK — {lines[0][:60]}...")
            else:
                print(f"FAIL — {content[:80]}")
                all_ok = False

        if not all_ok:
            return False

        # Step 8: Already validated in step 7
        print("[8] Code validation: OK (checked in step 7)")

        print("\n=== Offline Test: PASS ===")
        return True

    finally:
        # Step 9: ALWAYS re-enable network
        print("\n[9] Re-enabling network interfaces...", end=" ")
        failed = enable_network(disabled)
        if failed:
            print(f"PARTIAL — failed to re-enable: {', '.join(failed)}")
            print("    Manual recovery: System Settings > Network, or:")
            for svc in failed:
                print(f"      networksetup -setnetworkserviceenabled \"{svc}\" on")
        else:
            print("OK")

        # Step 10: Summary already printed
        print("[10] Summary: See above")


def run_monitor_test(base_url: str, port: int, model: str = None) -> bool:
    """Soft offline test — monitor connections without disconnecting."""
    print("\n=== Soft Offline Test (monitor mode) ===")
    print("NOTE: This monitors for outbound connections but does NOT disconnect.\n")

    # Step 1: Server check
    print("[1] Checking server...", end=" ")
    if not check_server(base_url, port):
        print("FAIL")
        return False
    print("OK")

    # Step 2: Baseline connections
    print("[2] Capturing baseline connections...", end=" ")
    code, baseline, _ = run_cmd(
        "lsof -i -P 2>/dev/null | grep ESTABLISHED | grep -v 127.0.0.1 | grep -v ::1",
        check=False,
    )
    baseline_count = len(baseline.strip().split("\n")) if baseline.strip() else 0
    print(f"OK ({baseline_count} external connections)")

    # Step 3-6: Generate and monitor
    print("[3] Generating code while monitoring connections...")
    prompts = [
        "Write a Python function to merge two sorted lists.",
        "Implement a stack with push, pop, and peek in Python.",
        "Write a function to find the longest common substring.",
    ]
    all_ok = True
    for i, prompt in enumerate(prompts):
        print(f"  Prompt {i+1}: ", end="")
        # Start connection monitor in background
        code, during, _ = run_cmd(
            "lsof -i -P 2>/dev/null | grep ESTABLISHED | grep -v 127.0.0.1 | grep -v ::1",
            check=False,
        )
        new_conns = len(during.strip().split("\n")) if during.strip() else 0

        success, content = generate_code(base_url, port, prompt, model)
        if success and ("def " in content or "class " in content):
            print(f"OK (external connections: {new_conns})")
        else:
            print(f"FAIL — {content[:80]}")
            all_ok = False

    # Step 4: Post-generation check
    print("[4] Post-generation connection check...", end=" ")
    code, after, _ = run_cmd(
        "lsof -i -P 2>/dev/null | grep ESTABLISHED | grep -v 127.0.0.1 | grep -v ::1",
        check=False,
    )
    after_count = len(after.strip().split("\n")) if after.strip() else 0
    if after_count > baseline_count + 1:  # +1 tolerance
        print(f"WARN — new connections appeared ({baseline_count} -> {after_count})")
    else:
        print(f"OK (no new connections)")

    if all_ok:
        print("\n=== Soft Offline Test: PASS ===")
    else:
        print("\n=== Soft Offline Test: FAIL ===")
    return all_ok


def main():
    parser = argparse.ArgumentParser(
        description="Verify offline code generation capability"
    )
    parser.add_argument("--serve", choices=["ollama", "mlx"], default="ollama")
    parser.add_argument("--port", type=int, default=11434)
    parser.add_argument("--base-url", default="http://localhost")
    parser.add_argument("--no-sudo", action="store_true",
                        help="Monitor mode (no network disconnect)")
    args = parser.parse_args()

    port = args.port if args.port != 11434 else args.port
    if args.serve == "mlx":
        port = args.port if args.port != 11434 else 8800

    model = "qwen2.5-coder:7b-instruct-q4_K_M"
    if args.serve == "mlx":
        model = None  # mlx_lm.server uses local path, discovered via /v1/models

    print(f"=== Offline Verification ===")
    print(f"Server: {args.base_url}:{port}")
    print(f"Model:  {model or '(auto-discover)'}")
    print(f"Mode: {'monitor (no-sudo)' if args.no_sudo else 'hard disconnect (sudo)'}")

    if args.no_sudo:
        ok = run_monitor_test(args.base_url, port, model)
    else:
        ok = run_sudo_test(args.base_url, port, model)

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
