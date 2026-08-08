// go.btgamevip.com — first-party short-link / 302 redirect
// Cloudflare Pages Advanced Mode worker (_worker.js). Ported 1:1 from
// netlify/edge-functions/go.js (ALL-66 / ALL-3 attribution) — ALL-247.
//
// Deploy: Cloudflare Pages project, framework preset = None,
//         build command = (empty), output directory = cf-pages
// Custom domain: go.btgamevip.com (CNAME from Netlify DNS -> <project>.pages.dev)
//
// To add a short link: add one entry to LINKS below and push to main.
// Pages redeploys automatically. Keep this table in sync with
// netlify/edge-functions/go.js until that file is retired.

const GO_HOST = "go.btgamevip.com";
const APEX = "https://btgamevip.com/";
const DEST_BASE = "https://qd.u2game99.com/down.html";
const AGENT_ID = "da00467";
const LDY = "1";
const COOKIE_DOMAIN = ".btgamevip.com";
const COOKIE_MAX_AGE = 60 * 60 * 24 * 90;

const LINKS = {
    "fb-bailian_wangzhe-a": { gid: "2346", utm: { utm_source: "facebook", utm_medium: "social_organic", utm_campaign: "bailian_wangzhe_launch_202607", utm_content: "image_a" } },
    "fb-bailian_wangzhe-b": { gid: "2346", utm: { utm_source: "facebook", utm_medium: "social_organic", utm_campaign: "bailian_wangzhe_launch_202607", utm_content: "image_b" } },
    "tw-bailian_wangzhe-a": { gid: "2346", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "bailian_wangzhe_launch_202607", utm_content: "tweet_a" } },
    "tw-bailian_wangzhe-b": { gid: "2346", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "bailian_wangzhe_launch_202607", utm_content: "tweet_b" } },
    "fb-shenqi_guangmang-a": { gid: "2353", utm: { utm_source: "facebook", utm_medium: "social_organic", utm_campaign: "shenqi_guangmang_launch_202607", utm_content: "image_a" } },
    "fb-shenqi_guangmang-b": { gid: "2353", utm: { utm_source: "facebook", utm_medium: "social_organic", utm_campaign: "shenqi_guangmang_launch_202607", utm_content: "image_b" } },
    "tw-shenqi_guangmang-a": { gid: "2353", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "shenqi_guangmang_launch_202607", utm_content: "tweet_a" } },
    "tw-shenqi_guangmang-b": { gid: "2353", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "shenqi_guangmang_launch_202607", utm_content: "tweet_b" } },
    "fb-wolong_sanguo-a": { gid: "2319", utm: { utm_source: "facebook", utm_medium: "social_organic", utm_campaign: "wolong_sanguo_launch_202607", utm_content: "image_a" } },
    "fb-wolong_sanguo-b": { gid: "2319", utm: { utm_source: "facebook", utm_medium: "social_organic", utm_campaign: "wolong_sanguo_launch_202607", utm_content: "image_b" } },
    "tw-wolong_sanguo-a": { gid: "2319", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "wolong_sanguo_launch_202607", utm_content: "tweet_a" } },
    "tw-wolong_sanguo-b": { gid: "2319", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "wolong_sanguo_launch_202607", utm_content: "tweet_b" } },
    // ALL-197 / daily 2026-07-24 social — tulongyingxiong gid2323 launch (no discount) / houdousanguo gid2333 topup 0.1折 (ag da00467)
    "tw-tulongyingxiong-a": { gid: "2323", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "tulongyingxiong_launch_202607", utm_content: "tweet_a" } },
    "tw-tulongyingxiong-b": { gid: "2323", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "tulongyingxiong_launch_202607", utm_content: "tweet_b" } },
    "fb-tulongyingxiong-a": { gid: "2323", utm: { utm_source: "facebook", utm_medium: "social_organic", utm_campaign: "tulongyingxiong_launch_202607", utm_content: "image_a" } },
    "fb-tulongyingxiong-b": { gid: "2323", utm: { utm_source: "facebook", utm_medium: "social_organic", utm_campaign: "tulongyingxiong_launch_202607", utm_content: "image_b" } },
    "tw-houdousanguo-a": { gid: "2333", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "houdousanguo_topup_202607", utm_content: "tweet_a" } },
    "tw-houdousanguo-b": { gid: "2333", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "houdousanguo_topup_202607", utm_content: "tweet_b" } },
    // ALL-233 retired pending valid gid — gid 1401 is dead at u2 (down.html has no title/button, desktop → 404).
    // Redirect to the games index instead of a zero-conversion dead page. Restore { gid: "<valid 23xx>" }
    // when lance confirms a correct gid from the u2 backend (ag da00467). Do NOT reuse 1401 or 46 (both dead).
    "tw-douluodalu-a": { to: "https://btgamevip.com/games/", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "douluodalu_evergreen_202607", utm_content: "tweet_a" } },
    "tw-douluodalu-b": { to: "https://btgamevip.com/games/", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "douluodalu_evergreen_202607", utm_content: "tweet_b" } },
    // ALL-165 daily 2026-07-23 — 大屠龙 gid 2366 launch (no discount) + 神奇三国 gid 2355 topup (0.1折/每日648, backend-verified)
    "tw-datulong-a": { gid: "2366", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "datulong_launch_202607", utm_content: "tweet_a" } },
    "tw-datulong-b": { gid: "2366", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "datulong_launch_202607", utm_content: "tweet_b" } },
    "fb-datulong-a": { gid: "2366", utm: { utm_source: "facebook", utm_medium: "social_organic", utm_campaign: "datulong_launch_202607", utm_content: "image_a" } },
    "fb-datulong-b": { gid: "2366", utm: { utm_source: "facebook", utm_medium: "social_organic", utm_campaign: "datulong_launch_202607", utm_content: "image_b" } },
    "tw-shenqisanguo-a": { gid: "2355", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "shenqisanguo_topup_202607", utm_content: "tweet_a" } },
    "tw-shenqisanguo-b": { gid: "2355", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "shenqisanguo_topup_202607", utm_content: "tweet_b" } },
    // ALL-193 / gid 2378 新盗墓笔记（0.1折天天2000代金）— landing CTA + FB/X A/B (ag da00467, wave-1 2026-07-24)
    "xdmbj": { gid: "2378", utm: { utm_source: "landing", utm_medium: "web", utm_campaign: "xin_daomu_biji_launch_202607", utm_content: "landing_cta" } },
    "fb-xin_daomu_biji-a": { gid: "2378", utm: { utm_source: "facebook", utm_medium: "social_organic", utm_campaign: "xin_daomu_biji_launch_202607", utm_content: "image_a" } },
    "fb-xin_daomu_biji-b": { gid: "2378", utm: { utm_source: "facebook", utm_medium: "social_organic", utm_campaign: "xin_daomu_biji_launch_202607", utm_content: "image_b" } },
    "tw-xin_daomu_biji-a": { gid: "2378", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "xin_daomu_biji_launch_202607", utm_content: "tweet_a" } },
    "tw-xin_daomu_biji-b": { gid: "2378", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "xin_daomu_biji_launch_202607", utm_content: "tweet_b" } },
    // ALL-99 / gid 2383 九界問仙 — launch FB+X A/B (ag da00467)
    "fb-jiujie_wenxian-a": { gid: "2383", utm: { utm_source: "facebook", utm_medium: "social_organic", utm_campaign: "jiujie_wenxian_launch_202607", utm_content: "image_a" } },
    "fb-jiujie_wenxian-b": { gid: "2383", utm: { utm_source: "facebook", utm_medium: "social_organic", utm_campaign: "jiujie_wenxian_launch_202607", utm_content: "image_b" } },
    "tw-jiujie_wenxian-a": { gid: "2383", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "jiujie_wenxian_launch_202607", utm_content: "tweet_a" } },
    "tw-jiujie_wenxian-b": { gid: "2383", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "jiujie_wenxian_launch_202607", utm_content: "tweet_b" } },
    // ALL-189 / gid 2368 釜底抽薪（切割沉默单职业）— landing + FB/X A/B (ag da00467, 首儲原價/no-discount)
    "fdcx": { gid: "2368", utm: { utm_source: "landing", utm_medium: "web", utm_campaign: "fudi_chouxin_launch_202607", utm_content: "cta" } },
    "fudichouxin-chuanqi": { gid: "2368", utm: { utm_source: "landing", utm_medium: "web", utm_campaign: "fudi_chouxin_launch_202607", utm_content: "cta" } },
    "fb-fudi_chouxin-a": { gid: "2368", utm: { utm_source: "facebook", utm_medium: "social_organic", utm_campaign: "fudi_chouxin_launch_202607", utm_content: "image_a" } },
    "fb-fudi_chouxin-b": { gid: "2368", utm: { utm_source: "facebook", utm_medium: "social_organic", utm_campaign: "fudi_chouxin_launch_202607", utm_content: "image_b" } },
    "tw-fudi_chouxin-a": { gid: "2368", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "fudi_chouxin_launch_202607", utm_content: "tweet_a" } },
    "tw-fudi_chouxin-b": { gid: "2368", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "fudi_chouxin_launch_202607", utm_content: "tweet_b" } },
    // ALL-134 / gid 2317 召喚師紛爭（0.05折百萬代金）— launch FB+X A/B (ag da00467)
    "fb-zhaohuanshi_fenzheng-a": { gid: "2317", utm: { utm_source: "facebook", utm_medium: "social_organic", utm_campaign: "zhaohuanshi_fenzheng_launch_202607", utm_content: "image_a" } },
    "fb-zhaohuanshi_fenzheng-b": { gid: "2317", utm: { utm_source: "facebook", utm_medium: "social_organic", utm_campaign: "zhaohuanshi_fenzheng_launch_202607", utm_content: "image_b" } },
    "tw-zhaohuanshi_fenzheng-a": { gid: "2317", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "zhaohuanshi_fenzheng_launch_202607", utm_content: "tweet_a" } },
    "tw-zhaohuanshi_fenzheng-b": { gid: "2317", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "zhaohuanshi_fenzheng_launch_202607", utm_content: "tweet_b" } },
    // ALL-230 / daily 2026-07-25 social — wenxiaoyao gid2358 launch (0.05折+送5000抽券) / jinbitanxian gid2325 topup (0.1折) / wangzhejizhan gid2295 evergreen (0.1折+全圖鑑), ag da00467
    "tw-wenxiaoyao-a": { gid: "2358", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "wenxiaoyao_launch_202607", utm_content: "tweet_a" } },
    "tw-wenxiaoyao-b": { gid: "2358", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "wenxiaoyao_launch_202607", utm_content: "tweet_b" } },
    "fb-wenxiaoyao-a": { gid: "2358", utm: { utm_source: "facebook", utm_medium: "social_organic", utm_campaign: "wenxiaoyao_launch_202607", utm_content: "image_a" } },
    "fb-wenxiaoyao-b": { gid: "2358", utm: { utm_source: "facebook", utm_medium: "social_organic", utm_campaign: "wenxiaoyao_launch_202607", utm_content: "image_b" } },
    "tw-jinbitanxian-a": { gid: "2325", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "jinbitanxian_topup_202607", utm_content: "tweet_a" } },
    "tw-jinbitanxian-b": { gid: "2325", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "jinbitanxian_topup_202607", utm_content: "tweet_b" } },
    "tw-wangzhejizhan-a": { gid: "2295", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "wangzhejizhan_evergreen_202607", utm_content: "tweet_a" } },
    "tw-wangzhejizhan-b": { gid: "2295", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "wangzhejizhan_evergreen_202607", utm_content: "tweet_b" } },
    // ALL-287 / daily 2026-07-26 social (母 ALL-286 / 祖 ALL-285) — xiyoumaoxian gid2363 launch / dandanqimiao gid2359 topup / yihaojuntuan gid2352 evergreen, ag da00467
    "tw-xiyoumaoxian-a": { gid: "2363", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "xiyoumaoxian_launch_202607", utm_content: "tweet_a" } },
    "tw-xiyoumaoxian-b": { gid: "2363", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "xiyoumaoxian_launch_202607", utm_content: "tweet_b" } },
    "fb-xiyoumaoxian-a": { gid: "2363", utm: { utm_source: "facebook", utm_medium: "social_organic", utm_campaign: "xiyoumaoxian_launch_202607", utm_content: "image_a" } },
    "fb-xiyoumaoxian-b": { gid: "2363", utm: { utm_source: "facebook", utm_medium: "social_organic", utm_campaign: "xiyoumaoxian_launch_202607", utm_content: "image_b" } },
    "tw-dandanqimiao-a": { gid: "2359", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "dandanqimiao_topup_202607", utm_content: "tweet_a" } },
    "tw-dandanqimiao-b": { gid: "2359", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "dandanqimiao_topup_202607", utm_content: "tweet_b" } },
    "tw-yihaojuntuan-a": { gid: "2352", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "yihaojuntuan_evergreen_202607", utm_content: "tweet_a" } },
    "tw-yihaojuntuan-b": { gid: "2352", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "yihaojuntuan_evergreen_202607", utm_content: "tweet_b" } },
    // ALL-390 / daily 2026-07-30 social（訊息軸「這款遊戲怎麼儲值最省」，重啟第一週）— 規格來源：
    // ALL-390 附件 ALL-390-links-registry.json（Social Editor 2026-07-30），Board 2026-07-30 上稿。
    // 目的地是自家 landing，所以用 to: 而不是 gid:（to: 分支只帶 UTM、不帶 ag/gid/ldy；u2 歸因由
    // landing 上的下載按鈕 ag=da00467 承接）。
    "tw-save-daomubiji": { to: "https://btgamevip.com/games/xin-daomubiji-topup-discount/", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "save_compare_202607", utm_content: "x_20260730" } },
    "fb-save-shengguang": { to: "https://btgamevip.com/games/shengguang-zhizhan/", utm: { utm_source: "facebook", utm_medium: "social_organic", utm_campaign: "save_howto_202607", utm_content: "fb_20260730" } },
    // ig-save = IG link-in-bio（ALL-375 已申請）。本週指向聖光之戰 landing；以後每週輪替只改這一行的 to:。
    "ig-save": { to: "https://btgamevip.com/games/shengguang-zhizhan/", utm: { utm_source: "instagram", utm_medium: "social_bio", utm_campaign: "save_ig_bio_202607", utm_content: "ig_20260730" } },
    // 2026-07-28 launch cohort - 4 titles, one landing page each.
    // Destination is our own landing page, so these use to: rather than gid: — the to: branch
    // carries UTM only, and the download button on the landing page carries the payout params.
    "fb-tianxuan_yingxiong-a": { to: "https://btgamevip.com/games/tianxuan-yingxiong/", utm: { utm_source: "facebook", utm_medium: "social_organic", utm_campaign: "tianxuan_yingxiong_launch_202607", utm_content: "image_a" } },
    "fb-tianxuan_yingxiong-b": { to: "https://btgamevip.com/games/tianxuan-yingxiong/", utm: { utm_source: "facebook", utm_medium: "social_organic", utm_campaign: "tianxuan_yingxiong_launch_202607", utm_content: "image_b" } },
    "tw-tianxuan_yingxiong-a": { to: "https://btgamevip.com/games/tianxuan-yingxiong/", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "tianxuan_yingxiong_launch_202607", utm_content: "tweet_a" } },
    "tw-tianxuan_yingxiong-b": { to: "https://btgamevip.com/games/tianxuan-yingxiong/", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "tianxuan_yingxiong_launch_202607", utm_content: "tweet_b" } },
    "fb-gongfu_zhiye-a": { to: "https://btgamevip.com/games/gongfu-zhiye/", utm: { utm_source: "facebook", utm_medium: "social_organic", utm_campaign: "gongfu_zhiye_launch_202607", utm_content: "image_a" } },
    "fb-gongfu_zhiye-b": { to: "https://btgamevip.com/games/gongfu-zhiye/", utm: { utm_source: "facebook", utm_medium: "social_organic", utm_campaign: "gongfu_zhiye_launch_202607", utm_content: "image_b" } },
    "tw-gongfu_zhiye-a": { to: "https://btgamevip.com/games/gongfu-zhiye/", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "gongfu_zhiye_launch_202607", utm_content: "tweet_a" } },
    "tw-gongfu_zhiye-b": { to: "https://btgamevip.com/games/gongfu-zhiye/", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "gongfu_zhiye_launch_202607", utm_content: "tweet_b" } },
    "fb-douzhuan_wulin-a": { to: "https://btgamevip.com/games/douzhuan-wulin/", utm: { utm_source: "facebook", utm_medium: "social_organic", utm_campaign: "douzhuan_wulin_launch_202607", utm_content: "image_a" } },
    "fb-douzhuan_wulin-b": { to: "https://btgamevip.com/games/douzhuan-wulin/", utm: { utm_source: "facebook", utm_medium: "social_organic", utm_campaign: "douzhuan_wulin_launch_202607", utm_content: "image_b" } },
    "tw-douzhuan_wulin-a": { to: "https://btgamevip.com/games/douzhuan-wulin/", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "douzhuan_wulin_launch_202607", utm_content: "tweet_a" } },
    "tw-douzhuan_wulin-b": { to: "https://btgamevip.com/games/douzhuan-wulin/", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "douzhuan_wulin_launch_202607", utm_content: "tweet_b" } },
    "fb-wangzhe_zhijian2-a": { to: "https://btgamevip.com/games/wangzhe-zhijian-2/", utm: { utm_source: "facebook", utm_medium: "social_organic", utm_campaign: "wangzhe_zhijian2_launch_202607", utm_content: "image_a" } },
    "fb-wangzhe_zhijian2-b": { to: "https://btgamevip.com/games/wangzhe-zhijian-2/", utm: { utm_source: "facebook", utm_medium: "social_organic", utm_campaign: "wangzhe_zhijian2_launch_202607", utm_content: "image_b" } },
    "tw-wangzhe_zhijian2-a": { to: "https://btgamevip.com/games/wangzhe-zhijian-2/", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "wangzhe_zhijian2_launch_202607", utm_content: "tweet_a" } },
    "tw-wangzhe_zhijian2-b": { to: "https://btgamevip.com/games/wangzhe-zhijian-2/", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "wangzhe_zhijian2_launch_202607", utm_content: "tweet_b" } },
    // u2game 品牌詞承接：目的地是自家品牌導引頁（非 u2），故走 to: 分支，不帶 ag/gid/ldy、零 payout 影響。
    "tw-u2_brand-a": { to: "https://btgamevip.com/u2game-brand-guide", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "u2game_brand_202608", utm_content: "tweet_a" } },
    "tw-u2_brand-b": { to: "https://btgamevip.com/u2game-brand-guide", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "u2game_brand_202608", utm_content: "tweet_b" } },
    "fb-u2_brand-a": { to: "https://btgamevip.com/u2game-brand-guide", utm: { utm_source: "facebook", utm_medium: "social_organic", utm_campaign: "u2game_brand_202608", utm_content: "image_a" } },
    "fb-u2_brand-b": { to: "https://btgamevip.com/u2game-brand-guide", utm: { utm_source: "facebook", utm_medium: "social_organic", utm_campaign: "u2game_brand_202608", utm_content: "image_b" } },
};

function readCookie(request, name) {
    const c = request.headers.get("Cookie");
    if (!c) return null;
    const m = c.match(new RegExp("(?:^|;\\s*)" + name + "=([^;]+)"));
    return m ? m[1] : null;
}

function handle(request) {
    const url = new URL(request.url);
    const host = (request.headers.get("host") || url.hostname).toLowerCase();

    // Pages also serves <project>.pages.dev and preview URLs. Only the real
    // short-link host does redirects; anything else goes to the apex so a
    // stray preview URL can never leak attribution-less traffic.
    const isGoHost = host === GO_HOST;

    const slug = decodeURIComponent(url.pathname.replace(/^\/+/, "").replace(/\/+$/, ""));

    if (!slug || slug === "healthz") {
        return new Response("go.btgamevip.com ok", {
            status: 200,
            headers: { "Cache-Control": "no-store", "Content-Type": "text/plain; charset=utf-8" },
        });
    }

    if (!isGoHost) return Response.redirect(APEX, 302);

    const entry = LINKS[slug];

    if (entry && entry.to) {
        // ALL-233: retired slug — 302 to an internal page instead of a dead u2 gid.
        // Board 2026-07-28: keep carrying the entry's UTM. This branch used to return
        // before the UTM loop below, so every click arriving from an already-published
        // post on a retired slug landed unlabelled and was invisible in GA4.
        // ag/gid/ldy are deliberately NOT added here — the destination is our own site,
        // not u2, so there is no payout param to carry.
        const to = new URL(entry.to);
        for (const [k, v] of Object.entries(entry.utm || {})) {
            if (v) to.searchParams.set(k, String(v));
        }
        return Response.redirect(to.toString(), 302);
    }

    if (!entry || !entry.gid) {
        return Response.redirect(APEX + "?e=badslug&s=" + encodeURIComponent(slug), 302);
    }

    const existing = readCookie(request, "aw_cid");
    const awCid = existing || crypto.randomUUID();

    const dest = new URL(DEST_BASE);
    dest.searchParams.set("ag", AGENT_ID);
    dest.searchParams.set("gid", String(entry.gid));
    dest.searchParams.set("ldy", LDY);
    for (const [k, v] of Object.entries(entry.utm || {})) {
        if (v) dest.searchParams.set(k, String(v));
    }
    dest.searchParams.set("aw_cid", awCid);

    const headers = new Headers({ Location: dest.toString(), "Cache-Control": "no-store" });
    if (!existing) {
        headers.append(
            "Set-Cookie",
            `aw_cid=${awCid}; Domain=${COOKIE_DOMAIN}; Path=/; Max-Age=${COOKIE_MAX_AGE}; Secure; SameSite=Lax`
        );
    }
    return new Response(null, { status: 302, headers });
}

export default {
    async fetch(request) {
        try {
            return handle(request);
        } catch (err) {
            // Never 500 on a short link — a broken redirect loses the click.
            return Response.redirect(APEX + "?e=goerr", 302);
        }
    },
};
