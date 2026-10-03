import { test } from "node:test";
import assert from "node:assert/strict";
import { ImportManager } from "../src/storage/imports.ts";
import type { ImportResult } from "../src/storage/client.ts";
const scope = { workspaceId: "semester-3", subjectId: "probability" };
const result: ImportResult = {
  source_id: "source",
  version_id: "version",
  version: 1,
  duplicate: false,
};

test("file transfers retain captured scope and continue without a mounted Materials subscriber", async () => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  const calls: string[] = [];
  const manager = new ImportManager({
    async upload(context, file) {
      calls.push(context.workspaceId + "/" + file.name);
      await gate;
      return result;
    },
    cancelTicket() {},
  });
  const unsubscribe = manager.subscribe(() => {});
  const uploading = manager.start(
    scope,
    [
      { id: "first", name: "one.txt", size: 10 },
      { id: "second", name: "two.txt", size: 20 },
    ],
    async () => true,
  );
  await Promise.resolve();
  unsubscribe();
  release();
  await uploading;
  assert.deepEqual(calls, ["semester-3/one.txt", "semester-3/two.txt"]);
  assert.equal(manager.getSnapshot().message, "2 file version(s) saved.");
  assert.equal(manager.getSnapshot().busy, false);
});
test("cancel aborts the native ticket and stops the rest of a batch", async () => {
  let started!: () => void;
  const active = new Promise<void>((resolve) => {
    started = resolve;
  });
  const cancelled: string[] = [];
  const manager = new ImportManager({
    async upload(_context, _file, signal) {
      started();
      return new Promise<ImportResult>((_resolve, reject) => {
        signal.addEventListener("abort", () => reject(new Error("aborted")), {
          once: true,
        });
      });
    },
    cancelTicket(id) {
      cancelled.push(id);
    },
  });
  const uploading = manager.start(
    scope,
    [
      { id: "ticket", name: "one.txt", size: 10 },
      { id: "unused", name: "two.txt", size: 10 },
    ],
    async () => true,
  );
  await active;
  manager.cancel();
  await uploading;
  assert.deepEqual(cancelled, ["ticket"]);
  assert.equal(manager.getSnapshot().busy, false);
  assert.match(manager.getSnapshot().message, /Import stopped/);
  assert.equal(manager.getSnapshot().error, "");
});
test("partial batch failure preserves earlier results and rejects parallel imports", async () => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let count = 0;
  const manager = new ImportManager({
    async upload() {
      await gate;
      if (++count === 2) throw new Error("disk full");
      return result;
    },
    cancelTicket() {},
  });
  const files = [
    { id: "first", name: "one.txt", size: 10 },
    { id: "second", name: "two.txt", size: 10 },
  ];
  const upload = manager.start(scope, files, async () => true);
  await assert.rejects(
    manager.start(scope, files, async () => true),
    /already running/,
  );
  release();
  await upload;
  assert.match(
    manager.getSnapshot().error,
    /disk full.*1 earlier file version/,
  );
  assert.equal(manager.getSnapshot().completed, 1);
});
