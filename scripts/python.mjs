import { createRequire } from "node:module";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
const require = createRequire(import.meta.url);
const { pythonPath } = require("../electron/backend.cjs");
const args = process.argv.slice(2);
const child = spawn(pythonPath(), args, {
  stdio: "inherit",
  windowsHide: true,
  env: {
    ...process.env,
    PYTHONPATH: fileURLToPath(new URL("../services", import.meta.url)),
  },
});
child.on("error", (error) => {
  console.error(error.message);
  process.exitCode = 1;
});
child.on("exit", (code) => {
  process.exitCode = code ?? 1;
});
