#!/usr/bin/env python3
"""Prompt for a restricted token and configure notification secrets without logging it."""

from getpass import getpass
import json
from pathlib import Path
import subprocess
import sys


def main():
    """Read the registry and send one user-supplied token to each source's Actions secret."""
    root = Path(__file__).resolve().parents[1]
    registry = json.loads((root / "content/projects.json").read_text())
    entries = registry["projects"]
    entries = entries + [child for entry in entries for child in entry.get("components", [])]
    repositories = sorted({entry["repository"] for entry in entries if "repository" in entry})
    print("Use a fine-grained token restricted to PanoPepino/PanoPepino, Contents read/write.")
    print("This stores PROFILE_SYNC_TOKEN in: " + ", ".join(repositories))
    if not sys.stdin.isatty():
        raise SystemExit("Run in an interactive terminal; do not pass a token on the command line.")
    token = getpass("Fine-grained token (hidden): ").strip()
    if not token.startswith("github_pat_"):
        raise SystemExit("Expected a fine-grained GitHub token. No secrets were changed.")
    for repository in repositories:
        result = subprocess.run(
            ["gh", "secret", "set", "PROFILE_SYNC_TOKEN", "--repo", repository],
            input=token, text=True, capture_output=True, timeout=60,
        )
        if result.returncode:
            raise SystemExit(f"Secret setup failed for {repository}; check GitHub CLI access and retry.")
        print(f"Configured {repository}")
    print("All five notification secrets configured. Run each notifier to verify dispatch.")


if __name__ == "__main__":
    main()
