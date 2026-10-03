import { test } from "node:test";
import assert from "node:assert/strict";
import { describeStorage, type HealthStatus } from "../src/storage/client.ts";

function health(overrides: Partial<HealthStatus> = {}): HealthStatus {
  return {
    ok: true,
    database: "sqlite",
    journal_mode: "wal",
    schema_version: "0005_youtube_media_links",
    ...overrides,
  };
}

test("storage mode is derived from the service journal_mode, never hardcoded", () => {
  assert.equal(describeStorage(health()), "SQLite · WAL enabled");
  // A non-WAL journal must be reported, not hidden behind a hardcoded claim.
  assert.equal(
    describeStorage(health({ journal_mode: "delete" })),
    "SQLite · WAL off (delete)",
  );
  assert.match(describeStorage(health({ journal_mode: "truncate" })), /WAL off \(truncate\)/);
});

test("storage mode does not assert WAL before the health endpoint answers", () => {
  assert.match(describeStorage(null), /Checking/);
  assert.doesNotMatch(describeStorage(null), /WAL enabled/);
});

test("storage mode follows the service when the database is not sqlite", () => {
  assert.equal(
    describeStorage(health({ database: "postgresql", journal_mode: "wal" })),
    "SQLite · WAL enabled",
  );
});