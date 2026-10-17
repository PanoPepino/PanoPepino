#!/usr/bin/env python3
"""Render approved project copy into the marked GitHub profile section."""

import argparse
import base64
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
START = "<!-- PROJECTS:START -->"
END = "<!-- PROJECTS:END -->"
SECTIONS = ("SHARED", "WEBPAGE", "PANOPEPINO")


def parse_source(text):
    """Validate three source blocks and return title, tags and destination copy."""
    blocks = {}
    remaining = text
    for name in SECTIONS:
        start, end = f"<!-- {name}:START -->", f"<!-- {name}:END -->"
        if text.count(start) != 1 or text.count(end) != 1:
            raise ValueError(f"Expected one {name} marker pair")
        before, rest = remaining.split(start, 1)
        body, remaining = rest.split(end, 1)
        if before.strip() or not body.strip() or "<" in body or ">" in body:
            raise ValueError(f"Invalid {name} block or marker order")
        blocks[name] = body.strip()
    if remaining.strip():
        raise ValueError("Content outside source markers")

    lines = blocks["SHARED"].splitlines()
    if not re.fullmatch(r"# [\wÀ-ž .+–-]+", lines[0]):
        raise ValueError("SHARED must start with one plain project title")
    tags = " ".join(line.strip() for line in lines[1:] if line.strip()).split(" · ")
    if not tags or any(not re.fullmatch(r"[\w .+/-]+", tag) for tag in tags):
        raise ValueError("SHARED must contain technologies separated by ·")
    for destination in ("WEBPAGE", "PANOPEPINO"):
        if re.search(r"^#", blocks[destination], re.M):
            raise ValueError("Destination copy must not contain headings")
        for link in re.findall(r"\]\(([^)]+)\)", blocks[destination]):
            validate_url(link)
    return {"title": lines[0][2:], "tags": tags, **blocks}


def validate_url(value):
    """Reject public links without an HTTPS host or with Markdown delimiters."""
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname or any(c in value for c in "()<> \n\r"):
        raise ValueError(f"Invalid public HTTPS URL: {value}")


def api_json(path):
    """Read a GitHub API path with optional runner authentication and a timeout."""
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "portfolio-profile-sync"}
    token = os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"https://api.github.com/{path}", headers=headers)
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def load_source(entry, remote, workspace, revisions):
    """Read an explicit local file or public repository file pinned to one commit."""
    if "local" in entry:
        path = (ROOT / entry["local"]).resolve()
        if not path.is_relative_to(ROOT):
            raise ValueError("Profile source escapes repository")
        return parse_source(path.read_bytes().decode("utf-8"))
    repository = entry["repository"]
    if not re.fullmatch(r"PanoPepino/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Unexpected source repository")
    if not remote:
        path = (workspace / entry["checkout"] / "README_FOR_WEBPAGE.md").resolve()
        if not path.is_relative_to(workspace):
            raise ValueError("Project source escapes workspace")
        return parse_source(path.read_bytes().decode("utf-8"))
    if repository not in revisions:
        metadata = api_json(f"repos/{repository}")
        if metadata["private"]:
            raise ValueError("Remote sources must be public")
        branch = quote(metadata["default_branch"], safe="")
        revision = api_json(f"repos/{repository}/commits/{branch}")["sha"]
        revisions[repository] = revision
        print(f"Source {repository}@{revision}")
    revision = revisions[repository]
    content = api_json(f"repos/{repository}/contents/README_FOR_WEBPAGE.md?ref={revision}")
    return parse_source(base64.b64decode(content["content"], validate=False).decode("utf-8"))


def render_projects(entries, remote=False, workspace=None):
    """Render registry order and nested Manim components using profile-only copy."""
    revisions, seen = {}, set()

    def render(entry, level):
        """Render one validated entry and its optional component children."""
        identifier = entry["id"]
        if not re.fullmatch(r"[a-z0-9-]+", identifier) or identifier in seen:
            raise ValueError(f"Invalid or duplicate project ID: {identifier}")
        seen.add(identifier)
        source = load_source(entry, remote, workspace or ROOT.parent, revisions)
        title = source["title"]
        url = entry.get("url")
        if url:
            validate_url(url)
            title = f"[{title}]({url})"
        tags = " ".join(f"`{tag}`" for tag in source["tags"])
        output = [f"{'#' * level} {title}", source["PANOPEPINO"], tags]
        for child in entry.get("components", []):
            output.append(render(child, level + 1))
        return "\n\n".join(output)

    return "\n\n".join(render(entry, 3) for entry in entries)


def replace_section(original, generated):
    """Replace one ordered marker pair while preserving surrounding bytes as text."""
    if original.count(START) != 1 or original.count(END) != 1:
        raise ValueError("README must contain exactly one PROJECTS marker pair")
    before, rest = original.split(START, 1)
    if END in before:
        raise ValueError("README markers are out of order")
    _, after = rest.split(END, 1)
    return before + START + "\n\n" + generated + "\n\n" + END + after


def main():
    """Validate all inputs, then check or write the generated profile README."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote", action="store_true", help="Read public GitHub sources")
    parser.add_argument("--workspace", type=Path, default=ROOT.parent, help="Local portfolio directory")
    parser.add_argument("--check", action="store_true", help="Fail on drift without writing")
    args = parser.parse_args()
    registry = json.loads((ROOT / "content/projects.json").read_text())
    if registry.get("version") != 1 or not registry.get("projects"):
        raise ValueError("Expected version 1 registry with projects")
    generated = render_projects(registry["projects"], args.remote, args.workspace.resolve())
    target = ROOT / "README.md"
    original = target.read_bytes().decode("utf-8")
    updated = replace_section(original, generated)
    if updated == original:
        print("Profile is up to date")
    elif args.check:
        raise ValueError("Profile differs from approved project sources; run scripts/sync_projects.py")
    else:
        target.write_bytes(updated.encode("utf-8"))
        print("Updated README.md Selected Projects")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError) as error:
        print(f"Sync failed: {error}", file=sys.stderr)
        sys.exit(1)
