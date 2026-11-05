/*
 * Feedback sink for the ads experiment.
 *
 * ads-experiment.js posts one small JSON document when a visitor answers the
 * question or switches away from ads. This Worker checks it and forwards it to
 * a webhook the maintainer already reads (a Discord or Slack incoming webhook,
 * for example), so no database is needed.
 *
 * Deploy with Wrangler and set:
 *   FEEDBACK_WEBHOOK_URL  the incoming webhook URL (a secret, not a var)
 *   ALLOWED_ORIGINS       comma-separated, e.g. "https://innioasis.app"
 *
 *   wrangler secret put FEEDBACK_WEBHOOK_URL --config wrangler.ads-feedback.toml
 *
 * Request:
 *   POST /ad-feedback   {"type":"ads-experiment","score":"fine","comment":"","page":"/","views":2,"at":"..."}
 *
 * Nothing is stored here and no IP address or user agent is forwarded.
 */

const MAX_BODY = 4096;
const MAX_COMMENT = 600;
const SCORES = ["fine", "slight", "intrusive", "donations", "optout"];

function parseList(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function corsHeaders(request, env) {
  const allowed = parseList(env.ALLOWED_ORIGINS);
  const origin = request.headers.get("Origin") || "";
  if (!allowed.length) return { "Access-Control-Allow-Origin": "*", Vary: "Origin" };
  if (!origin) return {};
  if (!allowed.includes(origin)) return null;
  return {
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    Vary: "Origin",
  };
}

function text(status, message, cors) {
  return new Response(message + "\n", {
    status,
    headers: Object.assign(
      { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store" },
      cors || {}
    ),
  });
}

function clean(value, limit) {
  return String(value == null ? "" : value).replace(/[\u0000-\u001f\u007f]/g, " ").trim().slice(0, limit);
}

export default {
  async fetch(request, env) {
    const cors = corsHeaders(request, env);
    if (request.method === "OPTIONS") {
      if (!cors) return text(403, "origin not allowed");
      return new Response(null, { status: 204, headers: cors });
    }
    if (request.method !== "POST") return text(405, "method not allowed", cors);
    if (!cors) return text(403, "origin not allowed");

    const raw = await request.text();
    if (raw.length > MAX_BODY) return text(413, "too large", cors);

    let body;
    try {
      body = JSON.parse(raw);
    } catch (_) {
      return text(400, "invalid json", cors);
    }
    if (!body || typeof body !== "object" || body.type !== "ads-experiment") {
      return text(400, "unexpected payload", cors);
    }
    const score = clean(body.score, 20).toLowerCase();
    if (!SCORES.includes(score)) return text(400, "unknown score", cors);

    const comment = clean(body.comment, MAX_COMMENT);
    const page = clean(body.page, 200) || "/";
    const views = Number(body.views);
    const viewsLabel = Number.isFinite(views) && views > 0 ? String(Math.trunc(views)) : "?";

    const webhook = env.FEEDBACK_WEBHOOK_URL;
    if (!webhook) return text(503, "feedback endpoint is not configured", cors);

    const lines = [
      "**Ads experiment feedback**",
      `Answer: \`${score}\``,
      `Page: \`${page}\` · page views in this browser: ${viewsLabel}`,
    ];
    if (comment) lines.push(`> ${comment.replace(/\n/g, "\n> ")}`);
    const payload = {
      content: lines.join("\n").slice(0, 1900),
      allowed_mentions: { parse: [] },
    };

    const upstream = await fetch(webhook, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!upstream.ok) return text(502, "webhook rejected the message", cors);
    return text(200, "ok", cors);
  },
};
