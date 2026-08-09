#!/usr/bin/env python3
"""Run the rendered pre-push gates without a local Jekyll installation.

This helper is intentionally not a Markdown renderer.  The caller supplies the
candidate page exactly as it will appear in Jekyll's output.  The helper then
materializes every handwritten page named by ``redline_rules.json`` beside the
candidate, strips build-time HTML comments, and runs the same three checks as
the Pages workflow.

Example (run from the repository root):

    python tools/rendered_pre_push.py candidate.html \
      --candidate-path 2026/08/08/mycard-discount-guide.html

Use ``--output-root`` when another agent needs the assembled build fixture.
The directory must not already exist; this tool never overwrites a prior build.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile


TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parent
RULES = TOOLS / "redline_rules.json"
STRIP = TOOLS / "strip-html-comments.py"
LINT = TOOLS / "redline_lint_site.py"


class FixtureError(Exception):
    """A fail-closed fixture construction error."""


def safe_relative_path(value: str, label: str) -> PurePosixPath:
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or not path.parts or any(part in ("", ".", "..") for part in path.parts):
        raise FixtureError(f"{label} must be a safe relative path: {value!r}")
    if path.suffix.lower() not in (".html", ".htm"):
        raise FixtureError(f"{label} must name an HTML file: {value!r}")
    return path


def load_named_pages() -> list[PurePosixPath]:
    try:
        raw = json.loads(RULES.read_text(encoding="utf-8"))
        entries = raw["handwritten_chrome"]["pages"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise FixtureError(f"cannot load handwritten_chrome pages from {RULES}: {exc}") from exc
    if not isinstance(entries, list) or not entries:
        raise FixtureError("handwritten_chrome.pages must be a non-empty list")

    pages = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise FixtureError(f"handwritten_chrome.pages[{index}] has no string path")
        pages.append(safe_relative_path(entry["path"], f"handwritten_chrome.pages[{index}].path"))
    if len(set(pages)) != len(pages):
        raise FixtureError("handwritten_chrome.pages contains a duplicate path")
    return pages


def rendered_handwritten_source(source: Path) -> str:
    try:
        text = source.read_text(encoding="utf-8")
    except OSError as exc:
        raise FixtureError(f"cannot read named handwritten page {source}: {exc}") from exc

    # Jekyll removes YAML front matter from layout:null pages.  These pages are
    # otherwise complete handwritten HTML, so removing that envelope is the
    # only rendering step required for them.
    lines = text.splitlines(keepends=True)
    if lines and lines[0].strip() == "---":
        for index, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                return "".join(lines[index + 1 :])
        raise FixtureError(f"unterminated YAML front matter in {source}")
    return text


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def run_gate(label: str, args: list[str]) -> None:
    print(f"\n=== {label} ===", flush=True)
    # Some findings contain characters outside the active Windows console code
    # page.  Force UTF-8 so reporting a warning cannot crash the fail-closed
    # linter before it emits its REDLINE summary.
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    proc = subprocess.run(args, cwd=REPO, env=env)
    if proc.returncode:
        raise FixtureError(f"{label} failed with exit code {proc.returncode}")


def assemble(root: Path, candidate: Path, candidate_path: PurePosixPath) -> int:
    named_pages = load_named_pages()
    if candidate_path in named_pages:
        raise FixtureError("candidate path collides with a named handwritten_chrome page")
    if not candidate.is_file():
        raise FixtureError(f"candidate rendered page does not exist: {candidate}")

    for relative in named_pages:
        source = REPO.joinpath(*relative.parts)
        if not source.is_file():
            raise FixtureError(f"named handwritten_chrome source is missing: {relative}")
        write_text(root.joinpath(*relative.parts), rendered_handwritten_source(source))

    target = root.joinpath(*candidate_path.parts)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(candidate, target)
    expected = len(named_pages) + 1
    actual = sum(1 for path in root.rglob("*") if path.is_file() and path.suffix.lower() in (".html", ".htm"))
    if actual != expected:
        raise FixtureError(f"fixture page count mismatch: expected {expected}, found {actual}")
    print(f"Fixture ready: {len(named_pages)} named handwritten page(s) + 1 candidate = {actual} HTML page(s)")
    return actual


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_html", help="rendered candidate HTML file")
    parser.add_argument("--candidate-path", required=True, help="candidate path inside the rendered build")
    parser.add_argument("--output-root", help="keep the assembled fixture at this new directory")
    args = parser.parse_args(argv)

    temp = None
    try:
        candidate_path = safe_relative_path(args.candidate_path, "--candidate-path")
        candidate = Path(args.candidate_html).resolve()
        if args.output_root:
            root = Path(args.output_root).resolve()
            if root.exists():
                raise FixtureError(f"--output-root already exists (refusing to overwrite): {root}")
            root.mkdir(parents=True)
        else:
            temp = tempfile.TemporaryDirectory(prefix="rendered-pre-push-")
            root = Path(temp.name)

        assemble(root, candidate, candidate_path)
        # Match the Pages workflow order.  No command is optional and failures
        # propagate immediately; there is no baseline or error suppression.
        run_gate("Strip HTML comments from build output", [sys.executable, str(STRIP), str(root)])
        run_gate("Verify no HTML comments are published", [sys.executable, str(STRIP), "--check", str(root)])
        run_gate("Redline lint (rendered HTML chrome)", [sys.executable, str(LINT), "--site-root", str(root)])
        run_gate(
            "Redline lint (build output, fail-closed)",
            [sys.executable, str(LINT), "--build-root", str(root), "--rules", str(RULES)],
        )
        print(f"\nRENDERED PRE-PUSH: PASS pages={sum(1 for _ in root.rglob('*.html'))}")
        if args.output_root:
            print(f"Build fixture: {root}")
        return 0
    except FixtureError as exc:
        print(f"\nRENDERED PRE-PUSH: FAIL: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - fail closed on the harness itself
        print(f"\nRENDERED PRE-PUSH: FAIL: unexpected error: {exc}", file=sys.stderr)
        return 2
    finally:
        if temp is not None:
            temp.cleanup()


if __name__ == "__main__":
    sys.exit(main())
