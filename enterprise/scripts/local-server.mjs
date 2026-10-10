// Loopback-only development identity bridge. Never publish this server.
import http from "node:http";
import { homedir } from "node:os";
import { join } from "node:path";
import { localEnvironment } from "./local-environment.mjs";

export function defaultLocalStateDir() {
  return join(
    process.env.LOCALAPPDATA || join(homedir(), ".local", "share"),
    "AEON",
    "localhost-private",
  );
}
function reject(res, status, error) {
  res.writeHead(status, {
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store",
    "x-content-type-options": "nosniff",
  });
  res.end(JSON.stringify({ error }));
}
export function createLocalServer(
  worker,
  { stateDir, ephemeral = false } = {},
) {
  const env = localEnvironment(
    ephemeral ? undefined : join(stateDir || defaultLocalStateDir(), "server"),
  );
  const server = http.createServer(async (req, res) => {
    try {
      const port = server.address().port,
        host = req.headers.host?.toLowerCase();
      if (![`127.0.0.1:${port}`, `localhost:${port}`].includes(host)) {
        req.resume();
        return reject(res, 403, "Loopback Host required.");
      }
      const origin = `http://${host}`;
      if (
        (req.headers.origin && req.headers.origin !== origin) ||
        req.headers["sec-fetch-site"] === "cross-site"
      ) {
        req.resume();
        return reject(res, 403, "Same-origin local request required.");
      }
      if (!req.url?.startsWith("/") || req.url.startsWith("//")) {
        req.resume();
        return reject(res, 400, "Invalid request target.");
      }
      const url = new URL(req.url, origin);
      if (url.origin !== origin) {
        req.resume();
        return reject(res, 400, "Invalid request target.");
      }
      const limit =
        /^\/api\/worker\/jobs\/[^/]+\/artifacts$/.test(url.pathname) &&
        req.method === "PUT"
          ? 8_000_000
          : 128_000;
      if (Number(req.headers["content-length"] || 0) > limit) {
        req.resume();
        return reject(res, 413, "Request too large.");
      }
      const chunks = [];
      let size = 0;
      for await (const chunk of req) {
        size += chunk.length;
        if (size > limit) {
          req.resume();
          return reject(res, 413, "Request too large.");
        }
        chunks.push(chunk);
      }
      const headers = new Headers();
      for (const [key, value] of Object.entries(req.headers)) {
        if (key.startsWith("oai-authenticated-user-") || value === undefined)
          continue;
        headers.set(key, Array.isArray(value) ? value.join(", ") : value);
      }
      if (!headers.has("authorization")) {
        headers.set("oai-authenticated-user-id", "local-owner");
        headers.set("oai-authenticated-user-email", "local-owner@example.com");
      }
      if (url.pathname === "/api/local/runtime" && req.method === "GET") {
        res.writeHead(200, {
          "content-type": "application/json",
          "cache-control": "no-store",
          "x-content-type-options": "nosniff",
        });
        res.end(JSON.stringify({ mode: "local", persistence: !ephemeral }));
        return;
      }
      const options = { method: req.method, headers };
      if (!["GET", "HEAD"].includes(req.method))
        options.body = Buffer.concat(chunks, size);
      const result = await worker.fetch(new Request(url, options), env, {});
      res.writeHead(result.status, Object.fromEntries(result.headers));
      res.end(Buffer.from(await result.arrayBuffer()));
    } catch (error) {
      console.error("local_request_failed", error.name);
      if (!res.headersSent) reject(res, 500, "Local preview error.");
      else res.destroy();
    }
  });
  server.requestTimeout = 30_000;
  server.headersTimeout = 15_000;
  server.on("close", () => env.close());
  return { server, env };
}
