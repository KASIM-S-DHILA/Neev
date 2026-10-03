import type { FileTicket, ImportResult } from "./client.ts";
import { maxBytes } from "./files.ts";
export type ImportFile = File | FileTicket;
export type ImportScope = {
  workspaceId: string;
  subjectId: string;
  sourceId?: string;
};
export type ImportState = {
  busy: boolean;
  progress: string;
  message: string;
  error: string;
  scope: ImportScope | null;
  completed: number;
};
type Transport = {
  upload: (
    scope: ImportScope,
    file: ImportFile,
    signal: AbortSignal,
  ) => Promise<ImportResult>;
  cancelTicket: (ticketId: string) => void;
};
export class ImportManager {
  private state: ImportState = {
    busy: false,
    progress: "",
    message: "",
    error: "",
    scope: null,
    completed: 0,
  };
  private listeners = new Set<() => void>();
  private canceled = false;
  private controller: AbortController | null = null;
  private ticket: string | null = null;
  private transport: Transport;
  constructor(transport: Transport) {
    this.transport = transport;
  }
  getSnapshot = () => this.state;
  subscribe = (listener: () => void) => {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  };
  private update(next: Partial<ImportState>) {
    this.state = { ...this.state, ...next };
    this.listeners.forEach((listener) => listener());
  }
  dismiss = () => {
    if (!this.state.busy) this.update({ message: "", error: "" });
  };
  cancel = () => {
    this.canceled = true;
    this.controller?.abort();
    if (this.ticket) this.transport.cancelTicket(this.ticket);
  };
  async start(
    scope: ImportScope,
    files: ImportFile[],
    flush: () => Promise<boolean>,
  ) {
    if (this.state.busy)
      throw new Error("An import is already running. Wait or cancel it first.");
    if (!files.length) return;
    if (files.length > 32) throw new Error("Choose up to 32 files at a time.");
    this.canceled = false;
    this.update({
      busy: true,
      scope,
      progress: "Preparing import…",
      error: "",
      message: "",
    });
    let added = 0;
    let duplicates = 0;
    try {
      if (!(await flush()))
        throw new Error(
          "Save the workspace before adding material. Retry the local connection.",
        );
      for (const [index, file] of files.entries()) {
        if (this.canceled) break;
        if (file.size > maxBytes)
          throw new Error(`${file.name} exceeds the 2 GB file limit.`);
        this.update({
          progress: `Saving ${index + 1} of ${files.length}: ${file.name}`,
        });
        this.controller = new AbortController();
        this.ticket = "id" in file ? file.id : null;
        const result = await this.transport.upload(
          scope,
          file,
          this.controller.signal,
        );
        this.ticket = null;
        if (result.duplicate) duplicates++;
        else added++;
      }
      this.update({
        message: this.canceled
          ? `Import stopped. ${added} file version(s) saved.`
          : `${added} file version(s) saved.${duplicates ? ` ${duplicates} identical version(s) already saved.` : ""}`,
      });
    } catch (cause) {
      if (this.canceled)
        this.update({
          message: `Import stopped. ${added} file version(s) saved. A file that finished just before cancellation may also appear in Materials.`,
        });
      else
        this.update({
          error: `${cause instanceof Error ? cause.message : "Import failed."}${added ? ` ${added} earlier file version(s) were saved.` : ""}`,
        });
    } finally {
      this.controller = null;
      this.ticket = null;
      this.update({
        busy: false,
        progress: "",
        completed: this.state.completed + 1,
      });
    }
  }
}
