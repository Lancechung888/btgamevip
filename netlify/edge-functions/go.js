// go.btgamevip.com - first-party short-link / 302 redirect (Netlify Edge Function)
// ALL-66 / ALL-3 attribution.
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
    // ALL-167 / gid 1401 斗羅大陸（逆转时空·0.1折武魂觉醒）— evergreen X A/B (ag da00467); corrected from dead gid 46 per ALL-166
    "tw-douluodalu-a": { gid: "1401", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "douluodalu_evergreen_202607", utm_content: "tweet_a" } },
    "tw-douluodalu-b": { gid: "1401", utm: { utm_source: "twitter", utm_medium: "social_organic", utm_campaign: "douluodalu_evergreen_202607", utm_content: "tweet_b" } },
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
};
export default async (request) => {
    const url = new URL(request.url);
    const host = (request.headers.get("host") || url.hostname).toLowerCase();
    if (host !== GO_HOST) return;
    const slug = decodeURIComponent(url.pathname.replace(/^\/+/, "").replace(/\/+$/, ""));
    if (!slug || slug === "healthz") {
          return new Response("go.btgamevip.com ok", { status: 200, headers: { "Cache-Control": "no-store" } });
    }
    const entry = LINKS[slug];
    if (!entry || !entry.gid) {
          return Response.redirect(APEX + "?e=badslug&s=" + encodeURIComponent(slug), 302);
    }
    const existing = readCookie(request, "aw_cid");
    const awCid = existing || crypto.randomUUID();
    const dest = new URL(DEST_BASE);
    dest.searchParams.set("ag", AGENT_ID);
    dest.searchParams.set("gid", String(entry.gid));
    dest.searchParams.set("ldy", LDY);
    for (const [k, v] of Object.entries(entry.utm || {})) { if (v) dest.searchParams.set(k, String(v)); }
    dest.searchParams.set("aw_cid", awCid);
    const headers = new Headers({ Location: dest.toString(), "Cache-Control": "no-store" });
    if (!existing) {
          headers.append("Set-Cookie", `aw_cid=${awCid}; Domain=${COOKIE_DOMAIN}; Path=/; Max-Age=${COOKIE_MAX_AGE}; Secure; SameSite=Lax`);
    }
    return new Response(null, { status: 302, headers });
};

function readCookie(request, name) {
    const c = request.headers.get("Cookie");
    if (!c) return null;
    const m = c.match(new RegExp("(?:^|;\\s*)" + name + "=([^;]+)"));
    return m ? m[1] : null;
}
