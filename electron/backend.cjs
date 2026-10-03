const fs = require("node:fs");
const path = require("node:path");
const os = require("node:os");
const crypto = require("node:crypto");
const readline = require("node:readline");
const { spawn } = require("node:child_process");

const projectRoot = path.resolve(__dirname, "..");

function pythonPath() {
  if (process.env.STUDYLENS_PYTHON) return process.env.STUDYLENS_PYTHON;
  const candidate = path.join(
    projectRoot,
    ".venv",
    process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
  );
  if (!fs.existsSync(candidate))
    throw new Error(
      "Create the project Python environment first. See README: Local service setup.",
    );
  return candidate;
}

function defaultDataRoot() {
  if (process.env.STUDYLENS_DATA_DIR)
    return path.resolve(process.env.STUDYLENS_DATA_DIR);
  const base =
    process.platform === "win32"
      ? process.env.APPDATA || path.join(os.homedir(), "AppData/Roaming")
      : process.platform === "darwin"
        ? path.join(os.homedir(), "Library/Application Support")
        : process.env.XDG_CONFIG_HOME || path.join(os.homedir(), ".config");
  return path.join(base, "StudyLens", "data");
}

async function startBackend({ dataRoot = defaultDataRoot(), port = 0 } = {}) {
  const token = crypto.randomBytes(32).toString("hex");
  const env = {
    ...process.env,
    STUDYLENS_API_TOKEN: token,
    PYTHONPATH: path.join(projectRoot, "services"),
    PYTHONUNBUFFERED: "1",
    STUDYLENS_PARENT_PIPE: "1",
  };
  const child = spawn(
    pythonPath(),
    ["-m", "studylens_service", "--data-dir", dataRoot, "--port", String(port)],
    {
      cwd: projectRoot,
      env,
      windowsHide: true,
      stdio: ["pipe", "pipe", "pipe"],
    },
  );
  let endpoint;
  let exited = false;
  const lines = readline.createInterface({ input: child.stdout });
  child.stderr.on("data", (data) => process.stderr.write(data));
  const ready = new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      child.kill();
      reject(new Error("Local service startup timed out."));
    }, 20000);
    child.once("error", (error) => {
      clearTimeout(timeout);
      reject(error);
    });
    child.once("exit", () => {
      exited = true;
      clearTimeout(timeout);
      reject(new Error("The local service stopped during startup."));
    });
    lines.on("line", (line) => {
      try {
        const message = JSON.parse(line);
        if (
          message.event === "ready" &&
          Number.isInteger(message.port) &&
          message.port > 0 &&
          message.port <= 65535
        ) {
          endpoint = "http://127.0.0.1:" + message.port;
          clearTimeout(timeout);
          resolve();
        }
      } catch {
        /* Ignore non-protocol output. Never print environment credentials. */
      }
    });
  });
  await ready;
  async function response(route, options = {}) {
    if (exited)
      throw new Error(
        "The local service is unavailable. Reopen the application.",
      );
    return fetch(endpoint + route, {
      ...options,
      headers: { ...options.headers, Authorization: "Bearer " + token },
    });
  }
  async function request(route, options = {}) {
    const result = await response(route, {
      signal: AbortSignal.timeout(15000),
      ...options,
    });
    const body = await result.json();
    if (!result.ok) {
      const error = new Error(
        typeof body.detail === "string"
          ? body.detail
          : "The workspace data is invalid.",
      );
      error.status = result.status;
      throw error;
    }
    return body;
  }
  for (let attempt = 0; ; attempt++) {
    try {
      await request("/health");
      break;
    } catch (error) {
      if (attempt >= 20 || exited) {
        child.kill();
        throw error;
      }
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
  }
  return {
    endpoint,
    token,
    request,
    response,
    get isRunning() {
      return !exited;
    },
    async stop() {
      if (exited) return;
      const stopped = new Promise((resolve) => child.once("exit", resolve));
      try {
        await request("/shutdown", {
          method: "POST",
          signal: AbortSignal.timeout(2000),
        });
      } catch {
        /* Bounded shutdown below. */
      }
      child.stdin.end();
      await Promise.race([
        stopped,
        new Promise((resolve) => setTimeout(resolve, 2500)),
      ]);
      if (!exited) child.kill();
      lines.close();
    },
  };
}

module.exports = { startBackend, defaultDataRoot, pythonPath };
