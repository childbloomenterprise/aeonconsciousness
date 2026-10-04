import { api } from "./api.js";
import { html, js } from "../generated/page.js";
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    let response;
    if (url.pathname.startsWith("/api/"))
      response = await api.fetch(
        new Request(
          new URL(url.pathname.slice(4) + url.search, url.origin),
          request,
        ),
        env,
        ctx,
      );
    else if (url.pathname === "/app.js")
      response = new Response(js, {
        headers: { "content-type": "text/javascript; charset=utf-8" },
      });
    else if (url.pathname === "/")
      response = new Response(html, {
        headers: { "content-type": "text/html; charset=utf-8" },
      });
    else response = new Response("Not found", { status: 404 });
    const headers = new Headers(response.headers);
    headers.set("cache-control", "no-store");
    headers.set("x-content-type-options", "nosniff");
    headers.set("referrer-policy", "same-origin");
    headers.set(
      "permissions-policy",
      "camera=(), microphone=(), geolocation=()",
    );
    if (!headers.has("content-security-policy"))
      headers.set(
        "content-security-policy",
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-src 'none'; object-src 'none'; base-uri 'none'; form-action 'self'",
      );
    return new Response(response.body, { status: response.status, headers });
  },
};
