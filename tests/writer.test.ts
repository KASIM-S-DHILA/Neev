import { test } from "node:test";
import assert from "node:assert/strict";
import { initialSession } from "../src/model.ts";
import { SessionWriter } from "../src/storage/writer.ts";
import { ApiError } from "../src/storage/client.ts";

test("session writes are serialized with current revisions and coalesce queued edits", async () => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  const calls: { revision: number; draft: string }[] = [];
  const writer = new SessionWriter(
    4,
    async (session, revision) => {
      calls.push({ revision, draft: session.tabs[0].draft });
      if (calls.length === 1) await gate;
      return { revision: revision + 1 };
    },
    () => {},
  );
  const first = initialSession();
  first.tabs[0].draft = "first";
  writer.queue(first);
  const saving = writer.flush();
  const middle = structuredClone(first);
  middle.tabs[0].draft = "middle";
  writer.queue(middle);
  const last = structuredClone(first);
  last.tabs[0].draft = "last";
  writer.queue(last);
  release();
  assert.equal(await saving, true);
  assert.deepEqual(calls, [
    { revision: 4, draft: "first" },
    { revision: 5, draft: "last" },
  ]);
  assert.equal(writer.revision, 6);
  writer.dispose();
});
test("failed save stops retries and preserves the latest edit for explicit retry", async () => {
  let fail = true;
  const drafts: string[] = [];
  const statuses: string[] = [];
  const writer = new SessionWriter(
    0,
    async (session, revision) => {
      drafts.push(session.tabs[0].draft);
      if (fail) throw new Error("disk unavailable");
      return { revision: revision + 1 };
    },
    (status) => statuses.push(status),
  );
  const session = initialSession();
  session.tabs[0].draft = "old";
  writer.queue(session);
  assert.equal(await writer.flush(), false);
  const next = structuredClone(session);
  next.tabs[0].draft = "latest";
  writer.queue(next);
  assert.equal(await writer.flush(), false);
  assert.deepEqual(drafts, ["old"]);
  fail = false;
  assert.equal(await writer.retry(), true);
  assert.deepEqual(drafts, ["old", "latest"]);
  assert.ok(statuses.includes("offline"));
  assert.equal(statuses.at(-1), "saved");
  writer.dispose();
});
test("revision conflict is reported and disposed writers stop queued saves", async () => {
  let status = "";
  let calls = 0;
  const writer = new SessionWriter(
    1,
    async () => {
      calls++;
      throw new ApiError("changed elsewhere", 409);
    },
    (state) => {
      status = state;
    },
  );
  writer.queue(initialSession());
  assert.equal(await writer.flush(), false);
  assert.equal(status, "conflict");
  writer.dispose();
  assert.equal(await writer.retry(), false);
  assert.equal(calls, 1);
});
