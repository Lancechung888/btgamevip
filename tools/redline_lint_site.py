#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""紅線質檢（rendered HTML 層）

為什麼存在：站台的合規風險有兩層，過去只查了其中一層。
  page-level（文章正文／front matter）——原本就有人工審稿在看。
  site-level chrome（`<title>` 尾綴、`og:site_name`、feed 標題、頁首頁尾站名）
      ——由 `_config.yml` 的 `title` / `description` 注入到「每一頁」，
        審稿看原始 markdown 永遠看不到，只有 build 後的 HTML 才顯形。

所以本腳本只認 build 產物：對 `_site/` 掃出來的東西才是使用者真正看到的東西。

兩條檢查：
  1. site-level：`_config.yml` 的 `title` / `description` 不得帶任何折扣宣稱。
     chrome 是全站無差別注入，一旦帶折字，禁折款的頁面必然違規。
  2. 禁折名單 × rendered HTML：名單內遊戲的頁面，其 `<title>`、`og:title`、
     `og:site_name`、`og:description`、`meta[name=description]` 與 feed 標題
     不得出現折字／折數。

用法：
    python3 tools/redline_lint_site.py                      # 預設 _config.yml + _site
    python3 tools/redline_lint_site.py --site-root _site
    python3 tools/redline_lint_site.py --config-only        # 沒有 build 產物時只跑檢查 1
    python3 tools/redline_lint_site.py --strict-body        # 連正文提及也算「涉及該款」

退出碼：0 = 全綠；1 = 有命中；2 = 用法／檔案錯誤。
純標準庫、零網路請求。
"""

from __future__ import annotations

import argparse
import html
import os
import re
import sys

# --- 紅線樣態 -----------------------------------------------------------------
# 中文「折」在合規語境幾乎只有折扣一義；為降低誤報，先把已知的非折扣詞挖掉再判。
NON_DISCOUNT_ZHE = ("轉折", "折騰", "折磨", "曲折", "波折", "挫折", "折返", "折衷", "骨折")

PATTERNS = [
    ("折數樣態", re.compile(r"\d+(?:\.\d+)?\s*折")),
    ("折起／折扣宣稱", re.compile(r"折\s*起|折扣|打折|折價")),
    ("折字", re.compile(r"折")),
    ("返現", re.compile(r"返現|返现")),
    ("首儲禮包", re.compile(r"首儲禮包|首充禮包")),
]

# rendered HTML 要查的欄位（欄位名 -> 抽取用 regex，group('v') 是值）
META_FIELDS = {
    "<title>": re.compile(r"<title>(?P<v>.*?)</title>", re.I | re.S),
    "og:title": re.compile(
        r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](?P<v>[^"\']*)', re.I
    ),
    "og:site_name": re.compile(
        r'<meta[^>]+property=["\']og:site_name["\'][^>]+content=["\'](?P<v>[^"\']*)', re.I
    ),
    "og:description": re.compile(
        r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](?P<v>[^"\']*)', re.I
    ),
    "meta[name=description]": re.compile(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](?P<v>[^"\']*)', re.I
    ),
}

# feed.xml：頻道層（chrome）與 entry 層要分開判，不能整份當一頁掃。
# 整份掃會把「允許款文章的標題」算進「這份 feed 涉及禁折款」而誤殺——
# feed 裡本來就同時裝著兩種款的 entry。
FEED_HEAD_FIELDS = {
    "feed <title>": re.compile(r"<title[^>]*>(?P<v>.*?)</title>", re.I | re.S),
    "feed <subtitle>": re.compile(r"<subtitle[^>]*>(?P<v>.*?)</subtitle>", re.I | re.S),
}
FEED_ENTRY_FIELDS = {
    "feed entry <title>": re.compile(r"<title[^>]*>(?P<v>.*?)</title>", re.I | re.S),
    "feed entry <summary>": re.compile(r"<summary[^>]*>(?P<v>.*?)</summary>", re.I | re.S),
}
ENTRY_RE = re.compile(r"<entry\b.*?</entry>", re.I | re.S)


def scrub(text: str) -> str:
    """把已知的非折扣「折」詞挖掉，避免誤報。"""
    for word in NON_DISCOUNT_ZHE:
        text = text.replace(word, "")
    return text


def hits(value: str):
    """回傳 [(規則名, 命中字串)]；同一段文字只報第一條命中的規則，避免洗版。"""
    cleaned = scrub(html.unescape(value))
    for name, pat in PATTERNS:
        m = pat.search(cleaned)
        if m:
            return [(name, m.group(0))]
    return []


# --- 檢查 1：site-level -------------------------------------------------------
def read_config_scalar(config_path: str, key: str):
    """從 _config.yml 讀頂層純量。不引入 yaml 依賴（本腳本只准用標準庫）。

    只認「行首無縮排 + key: 值」的形式，這正是 _config.yml 現行寫法；
    若哪天改成多行寫法，這裡會讀不到而回 None，check_config 會當成錯誤報出來。
    """
    pat = re.compile(r"^%s:\s*(.+?)\s*$" % re.escape(key), re.M)
    with open(config_path, encoding="utf-8") as fh:
        text = fh.read()
    m = pat.search(text)
    if not m:
        return None
    value = m.group(1)
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value


def check_config(config_path: str, failures: list) -> None:
    if not os.path.isfile(config_path):
        print("ERROR: 找不到 %s" % config_path, file=sys.stderr)
        sys.exit(2)
    for key in ("title", "description"):
        value = read_config_scalar(config_path, key)
        if value is None:
            failures.append((config_path, "site.%s" % key, "讀不到頂層 %s（格式改了？）" % key, ""))
            continue
        for rule, found in hits(value):
            failures.append((config_path, "site.%s" % key, rule, found))
    print("[1/2] site-level %s：title / description 檢查完成" % config_path)


# --- 檢查 2：禁折名單 × rendered HTML -----------------------------------------
def load_games(path: str):
    if not os.path.isfile(path):
        print("ERROR: 找不到禁折名單 %s" % path, file=sys.stderr)
        sys.exit(2)
    games = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            names = [n.strip() for n in line.split("|") if n.strip()]
            if names:
                games.append((names[0], names))
    if not games:
        print("ERROR: 禁折名單 %s 是空的" % path, file=sys.stderr)
        sys.exit(2)
    return games


def extract_fields(text: str, fields: dict):
    out = []
    for label, pat in fields.items():
        for m in pat.finditer(text):
            value = re.sub(r"<[^>]+>", "", m.group("v")).strip()
            if value:
                out.append((label, value))
    return out


def involved_games(path: str, text: str, meta_values, games, strict_body: bool):
    """判斷這頁「涉及」名單上的哪幾款。

    預設只看頁面身分（網址 + 上面那組 meta 欄位），不看正文：
    列表頁／首頁只是連到某款的文章，不該因此被當成該款的頁面而卡掉自己的宣稱。
    要收更緊就給 --strict-body。
    """
    haystack = path.replace(os.sep, "/") + "\n" + "\n".join(v for _, v in meta_values)
    if strict_body:
        haystack += "\n" + text
    return [canon for canon, names in games if any(n in haystack for n in names)]


def check_site(site_root: str, games, strict_body: bool, failures: list) -> int:
    if not os.path.isdir(site_root):
        print("ERROR: 找不到 build 產物目錄 %s（先跑 jekyll build，或加 --config-only）" % site_root,
              file=sys.stderr)
        sys.exit(2)
    scanned = 0
    for dirpath, _dirnames, filenames in os.walk(site_root):
        for filename in filenames:
            is_html = filename.endswith((".html", ".htm"))
            is_feed = filename in ("feed.xml", "atom.xml")
            if not (is_html or is_feed):
                continue
            full = os.path.join(dirpath, filename)
            rel = os.path.relpath(full, site_root).replace(os.sep, "/")
            with open(full, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            scanned += 1

            if is_feed:
                # 頻道層＝chrome，等同 site.title/description，無條件查。
                cut = text.lower().find("<entry")
                head = text[:cut] if cut != -1 else text
                for label, value in extract_fields(head, FEED_HEAD_FIELDS):
                    for rule, found in hits(value):
                        failures.append((rel, label, rule, "%s ← %s" % (found, value[:70])))
                # entry 層＝page-level，逐則各自判涉及哪款。
                for entry in ENTRY_RE.findall(text):
                    values = extract_fields(entry, FEED_ENTRY_FIELDS)
                    for game in involved_games(rel, entry, values, games, strict_body):
                        for label, value in values:
                            for rule, found in hits(value):
                                failures.append(
                                    (rel, "%s（涉及《%s》）" % (label, game), rule,
                                     "%s ← %s" % (found, value[:70])))
                continue

            values = extract_fields(text, META_FIELDS)
            for game in involved_games(rel, text, values, games, strict_body):
                for label, value in values:
                    for rule, found in hits(value):
                        failures.append(
                            (rel, "%s（涉及《%s》）" % (label, game), rule,
                             "%s ← %s" % (found, value[:70])))
    print("[2/2] rendered HTML %s：掃 %d 檔、禁折名單 %d 款" % (site_root, scanned, len(games)))
    return scanned


def main() -> int:
    ap = argparse.ArgumentParser(description="紅線質檢（rendered HTML 層）")
    ap.add_argument("--config", default="_config.yml")
    ap.add_argument("--site-root", default="_site")
    ap.add_argument("--games", default=os.path.join("tools", "redline_games.txt"))
    ap.add_argument("--config-only", action="store_true",
                    help="沒有 build 產物時只跑檢查 1")
    ap.add_argument("--strict-body", action="store_true",
                    help="連正文提及也算「涉及該款」（誤報會變多）")
    args = ap.parse_args()

    failures = []
    check_config(args.config, failures)
    if args.config_only:
        print("（--config-only：略過 rendered HTML 檢查）")
    else:
        check_site(args.site_root, load_games(args.games), args.strict_body, failures)

    if failures:
        print("\n紅線命中 %d 處：" % len(failures))
        for path, field, rule, found in failures:
            print("  FAIL %s :: %s :: %s :: %s" % (path, field, rule, found))
        print("\n處置：chrome（站名／站說明）零宣稱，折扣宣稱只留在允許款的 page-level。")
        return 1

    print("\nOK：無紅線命中。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
