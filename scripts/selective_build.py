#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Iterable


ALL_PLATFORMS = (
    "vs",
    "vpp",
    "alpinevs",
    "broadcom",
    "mellanox",
    "marvell-prestera-arm64",
    "marvell-prestera-armhf",
    "nvidia-bluefield",
    "aspeed-arm64",
)


GLOBAL_PATHS = (
    "Makefile",
    "Makefile.work",
    "slave.mk",
    "azure-pipelines.yml",
    ".azure-pipelines/",
    ".github/",
    "rules/",
)


PLATFORM_PATHS = {
    "vs": (
        "platform/vs/",
    ),
    "vpp": (
        "platform/vpp/",
    ),
    "alpinevs": (
        "platform/alpinevs/",
    ),
    "broadcom": (
        "platform/broadcom/",
    ),
    "mellanox": (
        "platform/mellanox/",
    ),
    "marvell-prestera-arm64": (
        "platform/marvell-prestera/",
    ),
    "marvell-prestera-armhf": (
        "platform/marvell-prestera/",
    ),
    "nvidia-bluefield": (
        "platform/nvidia-bluefield/",
    ),
    "aspeed-arm64": (
        "platform/aspeed/",
    ),
}


def path_matches(path: str, pattern: str) -> bool:
    """Return True for an exact file match or directory-prefix match."""
    if pattern.endswith("/"):
        directory = pattern.rstrip("/")
        return path == directory or path.startswith(pattern)

    return path == pattern


def all_platforms_result(
    changed_paths: list[str],
    mode: str,
    reason: str,
) -> dict:
    """Return a decision that enables every platform."""
    return {
        "mode": mode,
        "run_all": True,
        "run_vs_tests": True,
        "platforms": list(ALL_PLATFORMS),
        "changed_paths": changed_paths,
        "reasons": [reason],
    }


def select_platforms(
    changed_paths: Iterable[str],
    mode: str = "path",
) -> dict:
    """
    Select platform jobs based on changed paths.

    path mode:
      - known platform paths select only matching platforms;
      - global paths select every platform;
      - unknown paths select every platform safely;
      - no paths select every platform safely.

    all mode:
      - every platform is selected.
    """
    if mode not in {"path", "all"}:
        raise ValueError(f"Unsupported selection mode: {mode}")

    paths = sorted(
        {
            path.strip()
            for path in changed_paths
            if path and path.strip()
        }
    )

    if mode == "all":
        return all_platforms_result(
            changed_paths=paths,
            mode="all",
            reason="all-platform mode requested",
        )

    if not paths:
        return all_platforms_result(
            changed_paths=paths,
            mode="path",
            reason="no changed paths detected",
        )

    selected: set[str] = set()
    reasons: list[str] = []
    run_vs_tests = False

    for path in paths:
        global_match = next(
            (
                pattern
                for pattern in GLOBAL_PATHS
                if path_matches(path, pattern)
            ),
            None,
        )

        if global_match:
            reasons.append(
                f"{path} matched global path {global_match}"
            )

            result = all_platforms_result(
                changed_paths=paths,
                mode="path",
                reason=f"global path detected: {global_match}",
            )
            result["reasons"] = reasons
            return result

        matched_platforms = [
            platform
            for platform, patterns in PLATFORM_PATHS.items()
            if any(
                path_matches(path, pattern)
                for pattern in patterns
            )
        ]

        if not matched_platforms:
            reasons.append(
                f"{path} did not match a known platform path"
            )

            result = all_platforms_result(
                changed_paths=paths,
                mode="path",
                reason="unknown path detected",
            )
            result["reasons"] = reasons
            return result

        selected.update(matched_platforms)

        if "vs" in matched_platforms:
            run_vs_tests = True

        reasons.append(
            f"{path} selected "
            f"{', '.join(sorted(matched_platforms))}"
        )

    return {
        "mode": "path",
        "run_all": False,
        "run_vs_tests": run_vs_tests,
        "platforms": [
            platform
            for platform in ALL_PLATFORMS
            if platform in selected
        ],
        "changed_paths": paths,
        "reasons": reasons,
    }


def get_changed_paths(base: str, head: str) -> list[str]:
    """Return files changed from the merge-base to the head revision."""
    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "--diff-filter=ACMRD",
            f"{base}...{head}",
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    return sorted(
        {
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip()
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Select demo platform jobs from changed paths."
    )

    parser.add_argument(
        "--base",
        required=True,
        help="Base branch or commit.",
    )

    parser.add_argument(
        "--head",
        required=True,
        help="Head branch or commit.",
    )

    parser.add_argument(
        "--mode",
        choices=("path", "all"),
        default="path",
        help="Use changed-path selection or select all platforms.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON output file.",
    )

    args = parser.parse_args()

    changed_paths = get_changed_paths(
        args.base,
        args.head,
    )

    decision = select_platforms(
        changed_paths,
        mode=args.mode,
    )

    rendered = json.dumps(
        decision,
        indent=2,
    )

    print(rendered)

    if args.output:
        args.output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        args.output.write_text(
            rendered + "\n",
            encoding="utf-8",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())