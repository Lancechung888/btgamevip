#!/usr/bin/env python3
"""Require usable footer home links on every rendered Jekyll article."""

import argparse
from html.parser import HTMLParser
from pathlib import Path


class ArticleFooter(HTMLParser):
    def __init__(self):
        super().__init__()
        self.article = False
        self.footer = False
        self.in_footer = False
        self.regions = []
        self.anchor = None
        self.links = {"footer-heading": [], "p-name": []}

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        classes = attrs.get("class", "").split()
        if tag == "article" and "post" in classes:
            self.article = True
        if tag == "footer" and "site-footer" in classes:
            self.footer = self.in_footer = True
        if not self.in_footer:
            return
        for region in self.links:
            if region in classes:
                self.regions.append((tag, region))
        if tag == "a" and self.regions:
            self.anchor = [self.regions[-1][1], attrs.get("href"), ""]

    def handle_data(self, data):
        if self.anchor is not None:
            self.anchor[2] += data

    def handle_endtag(self, tag):
        if tag == "a" and self.anchor is not None:
            region, href, text = self.anchor
            self.links[region].append((href, text.strip()))
            self.anchor = None
        if self.regions and self.regions[-1][0] == tag:
            self.regions.pop()
        if tag == "footer":
            self.in_footer = False

    def errors(self, home="/"):
        if not self.article:
            return []
        if not self.footer:
            return ["article has no shared footer"]
        return [f"{region} needs a named anchor to {home}" for region, links in self.links.items()
                if not any(href == home and text for href, text in links)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", type=Path)
    parser.add_argument("--home", default="/")
    args = parser.parse_args()
    count = 0
    failures = []
    for file in sorted(args.site.rglob("*.html")):
        page = ArticleFooter()
        page.feed(file.read_text(encoding="utf-8"))
        count += int(page.article)
        failures.extend(f"{file.relative_to(args.site)}: {error}" for error in page.errors(args.home))
    if not count:
        failures.append("no rendered articles found; refusing an empty check")
    for failure in failures:
        print(failure)
    print(f"Article footer links: {count} articles, {len(failures)} failures")
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
