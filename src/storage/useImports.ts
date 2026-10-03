import { useEffect, useState, useSyncExternalStore } from "react";
import { ImportManager } from "./imports";
import { storageClient, unwrap } from "./client";
export function useImports() {
  const [manager] = useState(
    () =>
      new ImportManager({
        async upload(scope, file, signal) {
          if ("id" in file) {
            if (!window.studyLens?.storage)
              throw new Error("Desktop file picker is unavailable.");
            return unwrap(
              await window.studyLens.storage.importFile({
                ...scope,
                ticketId: file.id,
              }),
            );
          }
          return storageClient.importBrowserFile(
            scope.workspaceId,
            scope.subjectId,
            file,
            signal,
            scope.sourceId,
          );
        },
        cancelTicket(ticketId) {
          void window.studyLens?.storage.cancelImport({ ticketId });
        },
      }),
  );
  const state = useSyncExternalStore(manager.subscribe, manager.getSnapshot);
  useEffect(() => () => manager.cancel(), [manager]);
  return { manager, state };
}
