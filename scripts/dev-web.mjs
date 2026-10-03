import { createServer } from "vite";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { startBackend } = require("../electron/backend.cjs");
const backend = await startBackend({ port: 0 });
process.env.STUDYLENS_API_URL = backend.endpoint;
process.env.STUDYLENS_API_TOKEN = backend.token;
let server;
try {
  server = await createServer();
  await server.listen();
} catch (error) {
  await server?.close();
  await backend.stop();
  throw error;
}
server.printUrls();
let closing = false;
async function close() {
  if (closing) return;
  closing = true;
  await server.close();
  await backend.stop();
  process.exit();
}
process.on("SIGINT", close);
process.on("SIGTERM", close);
