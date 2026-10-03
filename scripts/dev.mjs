import { createServer } from "vite";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const server = await createServer({ server: { strictPort: false } });
try {
  await server.listen();
} catch (error) {
  await server.close();
  throw error;
}
const address = server.httpServer?.address();
if (!address || typeof address === "string") {
  await server.close();
  throw new Error("The desktop development server did not open a local port.");
}
const desktopUrl = `http://127.0.0.1:${address.port}`;
if (address.port !== 5173)
  console.log(`Port 5173 is occupied. Starting Neev desktop on ${desktopUrl}`);
server.printUrls();
const desktopEnv = {
  ...process.env,
  STUDYLENS_DEV_URL: desktopUrl,
};
delete desktopEnv.ELECTRON_RUN_AS_NODE;
const child = spawn(require("electron"), ["."], {
  stdio: ["inherit", "inherit", "inherit", "ipc"],
  windowsHide: true,
  env: desktopEnv,
});
let closing = false;
async function close(code = 0) {
  if (closing) return;
  closing = true;
  if (child.exitCode === null && child.connected) {
    const exited = new Promise((resolve) => child.once("exit", resolve));
    child.send({ action: "quit" });
    await Promise.race([
      exited,
      new Promise((resolve) => setTimeout(resolve, 25000)),
    ]);
    if (child.exitCode === null) child.kill();
  }
  await server.close();
  process.exit(code);
}
child.on("error", (error) => {
  console.error(error);
  close(1);
});
child.on("exit", (code) => close(code ?? 0));
process.on("SIGINT", () => close());
process.on("SIGTERM", () => close());
