# u2 開服表 DOM contract (verified 2026-08-09)

Source: `https://www.u2game99.com/game/server/index.html`
Response: `HTTP 200`, `text/html; charset=utf-8`, ~30 KB, **0 redirects**, static HTML
(server-rendered — the schedule rows are in the initial HTML, no JS needed).

## Layout
The schedule is a single list:

```html
<ul class="kaifu-lb">
  <li>
    <!-- <div class="kaifu-time">01-12<span>10:19</span></div> -->   <!-- TEMPLATE, commented out -->
    <div class="kaifu-time">08-02 00:00</div>                        <!-- REAL open time (MM-DD HH:MM) -->
    <div class="kaifu-game">
      <a href="/game/index/detial/id/1689.html">
        <img src="...gif">
        <h4>範例遊戲（官方版本尾綴）</h4>                              <!-- game name -->
      </a>
    </div>
    <div class="kaifu-qufu">星空244服</div>                          <!-- server / 區服 name -->
    <div class="kaifu-leixin">卡牌</div>                             <!-- game type / 類型 -->
    <div class="kaifu-pintai">
      <img src=".../android.png" class="az-img"> <img src=".../apple.png" class="pg-img">
    </div>                                                           <!-- platforms -->
    <div class="kaifu-down"><a href="/game/index/detial/id/1689.html">游戏专区</a></div>
  </li>
  ...
</ul>
```

## Gotchas the parser handles
1. **Commented-out template markup.** Each `<li>` ships a commented placeholder
   `<!-- <div class="kaifu-time">01-12...</div> -->` before the real value, plus
   commented `kaifu-logo` / `kaifu-libao` blocks. The parser strips **all** HTML
   comments (`<!-- ... -->`) before field extraction, otherwise it would read the
   `01-12 10:19` template instead of the live time.
2. **No year in the time.** The page prints `MM-DD HH:MM` only. We keep the raw
   string and expose month/day/hour/minute; year inference is left to the caller.
3. **Legit duplicate games.** The same game appears on multiple rows with different
   `kaifu-qufu` (e.g. 战影破穹 → 神器10区 / 9区 / 8区). These are distinct server
   openings, not dup bugs — do **not** dedupe by game.
4. **Leading tabs/whitespace** inside `kaifu-qufu` / `kaifu-leixin` — collapsed.
5. Only the current page of rows is captured (10 on the observed page). If u2 adds
   pagination and Pillar-A needs the full list, extend the fetcher — but note that
   following a "next page" link is a link-click and must stay a plain GET of a
   public `?page=N` URL, never a login/redirect.

## Publication boundary

The official `<h4>` frequently includes a parenthetical version or promotion
suffix. The parser omits that exact string, derives a neutral base `game_name` by
removing only the trailing parenthetical, records whether it removed a suffix in
`source_name_had_variant_suffix`, and sets `public_copy_allowed` to `false` on
every row. This skill is an ingest
adapter, not a policy engine: frozen gids, IP risks, prohibited claims, and any
future rule changes remain governed by the repository's reviewed red-line rules
and rendered-HTML deploy lint.
