# cf-pages — go.btgamevip.com 短鏈轉址器（Cloudflare Pages）

這個目錄是 `go.btgamevip.com` 的部署來源，取代原本的 Netlify Edge Function
（`netlify/edge-functions/go.js`）。搬家原因見 ALL-247：Netlify 建置額度用完後
每個 commit 都 Skipped，轉址器凍結在 7/24 舊版本，六條短鏈回錯誤頁、
所有短鏈轉出都沒有 UTM。

## Cloudflare Pages 專案設定

| 項目 | 值 |
| --- | --- |
| Framework preset | None |
| Build command | （留空） |
| Build output directory | `cf-pages` |
| Custom domain | `go.btgamevip.com` |

`_worker.js` 位於輸出目錄根部 = Pages Advanced Mode，所有請求都交給它處理，
不需要建置步驟。推 main 就自動重新部署。

## DNS

`go` 的 CNAME 留在 Netlify DNS，指向 `<project>.pages.dev`。
**不動 nameserver、不動 apex 的四筆 A 記錄、不動 www CNAME。**
出事只影響 `go` 子網域，主站不受影響。

## 新增一條短鏈

只改 `_worker.js` 裡的 `LINKS` 表，加一筆，推 main，Pages 自動部署。
在 `netlify/edge-functions/go.js` 退場前，兩邊的 `LINKS` 表要保持一致。

## 驗收

- `GET /healthz` → 200 `go.btgamevip.com ok`
- 任一有效 slug → 302 到 `qd.u2game99.com/down.html`，含 `ag=da00467`、
  正確 `gid`、`ldy=1`、完整 UTM、`aw_cid`
- 首次造訪要有 `Set-Cookie: aw_cid=...; Domain=.btgamevip.com`；
  帶既有 cookie 再訪要沿用同一個 `aw_cid`，不得重發
- 無效 slug → 302 到 `https://btgamevip.com/?e=badslug&s=<slug>`
- `tw-douluodalu-a` / `-b`（ALL-233 已退場）→ 302 到 `https://btgamevip.com/games/`
