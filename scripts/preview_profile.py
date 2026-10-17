#!/usr/bin/env python3
"""Render the local profile with GitHub's Markdown API into a standalone HTML preview."""

import argparse
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
STYLE = """+:root {color-scheme:dark; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
background:#0d1117;color:#f0f6fc;font-size:16px;line-height:1.5}
* {box-sizing:border-box} body {margin:0;padding:28px 20px 60px}
.notice {max-width:980px;margin:0 auto 16px;color:#9198a1;font-size:13px}
article {max-width:980px;margin:auto;padding:32px;border:1px solid #3d444d;border-radius:6px;overflow-wrap:break-word}
h1,h2,h3,h4 {font-weight:600;line-height:1.25;margin:24px 0 16px}
h1 {font-size:2em} h2 {font-size:1.5em} h3 {font-size:1.25em} h4 {font-size:1em}
h1,h2 {border-bottom:1px solid #3d444d;padding-bottom:.3em}
p,ul,ol {margin:0 0 16px} a {color:#4493f8;text-decoration:none} a:hover {text-decoration:underline}
code {font:85% ui-monospace,SFMono-Regular,Consolas,monospace;background:#656c7633;padding:.2em .4em;border-radius:6px;line-height:2}
img {max-width:100%;vertical-align:middle} hr {height:3px;background:#3d444d;border:0;margin:24px 0}
.anchor {display:none} [align=center] {text-align:center}
@media(max-width:600px) {body{padding:16px 10px} article{padding:18px} h1{font-size:1.6em}}
"""


def main():
    """Send public README text for Markdown rendering and write the requested HTML file."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / ".preview/index.html")
    parser.add_argument("--rendered-html", type=Path, help="Use an existing GitHub Markdown API response")
    args = parser.parse_args()
    payload = {"text": (ROOT / "README.md").read_text(), "mode": "gfm", "context": "PanoPepino/PanoPepino"}
    if args.rendered_html:
        rendered = args.rendered_html.read_text()
    else:
        rendered = subprocess.run(
            ["gh", "api", "--method", "POST", "markdown", "--input", "-"],
            input=json.dumps(payload), text=True, capture_output=True, check=True, timeout=60,
        ).stdout
    document = (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>PanoPepino — local profile preview</title>'
        f'<style>{STYLE}</style><body><div class="notice">PanoPepino / README.md · Local preview · '
        'GitHub-rendered Markdown with approximate dark-theme styling</div>'
        f'<article>{rendered}</article></body></html>'
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(document)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
