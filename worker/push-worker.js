// Cloudflare Worker that remembers who turned on notifications (free tier is plenty).
// It never sends anything itself: the GitHub workflow downloads the list (GET /subs, admin only) and sends the pushes.
//
// Bindings (Worker -> Settings):  KV namespace  SUBS
//   ALLOWED_ORIGIN  text, e.g. https://kkotsop.github.io   (the website that may subscribe people)
//   ADMIN_TOKEN     secret, long random text; the same value is the GitHub secret PUSH_ADMIN_TOKEN
//
// Public:  POST /subscribe {endpoint, keys:{p256dh,auth}, lg:["U14","U16"]}     POST /unsubscribe {endpoint}
// Admin:   GET /subs (list)    POST /prune {endpoints:[...]}

const LEAGUES = ["U14", "U16"];
const MAX_BODY = 4096;
const B64URL = /^[A-Za-z0-9_-]+={0,2}$/;

const json = (data, status, headers) =>
  new Response(JSON.stringify(data), { status: status || 200, headers: Object.assign({ "Content-Type": "application/json" }, headers || {}) });

async function sha256hex(text) {
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return Array.from(new Uint8Array(d)).map((b) => b.toString(16).padStart(2, "0")).join("");
}

function sameToken(a, b) {                              // constant-time compare
  if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length || !a) return false;
  let r = 0;
  for (let i = 0; i < a.length; i++) r |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return r === 0;
}

function validEndpoint(e) {
  if (typeof e !== "string" || e.length > 700 || e.indexOf("https://") !== 0) return false;
  try { return new URL(e).protocol === "https:"; } catch (x) { return false; }
}

async function readJson(req) {
  const text = await req.text();
  if (text.length > MAX_BODY) throw new Error("too large");
  return JSON.parse(text);
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const cors = {
      "Access-Control-Allow-Origin": env.ALLOWED_ORIGIN || "",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
      "Access-Control-Max-Age": "86400",
      Vary: "Origin",
    };
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });

    try {
      // ---- admin (GitHub workflow) ----
      if (url.pathname === "/subs" || url.pathname === "/prune") {
        const auth = req.headers.get("Authorization") || "";
        if (!sameToken(auth.replace(/^Bearer /, ""), env.ADMIN_TOKEN)) return json({ error: "unauthorized" }, 401);
        if (url.pathname === "/subs" && req.method === "GET") {
          const out = [];
          let cursor;
          do {
            const page = await env.SUBS.list({ prefix: "s:", cursor });
            for (const k of page.keys) {
              const v = await env.SUBS.get(k.name, "json");
              if (v) out.push({ endpoint: v.endpoint, keys: v.keys, lg: v.lg });
            }
            cursor = page.list_complete ? undefined : page.cursor;
          } while (cursor);
          return json(out);
        }
        if (url.pathname === "/prune" && req.method === "POST") {
          const body = await readJson(req);
          for (const e of (body.endpoints || []).slice(0, 500)) await env.SUBS.delete("s:" + (await sha256hex(String(e))));
          return json({ ok: true });
        }
        return json({ error: "not found" }, 404);
      }

      // ---- public (the website) ----
      if (req.method !== "POST" || (url.pathname !== "/subscribe" && url.pathname !== "/unsubscribe")) return json({ error: "not found" }, 404, cors);
      if (!env.ALLOWED_ORIGIN || req.headers.get("Origin") !== env.ALLOWED_ORIGIN) return json({ error: "forbidden" }, 403, cors);
      const body = await readJson(req);
      if (!validEndpoint(body.endpoint)) return json({ error: "bad endpoint" }, 400, cors);
      const id = "s:" + (await sha256hex(body.endpoint));

      if (url.pathname === "/unsubscribe") {
        await env.SUBS.delete(id);
        return json({ ok: true }, 200, cors);
      }
      const k = body.keys || {};
      if (typeof k.p256dh !== "string" || typeof k.auth !== "string" || k.p256dh.length > 200 || k.auth.length > 60 || !B64URL.test(k.p256dh) || !B64URL.test(k.auth)) {
        return json({ error: "bad keys" }, 400, cors);
      }
      const lg = (Array.isArray(body.lg) ? body.lg : LEAGUES).filter((x) => LEAGUES.indexOf(x) > -1);
      await env.SUBS.put(id, JSON.stringify({ endpoint: body.endpoint, keys: { p256dh: k.p256dh, auth: k.auth }, lg: lg.length ? lg : LEAGUES, t: Date.now() }), { expirationTtl: 60 * 60 * 24 * 400 });
      return json({ ok: true }, 200, cors);
    } catch (e) {
      return json({ error: "bad request" }, 400, cors);
    }
  },
};
