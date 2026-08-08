#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""redline_lint_site.py --build-root 的驗收測試。

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

PAGE = """<!doctype html><html><head>
<title>{title}</title>
<meta property="og:site_name" content="BT 手遊情報站｜台灣手遊儲值攻略與下載入口">
<meta name="description" content="{desc}">
</head><body>
<header><p>BT 手遊情報站</p></header>
{body}
<footer><p>{footer}</p></footer>
</body></html>
"""

# 共用版型（footer）的預設文字：三頁以上共用才會被認成 chrome。
PLAIN_FOOTER = "BT 手遊情報站｜台灣手遊儲值攻略與下載入口"

results = []


def page(title="一般標題｜BT 手遊情報站", desc="一般說明", body="", footer=PLAIN_FOOTER):
    return PAGE.format(title=title, desc=desc, body=body, footer=footer)


def run(files, extra=(), rules=RULES):
    """把 files（相對路徑 → 內容）寫成臨時建置產物，跑 lint，回 (rc, stdout)。"""
    root = tempfile.mkdtemp(prefix="redline-accept-")
    try:
        for rel, content in files.items():
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
check("summary 行存在且 pages 正確", s and s["pages"] == 3, out[-200:])

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

# --- 12. 公版規則表本身不得含內部資訊 ----------------------------------------
with open(RULES, encoding="utf-8") as fh:
    rules_text = fh.read()
leaks = [p for p in (r"ALL-\d+", "da00467", "cps", "分成", "firstpay",
                     "後台", "公告", "嚴控", "罰款", "封禁")
         if re.search(p, rules_text, re.I)]
check("公版規則表零內部欄位", not leaks, "命中：%s" % leaks)

# --- 收尾 --------------------------------------------------------------------
failed = [n for n, ok, _ in results if not ok]
print("\n驗收 %d 項，通過 %d 項。" % (len(results), len(results) - len(failed)))
if failed:
    print("未通過：%s" % "、".join(failed))
sys.exit(1 if failed else 0)
