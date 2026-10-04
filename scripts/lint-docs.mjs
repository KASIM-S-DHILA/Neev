/**
 * Documentation lint, wired into `npm run check`.
 *
 * Four rules, all cheap and all aimed at defects that have actually happened in
 * this repository:
 *
 *   A. Section numbers: within one document, `## N.` headings must ascend from 1
 *      with no duplicates and no gaps. Catches a section dropped or renumbered
 *      during an edit.
 *   B. Links: every relative markdown link must resolve to a real path.
 *   C. Empty sections: a heading followed by nothing but blanks (before the next
 *      heading) means a section lost its body.
 *   D. Truncation: the last non-blank line must end with terminal punctuation or
 *      close a fence. Catches a document cut off mid-sentence, which is how this
 *      repository's own M1 design doc lost its section tails.
 *
 * Deliberately no dependencies: this runs in `npm run check` on every
 * contribution, so it must not itself be a supply-chain event.
 */
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, dirname, resolve, relative } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(fileURLToPath(new URL("..", import.meta.url)));

/** Directories never linted: vendored, generated, or third-party trees. */
const SKIP_DIRS = new Set([
  "node_modules",
  ".git",
  ".venv",
  "dist",
  "tmp",
  ".npm-cache",
  ".electron-cache",
  "models",
  "__pycache__",
]);

const FENCE = /^(```|~~~)/;

function walk(dir, found = []) {
  for (const entry of readdirSync(dir)) {
    if (SKIP_DIRS.has(entry)) continue;
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) walk(full, found);
    else if (entry.endsWith(".md")) found.push(full);
  }
  return found;
}

/**
 * Blank out the *contents* of fenced code blocks so they are not linted as
 * prose, but keep the fence lines themselves. That distinction matters twice: a
 * section whose whole body is a code block is not empty, and a regex inside a
 * code block is not a broken markdown link.
 */
function stripFences(lines) {
  const out = [];
  let inFence = false;
  for (const line of lines) {
    if (FENCE.test(line.trim())) {
      inFence = !inFence;
      out.push(line);
      continue;
    }
    out.push(inFence ? null : line);
  }
  return { prose: out, fenceOpen: inFence };
}

const HEADING = /^#{1,6}\s+\S/;
/** Rule C applies from `##` down: an H1 is the document title and may be
 * followed immediately by its first section. */
const SECTION = /^#{2,6}\s+\S/;

function checkSections(prose, report) {
  const numbered = [];
  for (let i = 0; i < prose.length; i++) {
    if (prose[i] === null) continue;
    const match = /^##\s+(\d+)\.\s+\S/.exec(prose[i]);
    if (match) numbered.push({ number: Number(match[1]), line: i + 1 });
  }
  if (numbered.length === 0) return;
  const seen = new Map();
  for (const item of numbered) {
    if (seen.has(item.number))
      report.push(`A  duplicate section ${item.number} (lines ${seen.get(item.number)} and ${item.line})`);
    else seen.set(item.number, item.line);
  }
  for (let expected = 1; expected <= numbered.length; expected++)
    if (!seen.has(expected))
      report.push(`A  missing section ${expected}; sequence is ${numbered.map((n) => n.number).join(",")}`);
  for (let i = 1; i < numbered.length; i++)
    if (numbered[i].number < numbered[i - 1].number)
      report.push(`A  out of order: ${numbered[i - 1].number} then ${numbered[i].number} (line ${numbered[i].line})`);
  if (numbered[0].number !== 1)
    report.push(`A  first numbered section is ${numbered[0].number}, expected 1 (line ${numbered[0].line})`);
}


/**
 * A heading is empty only if nothing follows it before the next heading —
 * including no fenced code block. A section whose whole body is a code block is
 * normal, not a defect.
 */
function checkEmptySections(prose, report) {
  for (let i = 0; i < prose.length; i++) {
    if (prose[i] === null || !SECTION.test(prose[i])) continue;
    let body = 0;
    for (let j = i + 1; j < prose.length; j++) {
      if (prose[j] === null) continue;
      if (SECTION.test(prose[j])) break;
      if (prose[j].trim() !== "") body++;
    }
    if (body === 0) report.push(`C  empty section "${prose[i].trim()}" (line ${i + 1})`);
  }
}

/**
 * Check links in prose only (fenced content already blanked to null).
 *
 * Absolute paths are skipped deliberately: docs/audit/CURRENT_ARCHITECTURE.md
 * records the baseline layout as absolute `C:/Users/.../Study/...` paths on
 * purpose, as evidence of where things were at baseline 4deb661. Those are not
 * repository links and must not be "fixed" into something else.
 */
function checkLinks(prose, file, report) {
  const pattern = /\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)/g;
  const text = prose.map((line) => (line === null ? "" : line)).join("\n");
  for (const match of text.matchAll(pattern)) {
    const target = match[1];
    if (/^(https?:|mailto:|#|data:)/i.test(target)) continue;
    if (/^[a-z]:[\\/]/i.test(target)) continue; // absolute machine path
    if (target.startsWith("//")) continue;
    const [pathPart] = target.split("#");
    if (!pathPart) continue;
    const line = text.slice(0, match.index).split("\n").length;
    try {
      statSync(resolve(dirname(file), decodeURIComponent(pathPart)));
    } catch {
      report.push(`B  broken link -> ${target} (line ${line})`);
    }
  }
}

function checkTruncation(lines, report) {
  let last = -1;
  for (let i = lines.length - 1; i >= 0; i--) {
    if (lines[i].trim() !== "") {
      last = i;
      break;
    }
  }
  if (last < 0) {
    report.push("D  file is empty");
    return;
  }
  const tail = lines[last].trimEnd();
  if (FENCE.test(tail)) return;
  if (/[.!?:;)\]}>`*_~|]$/.test(tail)) return;
  report.push(`D  ends mid-sentence: "${tail.slice(-60)}" (line ${last + 1})`);
}

/**
 * A paragraph whose last line ends without terminal punctuation and which is
 * followed by a blank line is almost certainly truncated mid-sentence.
 *
 * This is rule D applied to the middle of a file. It is included because the
 * exact defect it catches really occurred: docs/ARCHITECTURE.md and
 * docs/archive/ingestion-pilots/phase-01.md both had a paragraph cut off after a
 * blank line, and neither was the last line of the file, so rule D missed both.
 *
 * Narrow on purpose: list items, table rows, blockquotes, headings and fenced
 * lines are all skipped, because they legitimately end without a full stop.
 */
function checkTruncatedParagraphs(prose, report) {
  for (let i = 0; i < prose.length; i++) {
    const line = prose[i];
    if (line === null) continue;
    const text = line.trim();
    if (text === "") continue;
    if (/^(#{1,6}\s|[-*+]\s|\d+\.\s|>|\||```|~~~|---+\s*$|\*\*\*\s*$)/.test(text)) continue;
    // Bold-key lines such as "**Status:** Accepted" are a single logical line
    // and routinely end without a full stop; they are not prose.
    if (/^\*\*[^*]+:\*\*/.test(text)) continue;
    if (/[.!?:;)\]}>`*_~|:"']$/.test(text)) continue;
    // Only a paragraph's LAST line is a candidate: the very next line must be
    // blank, or the file must end here. A wrapped continuation line is followed
    // immediately by more text, and must not be flagged.
    const next = prose[i + 1];
    const nextIsBlank = next === undefined || (next !== null && next.trim() === "");
    if (!nextIsBlank) continue; // more of the same paragraph follows
    report.push(`E  paragraph ends mid-sentence: "${text.slice(-60)}" (line ${i + 1})`);
  }
}

const files = walk(ROOT).sort();
const findings = [];
const failing = [];

for (const file of files) {
  const name = relative(ROOT, file).replace(/\\/g, "/");
  const text = readFileSync(file, "utf8");
  const lines = text.split("\n");
  const { prose, fenceOpen } = stripFences(lines);
  const report = [];
  if (fenceOpen) report.push("D  unclosed code fence");
  checkSections(prose, report);
  checkEmptySections(prose, report);
  checkLinks(prose, file, report);
  checkTruncatedParagraphs(prose, report);
  checkTruncation(lines, report);
  if (report.length) failing.push(name);
  for (const problem of report) findings.push(`  ${name}: ${problem}`);
}

if (findings.length === 0) {
  console.log(`docs:lint OK - ${files.length} markdown files checked, no findings`);
  process.exit(0);
}

console.error(`docs:lint FAILED - ${failing.length} file(s), ${findings.length} finding(s)`);
for (const line of findings) console.error(line);
process.exit(1);