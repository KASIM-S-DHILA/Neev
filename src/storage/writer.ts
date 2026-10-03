import type { Session } from "../model.ts";
import { ApiError } from "./client.ts";

export type SaveStatus = "saved" | "saving" | "offline" | "conflict";
export class SessionWriter {
  revision: number;
  private pending: Session | null = null;
  private inFlight: Promise<void> | null = null;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private disposed = false;
  private blocked = false;
  private readonly save: (
    session: Session,
    revision: number,
  ) => Promise<{ revision: number }>;
  private readonly notify: (
    status: SaveStatus,
    revision: number,
    error?: string,
  ) => void;
  constructor(
    revision: number,
    save: (session: Session, revision: number) => Promise<{ revision: number }>,
    notify: (status: SaveStatus, revision: number, error?: string) => void,
  ) {
    this.revision = revision;
    this.save = save;
    this.notify = notify;
  }
  queue(session: Session) {
    this.pending = session;
    if (this.blocked || this.disposed) return;
    this.notify("saving", this.revision);
    if (this.timer) clearTimeout(this.timer);
    this.timer = setTimeout(() => {
      void this.flush();
    }, 350);
  }
  async flush(): Promise<boolean> {
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    if (this.blocked || this.disposed) return false;
    if (this.inFlight) {
      await this.inFlight;
      return !this.blocked;
    }
    this.inFlight = (async () => {
      while (this.pending && !this.disposed && !this.blocked) {
        const snapshot = this.pending;
        this.pending = null;
        try {
          const saved = await this.save(snapshot, this.revision);
          this.revision = saved.revision;
          if (!this.disposed)
            this.notify(this.pending ? "saving" : "saved", this.revision);
        } catch (error) {
          this.pending ??= snapshot;
          this.blocked = true;
          if (!this.disposed)
            this.notify(
              error instanceof ApiError && error.status === 409
                ? "conflict"
                : "offline",
              this.revision,
              error instanceof Error
                ? error.message
                : "The workspace could not be saved.",
            );
        }
      }
    })();
    await this.inFlight;
    this.inFlight = null;
    return !this.blocked;
  }
  async retry() {
    this.blocked = false;
    return this.flush();
  }
  dispose() {
    this.disposed = true;
    if (this.timer) clearTimeout(this.timer);
  }
}
