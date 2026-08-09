#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""redline_lint_site.py --build-root 與 --text 的驗收測試。

為什麼要有：這支 lint 是擋在 deploy 前面的閘，它自己壞掉的失敗樣態是「安靜地全綠」
—— 規則沒載到、區塊沒切開、語境閘寫反，輸出看起來都一樣是 OK。所以每條判準都要有
一個會紅的反例把它釘住。

跑法：python3 tools/redline_lint_accept.py
退出碼：0 = 全過；1 = 有測試不過。純標準庫、零網路、用臨時目錄，不碰 repo 檔案。
"""

from __future__ import annotations

import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
LINT = os.path.join(HERE, "redline_lint_site.py")
RULES = os.path.join(HERE, "redline_rules.json")
with open(RULES, encoding="utf-8") as _rules_fh:
    _RULES_OBJ = json.load(_rules_fh)
CANON = _RULES_OBJ["site_identity"]["canonical_site_name"]

PAGE = """<!doctype html><html><head>
<title>{title}</title>
<meta property="og:site_name" content="BT 手遊情報站｜台灣手遊儲值攻略與下載入口">
<meta name="description" content="{desc}">
<link rel="canonical" href="https://btgamevip.com/test/">
<meta property="og:type" content="website">
<meta property="og:locale" content="zh_TW">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="https://btgamevip.com/test/">
<meta property="og:image" content="https://btgamevip.com/assets/posts/what-is-u2game-main-og.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="https://btgamevip.com/assets/posts/what-is-u2game-main-og.png">
</head><body>
<header><p>BT 手遊情報站</p></header>
{body}
<footer><p>{footer}</p></footer>
</body></html>
"""

# 共用版型（footer）的預設文字：三頁以上共用才會被認成 chrome。
PLAIN_FOOTER = "BT 手遊情報站｜台灣手遊儲值攻略與下載入口"

results = []


def page(title="一般標題｜BT 手遊情報站｜台灣手遊儲值攻略與下載入口", desc="一般說明", body="", footer=PLAIN_FOOTER):
    return PAGE.format(title=title, desc=desc, body=body, footer=footer)


def run(files, extra=(), rules=RULES, populate_named=True):
    """把 files（相對路徑 → 內容）寫成臨時建置產物，跑 lint，回 (rc, stdout)。"""
    root = tempfile.mkdtemp(prefix="redline-accept-")
    try:
        materialized = dict(files)
        if populate_named and rules == RULES:
            clean = page(title="Fixture｜%s" % CANON)
            for item in _RULES_OBJ["handwritten_chrome"]["pages"]:
                materialized.setdefault(item["path"], clean)
        for rel, content in materialized.items():
            full = os.path.join(root, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as fh:
                fh.write(content)
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        proc = subprocess.run(
            [sys.executable, LINT, "--build-root", root, "--rules", rules, *extra],
            capture_output=True, text=True, encoding="utf-8", env=env)
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def run_text(docs, extra=(), rules=RULES, stdin=None):
    """把 docs（名稱 → 內容）寫成臨時文案檔，跑 --text，回 (rc, stdout)。"""
    root = tempfile.mkdtemp(prefix="redline-text-")
    try:
        args = []
        for name, content in docs.items():
            full = os.path.join(root, name)
            with open(full, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(content)
            args += ["--text", full]
        if stdin is not None:
            args += ["--text", "-"]
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        proc = subprocess.run(
            [sys.executable, LINT, "--rules", rules, *args, *extra],
            capture_output=True, text=True, encoding="utf-8", env=env,
            input=stdin)
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def summary(out):
    m = re.search(r"REDLINE: error=(\d+) warn=(\d+) gated-pass=(\d+) pages=(\d+)", out)
    if not m:
        return None
    return dict(zip(("error", "warn", "gated", "pages"), map(int, m.groups())))


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print("  %s  %s%s" % ("PASS" if cond else "FAIL", name,
                          "" if cond else "  ← " + detail))


# --- 1. 乾淨站台 --------------------------------------------------------------
rc, out = run({"index.html": page(body="<p>平台介紹與下載入口，儲值教學一次看。</p>"),
               "a/index.html": page(body="<p>開服表整理。</p>"),
               "b/index.html": page(body="<p>版本差異說明。</p>")})
s = summary(out)
check("乾淨站台 → rc 0 且 error=0", rc == 0 and s and s["error"] == 0, out[-400:])
_expected_pages = len({"index.html", "a/index.html", "b/index.html"} |
                      {item["path"] for item in _RULES_OBJ["handwritten_chrome"]["pages"]})
check("summary 行存在且 pages 正確", s and s["pages"] == _expected_pages, out[-200:])

# --- 1a. /games/* robots noindex deploy 前不變式 -----------------------------
rc, out = run({'index.html': page(), 'a/index.html': page(),
               'games/clean/index.html': page().replace(
                   '</head>', '<meta name=robots content=index,follow>\n</head>')})
check('/games/* rendered robots=index,follow → 放行',
      rc == 0 and summary(out)['error'] == 0, out[-500:])

rc, out = run({'index.html': page(), 'a/index.html': page(),
               'games/blocked/index.html': page().replace(
                   '</head>', '<meta content=NOINDEX,nofollow name=robots>\n</head>')})
check('/games/* rendered robots=noindex（屬性倒序）→ error、擋部署',
      rc == 1 and summary(out)['error'] == 1 and 'game_robots' in out,
      out[-700:])

rc, out = run({'index.html': page(), 'a/index.html': page(),
               'games/none/index.html': page().replace(
                   '</head>', '<meta name=robots content=none>\n</head>')})
check('/games/* rendered robots=none（等同 noindex,nofollow）→ error、擋部署',
      rc == 1 and summary(out)['error'] == 1 and 'game_robots' in out,
      out[-700:])

rc, out = run({'index.html': page(), 'a/index.html': page(),
               'blog/private/index.html': page().replace(
                   '</head>', '<meta name=robots content=noindex>\n</head>')})
check('非 /games/* 的刻意 noindex 頁不受 scoped 閘誤擋',
      rc == 0 and summary(out)['error'] == 0, out[-500:])

# --- 2. 點名遊戲 × 折數，同塊共現 --------------------------------------------
rc, out = run({"index.html": page(body="<p>上古王冠現在有 0.1 折超值方案</p>"),
               "a/index.html": page(), "b/index.html": page()})
check("禁折款與折數同塊 → error", rc == 1 and summary(out)["error"] >= 1, out[-400:])

# --- 3. 跨連結不算共現（誤報防線）--------------------------------------------
rc, out = run({
    "index.html": page(body='<p><a href="/a/">上古王冠開服表整理</a>'
                            '<a href="/b/">MyCard 折扣 95 折沒了嗎</a></p>'),
    "a/index.html": page(), "b/index.html": page()})
check("相鄰兩連結標題不算同塊共現 → 0 error", rc == 0 and summary(out)["error"] == 0,
      out[-500:])

# --- 4. 同一頁不同段各自出現 → 不算違規 --------------------------------------
rc, out = run({"index.html": page(body="<p>上古王冠關服了嗎</p><p>MyCard 95 折沒了嗎</p>"),
               "a/index.html": page(), "b/index.html": page()})
check("同頁不同段各自出現 → 0 error", rc == 0 and summary(out)["error"] == 0, out[-500:])

# --- 5. 共用版型區塊命中逐 gid 規則 → error（不是 warn）------------------------
gid_link = '<p><a href="https://qd.u2game99.com/?ag=x&gid=2367">立即下載</a></p>'
bad_footer = "全站最低 0.5 折起"
rc, out = run({"index.html": page(body=gid_link, footer=bad_footer),
               "a/index.html": page(body=gid_link, footer=bad_footer),
               "b/index.html": page(body=gid_link, footer=bad_footer)})
s = summary(out)
check("共用版型區塊 × 逐 gid 規則 → error 而非 warn",
      rc == 1 and s["error"] >= 1 and "共用版型區塊" in out, out[-600:])

# --- 6. 語境閘：未成年 --------------------------------------------------------
rc, out = run({"index.html": page(body="<p>未成年玩家若需退費，請由監護人提出申請。</p>"),
               "a/index.html": page(), "b/index.html": page()})
s = summary(out)
check("未成年＋退費語境（正文）→ gated-pass，不算 error",
      rc == 0 and s["error"] == 0 and s["gated"] == 1, out[-400:])

rc, out = run({"index.html": page(body="<p>未成年也能輕鬆上手。</p>"),
               "a/index.html": page(), "b/index.html": page()})
check("未成年無退費語境 → error", rc == 1 and summary(out)["error"] >= 1, out[-400:])

rc, out = run({"index.html": page(title="未成年退費申請說明｜BT 手遊情報站"),
               "a/index.html": page(), "b/index.html": page()})
check("未成年出現在 <title>（chrome）→ 即使有退費語境仍 error",
      rc == 1 and summary(out)["error"] >= 1 and "chrome" in out, out[-500:])

rc, out = run({"index.html": page(desc="未成年退費申請請洽監護人"),
               "a/index.html": page(), "b/index.html": page()})
check("未成年出現在 meta description（chrome）→ error",
      rc == 1 and summary(out)["error"] >= 1, out[-500:])

rc, out = run({"index.html": page(footer="未成年消費可由監護人申請退款"),
               "a/index.html": page(), "b/index.html": page()})
check("手寫頁獨有 header/footer 仍按 chrome 判定，不靠 30% 共用版型",
      rc == 1 and summary(out)["error"] >= 1 and "chrome" in out, out[-500:])

# --- 7. 語境閘：零風險（否定詞須同句且在前）----------------------------------
rc, out = run({"index.html": page(body="<p>沒有任何平台能保證零風險，請自行評估。</p>"),
               "a/index.html": page(), "b/index.html": page()})
s = summary(out)
check("零風險＋同句前置否定 → gated-pass（靜默）",
      rc == 0 and s["error"] == 0 and s["gated"] == 1, out[-400:])
check("gated-pass 預設不逐筆列印（silent_pass）", "gated-pass index" not in out,
      out[-300:])

rc, out = run({"index.html": page(body="<p>本站儲值零風險，放心買。</p>"),
               "a/index.html": page(), "b/index.html": page()})
check("零風險無否定 → error", rc == 1 and summary(out)["error"] >= 1, out[-400:])

rc, out = run({"index.html": page(body="<p>我們主打零風險，其實沒有這種事。</p>"),
               "a/index.html": page(), "b/index.html": page()})
check("否定詞在該詞之後 → 不放行，error", rc == 1 and summary(out)["error"] >= 1,
      out[-400:])

rc, out = run({"index.html": page(body="<p>沒有人能保證。本站儲值零風險。</p>"),
               "a/index.html": page(), "b/index.html": page()})
check("否定詞在別句 → 不放行，error", rc == 1 and summary(out)["error"] >= 1, out[-400:])

# --- 8. 例外駁回的詞條維持 error ---------------------------------------------
for word in ("學生黨最愛的儲值方案", "穩定收益的長線玩法"):
    rc, out = run({"index.html": page(body="<p>%s</p>" % word),
                   "a/index.html": page(), "b/index.html": page()})
    check("「%s…」→ 維持 error" % word[:3], rc == 1 and summary(out)["error"] >= 1,
          out[-400:])

# --- 9. 永久跳過名單／全站禁令 ------------------------------------------------
rc, out = run({"index.html": page(body="<p>勇者傳承新版本上線</p>"),
               "a/index.html": page(), "b/index.html": page()})
check("未授權蹭 IP 名單出現即 error", rc == 1 and summary(out)["error"] >= 1, out[-400:])

rc, out = run({"index.html": page(body="<p>登入就送自選 1000 連抽</p>"),
               "a/index.html": page(), "b/index.html": page()})
check("固定額度贈送 → error", rc == 1 and summary(out)["error"] >= 1, out[-400:])

# --- 10. fail-closed ----------------------------------------------------------
rc, out = run({"index.html": page()}, rules=os.path.join(HERE, "no_such_rules.json"))
check("規則檔缺檔 → rc 2", rc == 2 and "fail-closed" in out, out[-300:])

broken = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
broken.write("{ this is not json ")
broken.close()
rc, out = run({"index.html": page()}, rules=broken.name)
os.unlink(broken.name)
check("規則檔 JSON 壞掉 → rc 2", rc == 2 and "JSON" in out, out[-300:])

empty = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
json.dump({"version": "x"}, empty)
empty.close()
rc, out = run({"index.html": page()}, rules=empty.name)
os.unlink(empty.name)
check("規則表沒有任何可執行規則 → rc 2", rc == 2, out[-300:])

root = tempfile.mkdtemp(prefix="redline-empty-")
proc = subprocess.run([sys.executable, LINT, "--build-root", root, "--rules", RULES],
                      capture_output=True, text=True, encoding="utf-8",
                      env=dict(os.environ, PYTHONIOENCODING="utf-8"))
shutil.rmtree(root, ignore_errors=True)
check("建置產物是空的（八成建置失敗）→ rc 2，不得當成全綠", proc.returncode == 2,
      (proc.stdout or "") + (proc.stderr or ""))

proc = subprocess.run([sys.executable, LINT, "--build-root",
                       os.path.join(HERE, "definitely_not_here"), "--rules", RULES],
                      capture_output=True, text=True, encoding="utf-8",
                      env=dict(os.environ, PYTHONIOENCODING="utf-8"))
check("建置產物目錄不存在 → rc 2", proc.returncode == 2,
      (proc.stdout or "") + (proc.stderr or ""))

# --- 11. baseline：只豁免列名的那幾筆，其餘照擋 -------------------------------
BASE_FILES = {"index.html": page(body="<p>上古王冠現在有 0.1 折超值方案</p>"),
              "a/index.html": page(), "b/index.html": page()}
BASE_KEY = "index.html|game_redline|「上古王冠」×「0.1 折」"
FUTURE = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
PAST = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()


def baseline_file(**extra):
    fh = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    entry = {"key": BASE_KEY, "page": "index.html", "owner": "Content Editor",
             "note": "測試用"}
    entry.update(extra)
    json.dump({"entries": [entry]}, fh, ensure_ascii=False)
    fh.close()
    return fh.name


bl = baseline_file(due=FUTURE)
rc, out = run(BASE_FILES, extra=["--baseline", bl])
check("baseline 列名（未到期）的 error → 不擋部署但仍印出 BASELINED",
      rc == 0 and "BASELINED" in out and summary(out)["error"] == 0, out[-500:])
check("BASELINED 那行帶到期日與 owner", "BASELINED (due %s, owner=Content Editor)" % FUTURE in out,
      out[-500:])

# 護欄②：到期日過了就升回會擋部署的 error（不是繼續提醒）。
expired = baseline_file(due=PAST)
rc, out = run(BASE_FILES, extra=["--baseline", expired])
check("baseline 條目過期 → 升回 error、擋部署",
      rc == 1 and summary(out)["error"] == 1 and "EXPIRED" in out, out[-600:])
os.unlink(expired)

# fail-closed：沒有到期日的豁免不算豁免（否則清單永遠不會變短）。
nodue = baseline_file()
rc, out = run(BASE_FILES, extra=["--baseline", nodue])
check("baseline 條目缺 due → 不豁免（fail-closed）",
      rc == 1 and summary(out)["error"] == 1, out[-600:])
os.unlink(nodue)

baddue = baseline_file(due="2026/08/15")
rc, out = run(BASE_FILES, extra=["--baseline", baddue])
check("baseline 條目 due 格式不對 → 不豁免（fail-closed）",
      rc == 1 and summary(out)["error"] == 1, out[-600:])
os.unlink(baddue)

# 同一份 baseline，換一筆沒列名的違規 → 照樣擋。
rc, out = run({"index.html": page(body="<p>一念劍歌限時 0.3 折</p>"),
               "a/index.html": page(), "b/index.html": page()},
              extra=["--baseline", bl])
check("baseline 未列名的 error → 照樣擋", rc == 1 and summary(out)["error"] >= 1,
      out[-500:])

rc, out = run(BASE_FILES, extra=["--baseline", bl + ".nope"])
check("--baseline 指向不存在的檔 → rc 2（不確定豁免什麼就不豁免）", rc == 2, out[-300:])
os.unlink(bl)

# --- 12. 站台身分不變式（og:site_name） --------------------------------------
# 這條擋的是「手寫完整 HTML 的頁繞過版型 include」——那些頁不共用版型，
# 所以共用版型偵測抓不到它們，只能逐頁比對站名常數。
CANON = "BT 手遊情報站｜台灣手遊儲值攻略與下載入口"


def handwritten(site_name):
    """模擬繞過 include 的手寫頁：自己硬寫 <head>，站名自己填。"""
    return ('<!doctype html><html><head><title>手寫頁</title>'
            '<meta property="og:site_name" content="%s">'
            '</head><body><p>本頁不走版型。</p></body></html>' % site_name)


rc, out = run({"index.html": page(), "a/index.html": page(),
               "games/x/index.html": handwritten("U2game")})
s = summary(out)
check("og:site_name 自稱平台方名字 → error、擋部署",
      rc == 1 and s["error"] == 1 and "site_identity" in out, out[-600:])
check("錯誤訊息帶得出實際值與正規值",
      "og:site_name='U2game'" in out and CANON in out, out[-600:])

rc, out = run({"index.html": page(), "a/index.html": page(),
               "games/x/index.html": handwritten(CANON)})
check("og:site_name 等於正規站名 → 放行", rc == 0 and summary(out)["error"] == 0,
      out[-400:])

# 具名手寫頁缺 og:site_name 或任何 chrome 欄位都必須擋下。
rc, out = run({"index.html": page(), "a/index.html": page(),
               "404.html": '<!doctype html><html><head><title>頁面不存在 | %s</title>'
                           '</head><body><p>找不到</p></body></html>' % CANON})
check("具名 404 缺 og:site_name → error（缺格 fail-closed）",
      rc == 1 and summary(out)["error"] > 0 and
      "meta:og:site_name actual=<missing> expected=<present>" in out,
      out[-400:])

broken = page(title="Fixture｜%s" % CANON).replace(
    'name="twitter:card" content="summary_large_image"',
    'name="twitter:card" content="summary"')
rc, out = run({"404.html": broken})
check("具名頁實際值不符 → EXIT=1 且帶實際值與應有值",
      rc == 1 and
      "meta:twitter:card actual='summary' expected='summary_large_image'" in out,
      out[-600:])
rc, out = run({"404.html": page(title="Fixture｜%s" % CANON)})
check("具名頁改回完整 chrome → EXIT=0", rc == 0 and summary(out)["error"] == 0,
      out[-400:])

rc, out = run({"404.html": page(title="Fixture without publisher suffix")})
check("具名頁 title 缺正規站名尾綴 → EXIT=1 且帶實際值與應有值",
      rc == 1 and "title-site-name actual='Fixture without publisher suffix'" in out
      and CANON in out, out[-600:])

# 單引號屬性、屬性順序顛倒、實體編碼 —— 換個寫法就繞過去的閘等於沒有。
rc, out = run({"index.html": page(), "a/index.html": page(),
               "games/x/index.html": '<!doctype html><html><head>'
               "<meta content='BT&nbsp;Game' property='og:site_name'>"
               "</head><body><p>x</p></body></html>"})
check("單引號＋屬性順序顛倒＋HTML 實體 → 一樣擋得下",
      rc == 1 and summary(out)["error"] == 1, out[-600:])

# 基建層：規則表缺這個常數＝沒有可比對的基準，一律 rc 2（不受任何豁免影響）。
with open(RULES, encoding="utf-8") as fh:
    _rules_obj = json.load(fh)
check("公版規則表帶得出具名常數 site_identity.canonical_site_name",
      _rules_obj.get("site_identity", {}).get("canonical_site_name") == CANON,
      repr(_rules_obj.get("site_identity")))
_stripped = dict(_rules_obj)
_stripped.pop("site_identity", None)
_fd, _noident = tempfile.mkstemp(suffix=".json")
with os.fdopen(_fd, "w", encoding="utf-8") as fh:
    json.dump(_stripped, fh, ensure_ascii=False)
rc, out = run({"index.html": page()}, rules=_noident)
check("規則表缺站名常數 → rc 2（fail-closed，不是靜默略過）", rc == 2, out[-400:])
os.unlink(_noident)

_stripped = dict(_rules_obj)
_stripped.pop("handwritten_chrome", None)
_fd, _nohandwritten = tempfile.mkstemp(suffix=".json")
with os.fdopen(_fd, "w", encoding="utf-8") as fh:
    json.dump(_stripped, fh, ensure_ascii=False)
rc, out = run({"index.html": page()}, rules=_nohandwritten)
check("規則表缺 handwritten_chrome 常數 → rc 2（fail-closed）", rc == 2, out[-400:])
os.unlink(_nohandwritten)

rc, out = run({"index.html": page()}, populate_named=False)
check("具名清單頁未出現在 build → rc 2（基建層，不受 baseline）",
      rc == 2 and "named handwritten_chrome pages missing from build" in out, out[-500:])

# --- 13. 公版規則表本身不得含內部資訊 ----------------------------------------
with open(RULES, encoding="utf-8") as fh:
    rules_text = fh.read()
leaks = [p for p in (r"ALL-\d+", "da00467", "cps", "分成", "firstpay",
                     "後台", "公告", "嚴控", "罰款", "封禁")
         if re.search(p, rules_text, re.I)]
check("公版規則表零內部欄位", not leaks, "命中：%s" % leaks)

# --- 14. --text 純文字模式（社群文案：非建置產物路徑）------------------------
# 為什麼要有這一節：CI 閘掃的是建置產物，社群貼文不經 Jekyll、不進 repo，
# 對它的覆蓋率本來是 0%。判定我們的是 u2，它不管文字從哪個管線出去。

DIRTY_POST = """【今日推薦】上古王冠 改版上線！

老玩家回歸禮包直接領，
新手入坑首儲 0.1 折起。
還有老虎機小遊戲每天免費轉。

下載 → https://qd.u2game99.com/?ag=xxxx&gid=2367&ldy=1
"""
CLEAN_POST = """【開服快報】本週新服開放時間整理

三個時段各有不同的開服活動，
入坑前先看版本差異與角色定位。

完整整理 → https://btgamevip.com/games/
"""

rc, out = run_text({"dirty.txt": DIRTY_POST})
s = summary(out)
check("故意寫壞的貼文 → rc 1、逐筆列名", rc == 1 and s and s["error"] >= 2, out[-800:])
check("命中帶得出規則 id（禁折款＋賭博字樣）",
      "shanggu-wangguan" in out and "老虎機" in out, out[-800:])

rc, out = run_text({"clean.txt": CLEAN_POST})
check("乾淨貼文 → rc 0", rc == 0 and summary(out)["error"] == 0, out[-400:])

# 整篇共現：純文字沒有 HTML 區塊結構，遊戲名與折數分行寫是最典型的違規樣態，
# 沿用建置產物的「同塊」判定會整批漏掉。
rc, out = run_text({"split.txt": "上古王冠 改版上線\n\n入坑首儲 0.1 折起\n"})
check("遊戲名與折數不同行 → 仍算整篇共現、error",
      rc == 1 and summary(out)["error"] >= 1 and "整篇共現" in out, out[-600:])

# 但兩者都沒有就不能誤報 —— 只提遊戲、不提折數是正常文案。
rc, out = run_text({"nameonly.txt": "上古王冠 改版上線，新副本開放。\n"})
check("只提禁折款、不提折數 → 0 error", rc == 0 and summary(out)["error"] == 0,
      out[-400:])

# stdin 管線：發文腳本是把記憶體裡的文案餵進來，不見得有檔案。
rc, out = run_text({}, stdin=DIRTY_POST)
check("stdin（`-`）→ 一樣擋得下", rc == 1 and summary(out)["error"] >= 2, out[-600:])

# 多份一起掃（一天多平台）。
rc, out = run_text({"a.txt": CLEAN_POST, "b.txt": DIRTY_POST})
check("多份文案：一份髒就整批非 0", rc == 1 and summary(out)["pages"] == 2, out[-600:])

# 永久跳過名單／未授權蹭 IP：出現即命中，不需要折數。
rc, out = run_text({"ip.txt": "勇者傳承 新版本上線，快來體驗。\n"})
check("未授權蹭 IP 名單出現在貼文 → error", rc == 1 and summary(out)["error"] >= 1,
      out[-400:])

# 語境閘照跑（規則表同一份，工程端不得自行增刪詞條）。
rc, out = run_text({"g1.txt": "沒有任何平台能保證零風險，請自行評估。\n"})
check("零風險＋同句前置否定 → gated-pass，不算 error",
      rc == 0 and summary(out)["error"] == 0 and summary(out)["gated"] == 1, out[-400:])
rc, out = run_text({"g2.txt": "本站儲值零風險，放心買。\n"})
check("零風險無否定 → error", rc == 1 and summary(out)["error"] >= 1, out[-400:])

# 空輸入是這種閘最典型的靜默失效（管線接錯／變數是空的），必須 fail-closed。
rc, out = run_text({"empty.txt": "\n\n"})
check("空文案 → rc 2（沒有東西可掃 ≠ 乾淨）", rc == 2, out[-400:])

rc, out = run_text({"x.txt": CLEAN_POST}, rules=os.path.join(HERE, "no_such.json"))
check("--text 規則檔缺檔 → rc 2", rc == 2 and "fail-closed" in out, out[-300:])

_bad = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
_bad.write('{ "by_name": [[[ ')
_bad.close()
rc, out = run_text({"x.txt": CLEAN_POST}, rules=_bad.name)
os.unlink(_bad.name)
check("--text 規則檔 JSON 壞掉 → rc 2", rc == 2 and "JSON" in out, out[-300:])

proc = subprocess.run([sys.executable, LINT, "--rules", RULES, "--text",
                       os.path.join(HERE, "definitely_no_draft.txt")],
                      capture_output=True, text=True, encoding="utf-8",
                      env=dict(os.environ, PYTHONIOENCODING="utf-8"))
check("--text 指向不存在的檔 → rc 2", proc.returncode == 2,
      (proc.stdout or "") + (proc.stderr or ""))

# baseline 是站台既有內容的過渡機制；貼文每天新寫，開這個口就是給貼文開後門。
rc, out = run_text({"x.txt": CLEAN_POST}, extra=["--baseline", "whatever.json"])
check("--text 不接受 baseline 豁免 → rc 2", rc == 2, out[-300:])

# 兩種輸入不得混用（避免「以為掃了建置產物、其實只掃了文案」）。
rc, out = run_text({"x.txt": CLEAN_POST}, extra=["--build-root", HERE])
check("--text 與 --build-root 混用 → rc 2", rc == 2, out[-300:])


# --- 收尾 --------------------------------------------------------------------
failed = [n for n, ok, _ in results if not ok]
print("\n驗收 %d 項，通過 %d 項。" % (len(results), len(results) - len(failed)))
if failed:
    print("未通過：%s" % "、".join(failed))
sys.exit(1 if failed else 0)
