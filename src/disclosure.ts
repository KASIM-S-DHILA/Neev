/**
 * One-time cloud disclosure.
 *
 * Kept in its own module with no React and no storage access at import time so
 * the wording and the show-once rule are unit-testable. See
 * docs/PRIVACY_AND_DATA_FLOW.md and docs/DECISIONS.md D8/D8a.
 */

/** localStorage key. Versioned so the wording can change and re-notify. */
export const DISCLOSURE_KEY = "studylens.cloud-disclosure.v1";

/** Factual, one-time notice. No per-upload consent is collected or implied. */
export const CLOUD_DISCLOSURE =
  "When a cloud speech or vision provider is configured, detected speech intervals and selected images or video frames are sent to it automatically. Original files stay on this device. Turn it off with the STUDYLENS_AUTO_* settings before launching.";

/**
 * True when any cloud transfer is configured, so something may leave the machine.
 *
 * Accepts both shapes the service returns: /audio reports `cloud_enabled`,
 * /vision reports `configured`. Both mean the same thing, so normalise here
 * rather than at each call site.
 */
export function cloudEnabled(
  audio?: { cloud_enabled?: boolean } | null,
  vision?: { configured?: boolean } | null,
): boolean {
  return Boolean(audio?.cloud_enabled || vision?.configured);
}

/**
 * Whether the first-run disclosure should still be shown.
 *
 * Shown once per versioned key. Returns true when `acknowledge` is null.
 */
export function shouldShowDisclosure(acknowledge: string | null): boolean {
  return acknowledge !== DISCLOSURE_KEY;
}

/** The value to persist when the student acknowledges the notice. */
export function acknowledgedValue(): string {
  return DISCLOSURE_KEY;
}