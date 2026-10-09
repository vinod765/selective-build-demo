#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Iterable

ALL_PLATFORMS = ("broadcom", "mellanox", "marvell-prestera-arm64", "marvell-prestera-armhf", "nvidia-bluefield", "aspeed-arm64", "vs")
GLOBAL_PATHS = ("Makefile", "azure-pipelines.yml", ".azure-pipelines/", "scripts/")
PLATFORM_PATHS = {
    "broadcom": ("platform/broadcom/",),
    "mellanox": ("platform/mellanox/",),
    "marvell-prestera-arm64": ("platform/marvell-prestera/",),
    "marvell-prestera-armhf": ("platform/marvell-prestera/",),
    "nvidia-bluefield": ("platform/nvidia-bluefield/",),
    "aspeed-arm64": ("platform/aspeed/",),
    "vs": ("platform/vs/",),
}

def path_matches(path: str, pattern: str) -> bool:
    return path == pattern.rstrip("/") or path.startswith(pattern) if pattern.endswith("/") else path == pattern

def select_platforms(changed_paths: Iterable[str], mode: str = "path") -> dict:
    if mode not in {"path", "all"}:
        raise ValueError(f"unsupported selection mode: {mode}")
    paths = sorted({path for path in changed_paths if path})
    if mode == "all":
        return {"mode": "all", "run_all": True, "run_vs_tests": True, "platforms": list(ALL_PLATFORMS), "changed_paths": paths, "reasons": ["all-platform mode requested"]}
    selected, reasons = set(), []
    run_all = run_vs_tests = False
    for path in paths:
        global_match = next((pattern for pattern in GLOBAL_PATHS if path_matches(path, pattern)), None)
        if global_match:
            run_all = run_vs_tests = True
            reasons.append(f"{path} matched global path {global_match}")
            continue
        matched = [platform for platform, patterns in PLATFORM_PATHS.items() if any(path_matches(path, pattern) for pattern in patterns)]
        if not matched:
            run_all = run_vs_tests = True
            reasons.append(f"{path} did not match a known path")
            continue
        selected.update(matched)
        reasons.append(f"{path} selected {', '.join(sorted(matched))}")
        if "vs" in matched:
            run_vs_tests = True
    if run_all or not paths:
        selected = set(ALL_PLATFORMS)
        run_all = run_vs_tests = True
        if not paths:
            reasons.append("no changed paths were detected")
    return {"mode": "path", "run_all": run_all, "run_vs_tests": run_vs_tests, "platforms": [p for p in ALL_PLATFORMS if p in selected], "changed_paths": paths, "reasons": reasons}

def get_changed_paths(base: str, head: str) -> list[str]:
    result = subprocess.run(["git", "diff", "--name-only", "--diff-filter=ACMRD", f"{base}..{head}"], check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return sorted({line.strip() for line in result.stdout.splitlines() if line.strip()})

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--mode", choices=("path", "all"), default="path")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        decision = select_platforms(get_changed_paths(args.base, args.head), args.mode)
    except (subprocess.CalledProcessError, ValueError) as error:
        print(f"selective build decision failed: {error}", file=sys.stderr)
        return 2
    rendered = json.dumps(decision, indent=2)
    print(rendered)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
