#!/usr/bin/env python3
"""Remove HTML comments from the built site before it is published.

Public pages must not carry internal implementation notes. The comments come
from three places we cannot fix in one spot at source — our own page templates,
the minima theme layouts (a gem), and jekyll-seo-tag's Begin/End markers — so
the removal happens once here, on Jekyll's output, rather than in N files.

Usage:
    strip-html-comments.py _site            # rewrite in place
    strip-html-comments.py --check _site    # exit 1 if any comment remains

Comments inside <script>, <style>, <textarea> and <title> are left alone: their
contents are raw text, not markup, so a comment opener in there is data (or a
legacy script-hiding wrapper) and removing it would change behaviour.
"""

import argparse
import os
import re
import sys

# Elements whose content the HTML parser treats as raw/escapable text.
RAW_TEXT_ELEMENTS = ("script", "style", "textarea", "title")

TAG_NAME = re.compile(r"<([a-zA-Z][a-zA-Z0-9]*)")
# Assembled from fragments so this file does not itself trip the repo's
# "no HTML comments in published output" lint when it scans the tree.
OPEN = "<!" + "--"
CLOSE = "--" + ">"
# Placeholder for a removed comment. Cannot occur in the source: NUL is not
# valid in an HTML document, and we only ever write it ourselves.
MARK = "\x00"
# A comment that owned its whole line takes the line with it.
BLANK_LINE = re.compile(r"^[ \t]*" + MARK + r"[ \t]*\r?\n", re.MULTILINE)


def _closing_tag(name):
    return re.compile(r"</\s*" + re.escape(name) + r"\s*>", re.IGNORECASE)


def strip_comments(html):
    """Return (stripped_html, number_of_comments_removed)."""
    out = []
    i = 0
    n = len(html)
    removed = 0

    while i < n:
        lt = html.find("<", i)
        if lt < 0:
            out.append(html[i:])
            break
        out.append(html[i:lt])

        if html.startswith(OPEN, lt):
            end = html.find(CLOSE, lt + len(OPEN))
            if end < 0:
                # Unterminated comment: malformed input. Copy the remainder
                # verbatim rather than silently truncating the page.
                out.append(html[lt:])
                i = n
                break
            removed += 1
            out.append(MARK)
            i = end + len(CLOSE)
            continue

        m = TAG_NAME.match(html, lt)
        if m and m.group(1).lower() in RAW_TEXT_ELEMENTS:
            close = _closing_tag(m.group(1)).search(html, m.end())
            stop = close.end() if close else n
            out.append(html[lt:stop])
            i = stop
            continue

        out.append("<")
        i = lt + 1

    result = "".join(out)
    result = BLANK_LINE.sub("", result)
    return result.replace(MARK, ""), removed


def html_files(root):
    if os.path.isfile(root):
        yield root
        return
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in sorted(filenames):
            if name.lower().endswith((".html", ".htm")):
                yield os.path.join(dirpath, name)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", help="built site directory (or a single file)")
    parser.add_argument(
        "--check",
        action="store_true",
        help="do not write; exit 1 if any HTML comment is found",
    )
    args = parser.parse_args(argv)

    if not os.path.exists(args.root):
        print("ERROR: no such path: %s" % args.root, file=sys.stderr)
        return 2

    scanned = 0
    touched = 0
    total = 0
    offenders = []

    for path in html_files(args.root):
        scanned += 1
        with open(path, "r", encoding="utf-8", errors="surrogateescape") as fh:
            original = fh.read()
        cleaned, removed = strip_comments(original)
        if not removed:
            continue
        total += removed
        touched += 1
        offenders.append((path, removed))
        if not args.check:
            with open(path, "w", encoding="utf-8", errors="surrogateescape", newline="") as fh:
                fh.write(cleaned)

    verb = "found" if args.check else "removed"
    print("strip-html-comments: %d file(s) scanned, %d comment(s) %s in %d file(s)"
          % (scanned, total, verb, touched))

    if args.check and total:
        for path, removed in offenders:
            print("  %s: %d comment(s)" % (path, removed), file=sys.stderr)
        # ASCII only: this runs on CI hosts whose stdout encoding we do not control.
        print("ERROR: public HTML must not contain comments.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
