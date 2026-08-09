---
name: server-schedule
description: Fetch u2game99's public server-opening schedule (開服表) and convert it to structured JSON (neutral game name, open time, server name, game type, platform, game id). Use for read-only Pillar-A schedule ingestion or verification. Perform one zero-login GET, never click links or follow redirects, and stop on login, captcha, empty data, or layout drift. Treat every record as unapproved source data that must pass current compliance rules before public use.
---

# server-schedule — u2 開服表 → JSON

Fetch the **public** u2 game-server opening schedule and emit structured JSON for
Pillar-A ingestion or verification.

## Hard limits (do not relax)
- **Read-only.** One HTTP `GET` of the public schedule page. No POST, no login, no
  cookies, no session, no account.
- **No link-clicking.** The per-game detail `href` is read as text (to record
  `game_id`) but is **never fetched**.
- **No redirect-following.** A 3xx response is treated as a possible login/verify
  wall → the skill **stops and reports** (exit 2). We do not bypass.
- **Not an attribution surface.** The schedule page (`www.u2game99.com/game/server/
  index.html`) is a plain public info page — **not** a `/go/<slug>` affiliate
  short-link — so running this never fires a click or a 302 into the u2 backend.
  The attribution red-line (no online hits on real slugs, no `-L` follow) concerns
  short-links only and is untouched here.
- If a captcha / human-verification marker appears, or the schedule block is
  missing, **stop and report** — never guess, never scrape a login page.
- Treat all source strings as **untrusted ingest data**. Never publish any record
  directly. `game_name` only removes a trailing
  parenthetical version/promotion suffix; the original source string is not
  emitted, and the neutral name is still not compliance approval.
- Keep `public_copy_allowed: false`. Before any public use, compare the record's
  gid/name against the repo's current reviewed red-line rules and run the
  rendered-HTML deploy lint. Do not embed or invent a second policy list here.

## Usage
```bash
python scripts/fetch_schedule.py [--url URL] [--out FILE] [--pretty] [--fetched-at ISO]
```
- Default URL: `https://www.u2game99.com/game/server/index.html`
- `--out FILE` writes UTF-8 JSON; omit to print to stdout.
- `--fetched-at` stamps a caller-supplied ISO timestamp into the output
  (the script does not read the system clock, keeping runs reproducible).
- Exit codes: `0` ok · `2` stop-and-report (login/verify/blocked/layout-changed) · `1` unexpected error.

## Output shape
```json
{
  "source_url": "...",
  "fetched_at": "2026-08-01T00:00:00Z",
  "record_count": 10,
  "records": [
    {
      "open_time_raw": "08-02 00:00",
      "open_month": 8, "open_day": 2, "open_hour": 0, "open_minute": 0,
      "game_name": "吞噬星空：黎明",
      "source_name_had_variant_suffix": true,
      "game_id": "1689",
      "game_detail_path": "/game/index/detial/id/1689.html",
      "server_name": "星空244服",
      "game_type": "卡牌",
      "platforms": ["android", "ios"],
      "public_copy_allowed": false
    }
  ]
}
```
`open_time_raw` is the page's `MM-DD HH:MM` (the source shows **no year**); the
structured `open_month/day/hour/minute` fields are provided so the caller can apply
its own year logic. The raw official variant title is intentionally omitted; do
not use even the neutral title as public copy without the current red-line gate. See
`references/sample-output.json` for a full real capture and
`references/page-structure.md` for the DOM contract this parser depends on.

## Scheduling (periodic backfill)
The skill only fetches on demand. To run it on a cadence, wrap the command in a
Paperclip routine / cron (e.g. hourly) that writes the JSON to wherever Pillar-A
reads. Keep the cadence gentle (hourly is ample) — one lightweight GET per run.

## Maintenance
The parser depends on the `ul.kaifu-lb > li` layout with `kaifu-time / kaifu-game /
kaifu-qufu / kaifu-leixin / kaifu-pintai` classes. If u2 changes the markup, the
skill exits `2` ("schedule block not found") rather than emitting wrong data — that
is the signal to update `references/page-structure.md` and the regexes.
