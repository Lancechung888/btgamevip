#!/usr/bin/env python3
"""Report residual Simplified Chinese without changing the input."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Callable, Iterable

HERE = Path(__file__).resolve().parent
WORDBANK_PATH = HERE.parent / "references" / "wordbank.json"
HAN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


class ScanError(RuntimeError):
    """Fail-closed scanner error."""


def load_opencc() -> tuple[Callable[[str], str], Callable[[str], str]]:
    try:
        from opencc import OpenCC

        s2t = OpenCC("s2t")
        s2twp = OpenCC("s2twp")
    except Exception as exc:  # dependency/config failures share exit 2
        raise ScanError(
            "setup_required: an existing OpenCC Python package is required"
        ) from exc
    return s2t.convert, s2twp.convert


def load_wordbank() -> dict:
    try:
        data = json.loads(WORDBANK_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ScanError(f"invalid wordbank: {exc}") from exc
    allowed = {"priority_terms", "review_only_chars"}
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise ScanError(f"wordbank contains unknown keys: {', '.join(unknown)}")
    if not isinstance(data.get("priority_terms", {}), dict):
        raise ScanError("wordbank priority_terms must be an object")
    if not isinstance(data.get("review_only_chars", []), list):
        raise ScanError("wordbank review_only_chars must be an array")
    return data


def extract_han_run(line: str, index: int) -> str:
    start = index
    while start > 0 and HAN.fullmatch(line[start - 1]):
        start -= 1
    end = index + 1
    while end < len(line) and HAN.fullmatch(line[end]):
        end += 1
    return line[start:end]


def priority_term_at(line: str, index: int, terms: dict[str, str]) -> tuple[str, str] | None:
    matches: list[tuple[str, str]] = []
    for source, target in terms.items():
        cursor = 0
        while True:
            found = line.find(source, cursor)
            if found < 0:
                break
            if found <= index < found + len(source):
                matches.append((source, target))
            cursor = found + 1
    return max(matches, key=lambda item: len(item[0]), default=None)


def scan_text(
    text: str,
    source_label: str,
    convert_char: Callable[[str], str],
    convert_term: Callable[[str], str],
    wordbank: dict,
) -> list[dict]:
    priority_terms: dict[str, str] = wordbank.get("priority_terms", {})
    review_only = set(wordbank.get("review_only_chars", []))
    findings: list[dict] = []

    for line_number, line in enumerate(text.splitlines(), start=1):
        for column, char in enumerate(line, start=1):
            if not HAN.fullmatch(char):
                continue
            suggested_char = convert_char(char)
            if suggested_char == char:
                continue

            override = priority_term_at(line, column - 1, priority_terms)
            source_term = override[0] if override else extract_han_run(line, column - 1)
            suggested_term = override[1] if override else convert_term(source_term)
            severity = "FIX" if override or char not in review_only else "REVIEW"
            reason = (
                "deterministic phrase override"
                if override
                else "context-sensitive character; review the full phrase"
                if severity == "REVIEW"
                else "OpenCC Simplified-to-Traditional difference"
            )
            findings.append(
                {
                    "file": source_label,
                    "line": line_number,
                    "column": column,
                    "character": char,
                    "suggestedCharacter": suggested_char,
                    "term": source_term,
                    "suggestedTerm": suggested_term,
                    "severity": severity,
                    "reason": reason,
                    "context": line.strip()[:160],
                }
            )
    return findings


def iter_files(paths: Iterable[Path], extensions: set[str]) -> Iterable[Path]:
    for path in paths:
        if not path.exists():
            raise ScanError(f"input does not exist: {path}")
        if path.is_file():
            yield path
            continue
        for child in sorted(path.rglob("*")):
            if child.is_file() and (not extensions or child.suffix.lower() in extensions):
                yield child


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="Files or directories to scan")
    parser.add_argument("--stdin", action="store_true", help="Read UTF-8 text from stdin")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument("--pretty", action="store_true", help="Indent JSON or show readable text")
    parser.add_argument(
        "--ext",
        default=".html,.htm,.md,.txt,.json,.xml,.js,.yml,.yaml",
        help="Comma-separated extensions used for directory scans",
    )
    parser.add_argument(
        "--fail-on",
        choices=("fix", "any", "none"),
        default="fix",
        help="Select which findings produce exit 1",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.stdin and args.paths:
        raise ScanError("use --stdin or paths, not both")
    if not args.stdin and not args.paths:
        raise ScanError("provide at least one path or --stdin")

    convert_char, convert_term = load_opencc()
    wordbank = load_wordbank()
    findings: list[dict] = []

    if args.stdin:
        findings.extend(
            scan_text(sys.stdin.read(), "<stdin>", convert_char, convert_term, wordbank)
        )
    else:
        extensions = {
            ext.lower() if ext.startswith(".") else f".{ext.lower()}"
            for ext in args.ext.split(",")
            if ext.strip()
        }
        for path in iter_files((Path(value) for value in args.paths), extensions):
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                raise ScanError(f"cannot read UTF-8 input {path}: {exc}") from exc
            findings.extend(
                scan_text(text, str(path), convert_char, convert_term, wordbank)
            )

    fix_count = sum(item["severity"] == "FIX" for item in findings)
    review_count = sum(item["severity"] == "REVIEW" for item in findings)
    result = {
        "status": "findings" if findings else "clean",
        "summary": {"fix": fix_count, "review": review_count, "total": len(findings)},
        "findings": findings,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    else:
        for item in findings:
            print(
                f"{item['file']}:{item['line']}:{item['column']} "
                f"[{item['severity']}] {item['character']}→{item['suggestedCharacter']} "
                f"{item['term']}→{item['suggestedTerm']} ({item['reason']})"
            )
        print(f"SUMMARY FIX={fix_count} REVIEW={review_count} TOTAL={len(findings)}")

    if args.fail_on == "none":
        return 0
    if args.fail_on == "any":
        return 1 if findings else 0
    return 1 if fix_count else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ScanError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
