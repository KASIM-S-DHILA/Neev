import { useEffect, useRef, useState } from "react";
import { storageClient, type Job, type QueueStatus } from "./client";
export function useJobs(workspaceId: string, ready: boolean) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [status, setStatus] = useState<QueueStatus | null>(null);
  const [error, setError] = useState("");
  const currentWorkspace = useRef(workspaceId);
  currentWorkspace.current = workspaceId;
  const refresh = useRef<() => Promise<void>>(async () => {});
  useEffect(() => {
    let disposed = false;
    let busy = false;
    let timer: ReturnType<typeof setTimeout>;
    setJobs([]);
    async function poll() {
      if (busy || disposed) return;
      clearTimeout(timer);
      busy = true;
      try {
        const [items, info] = await Promise.all([
          storageClient.listJobs(workspaceId),
          storageClient.queueStatus(),
        ]);
        if (!disposed) {
          setJobs(items);
          setStatus(info);
          setError(info.error ?? "");
        }
      } catch (cause) {
        if (!disposed)
          setError(
            cause instanceof Error
              ? cause.message
              : "Background work is unavailable.",
          );
      } finally {
        busy = false;
        if (!disposed) timer = setTimeout(() => void poll(), 1200);
      }
    }
    refresh.current = poll;
    if (ready) void poll();
    return () => {
      disposed = true;
      clearTimeout(timer);
    };
  }, [workspaceId, ready]);
  async function action(
    operation: "cancel" | "retry" | "verify" | "test",
    id = "",
  ) {
    try {
      const job =
        operation === "cancel"
          ? await storageClient.cancelJob(workspaceId, id)
          : operation === "retry"
            ? await storageClient.retryJob(workspaceId, id)
            : operation === "verify"
              ? await storageClient.verifyOriginal(workspaceId, id)
              : await storageClient.createQueueTest(workspaceId);
      if (currentWorkspace.current !== workspaceId) return;
      setJobs((previous) =>
        [job, ...previous.filter((item) => item.id !== job.id)].slice(0, 50),
      );
      setError("");
      await refresh.current();
    } catch (cause) {
      if (currentWorkspace.current === workspaceId)
        setError(
          cause instanceof Error
            ? cause.message
            : "The job could not be updated.",
        );
    }
  }
  return {
    jobs: jobs.filter((job) => job.workspace_id === workspaceId),
    status,
    error,
    action,
    refresh: () => refresh.current(),
  };
}
