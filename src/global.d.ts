export {};
import type { StorageBridge } from "./storage/client";
declare global {
  interface Window {
    studyLens?: {
      storage: StorageBridge;
      windowAction: (action: "minimize" | "maximize" | "close") => void;
      onMaximized: (callback: (value: boolean) => void) => () => void;
    };
  }
}
