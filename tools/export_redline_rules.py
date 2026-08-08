#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""redline 規則表：私版 → 公版，單向產出。

為什麼存在：紅線閘要在 CI（公開 repo）裡跑，就得把規則表放進 repo；
但規則表的權威來源含 provenance（平台方公告來源、內部工單號、罰則金額），
那些一個字都不能公開。所以拆兩份、由本腳本單向產出：

    data/game_redlines.json      私版（.gitignore；provenance 與稽核欄位留這裡）
        │  export_redline_rules.py
        ▼
    tools/redline_rules.json     公版（進 repo；只有 id／名稱／pattern／severity／語境閘）

兩道閘，任一不過就中止、不寫檔（fail-closed）：

  閘 1｜欄位白名單
      每個區段的鍵拆成 public（輸出）與 private_only（明示丟棄）兩張表。
      **落在兩張表之外的鍵一律報錯中止**，不靜默丟棄 —— 靜默丟棄的失敗樣態是
      「哪天私版多一個敏感欄位，沒人發現它已經被漏進公版」。丟棄哪些鍵會列印出來。

  閘 2｜輸出值掃描
      把即將寫出的公版整份序列化，用內部資訊樣態掃一遍（工單號／後台／公告／
      分潤欄位／代理碼／罰款）。命中即中止。閘 1 管結構、閘 2 管內容，
      因為 public 欄位裡也可能被人手寫進來源說明。

用法：
    python3 tools/export_redline_rules.py                 # 產出
    python3 tools/export_redline_rules.py --check         # 只驗現有公版是否與私版一致（不寫檔）

退出碼：0 = 成功；1 = 白名單／掃描不過或 --check 不一致；2 = 檔案／JSON 錯誤。
純標準庫、零網路。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PRIVATE = os.path.join(ROOT, "data", "game_redlines.json")
PUBLIC = os.path.join(HERE, "redline_rules.json")

# --- 閘 1：欄位白名單 ---------------------------------------------------------
# public：輸出到公版的鍵。private_only：已知的內部欄位，明示丟棄（會列印）。
# rename：私版鍵 → 公版鍵（public_message → message 等；公版說明是另外寫的乾淨版本）。
SECTIONS = {
    "__root__": {
        "public": ["version", "discount_patterns", "by_name", "frozen", "by_gid",
                   "wording", "context_gates", "density"],
        "private_only": ["_comment"],
    },
    "by_name": {
        "public": ["id", "names", "rule", "severity", "public_message", "public_suggestion"],
        "private_only": ["source", "message", "suggestion", "notes"],
    },
    "frozen": {
        "public": ["id", "names", "severity", "public_message", "public_suggestion"],
        "private_only": ["source", "message", "suggestion", "notes"],
    },
    "by_gid": {
        "public": ["id", "gids", "patterns", "unless_page", "severity",
                   "public_message", "public_suggestion"],
        "private_only": ["source", "message", "suggestion", "notes"],
    },
    "wording": {
        "public": ["id", "pattern", "severity", "public_message", "public_suggestion"],
        "private_only": ["source", "message", "suggestion", "notes"],
    },
    "context_gates": {
        "public": ["id", "pattern", "gate", "cues", "chrome_never_pass", "silent_pass",
                   "severity", "public_message", "public_suggestion"],
        "private_only": ["source", "message", "suggestion", "notes"],
    },
    "density": {
        "public": ["pattern", "strict_pattern", "aggregation_threshold",
                   "title_max_chars", "severity", "public_message", "public_suggestion"],
        "private_only": ["source", "message", "suggestion", "notes"],
    },
}

RENAME = {"public_message": "message", "public_suggestion": "suggestion"}

# --- 閘 2：內部資訊樣態 -------------------------------------------------------
# 對外只要出現這些，就是內部資訊外流（工單號／後台路徑／分潤數字），一律中止。
INTERNAL_MARKERS = [
    (r"ALL-\d+", "內部工單號"),
    (r"ag=[a-z]{2}\d{4,}", "代理碼"),
    (r"cps|分成|firstpay|首儲金額|payout|commission|sub[_-]?id|aw_cid", "分潤／歸因內部欄位"),
    (r"後台|backend|admin\.|dashboard\.", "後台路徑"),
    (r"公告|嚴控|通知編號|逐字讀", "平台方公告來源說明"),
    (r"罰款|罰則|停止合作|封禁", "罰則條款"),
    (r"u2\s*(後台|公告|規則|平台)", "平台方內部規則引述"),
    (r"§\s*[一二三四五六七八九十]+", "內部政策快照條號"),
    (r"Board|CoS|老闆|lance", "內部角色"),
]


def die(msg: str, code: int = 1):
    print("EXPORT FAIL: %s" % msg, file=sys.stderr)
    sys.exit(code)


def filter_keys(obj: dict, section: str, where: str) -> dict:
    """套白名單。未列名的鍵 → 中止（不靜默丟棄）。"""
    spec = SECTIONS[section]
    public, private_only = spec["public"], spec["private_only"]
    unknown = [k for k in obj if k not in public and k not in private_only]
    if unknown:
        die("%s 出現白名單外的鍵 %s。\n"
            "     這是刻意 fail-closed：新欄位可能含內部資訊，必須有人明確決定它\n"
            "     該進公版（加進 SECTIONS['%s']['public']）還是留私版（加進 private_only）。"
            % (where, unknown, section))
    dropped = [k for k in obj if k in private_only]
    if dropped:
        DROP_LOG.append("%s → 丟棄 %s" % (where, ", ".join(dropped)))
    return {RENAME.get(k, k): obj[k] for k in obj if k in public}


DROP_LOG: list = []


def build_public(priv: dict) -> dict:
    out = filter_keys(priv, "__root__", "根層")
    for section in ("by_name", "frozen", "by_gid", "wording", "context_gates"):
        if section in out:
            out[section] = [
                filter_keys(item, section, "%s[%d] (%s)" % (section, i, item.get("id", "?")))
                for i, item in enumerate(out[section])
            ]
    if "density" in out:
        out["density"] = filter_keys(out["density"], "density", "density")
    out["_generated_by"] = ("tools/export_redline_rules.py —— 本檔為自動產出的公版，"
                            "請勿手改；改規則請改私版後重跑本腳本。")
    return out


def scan_output(text: str) -> None:
    """閘 2：對即將寫出的內容做內部資訊掃描。"""
    hits = []
    for pattern, label in INTERNAL_MARKERS:
        for m in re.finditer(pattern, text, re.I):
            line = text.count("\n", 0, m.start()) + 1
            hits.append("  L%d %s：%r" % (line, label, m.group(0)))
    if hits:
        die("公版內容命中內部資訊樣態 %d 處，已中止、未寫檔：\n%s\n"
            "     處置：把該說明改寫成不含來源／工單／罰則的 public_message。"
            % (len(hits), "\n".join(hits[:40])))


def main() -> int:
    ap = argparse.ArgumentParser(description="redline 規則表 私版→公版 單向產出")
    ap.add_argument("--private", default=PRIVATE)
    ap.add_argument("--public", default=PUBLIC)
    ap.add_argument("--check", action="store_true",
                    help="只比對現有公版是否與私版一致，不寫檔")
    args = ap.parse_args()

    if not os.path.isfile(args.private):
        die("找不到私版規則表 %s（它在 .gitignore 裡，CI 上本來就不該有；"
            "本腳本只在本機跑）" % args.private, 2)
    try:
        with open(args.private, encoding="utf-8") as fh:
            priv = json.load(fh)
    except json.JSONDecodeError as exc:
        die("私版 JSON 解析失敗：%s" % exc, 2)

    pub = build_public(priv)
    text = json.dumps(pub, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    scan_output(text)

    for line in DROP_LOG:
        print("  drop  %s" % line)
    print("閘 1 欄位白名單：通過（明示丟棄 %d 處）" % len(DROP_LOG))
    print("閘 2 內部資訊掃描：通過（%d 條樣態全數 0 命中）" % len(INTERNAL_MARKERS))

    if args.check:
        if not os.path.isfile(args.public):
            die("--check：公版 %s 不存在" % args.public)
        with open(args.public, encoding="utf-8") as fh:
            current = fh.read()
        if current != text:
            die("--check：公版與私版不一致，請重跑本腳本產出。")
        print("--check：公版與私版一致。")
        return 0

    with open(args.public, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print("已產出公版 %s（%d bytes）" % (args.public, len(text.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
