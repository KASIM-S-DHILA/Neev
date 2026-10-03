import { test } from "node:test";
import assert from "node:assert/strict";
import {
  addTab,
  closeTab,
  initialSession,
  MAX_TABS,
  navigate,
  restoreSession,
} from "../src/model.ts";

test("new tab opens Workspace and retains the previous study context and draft", () => {
  let session = navigate(initialSession(), "ask", "probability", "conditional");
  session.tabs[0].draft = "Why does the denominator change?";
  const old = structuredClone(session.tabs[0]);
  const next = addTab(session);
  assert.equal(next.tabs[1].view, "workspace");
  assert.equal(next.tabs[1].subjectId, undefined);
  assert.deepEqual(next.tabs[0], old);
  assert.equal(next.activeTabId, next.tabs[1].id);
});
test("closing the last tab keeps the application usable without removing subjects", () => {
  const session = initialSession();
  const next = closeTab(session, session.activeTabId);
  assert.equal(next.tabs.length, 1);
  assert.equal(next.tabs[0].view, "workspace");
  assert.notEqual(next.activeTabId, session.activeTabId);
  assert.deepEqual(next.subjects, session.subjects);
});
test("closing an inactive tab does not move focus", () => {
  const session = addTab(initialSession());
  assert.equal(
    closeTab(session, session.tabs[0].id).activeTabId,
    session.activeTabId,
  );
});
test("switching subject clears the active draft but never touches another tab", () => {
  const session = addTab(
    navigate(initialSession(), "ask", "probability", "conditional"),
  );
  session.tabs[0].draft = "Saved in probability";
  session.tabs[1].draft = "A different context";
  const next = navigate(session, "ask", "linear-algebra", "vectors");
  assert.equal(next.tabs[0].draft, "Saved in probability");
  assert.equal(next.tabs[1].draft, "");
});
test("valid session round-trips with local subjects, drafts, and reading completion", () => {
  const session = navigate(
    initialSession(),
    "ask",
    "probability",
    "conditional",
  );
  session.tabs[0].draft = "मेरे लिए समझाइए";
  session.subjects[0].topics[1].read = true;
  assert.deepEqual(restoreSession(JSON.stringify(session)), session);
});
test("corrupted or dangling session references fail safely", () => {
  assert.equal(restoreSession("{broken"), null);
  const session = initialSession();
  session.activeTabId = "missing-tab";
  assert.equal(restoreSession(JSON.stringify(session)), null);
  const invalid = navigate(
    initialSession(),
    "learn",
    "probability",
    "missing-topic",
  );
  assert.equal(restoreSession(JSON.stringify(invalid)), null);
  const duplicate = initialSession();
  duplicate.subjects.push(duplicate.subjects[0]);
  assert.equal(restoreSession(JSON.stringify(duplicate)), null);
});
test("tab cap prevents unbounded growth", () => {
  let session = initialSession();
  for (let i = 0; i < MAX_TABS; i++) session = addTab(session);
  assert.equal(session.tabs.length, MAX_TABS);
  assert.equal(addTab(session), session);
});
