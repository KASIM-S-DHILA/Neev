/**
 * Emit the counts that appear in documentation, so no doc carries a
 * hand-written number.
 *
 * Every figure printed here is measured from the working tree at run time. If a
 * doc quotes one of these, quote this output, not a recollection.
 *
 * Usage: node scripts/report-counts.mjs
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(fileURLToPath(new URL("..", import.meta.url)));
const SKIP = new Set(["node_modules", ".git", ".venv", "dist", "tmp", "models", "__pycache__", ".npm-cache", ".electron-cache"]);

function walk(dir, filter, found = []) {
  for (const entry of readdirSync(dir)) {
    if (SKIP.has(entry)) continue;
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) walk(full, filter, found);
    else if (filter(entry)) found.push(full);
  }
  return found;
}

function git(args) {
  return execFileSync("git", args, { cwd: ROOT, encoding: "utf8" });
}

const python = join(ROOT, ".venv/Scripts/python.exe");
const pythonExists = statSync(python, { throwIfNoEntry: false }) !== undefined;

import { execFileSync, spawnSync } from "node:child_process";

// --- Python test count --------------------------------------------------------
// unittest writes its summary to stderr, so both streams are needed.
let apiLine = "not run (no .venv)";
if (pythonExists) {
  const result = spawnSync(
    python,
    ["-m", "unittest", "discover", "-s", "services/tests", "-v"],
    {
      cwd: ROOT,
      encoding: "utf8",
      env: { ...process.env, PYTHONPATH: join(ROOT, "services") },
      timeout: 900000,
      maxBuffer: 64 * 1024 * 1024,
    },
  );
  const out = `${result.stdout ?? ""}${result.stderr ?? ""}`;
  const ran = /Ran (\d+) tests in ([\d.]+)s/.exec(out);
  const skipped = /skipped=(\d+)/.exec(out);
  const status = /^(OK|FAILED)/m.exec(out);
  if (ran) {
    const total = Number(ran[1]);
    const skip = skipped ? Number(skipped[1]) : 0;
    apiLine = `${total} collected, ${total - skip} pass, ${skip} skipped (${status ? status[1] : "?"})`;
  } else {
    apiLine = "could not parse";
  }
}

// --- JavaScript test count: count top-level test() calls per file. ------------
const jsFiles = walk(join(ROOT, "tests"), (e) => e.endsWith(".test.ts")).sort();
const jsCounts = jsFiles.map((f) => ({
  file: f.slice(ROOT.length + 1).replace(/\\/g, "/"),
  count: (readFileSync(f, "utf8").match(/^test\(/gm) ?? []).length,
}));
const jsTotal = jsCounts.reduce((sum, x) => sum + x.count, 0);

// --- Files and routes ---------------------------------------------------------
const tracked = git(["ls-files"]).split("\n").filter(Boolean);
const markdown = tracked.filter((p) => p.endsWith(".md")).length;

// --- Routes: instantiate the real app, exactly as the audit did. -------------
// A grep over api.py is not reliable: @app.api_route(..., methods=["GET","HEAD"])
// carries two method-path pairs in one decorator, and is easy to miss.
const routeProbe = `
import json, tempfile
from pathlib import Path
from studylens_service.api import create_app
with tempfile.TemporaryDirectory() as tmp:
    app = create_app(Path(tmp), "audit-token-placeholder-at-least-24", start_worker=False)
    rows = []
    for r in app.routes:
        methods = sorted(m for m in getattr(r, "methods", set()) if m not in ("HEAD", "OPTIONS"))
        all_methods = sorted(getattr(r, "methods", set()))
        rows.append({"path": r.path, "methods": all_methods, "api_methods": methods, "name": r.name})
    print(json.dumps(rows))
`;
let routes = { objects: 0, pairs: 0, apiPairs: 0 };
if (pythonExists) {
  try {
    const result = spawnSync(python, ["-c", routeProbe], {
      cwd: ROOT,
      encoding: "utf8",
      env: { ...process.env, PYTHONPATH: join(ROOT, "services") },
      timeout: 120000,
    });
    const rows = JSON.parse((result.stdout ?? "").trim().split("\n").pop());
    const docs = new Set(["/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"]);
    const real = rows.filter((r) => !docs.has(r.path));
    routes.objects = real.length;
    routes.pairs = real.reduce((n, r) => n + r.methods.length, 0);
    routes.apiPairs = real.reduce((n, r) => n + r.api_methods.length, 0);
  } catch (error) {
    routes.objects = -1;
  }
}

const lock = readFileSync(join(ROOT, "services/requirements-lock.txt"), "utf8")
  .split("\n").filter((l) => l.trim() !== "").length;

const fixtures = walk(join(ROOT, "tests/fixtures/ingestion"), () => true).length;

const migrations = readdirSync(join(ROOT, "services/migrations/versions"))
  .filter((f) => f.endsWith(".py") && f !== "__init__.py").length;

console.log(`tracked files (git ls-files)   : ${tracked.length}`);
console.log(`  of which markdown            : ${markdown}`);
console.log(`python lock entries            : ${lock}`);
console.log(`alembic migration revisions    : ${migrations}`);
console.log(`registered route objects        : ${routes.objects}`);
console.log(`  method-path pairs (incl HEAD)  : ${routes.pairs}`);
console.log(`  method-path pairs (excl HEAD)  : ${routes.apiPairs}`);
console.log(`ingestion fixture files        : ${fixtures}`);
console.log(`api:test                       : ${apiLine}`);
console.log(`check (JS tests)               : ${jsTotal} in ${jsCounts.length} files`);
for (const { file, count } of jsCounts) console.log(`    ${file.padEnd(28)} ${count}`);