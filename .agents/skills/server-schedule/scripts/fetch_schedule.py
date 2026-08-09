#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
server-schedule / fetch_schedule.py

Fetch u2's PUBLIC server-opening schedule (開服表) page and emit structured JSON.

HARD LIMITS:
  * READ-ONLY: performs a single HTTP GET of the public schedule page. No POST,
    no form submit, no login, no cookies, no session.
  * DOES NOT click / follow / fetch any link on the page. The per-game detail
    href is READ as text (to extract the game id) but never requested.
  * DOES NOT follow redirects. A 3xx response is treated as "page may require
    login / verification" -> STOP and report (exit 2). We do not bypass.
  * If the schedule block is missing, or login/captcha markers are present,
    STOP and report (exit 2) instead of guessing.

This page (https://www.u2game99.com/game/server/index.html) is a public
information page, NOT an affiliate referral short-link, so reading it does not
touch attribution (no slug hit, no 302 follow) — the attribution red-line is
about /go/<slug> short-links, which this script never contacts.

Usage:
    python fetch_schedule.py [--url URL] [--out FILE] [--pretty]
Exit codes: 0 ok | 2 stop-and-report (login/verify/blocked) | 1 unexpected error
"""
import argparse
import json
import re
import sys
import urllib.request
import urllib.error

DEFAULT_URL = "https://www.u2game99.com/game/server/index.html"
UA = "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Mobile Safari/537.36"

# Markers that mean the page is forcing a human-verification / captcha wall.
# If any appears we STOP rather than attempt to bypass.
# NOTE: a plain "登录/登入" LINK in the site header is normal chrome on a public
# page and is NOT a block — the real "requires login" signal is the schedule
# block being absent, which parse() catches. So we only hard-stop on captcha /
# forced-verification markers here, not on the mere word "login".
BLOCK_MARKERS = ("验证码", "驗證碼", "captcha", "geetest",
                 "滑动验证", "滑動驗證", "人机验证", "人機驗證", "safe-verify")


class StopAndReport(Exception):
    """Raised when the page requires login / verification / is otherwise blocked."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse to follow any redirect — surfaces 3xx as an error we can inspect."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise StopAndReport(
            "server returned redirect %s -> %s; a public schedule page should "
            "answer 200 directly. Not following (possible login/verify wall)." % (code, newurl))


def fetch(url):
    opener = urllib.request.build_opener(_NoRedirect)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    try:
        with opener.open(req, timeout=20) as resp:
            status = resp.getcode()
            raw = resp.read()
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308):
            raise StopAndReport("HTTP %s redirect — not following (possible login/verify)." % e.code)
        raise StopAndReport("HTTP %s from schedule page." % e.code)
    if status != 200:
        raise StopAndReport("non-200 (%s) from schedule page." % status)
    html = raw.decode("utf-8", errors="replace")
    low = html.lower()
    for mk in BLOCK_MARKERS:
        if mk in html or mk in low:
            raise StopAndReport("login/verification marker %r present — STOP, not bypassing." % mk)
    return html


# ---- parsing (regex-only; no third-party deps) --------------------------------

_LB_RE = re.compile(r'<ul class="kaifu-lb">(.*?)</ul>', re.S)
_LI_RE = re.compile(r'<li>(.*?)</li>', re.S)


def _clean(s):
    if s is None:
        return None
    s = re.sub(r'<[^>]+>', '', s)          # strip any inner tags
    s = s.replace('&nbsp;', ' ')
    s = re.sub(r'\s+', ' ', s).strip()
    return s or None


def _neutral_game_name(source_name):
    """Remove u2's parenthetical variant/promotion suffix from the ingest label.

    The unmodified official string is intentionally not emitted. This function
    does not decide whether a title is publishable; gid/IP freezes and red-line
    policy stay in the repository's reviewed rules table.
    """
    if not source_name:
        return None
    neutral = re.sub(r'\s*[（(][^（）()]*[）)]\s*$', '', source_name).strip()
    return neutral or source_name


def _field(li, cls):
    m = re.search(r'<div class="%s">(.*?)</div>' % re.escape(cls), li, re.S)
    return m.group(1) if m else None


def parse(html):
    # The page ships commented-out template markup (e.g. a placeholder
    # <!-- <div class="kaifu-time">01-12<span>10:19</span></div> --> before the
    # real value). Strip HTML comments first so we never parse the template.
    html = re.sub(r'<!--.*?-->', '', html, flags=re.S)
    block = _LB_RE.search(html)
    if not block:
        raise StopAndReport("schedule block <ul class='kaifu-lb'> not found — layout changed or page blocked.")
    records = []
    for li in _LI_RE.findall(block.group(1)):
        open_time = _clean(_field(li, "kaifu-time"))

        game_div = _field(li, "kaifu-game") or ""
        gm = re.search(r'<h4>(.*?)</h4>', game_div, re.S)
        source_game_name = _clean(gm.group(1)) if gm else None
        game_name = _neutral_game_name(source_game_name)
        source_name_had_variant_suffix = game_name != source_game_name
        hm = re.search(r'href="([^"]*id/(\d+)\.html)"', game_div)
        game_detail_path = hm.group(1) if hm else None
        game_id = hm.group(2) if hm else None

        server_name = _clean(_field(li, "kaifu-qufu"))
        game_type = _clean(_field(li, "kaifu-leixin"))

        pintai = _field(li, "kaifu-pintai") or ""
        platforms = []
        if "android" in pintai.lower():
            platforms.append("android")
        if "apple" in pintai.lower() or "ios" in pintai.lower():
            platforms.append("ios")

        # structured time parts (page shows MM-DD HH:MM, no year)
        month = day = hh = mm = None
        if open_time:
            tm = re.search(r'(\d{1,2})-(\d{1,2})\s*(\d{1,2}):(\d{2})', open_time)
            if tm:
                month, day, hh, mm = (int(x) for x in tm.groups())

        records.append({
            "open_time_raw": open_time,
            "open_month": month, "open_day": day,
            "open_hour": hh, "open_minute": mm,
            "game_name": game_name,
            "source_name_had_variant_suffix": source_name_had_variant_suffix,
            "game_id": game_id,
            "game_detail_path": game_detail_path,   # NOTE: read only, never fetched
            "server_name": server_name,
            "game_type": game_type,
            "platforms": platforms,
            # Ingest data is never publication approval. A downstream public
            # page must check the current reviewed red-line rules by gid/name
            # and lint rendered HTML before deploy.
            "public_copy_allowed": False,
        })
    if not records:
        raise StopAndReport("schedule block contains no rows — layout changed or source is empty.")

    required = ("open_time_raw", "game_name", "game_id", "server_name", "game_type")
    for index, record in enumerate(records, start=1):
        missing = [key for key in required if not record[key]]
        if missing:
            raise StopAndReport(
                "schedule row %d is missing required fields (%s) — layout changed; refusing partial data."
                % (index, ", ".join(missing)))
    return records


def main():
    ap = argparse.ArgumentParser(description="Fetch u2 public 開服表 -> JSON (read-only, zero-login).")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--out", default=None, help="write JSON here (default: stdout)")
    ap.add_argument("--pretty", action="store_true")
    ap.add_argument("--fetched-at", default=None, help="ISO timestamp to stamp into output")
    args = ap.parse_args()

    try:
        html = fetch(args.url)
        records = parse(html)
    except StopAndReport as e:
        sys.stderr.write("STOP-AND-REPORT: %s\n" % e)
        sys.exit(2)
    except Exception as e:  # noqa
        sys.stderr.write("ERROR: %s\n" % e)
        sys.exit(1)

    out = {
        "source_url": args.url,
        "fetched_at": args.fetched_at,
        "record_count": len(records),
        "records": records,
    }
    text = json.dumps(out, ensure_ascii=False, indent=2 if args.pretty else None)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        sys.stderr.write("wrote %d records -> %s\n" % (len(records), args.out))
    else:
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.write(b"\n")


if __name__ == "__main__":
    main()
