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

--build-root 模式（CI 閘）
------------------------
上面兩條是「chrome 快篩」，只看 meta 欄位。CI 上要擋的還有第三層：
索引／樞紐頁（`/blog/`、`/games/`）的內容不存在於任何原始檔，它由各篇
front-matter title 在建置時聚合而成 —— 只審 markdown 一樣掃不到。

`--build-root` 把整份建置產物拆成「文字區塊」（一個 h1-h6/p/li/td/title/meta/img@alt
為一塊）逐塊判定，規則來自 `--rules` 指定的公版規則表：

  * 點名遊戲 × 折數字樣「同塊」共現才算命中；同頁不同段各自出現不算違規。
    區塊內有 ≥2 個不同連結時（連結清單／卡片列）再按連結切開 —— 不然相鄰兩篇
    不相干的標題會被算成共現。
  * 逐 gid 規則的語境由「塊內連結解析到落地頁的 gid」取得，所以索引頁上的一張卡
    也吃得到那款的規則。
  * 全站共用版型區塊（≥30% 頁面共用的 header/footer/導覽/預設 meta）命中時
    **判 error**。站名去折已於 2026-08-08 上線，此類命中的角色是「回歸偵測」，
    不是待辦提示，所以不降 warn。
  * 語境閘：合規政策定義在規則表的 `context_gates`，工程端不得自行增刪詞條。

用法：
    python3 tools/redline_lint_site.py                      # 預設 _config.yml + _site
    python3 tools/redline_lint_site.py --site-root _site
    python3 tools/redline_lint_site.py --config-only        # 沒有 build 產物時只跑檢查 1
    python3 tools/redline_lint_site.py --strict-body        # 連正文提及也算「涉及該款」
    python3 tools/redline_lint_site.py --build-root _site --rules tools/redline_rules.json

最後一行固定輸出：REDLINE: error=N warn=N gated-pass=N pages=N
其中 error 一律指「會擋下部署的 error」，也就是不在 baseline 裡的那些。

baseline（既有存量）
--------------------
閘上線當天，站上已有 N 處**內容層**的 error 級命中（文案用詞、既有頁面的折字），
它們的處置權在 Content，不在工程端。若因此讓閘一上線就把整站部署鎖死，
Publisher 連一篇乾淨稿都推不上去 —— 閘會在第一天就被繞過，等於沒做。

所以既有存量走 `--baseline`：一份**逐筆列名、進版控、每次執行都完整列印**的清單。
它不是 `|| true`，也不是 continue-on-error：
  * 清單外的任何 error 照樣讓整個 workflow 非 0 中斷，deploy 不執行；
  * 清單內的每一筆每次都以 BASELINED 印出來，看得到、賴不掉；
  * 清單只能變短。存量清完就刪掉這個檔案與 CI 上的 --baseline 參數。
基礎建設層的失敗（規則檔缺檔／JSON 壞掉／腳本自己爆掉）**不受 baseline 影響**，
一律非 0。

退出碼：0 = 全綠；1 = 有（非 baseline 的）error 級命中；
        2 = 用法／檔案／規則表錯誤或腳本自身丟例外。
fail-closed：規則檔缺檔、JSON 壞掉、腳本自己爆掉，一律非 0 —— CI 上絕不可以放行。
純標準庫、零網路請求。
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import traceback
from html.parser import HTMLParser

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


# =============================================================================
# --build-root 模式：建置產物的區塊級紅線閘（CI 用）
# =============================================================================

BUILD_SKIP_TAGS = {"script", "style", "noscript", "template", "svg"}
BUILD_BLOCK_TAGS = {
    "title", "h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "th", "dt", "dd",
    "div", "section", "article", "header", "footer", "nav", "main", "aside",
    "blockquote", "figcaption", "caption", "tr", "ul", "ol", "table", "br", "hr",
    "form", "label", "button", "option", "summary", "details", "address", "pre",
}
BUILD_META_KEYS = {"description", "og:title", "og:description", "og:site_name",
                   "twitter:title", "twitter:description", "keywords"}
GID_RE = re.compile(r"gid=?(\d{3,5})")
SITE_HOSTS = ("btgamevip.com", "www.btgamevip.com")
SITE_HTML_EXT = {".html", ".htm"}

# 句子邊界。語境閘一律「同句」判定 —— 跨句的否定語／退費語境不算數，
# 不然整頁只要任何一處出現「退款」就能替全頁的「未成年」解套。
SENTENCE_SPLIT = re.compile(r"[。！？!?；;\n]")


class _BuildExtractor(HTMLParser):
    """把一份建置好的 HTML 拆成文字區塊 [(行號, 文字, 該塊涵蓋的連結, 位置)]。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks = []
        self._segs = []          # [(text, anchor_key, line)]
        self._astack = []        # [(anchor_key, href)]
        self._akeys = {}
        self._aseq = 0
        self._skip = 0
        self._in_title = False
        self._title_buf = []
        self._title_line = 1

    def _emit(self, segs, where="body"):
        text = re.sub(r"\s+", " ", "".join(s[0] for s in segs)).strip()
        if not text:
            return
        line = next((s[2] for s in segs if s[0].strip()), 1)
        own = {self._akeys.get(s[1], "") for s in segs if s[1] is not None}
        anc = {h for _k, h in self._astack if h}
        self.blocks.append(dict(line=line, text=text,
                                links=sorted({h for h in (own | anc) if h}),
                                where=where, anchored=bool(own | anc)))

    def _flush(self):
        segs, self._segs = self._segs, []
        if not segs:
            return
        # 一個區塊裡有 ≥2 個不同連結（＝連結清單／卡片列）時，按連結切開再判定。
        # 不切開的話，首頁上相鄰的兩則不相干標題會被算成「同塊共現」而誤報。
        keys = [s[1] for s in segs if s[1] is not None]
        if len(set(keys)) >= 2:
            group, cur = [], object()
            for s in segs:
                if s[1] != cur and group:
                    self._emit(group)
                    group = []
                cur = s[1]
                group.append(s)
            if group:
                self._emit(group)
        else:
            self._emit(segs)

    def _standalone(self, text, where, line):
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            self.blocks.append(dict(line=line, text=text, where=where,
                                    links=sorted({h for _k, h in self._astack if h}),
                                    anchored=False))

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        href = (d.get("href") or "").strip()
        if tag == "a":
            self._aseq += 1
            self._akeys[self._aseq] = href
            self._astack.append((self._aseq, href))
        if tag == "title":
            # <title> 在 <head> 裡，但它是最重要的一塊 chrome，必須單獨收。
            self._in_title, self._title_buf = True, []
            self._title_line = self.getpos()[0]
            return
        if tag in BUILD_SKIP_TAGS:
            self._skip += 1
            return
        if tag in BUILD_BLOCK_TAGS:
            self._flush()
        line = self.getpos()[0]
        if tag == "img":
            self._standalone(d.get("alt") or "", "img@alt", line)
        elif tag == "meta":
            key = (d.get("name") or d.get("property") or "").lower()
            if key in BUILD_META_KEYS:
                self._standalone(d.get("content") or "", "meta[%s]" % key, line)

    def handle_endtag(self, tag):
        if tag == "title":
            self._standalone("".join(self._title_buf), "<title>", self._title_line)
            self._in_title, self._title_buf = False, []
            return
        if tag in BUILD_SKIP_TAGS:
            self._skip = max(0, self._skip - 1)
            return
        if tag == "a" and self._astack:
            self._astack.pop()
        if tag in BUILD_BLOCK_TAGS:
            self._flush()

    def handle_data(self, data):
        if self._in_title:
            self._title_buf.append(data)
            return
        if self._skip:
            return
        key = self._astack[-1][0] if self._astack else None
        self._segs.append((data, key, self.getpos()[0]))

    def close(self):
        super().close()
        self._flush()


def load_rules(path: str) -> dict:
    """讀公版規則表並預編譯。fail-closed：缺檔／JSON 壞掉一律 exit 2。"""
    if not os.path.isfile(path):
        print("ERROR: 找不到規則表 %s —— 規則表是閘的前提，缺檔一律當失敗（fail-closed）"
              % path, file=sys.stderr)
        sys.exit(2)
    try:
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
    except json.JSONDecodeError as exc:
        print("ERROR: 規則表 %s JSON 解析失敗：%s" % (path, exc), file=sys.stderr)
        sys.exit(2)

    def names(items):
        return [re.compile(n[3:], re.I) if n.startswith("re:") else re.compile(re.escape(n))
                for n in items]

    try:
        rules = {
            "discount": [re.compile(x) for x in raw.get("discount_patterns", [])],
            "by_name": [dict(r, _names=names(r["names"])) for r in raw.get("by_name", [])],
            "frozen": [dict(r, _names=names(r["names"])) for r in raw.get("frozen", [])],
            "by_gid": [dict(r, _pats=[re.compile(x) for x in r["patterns"]],
                            _gids=set(r["gids"])) for r in raw.get("by_gid", [])],
            "wording": [dict(r, _pat=re.compile(r["pattern"]))
                        for r in raw.get("wording", [])],
            "gates": [dict(r, _pat=re.compile(r["pattern"]))
                      for r in raw.get("context_gates", [])],
            "density": None,
        }
    except (KeyError, re.error) as exc:
        print("ERROR: 規則表 %s 內容不合法：%s" % (path, exc), file=sys.stderr)
        sys.exit(2)
    d = raw.get("density")
    if d:
        rules["density"] = dict(d, _pat=re.compile(d["pattern"]),
                                _strict=re.compile(d["strict_pattern"]))
    if not (rules["by_name"] or rules["by_gid"] or rules["gates"]):
        print("ERROR: 規則表 %s 是空的（沒有任何可執行規則）" % path, file=sys.stderr)
        sys.exit(2)
    return rules


def url_to_relpath(href: str, base_relpath: str = ""):
    """把站內連結正規化成建置產物的相對檔案路徑；站外／錨點回 None。"""
    href = href.strip()
    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
        return None
    m = re.match(r"https?://([^/]+)(/.*)?$", href, re.I)
    if m:
        if m.group(1).lower() not in SITE_HOSTS:
            return None
        path = m.group(2) or "/"
    elif href.startswith("/"):
        path = href
    else:
        base_dir = os.path.dirname(base_relpath.replace(os.sep, "/"))
        path = "/" + os.path.normpath(os.path.join(base_dir, href)).replace(os.sep, "/").lstrip("/")
    path = path.split("#")[0].split("?")[0]
    if path.endswith("/") or "." not in os.path.basename(path):
        path = path.rstrip("/") + "/index.html"
    return path.lstrip("/")


def discover_build_files(root: str):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in {".git", "node_modules"}]
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() in SITE_HTML_EXT:
                out.append(os.path.join(dirpath, fn))
    return sorted(out)


def find_boilerplate(all_blocks: dict, min_pages: int = 3, ratio: float = 0.30):
    """跨全站出現在 ≥ratio 頁的區塊文字＝共用版型（header/footer/導覽/預設 meta）。"""
    seen = {}
    for rel, blocks in all_blocks.items():
        for t in {b["text"] for b in blocks}:
            seen.setdefault(t, set()).add(rel)
    n = max(1, len(all_blocks))
    return {t for t, pages in seen.items()
            if len(pages) >= min_pages and len(pages) / n >= ratio}


def sentence_at(text: str, pos: int):
    """回傳 (該位置所在的整句, 位置在句內的 offset)。"""
    start = 0
    for m in SENTENCE_SPLIT.finditer(text):
        if m.end() > pos:
            break
        start = m.end()
    end = len(text)
    nxt = SENTENCE_SPLIT.search(text, pos)
    if nxt:
        end = nxt.start()
    return text[start:end], pos - start


def is_chrome(block, boilerplate) -> bool:
    """chrome＝使用者在每一頁都看得到、由版型注入的東西。

    <title>／og:*／meta description 是 chrome 的定義欄位；
    另外任何跨 ≥30% 頁面重複的區塊（頁首站名、頁尾簡介、導覽列）也是。
    """
    where = block.get("where", "body")
    return (where == "<title>" or where.startswith("meta[")
            or block["text"] in boilerplate)


def check_gates(block, rules, chrome, findings, gated):
    """語境閘。詞條與閘的定義都在規則表裡，工程端不得自行增刪。"""
    text = block["text"]
    for g in rules["gates"]:
        m = g["_pat"].search(text)
        if not m:
            continue
        gate = g.get("gate", "none")
        sentence, off = sentence_at(text, m.start())
        excerpt = sentence if len(sentence) <= 70 else sentence[:67] + "…"
        cues = g.get("cues", [])

        if gate == "allow_if_same_sentence":
            if chrome and g.get("chrome_never_pass"):
                findings.append(dict(
                    sev="error", cat="context_gate", line=block["line"],
                    match=m.group(0),
                    msg="%s｜chrome 區塊不放行（%s）｜%s"
                        % (g.get("message", g["id"]), block.get("where", "body"), excerpt),
                    fix=g.get("suggestion", "")))
                continue
            if any(c in sentence for c in cues):
                gated.append((g["id"], m.group(0), block["line"], excerpt,
                              bool(g.get("silent_pass"))))
                continue
        elif gate == "require_negation_before_same_sentence":
            # 否定詞必須在同一句、且位於該詞之前，否則不算否定語境。
            if any(c in sentence[:off] for c in cues):
                gated.append((g["id"], m.group(0), block["line"], excerpt,
                              bool(g.get("silent_pass"))))
                continue
        findings.append(dict(
            sev=g.get("severity", "error"), cat="context_gate", line=block["line"],
            match=m.group(0),
            msg="%s｜%s" % (g.get("message", g["id"]), excerpt),
            fix=g.get("suggestion", "")))


def scan_build_block(block, rules, ctx_gids, page_text, chrome, findings, gated):
    text, line = block["text"], block["line"]
    excerpt = text if len(text) <= 60 else text[:57] + "…"

    # (1) 點名遊戲 × 折數字樣，同塊共現
    for r in rules["by_name"]:
        nm = next((p.search(text) for p in r["_names"] if p.search(text)), None)
        if not nm:
            continue
        for dp in rules["discount"]:
            dm = dp.search(text)
            if dm:
                findings.append(dict(
                    sev=r.get("severity", "error"), cat="game_redline", line=line,
                    match="「%s」×「%s」" % (nm.group(0), dm.group(0)),
                    msg="%s（%s）｜區塊：%s" % (r.get("message", "禁折款"), r["id"], excerpt),
                    fix="移除該塊折數字樣，或整塊下架"))
                break

    # (2) 永久凍結／未授權蹭 IP：出現即命中
    for r in rules["frozen"]:
        fm = next((p.search(text) for p in r["_names"] if p.search(text)), None)
        if fm:
            findings.append(dict(
                sev=r.get("severity", "error"), cat="game_redline", line=line,
                match=fm.group(0),
                msg="%s（%s）｜區塊：%s" % (r.get("message", "永久跳過名單"), r["id"], excerpt),
                fix=r.get("suggestion", "")))

    # (3) 逐 gid 規則（語境由塊內連結解析而來）
    for r in rules["by_gid"]:
        hit = r["_gids"] & ctx_gids
        if not hit:
            continue
        if any(u in page_text for u in r.get("unless_page", [])):
            continue          # 該頁已自陳合規語，不重複開單
        for p in r["_pats"]:
            pm = p.search(text)
            if pm:
                findings.append(dict(
                    sev=r.get("severity", "error"), cat="game_redline", line=line,
                    match=pm.group(0),
                    msg="gid %s：%s%s｜區塊：%s"
                        % ("/".join(sorted(hit)), r.get("message", ""),
                           "【全站共用版型區塊 —— 版型上的折數字樣會讓所有掛此 gid 的頁面連帶曝險；"
                           "站名去折已上線，此類命中＝回歸】" if chrome else "", excerpt),
                    fix=r.get("suggestion", "")))
                break

    # (4) 措辭（不分遊戲的全站禁令）
    for r in rules["wording"]:
        if r.get("severity") == "info":
            continue
        wm = r["_pat"].search(text)
        if wm:
            findings.append(dict(
                sev=r.get("severity", "warn"), cat="wording", line=line,
                match=wm.group(0),
                msg="%s｜區塊：%s" % (r.get("message", r["id"]), excerpt),
                fix=r.get("suggestion", "")))

    check_gates(block, rules, chrome, findings, gated)


def scan_density(blocks, rules):
    d = rules.get("density")
    if not d:
        return []
    joined = "\n".join(b["text"] for b in blocks)
    titles = [b for b in blocks
              if b.get("anchored") and len(b["text"]) <= d.get("title_max_chars", 90)
              and d["_pat"].search(b["text"])]
    if len(titles) < d.get("aggregation_threshold", 5):
        return []
    sample = "；".join(t["text"][:34] for t in titles[:3])
    return [dict(sev=d.get("severity", "warn"), cat="density", line=1,
                 match="聚合標題 %d 筆帶折數（全頁「折」×%d、0.x 折 ×%d）"
                       % (len(titles), len(d["_pat"].findall(joined)),
                          len(d["_strict"].findall(joined))),
                 msg=d.get("message", ""), fix=d.get("suggestion", ""))]


def run_build_scan(build_root: str, rules_path: str) -> tuple:
    """回傳 (findings_by_page, gated, pages)。"""
    if not os.path.isdir(build_root):
        print("ERROR: 找不到建置產物目錄 %s（CI 上必須先 jekyll build）" % build_root,
              file=sys.stderr)
        sys.exit(2)
    rules = load_rules(rules_path)
    files = discover_build_files(build_root)
    if not files:
        print("ERROR: %s 底下沒有任何 HTML —— 建置八成失敗了，不能當成「全綠」" % build_root,
              file=sys.stderr)
        sys.exit(2)

    # 第 1 趟：全站解析。共用版型偵測需要全站語料，不能一檔一檔看。
    parsed, gid_index = {}, {}
    for full in files:
        rel = os.path.relpath(full, build_root).replace(os.sep, "/")
        with open(full, encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
        ex = _BuildExtractor()
        ex.feed(raw)
        ex.close()
        parsed[rel] = ex.blocks
        gid_index[rel] = set(GID_RE.findall(raw))
    boilerplate = find_boilerplate(parsed)

    # 第 2 趟：逐塊判定。
    out, gated = {}, []
    for rel, blocks in parsed.items():
        page_text = "\n".join(b["text"] for b in blocks)
        findings = []
        for b in blocks:
            ctx = set(gid_index.get(rel, ()))
            for href in b["links"]:
                tgt = url_to_relpath(href, rel)
                if tgt and tgt in gid_index:
                    ctx |= gid_index[tgt]
                ctx |= set(GID_RE.findall(href))
            page_gated = []
            scan_build_block(b, rules, ctx, page_text,
                             is_chrome(b, boilerplate), findings, page_gated)
            gated.extend((rel,) + g for g in page_gated)
        findings.extend(scan_density(blocks, rules))
        if findings:
            out[rel] = findings
    print("[build] 掃 %d 份建置產物、共用版型區塊 %d 塊、規則表 %s"
          % (len(files), len(boilerplate), rules_path))
    return out, gated, len(files)


def finding_key(rel: str, f: dict) -> str:
    """baseline 的比對鍵。刻意不含行號 —— 上下文一改行號就漂，
    比對鍵漂掉會讓存量條目每次都變成「新命中」，閘就永遠是紅的。"""
    return "%s|%s|%s" % (rel, f["cat"], f["match"])


def load_baseline(path: str):
    if not path:
        return None
    if not os.path.isfile(path):
        print("ERROR: 指定了 --baseline %s 但檔案不存在 —— 不確定要豁免什麼就一律不豁免"
              % path, file=sys.stderr)
        sys.exit(2)
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        print("ERROR: baseline %s JSON 解析失敗：%s" % (path, exc), file=sys.stderr)
        sys.exit(2)
    return {e["key"]: e for e in data.get("entries", [])}


def main() -> int:
    ap = argparse.ArgumentParser(description="紅線質檢（rendered HTML 層）")
    ap.add_argument("--config", default="_config.yml")
    ap.add_argument("--site-root", default=None,
                    help="chrome 快篩模式：_config.yml + 建置產物的 meta/feed 欄位")
    ap.add_argument("--games", default=os.path.join("tools", "redline_games.txt"))
    ap.add_argument("--config-only", action="store_true",
                    help="沒有 build 產物時只跑檢查 1")
    ap.add_argument("--strict-body", action="store_true",
                    help="連正文提及也算「涉及該款」（誤報會變多）")
    ap.add_argument("--build-root", default=None,
                    help="CI 閘模式：對建置產物做區塊級判定")
    ap.add_argument("--rules", default=os.path.join("tools", "redline_rules.json"),
                    help="--build-root 用的公版規則表")
    ap.add_argument("--show-gated", action="store_true",
                    help="連 silent_pass 的語境閘放行也逐筆列出（除錯用）")
    ap.add_argument("--baseline", default=None,
                    help="既有存量清單；清單內的 error 不擋部署，但每次都完整列印")
    ap.add_argument("--write-baseline", default=None, metavar="FILE",
                    help="把目前所有 error 級命中寫成 baseline 檔（只在建立存量時用一次）")
    args = ap.parse_args()

    errors = warns = gated_pass = pages = 0

    if args.build_root:
        by_page, gated, pages = run_build_scan(args.build_root, args.rules)
        baseline = load_baseline(args.baseline)
        baselined, blocking, seen_keys = [], 0, set()

        for rel in sorted(by_page):
            print("\n%s" % rel)
            for f in sorted(by_page[rel], key=lambda x: (x["sev"] != "error", x["line"])):
                key = finding_key(rel, f)
                is_base = f["sev"] == "error" and baseline is not None and key in baseline
                if is_base:
                    seen_keys.add(key)
                    baselined.append((rel, f, baseline[key]))
                    mark = "BASELINED"
                elif f["sev"] == "error":
                    blocking += 1
                    mark = "FAIL"
                else:
                    mark = "warn"
                print("  %s L%d [%s] %s :: %s" % (mark, f["line"], f["cat"],
                                                  f["match"], f["msg"]))
                if f["fix"] and mark != "BASELINED":
                    print("        → %s" % f["fix"])
                if is_base:
                    print("        → 既有存量（owner: %s）：%s"
                          % (baseline[key].get("owner", "?"),
                             baseline[key].get("note", "")))
        warns = sum(1 for fs in by_page.values() for f in fs if f["sev"] == "warn")
        errors = blocking
        gated_pass = len(gated)
        for rel, gid, match, line, excerpt, silent in gated:
            if not silent or args.show_gated:
                print("  gated-pass %s L%d [%s] %s :: %s" % (rel, line, gid, match, excerpt))

        if args.write_baseline:
            entries = [dict(key=finding_key(rel, f), page=rel, category=f["cat"],
                            match=f["match"], owner="Content Editor",
                            note="待 Content 文案改寫；清掉後把這筆從本檔刪除")
                       for rel in sorted(by_page) for f in by_page[rel]
                       if f["sev"] == "error"]
            with open(args.write_baseline, "w", encoding="utf-8", newline="\n") as fh:
                json.dump({"_comment": "紅線閘的既有存量清單。只能變短：清完一筆刪一筆，"
                                       "全清完就連同 CI 上的 --baseline 參數一起刪掉。"
                                       "新增條目必須經合規核可，不是工程端自己加。",
                           "entries": entries}, fh, ensure_ascii=False, indent=2)
                fh.write("\n")
            print("\n已寫出 baseline %s（%d 筆）" % (args.write_baseline, len(entries)))
            return 0

        if baseline is not None:
            stale = [k for k in baseline if k not in seen_keys]
            print("\n既有存量 baseline：%d 筆列名、%d 筆本次仍命中、%d 筆已消失（可從清單刪除）"
                  % (len(baseline), len(seen_keys), len(stale)))
            for k in stale:
                print("  stale %s" % k)
            print("  ↑ 這些不擋部署，但它們是真命中。清單只能變短。")
    else:
        failures = []
        check_config(args.config, failures)
        if args.config_only:
            print("（--config-only：略過 rendered HTML 檢查）")
        else:
            pages = check_site(args.site_root or "_site", load_games(args.games),
                               args.strict_body, failures)
        if failures:
            print("\n紅線命中 %d 處：" % len(failures))
            for path, field, rule, found in failures:
                print("  FAIL %s :: %s :: %s :: %s" % (path, field, rule, found))
            print("\n處置：chrome（站名／站說明）零宣稱，折扣宣稱只留在允許款的 page-level。")
        errors = len(failures)

    if errors:
        print("\n有 %d 處 error 級紅線命中 —— 不得部署。" % errors)
    else:
        print("\nOK：無 error 級紅線命中。")
    # 這一行的格式是對外契約（CI log 與班次報告都靠它取數），不要改。
    print("REDLINE: error=%d warn=%d gated-pass=%d pages=%d"
          % (errors, warns, gated_pass, pages))
    return 1 if errors else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:                                  # noqa: BLE001
        # fail-closed：閘自己爆掉時，絕不能因為「沒印出 FAIL」就被當成綠燈。
        traceback.print_exc()
        print("\nERROR: redline lint 自身丟例外 —— 視同失敗（fail-closed）。",
              file=sys.stderr)
        print("REDLINE: error=1 warn=0 gated-pass=0 pages=0")
        sys.exit(2)
