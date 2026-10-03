import { test } from "node:test";
import assert from "node:assert/strict";
import {
  acknowledgedValue,
  CLOUD_DISCLOSURE,
  cloudEnabled,
  DISCLOSURE_KEY,
  shouldShowDisclosure,
} from "../src/disclosure.ts";

test("cloud processing is reported as off unless a provider is configured", () => {
  // Unconfigured is the common case: nothing may leave the machine.
  assert.equal(cloudEnabled(null, null), false);
  assert.equal(cloudEnabled({ cloud_enabled: false }, { configured: false }), false);
  assert.equal(cloudEnabled({ cloud_enabled: true }, null), true);
  // /vision reports `configured`, not `cloud_enabled`; both must work.
  assert.equal(cloudEnabled(null, { configured: true }), true);
});

test("the disclosure names audio and selected images or frames", () => {
  // The notice is the whole point: it must actually say what is sent.
  assert.match(CLOUD_DISCLOSURE, /speech/i);
  assert.match(CLOUD_DISCLOSURE, /frames?/i);
  assert.match(CLOUD_DISCLOSURE, /images?/i);
  assert.match(CLOUD_DISCLOSURE, /stay on this device/i);
});

test("the disclosure is shown once and stays acknowledged", () => {
  assert.equal(shouldShowDisclosure(null), true, "first run must show it");
  assert.equal(shouldShowDisclosure(""), true, "absent value must show it");
  assert.equal(shouldShowDisclosure(acknowledgedValue()), false);
  assert.equal(shouldShowDisclosure(DISCLOSURE_KEY), false);
});

test("changing the key re-notifies rather than hiding a new wording", () => {
  // Versioned key: if the wording changes, DISCLOSURE_KEY changes, and an old
  // acknowledgement must not suppress the new notice.
  assert.equal(acknowledgedValue(), DISCLOSURE_KEY);
  assert.equal(
    shouldShowDisclosure("studylens.cloud-disclosure.v0"),
    true,
    "an acknowledgement from an older key must not suppress the notice",
  );
});