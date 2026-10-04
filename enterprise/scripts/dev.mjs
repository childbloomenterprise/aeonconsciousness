// Local preview: development identity only. Never publish this HTTP server.
import http from "node:http";
import { readFileSync } from "node:fs";
import { environment } from "../tests/harness.mjs";
import worker from "../dist/server/index.js";
const env = environment();
const server = http.createServer(async (req, res) => {
  try {
    const chunks = [];
    for await (const chunk of req) chunks.push(chunk);
    const headers = new Headers(req.headers);
    if (!headers.has("authorization")) {
      headers.set("oai-authenticated-user-id", "local-owner");
      headers.set("oai-authenticated-user-email", "local-owner@example.com");
    }
    const options = { method: req.method, headers };
    if (!["GET", "HEAD"].includes(req.method))
      options.body = Buffer.concat(chunks);
    const result = await worker.fetch(
      new Request(`http://127.0.0.1:8787${req.url}`, options),
      env,
      {},
    );
    res.writeHead(result.status, Object.fromEntries(result.headers));
    res.end(Buffer.from(await result.arrayBuffer()));
  } catch (e) {
    console.error(e.name, e.message);
    res.writeHead(500);
    res.end("Local preview error");
  }
});
server.listen(8787, "127.0.0.1", () =>
  console.log(
    "Local enterprise preview: http://127.0.0.1:8787 (development identity)",
  ),
);
