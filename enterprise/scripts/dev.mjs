// Local preview only. Production entrypoint remains dist/server/index.js.
import worker from "../dist/server/index.js";
import { createLocalServer } from "./local-server.mjs";
const args = process.argv.slice(2);
let port = Number(process.env.AEON_LOCAL_PORT || 8787);
let stateDir = process.env.AEON_LOCAL_STATE_DIR;
let ephemeral = false;
for (let i = 0; i < args.length; i++) {
  if (args[i] === "--port") port = Number(args[++i]);
  else if (args[i] === "--state-dir") stateDir = args[++i];
  else if (args[i] === "--ephemeral") ephemeral = true;
  else throw new Error(`Unknown local preview option: ${args[i]}`);
}
if (!Number.isInteger(port) || port < 1 || port > 65535)
  throw new Error("Local port must be an integer from 1 to 65535.");
const { server } = createLocalServer(worker, { stateDir, ephemeral });
server.on("error", (error) => {
  console.error(
    error.code === "EADDRINUSE"
      ? `Local port ${port} already in use; reuse that preview or choose --port.`
      : `Local preview failed: ${error.code}`,
  );
  process.exitCode = 1;
});
server.listen(port, "127.0.0.1", () => {
  console.log(
    `Local enterprise preview: http://127.0.0.1:${port} (development identity; ${ephemeral ? "ephemeral" : "persistent"} storage)`,
  );
});
for (const signal of ["SIGINT", "SIGTERM"])
  process.on(signal, () => {
    server.close();
    server.closeIdleConnections();
  });
