import { test } from "node:test";
import assert from "node:assert/strict";
import { jobStatus } from "../src/jobStatus.ts";
import type { Job } from "../src/storage/client.ts";

function job(overrides: Partial<Job> = {}): Job {
  return {
    id: "job",
    workspace_id: "semester-3",
    subject_id: "probability",
    source_version_id: "version",
    kind: "extract_source",
    label: "Phase 06",
    state: "queued",
    stage: "Waiting for Groq audio quota",
    done: 0,
    total: 1,
    error: null,
    cancel_requested: false,
    attempts: 1,
    failures: 0,
    max_attempts: 3,
    recoveries: 0,
    created_at: 0,
    updated_at: 0,
    checkpoint: {},
    result: null,
    ...overrides,
  };
}

test("a deferred quota or pacing wait is visible, not a bare Waiting", () => {
  // worker.execute sets state=queued with the Deferred's stage. The student must
  // see why the job is not progressing, or it looks like a silent stall.
  assert.equal(
    jobStatus(job({ stage: "Pacing Groq audio requests" })),
    "Pacing Groq audio requests",
  );
  assert.equal(
    jobStatus(job({ stage: "Waiting for Groq audio quota" })),
    "Waiting for Groq audio quota",
  );
  assert.equal(jobStatus(job({ stage: "Waiting for Groq quota" })), "Waiting for Groq quota");
});

test("an unrecognised queued stage still degrades to Waiting", () => {
  // Unknown stages must not leak raw internal text into the UI.
  assert.equal(jobStatus(job({ stage: "Some internal detail" })), "Waiting");
});

test("a running job shows its stage rather than a wait label", () => {
  assert.equal(jobStatus(job({ state: "running", stage: "Transcribing audio locally 1 of 2" })), "Transcribing audio locally 1 of 2");
  assert.equal(jobStatus(job({ state: "running", cancel_requested: true })), "Stopping…");
});