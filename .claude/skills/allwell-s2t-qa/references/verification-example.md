# Verification example

Run the bundled positive fixture:

```powershell
python scripts/scan_simplified.py assets/sample-simplified.html --json --pretty
```

The checked-in fixture was verified with the existing OpenCC package on 2026-08-14. It returns exit 1 with `FIX=13`, `REVIEW=1`, and `TOTAL=14`, lists every detected file/line/column, and includes both:

- `FIX` suggestions such as `下载→下載`, `账号→帳號`, `登录→登入`, `页面→頁面`, `网络→網路`, `链接→連結`, `软件→軟體`, `后台→後台`, and `异常→異常`.
- A `REVIEW` finding for `皇后`, because `后` is context-sensitive and should not be replaced automatically.

Run a clean negative fixture through stdin:

```powershell
"下載與帳號登入說明。故事中的皇后維持原字。" |
  python scripts/scan_simplified.py --stdin --json --pretty
```

The clean fixture returns exit 0 with `FIX=0`, `REVIEW=0`, and `TOTAL=0`.

These fixtures prove detection and reporting behavior only. They do not replace rendered-HTML redline lint, source validation, or human review of proper nouns.
