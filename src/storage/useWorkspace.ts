import { useEffect, useRef, useState } from "react";
import {
  initialSession,
  restoreSession,
  SESSION_KEY,
  type Session,
} from "../model";
import { storageClient, type Workspace } from "./client";
import { SessionWriter, type SaveStatus } from "./writer";

const ACTIVE_KEY = "studylens.active-workspace.v1";
const cacheKey = (id: string) => "studylens.workspace-cache.v1." + id;
type Cache = { revision: number; dirty: boolean; session: Session };
function readCache(id: string): Cache | null {
  try {
    const value = JSON.parse(localStorage.getItem(cacheKey(id)) ?? "null");
    const session = restoreSession(JSON.stringify(value?.session));
    return session &&
      Number.isInteger(value.revision) &&
      value.revision >= 0 &&
      typeof value.dirty === "boolean"
      ? { ...value, session }
      : null;
  } catch {
    return null;
  }
}
function legacySession() {
  try {
    return (
      restoreSession(localStorage.getItem(SESSION_KEY)) ?? initialSession()
    );
  } catch {
    return initialSession();
  }
}
function preferredWorkspace() {
  try {
    return localStorage.getItem(ACTIVE_KEY) ?? "semester-3";
  } catch {
    return "semester-3";
  }
}
function cache(id: string, value: Cache) {
  localStorage.setItem(cacheKey(id), JSON.stringify(value));
  localStorage.setItem(ACTIVE_KEY, id);
}

export function useWorkspace() {
  const [session, setSession] = useState<Session>(
    () => readCache(preferredWorkspace())?.session ?? legacySession(),
  );
  const [workspace, setWorkspace] = useState<Workspace>({
    id: preferredWorkspace(),
    name: "Semester 3",
  });
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [status, setStatus] = useState<SaveStatus | "loading">("loading");
  const [error, setError] = useState("");
  const [hydrated, setHydrated] = useState(false);
  const writer = useRef<SessionWriter | null>(null);
  const latest = useRef(session);
  const revision = useRef(0);
  const generation = useRef(0);
  const lastQueued = useRef<Session | null>(null);
  latest.current = session;

  async function load(id = preferredWorkspace(), useSaved = false) {
    const current = ++generation.current;
    writer.current?.dispose();
    writer.current = null;
    setHydrated(false);
    setStatus("loading");
    setError("");
    try {
      const list = await storageClient.listWorkspaces();
      const selected = list.find((item) => item.id === id) ?? list[0];
      if (!selected) throw new Error("No workspace was found.");
      const record = await storageClient.loadSession(selected.id);
      if (generation.current !== current) return;
      const saved =
        record.session && restoreSession(JSON.stringify(record.session));
      if (record.session && !saved)
        throw new Error("The saved workspace could not be validated.");
      const previous = readCache(selected.id);
      let snapshot =
        saved ??
        (selected.id === "semester-3"
          ? legacySession()
          : { ...initialSession(), subjects: [] });
      let conflict = false;
      if (previous?.dirty && !useSaved) {
        if (JSON.stringify(previous.session) === JSON.stringify(saved)) {
          snapshot = previous.session;
        } else {
          snapshot = previous.session;
          conflict = previous.revision !== record.revision;
        }
      }
      if (useSaved && previous?.dirty)
        localStorage.setItem(
          cacheKey(selected.id) + ".recovery",
          JSON.stringify(previous),
        );
      revision.current = record.revision;
      latest.current = snapshot;
      lastQueued.current = snapshot;
      setSession(snapshot);
      setWorkspace(selected);
      setWorkspaces(list);
      const instance = new SessionWriter(
        record.revision,
        (value, base) => storageClient.saveSession(selected.id, value, base),
        (state, nextRevision, message) => {
          if (generation.current !== current) return;
          revision.current = nextRevision;
          setStatus(state);
          setError(message ?? "");
          try {
            cache(selected.id, {
              revision: nextRevision,
              dirty: state !== "saved",
              session: latest.current,
            });
          } catch {
            setError(
              "The recovery cache could not be saved. Keep this window open until the database save succeeds.",
            );
          }
        },
      );
      writer.current = instance;
      setHydrated(true);
      setStatus(conflict ? "conflict" : "saved");
      if (conflict) {
        setError(
          "This workspace changed in another window. Your unsaved session is still cached on this device.",
        );
      } else if (
        !saved ||
        (previous?.dirty && JSON.stringify(snapshot) !== JSON.stringify(saved))
      ) {
        instance.queue(snapshot);
      } else {
        cache(selected.id, {
          revision: record.revision,
          dirty: false,
          session: snapshot,
        });
      }
    } catch (cause) {
      if (generation.current !== current) return;
      setStatus("offline");
      setError(
        cause instanceof Error
          ? cause.message
          : "The local service is unavailable.",
      );
      setHydrated(false);
    }
  }

  useEffect(() => {
    void load();
    return () => {
      generation.current++;
      writer.current?.dispose();
    };
  }, []);
  useEffect(() => {
    if (!hydrated || lastQueued.current === session) return;
    lastQueued.current = session;
    try {
      cache(workspace.id, { revision: revision.current, dirty: true, session });
    } catch {
      setError(
        "The recovery cache is unavailable. Keep this window open until the database save succeeds.",
      );
    }
    if (status !== "conflict") writer.current?.queue(session);
  }, [session, hydrated, workspace.id]);

  return {
    session,
    setSession,
    workspace,
    workspaces,
    status,
    error,
    ready: hydrated && status !== "conflict" && status !== "offline",
    async flush() {
      return writer.current ? writer.current.flush() : false;
    },
    async retry() {
      if (writer.current && hydrated && status !== "conflict")
        await writer.current.retry();
      else await load(workspace.id);
    },
    async switchWorkspace(id: string) {
      if (!hydrated || status === "conflict")
        throw new Error(
          "Resolve the workspace connection or save conflict before switching.",
        );
      if (writer.current && !(await writer.current.flush()))
        throw new Error(
          "Save the current workspace before switching. Your changes remain cached.",
        );
      await load(id);
    },
    async createWorkspace(name: string) {
      if (!hydrated || status === "conflict")
        throw new Error(
          "Resolve the workspace connection or save conflict first.",
        );
      if (writer.current && !(await writer.current.flush()))
        throw new Error("Save the current workspace before creating another.");
      const created = await storageClient.createWorkspace(name);
      await load(created.id);
    },
    loadSaved: () => load(workspace.id, true),
  };
}
