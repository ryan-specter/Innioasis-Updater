/*
 * Optional same-origin download proxy for firmware.html.
 *
 * GitHub release assets cannot be renamed by the browser: they are served from
 * release-assets.githubusercontent.com without CORS headers, and the HTML
 * `download` attribute is ignored cross-origin. This Worker streams an allowed
 * GitHub release asset with a Content-Disposition filename, so the site can
 * save a portable package under the original firmware name (for example
 * rom.zip).
 *
 * Deploy with Wrangler and set:
 *   ALLOWED_REPOS   comma-separated, e.g. "you/y1-stock-rom-portable"
 *   ALLOWED_ORIGINS comma-separated, e.g. "https://innioasis.app"
 *
 * Request:
 *   GET /?url=<github release asset url>&filename=rom.zip
 *
 * Usage from the page:
 *   PortablePackages.download(asset.url, "rom.zip", {
 *     proxyUrl: "https://dl.innioasis.app/"
 *   });
 */

const MAX_FILENAME = 180;

function parseList(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function corsHeaders(request, env) {
  const allowed = parseList(env.ALLOWED_ORIGINS);
  const origin = request.headers.get("Origin") || "";
  if (!allowed.length) {
    return { "Access-Control-Allow-Origin": "*", Vary: "Origin" };
  }
  // A plain anchor download is a navigation and carries no Origin.  It needs
  // no CORS headers, so let it through; only cross-origin fetch is checked.
  if (!origin) return {};
  if (!allowed.includes(origin)) return null;
  return {
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
    "Access-Control-Allow-Headers": "Range",
    "Access-Control-Expose-Headers": "Content-Disposition, Content-Length",
    Vary: "Origin",
  };
}

function safeFilename(name) {
  const base = String(name || "")
    .split(/[\\/]/)
    .pop();
  const cleaned = base
    .replace(/[^A-Za-z0-9._ +()-]/g, "_")
    .replace(/^\.+/, "")
    .trim();
  return (cleaned || "firmware.zip").slice(0, MAX_FILENAME);
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

export default {
  async fetch(request, env) {
    const cors = corsHeaders(request, env);
    if (request.method === "OPTIONS") {
      if (!cors) return text(403, "origin not allowed");
      return new Response(null, { status: 204, headers: cors });
    }
    if (request.method !== "GET" && request.method !== "HEAD") {
      return text(405, "method not allowed", cors);
    }
    if (!cors) return text(403, "origin not allowed");

    const requestUrl = new URL(request.url);
    const targetParam = requestUrl.searchParams.get("url");
    if (!targetParam) return text(400, "missing url", cors);

    let target;
    try {
      target = new URL(targetParam);
    } catch (_) {
      return text(400, "invalid url", cors);
    }
    if (target.protocol !== "https:" || target.hostname !== "github.com") {
      return text(403, "only https://github.com assets are allowed", cors);
    }

    const parts = target.pathname.split("/").filter(Boolean);
    if (parts.length < 6 || parts[2] !== "releases" || parts[3] !== "download") {
      return text(403, "only release assets are allowed", cors);
    }
    const repo = (parts[0] + "/" + parts[1]).toLowerCase();
    const allowedRepos = parseList(env.ALLOWED_REPOS).map((item) => item.toLowerCase());
    if (allowedRepos.length && !allowedRepos.includes(repo)) {
      return text(403, "repository not allowed", cors);
    }

    const filename = safeFilename(
      requestUrl.searchParams.get("filename") || parts[parts.length - 1]
    );

    const upstream = await fetch(target.toString(), {
      method: "GET",
      redirect: "follow",
      headers: { Accept: "application/octet-stream" },
    });
    if (!upstream.ok || !upstream.body) {
      return text(upstream.status || 502, "upstream error", cors);
    }

    const headers = new Headers(cors);
    headers.set("Content-Type", "application/octet-stream");
    headers.set(
      "Content-Disposition",
      'attachment; filename="' + filename.replace(/["\\]/g, "_") + '"'
    );
    headers.set("Cache-Control", "no-store");
    const length = upstream.headers.get("Content-Length");
    if (length) headers.set("Content-Length", length);

    if (request.method === "HEAD") {
      return new Response(null, { status: 200, headers });
    }
    return new Response(upstream.body, { status: 200, headers });
  },
};
