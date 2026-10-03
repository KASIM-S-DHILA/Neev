const { app, BrowserWindow, ipcMain } = require("electron");
const path = require("node:path");
const fs = require("node:fs");
const { startBackend } = require("./backend.cjs");
const { registerStorage } = require("./storage.cjs");
app.setName("Neev");

let window;
const smoke = process.env.STUDYLENS_SMOKE === "1";
if (smoke) {
  app.disableHardwareAcceleration();
  const testData = path.join(__dirname, "../tmp/electron-smoke");
  fs.mkdirSync(testData, { recursive: true });
  app.setPath("userData", testData);
} else {
  // Keep the existing profile/database through the public-name change.
  const existingProfile = path.join(app.getPath("appData"), "StudyLens");
  fs.mkdirSync(existingProfile, { recursive: true });
  app.setPath("userData", existingProfile);
}
let backendPromise;
let backend;
async function getBackend() {
  if (backend && !backend.isRunning) backendPromise = null;
  if (!backendPromise)
    backendPromise = startBackend({
      dataRoot:
        process.env.STUDYLENS_DATA_DIR ||
        path.join(app.getPath("userData"), "data"),
    })
      .then((value) => {
        backend = value;
        return value;
      })
      .catch((error) => {
        backendPromise = null;
        throw error;
      });
  return backendPromise;
}
registerStorage(() => window, getBackend);
async function smokeExit(code) {
  await backend?.stop();
  app.exit(code);
}

function createWindow() {
  window = new BrowserWindow({
    width: 1366,
    height: 768,
    minWidth: 760,
    minHeight: 540,
    title: "Neev",
    backgroundColor: "#fbfbfa",
    frame: false,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      offscreen: smoke,
    },
  });
  window.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
  window.webContents.on("will-navigate", (event, url) => {
    const allowed = process.env.STUDYLENS_DEV_URL;
    if (
      url !== window.webContents.getURL() &&
      !(allowed && url.startsWith(allowed + "/"))
    )
      event.preventDefault();
  });
  if (process.env.STUDYLENS_DEV_URL)
    window.loadURL(process.env.STUDYLENS_DEV_URL);
  else window.loadFile(path.join(__dirname, "../dist/index.html"));
  window.once("ready-to-show", () => {
    if (!smoke) window.show();
  });
  window.on("maximize", () =>
    window.webContents.send("window:maximized", true),
  );
  window.on("unmaximize", () =>
    window.webContents.send("window:maximized", false),
  );
  if (smoke) {
    window.webContents.once("did-finish-load", async () => {
      try {
        console.log("Desktop production page loaded");
        const result = await window.webContents
          .executeJavaScript(`new Promise((resolve, reject) => {
          const deadline = Date.now() + 8000;
          function inspect() {
            if (document.querySelector('[data-testid="workspace"]')) {
              resolve({title: document.title, isolated: typeof require === 'undefined', bridge: !!window.studyLens, tabs: document.querySelectorAll('[role="tab"]').length});
            } else if (Date.now() > deadline) reject(new Error('Workspace did not render'));
            else setTimeout(inspect, 100);
          }
          inspect();
        })`);
        if (!result.isolated || !result.bridge || !result.tabs)
          throw new Error("Desktop boundary check failed");
        const health = await window.webContents.executeJavaScript(
          "window.studyLens.storage.request({action:'health'})",
        );
        if (!health.ok || health.data.journal_mode !== "wal")
          throw new Error("Desktop storage bridge failed");
        result.storage = health.data;
        if (
          !health.data.queue?.available ||
          health.data.queue.max_active_heavy_jobs !== 1
        )
          throw new Error("Desktop background worker did not start");
        await window.webContents
          .executeJavaScript(`new Promise((resolve, reject) => {
          const deadline = Date.now() + 8000;
          function inspect() {
            if (document.querySelector('.save-state.saved')) resolve(true);
            else if (Date.now() > deadline) reject(new Error('Workspace storage did not become ready'));
            else setTimeout(inspect, 100);
          }
          inspect();
        })`);
        const saved = await window.webContents.executeJavaScript(
          "window.studyLens.storage.request({action:'loadSession',workspaceId:'semester-3'})",
        );
        if (!saved.ok || !saved.data.session)
          throw new Error("Desktop session was not persisted");
        result.sessionPersisted = true;
        const fixture = fs.readFileSync(
          path.join(
            __dirname,
            "../docs/evaluation/fixtures/phase-04/digital-notes.pdf",
          ),
        );
        const original = await backend.request(
          "/workspaces/semester-3/subjects/probability/sources?filename=phase-04-digital.pdf",
          {
            method: "POST",
            headers: { "Content-Type": "application/octet-stream" },
            body: fixture,
          },
        );
        const contentPayload = JSON.stringify({
          action: "readContent",
          workspaceId: "semester-3",
          versionId: original.version_id,
          offset: 1,
        });
        const contentDeadline = Date.now() + 10000;
        let nativeContent;
        while (Date.now() < contentDeadline) {
          nativeContent = await window.webContents.executeJavaScript(
            "window.studyLens.storage.request(" + contentPayload + ")",
          );
          if (nativeContent.ok && nativeContent.data.state === "succeeded")
            break;
          await new Promise((resolve) => setTimeout(resolve, 100));
        }
        if (
          !nativeContent?.ok ||
          !nativeContent.data.integrity_verified ||
          nativeContent.data.units[0]?.locator.page !== 2 ||
          !nativeContent.data.units[0]?.text.includes(
            "A prior probability is updated after observing evidence.",
          )
        )
          throw new Error("Desktop extracted content bridge failed");
        result.sourceContent = {
          state: nativeContent.data.state,
          page: nativeContent.data.units[0].locator.page,
          total: nativeContent.data.total,
        };
        const visualOriginal = await backend.request(
          "/workspaces/semester-3/subjects/probability/sources?filename=phase-05-scan.png",
          {
            method: "POST",
            headers: { "Content-Type": "application/octet-stream" },
            body: fs.readFileSync(
              path.join(
                __dirname,
                "../docs/evaluation/fixtures/phase-05/scan.png",
              ),
            ),
          },
        );
        const visualPayload = JSON.stringify({
          action: "readContent",
          workspaceId: "semester-3",
          versionId: visualOriginal.version_id,
          offset: 0,
        });
        const visualDeadline = Date.now() + 12000;
        let visualContent;
        while (Date.now() < visualDeadline) {
          visualContent = await window.webContents.executeJavaScript(
            "window.studyLens.storage.request(" + visualPayload + ")",
          );
          if (visualContent.ok && visualContent.data.state === "partial") break;
          await new Promise((resolve) => setTimeout(resolve, 100));
        }
        const visualUnit = visualContent?.data?.units[0];
        if (
          !visualContent?.ok ||
          !visualUnit?.text.includes("100 outcomes") ||
          visualUnit.status !== "suspect" ||
          !visualUnit.metadata.assets[0].data_url.startsWith(
            "data:image/png;base64,",
          )
        )
          throw new Error("Desktop OCR/visual preview bridge failed");
        result.sourceVisual = {
          state: visualContent.data.state,
          page: visualUnit.locator.page,
          reviewRequired: visualUnit.metadata.review_required,
          preview: true,
        };
        const vision = await window.webContents.executeJavaScript(
          "window.studyLens.storage.request({action:'visionStatus'})",
        );
        if (!vision.ok || vision.data.configured !== false || !vision.data.model)
          throw new Error("Desktop vision capability bridge failed");
        const cloudDenied = await window.webContents.executeJavaScript(
          "window.studyLens.storage.request(" + JSON.stringify({
            action: "processCloudVisuals", workspaceId: "semester-3",
            versionId: visualOriginal.version_id, body: { provider: "unsupported" },
          }) + ")",
        );
        if (cloudDenied.ok || cloudDenied.error.status !== 422)
          throw new Error("Desktop cloud provider boundary failed");
        result.cloudProviderBoundary = true;
        const rebuilt = await window.webContents.executeJavaScript(
          "window.studyLens.storage.request(" +
            JSON.stringify({
              action: "processVisuals",
              workspaceId: "semester-3",
              versionId: visualOriginal.version_id,
            }) +
            ")",
        );
        if (
          !rebuilt.ok ||
          !["queued", "running", "partial"].includes(rebuilt.data.state)
        )
          throw new Error("Desktop visual reprocessing bridge failed");
        const rebuildDeadline = Date.now() + 12000;
        let rebuiltContent;
        while (Date.now() < rebuildDeadline) {
          rebuiltContent = await window.webContents.executeJavaScript(
            "window.studyLens.storage.request(" + visualPayload + ")",
          );
          if (rebuiltContent.ok && rebuiltContent.data.state === "partial")
            break;
          await new Promise((resolve) => setTimeout(resolve, 100));
        }
        if (
          !rebuiltContent?.ok ||
          rebuiltContent.data.units[0]?.id !== visualUnit.id ||
          !rebuiltContent.data.units[0]?.text.includes("100 outcomes")
        )
          throw new Error("Desktop reprocessed source content did not return");
        console.log("STUDYLENS_SMOKE_OK " + JSON.stringify(result));
        try {
          await window.webContents.executeJavaScript(
            "document.fonts.ready.then(() => true)",
          );
          const screenshot = await window.webContents.capturePage(undefined, {
            stayHidden: true,
          });
          const output = path.join(__dirname, "../docs/evaluation/screenshots");
          fs.mkdirSync(output, { recursive: true });
          fs.writeFileSync(
            path.join(output, "phase-05-workspace-desktop.png"),
            screenshot.toPNG(),
          );
        } catch (error) {
          console.warn(
            "Desktop screenshot unavailable; use browser visual review:",
            error.message,
          );
        }
        await smokeExit(0);
      } catch (error) {
        console.error(error);
        await smokeExit(1);
      }
    });
    window.webContents.once("did-fail-load", (_event, code, message) => {
      console.error(code, message);
      void smokeExit(1);
    });
    setTimeout(() => {
      console.error("Desktop smoke timed out");
      void smokeExit(1);
    }, 30000).unref();
  }
}

ipcMain.on("window:action", (event, action) => {
  if (!window || event.sender !== window.webContents) return;
  if (action === "minimize") window.minimize();
  if (action === "maximize")
    window.isMaximized() ? window.unmaximize() : window.maximize();
  if (action === "close") window.close();
});
app.whenReady().then(() => {
  createWindow();
  void getBackend().catch((error) => console.error(error.message));
});
let quitting = false;
app.on("before-quit", (event) => {
  if (quitting || !backendPromise) return;
  event.preventDefault();
  quitting = true;
  // Cancel active original-video streams before asking the service to exit.
  if (window && !window.isDestroyed()) window.destroy();
  backendPromise
    .then((value) => value.stop())
    .catch(() => {})
    .finally(() => app.quit());
});
process.on("message", (message) => {
  if (message?.action === "quit") app.quit();
});
app.on("window-all-closed", () => {
  if (process.platform !== "darwin" && !quitting) app.quit();
});
app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
