import { spawn } from "node:child_process";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const env = { ...process.env, STUDYLENS_SMOKE: "1" };
delete env.ELECTRON_RUN_AS_NODE;
delete env.STUDYLENS_DEV_URL;
delete env.STUDYLENS_DATA_DIR;
delete env.STUDYLENS_QUEUE_EVAL;
delete env.STUDYLENS_VISION_MODEL;
delete env.STUDYLENS_OCR_LANG;
delete env.GROQ_API_KEY;
const child = spawn(require("electron"), ["."], { stdio: "inherit", env });
child.on("error", (error) => {
  console.error(error);
  process.exitCode = 1;
});
child.on("exit", (code) => {
  process.exitCode = code ?? 1;
});
