const { ipcMain, dialog, app } = require("electron");
const fs = require("node:fs");
const fsp = require("node:fs/promises");
const path = require("node:path");
const crypto = require("node:crypto");
const { Readable } = require("node:stream");
const { pipeline } = require("node:stream/promises");
const { registerMedia } = require("./media.cjs");
const { youtubePlaybackUrl } = require("./youtube.cjs");

const extensions = [
  "pdf",
  "txt",
  "md",
  "ppt",
  "pptx",
  "mp4",
  "mkv",
  "mov",
  "webm",
  "mp3",
  "wav",
  "m4a",
  "ogg",
  "flac",
  "png",
  "jpg",
  "jpeg",
  "webp",
  "tif",
  "tiff",
  "bmp",
];

function identifier(value) {
  if (typeof value !== "string" || !/^[a-zA-Z0-9_-]{1,200}$/.test(value))
    throw new Error("Invalid storage identifier.");
  return encodeURIComponent(value);
}
function registerStorage(getWindow, getBackend) {
  registerMedia(getWindow, getBackend);
  const tickets = new Map();
  const uploads = new Map();
  function guard(event) {
    const window = getWindow();
    if (
      !window ||
      event.sender !== window.webContents ||
      event.senderFrame !== window.webContents.mainFrame
    )
      throw new Error("Storage is available only to the Neev window.");
    return window;
  }
  function handler(channel, action) {
    ipcMain.handle(channel, async (event, payload) => {
      try {
        guard(event);
        return { ok: true, data: await action(payload, event) };
      } catch (error) {
        return {
          ok: false,
          error: {
            message: error.message || "Local storage request failed.",
            status: error.status || 0,
          },
        };
      }
    });
  }
  handler(
    "storage:request",
    async ({ action, workspaceId, jobId, versionId, offset = 0, body }) => {
      const backend = await getBackend();
      const json = (value) => ({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(value),
      });
      if (action === "listWorkspaces") return backend.request("/workspaces");
      if (action === "createWorkspace")
        return backend.request("/workspaces", json(body));
      if (action === "loadSession")
        return backend.request(
          "/workspaces/" + identifier(workspaceId) + "/session",
        );
      if (action === "saveSession") {
        const options = json(body);
        if (Buffer.byteLength(options.body) > 1_000_000)
          throw new Error("This workspace is too large to save as a session.");
        options.method = "PUT";
        return backend.request(
          "/workspaces/" + identifier(workspaceId) + "/session",
          options,
        );
      }
      if (action === "storageInfo") return backend.request("/storage");
      if (action === "health") return backend.request("/health");
      if (action === "queueStatus") return backend.request("/queue");
      if (action === "visionStatus") return backend.request("/vision");
      if (action === "audioStatus") return backend.request("/audio");
      if (action === "importYouTube")
        return backend.request("/workspaces/" + identifier(workspaceId) + "/subjects/" + identifier(body?.subjectId) + "/youtube",
          json({url:body.url,language:body.language,title:body.title || ""}));
      if (action === "openYouTube") {
        await require("electron").shell.openExternal(youtubePlaybackUrl(body?.url));
        return {opened:true};
      }
      if (action === "processCloudVisuals")
        return backend.request(
          "/workspaces/" + identifier(workspaceId) + "/source-versions/" + identifier(versionId) + "/cloud-visuals",
          json(body),
        );
      if (action === "listJobs")
        return backend.request(
          "/workspaces/" + identifier(workspaceId) + "/jobs",
        );
      if (action === "cancelJob" || action === "retryJob")
        return backend.request(
          "/workspaces/" +
            identifier(workspaceId) +
            "/jobs/" +
            identifier(jobId) +
            (action === "cancelJob" ? "/cancel" : "/retry"),
          { method: "POST" },
        );
      if (action === "verifyOriginal" || action === "processVisuals" || action === "processAudio" || action === "processVideoFrames")
        return backend.request(
          "/workspaces/" +
            identifier(workspaceId) +
            "/source-versions/" +
            identifier(versionId) +
            (action === "verifyOriginal" ? "/verify" : action === "processAudio" ? "/process-audio" : action === "processVideoFrames" ? "/process-video-frames" : "/process-visuals"),
          { method: "POST" },
        );
      if (action === "readContent" || action === "readVideoFrames") {
        if (!Number.isInteger(offset) || offset < 0 || offset > 10000)
          throw new Error("Invalid content location.");
        return backend.request(
          "/workspaces/" +
            identifier(workspaceId) +
            "/source-versions/" +
            identifier(versionId) +
            (action === "readContent" ? "/content?offset=" : "/video-frames?offset=") +
            offset,
        );
      }
      if (action === "createQueueTest")
        return backend.request(
          "/workspaces/" + identifier(workspaceId) + "/queue-test",
          json(body),
        );
      throw new Error("Unsupported storage operation.");
    },
  );
  handler("storage:listSources", async ({ workspaceId, subjectId }) => {
    const backend = await getBackend();
    return backend.request(
      "/workspaces/" +
        identifier(workspaceId) +
        "/subjects/" +
        identifier(subjectId) +
        "/sources",
    );
  });
  handler("storage:chooseFiles", async ({ multiple = true } = {}, event) => {
    const chosen = await dialog.showOpenDialog(guard(event), {
      title: "Add course materials",
      properties: multiple ? ["openFile", "multiSelections"] : ["openFile"],
      filters: [{ name: "Course materials", extensions }],
    });
    if (chosen.canceled) return [];
    const now = Date.now();
    for (const [id, ticket] of tickets)
      if (now - ticket.created > 15 * 60 * 1000) tickets.delete(id);
    if (chosen.filePaths.length > 32)
      throw new Error("Choose up to 32 files at a time.");
    return Promise.all(
      chosen.filePaths.map(async (filename) => {
        const stats = await fsp.stat(filename);
        const id = crypto.randomUUID();
        tickets.set(id, { path: filename, created: now });
        return { id, name: path.basename(filename), size: stats.size };
      }),
    );
  });
  handler(
    "storage:importFile",
    async ({ workspaceId, subjectId, ticketId, sourceId }) => {
      const ticket = tickets.get(ticketId);
      if (!ticket || Date.now() - ticket.created > 15 * 60 * 1000)
        throw new Error("File selection expired. Choose the file again.");
      tickets.delete(ticketId);
      const controller = new AbortController();
      uploads.set(ticketId, controller);
      let stream;
      try {
        const backend = await getBackend();
        controller.signal.throwIfAborted();
        const query = new URLSearchParams({
          filename: path.basename(ticket.path),
        });
        if (sourceId) query.set("source_id", identifier(sourceId));
        stream = fs.createReadStream(ticket.path, {
          highWaterMark: 1024 * 1024,
        });
        return await backend.request(
          "/workspaces/" +
            identifier(workspaceId) +
            "/subjects/" +
            identifier(subjectId) +
            "/sources?" +
            query,
          {
            method: "POST",
            headers: { "Content-Type": "application/octet-stream" },
            body: stream,
            duplex: "half",
            signal: controller.signal,
          },
        );
      } finally {
        stream?.destroy();
        uploads.delete(ticketId);
      }
    },
  );
  handler("storage:cancelImport", async ({ ticketId }) => {
    uploads.get(ticketId)?.abort();
    return { ok: true };
  });
  handler("storage:download", async ({ versionId, filename }, event) => {
    const backend = await getBackend();
    const safeName = path.basename(
      typeof filename === "string" ? filename : "original",
    );
    const chosen = await dialog.showSaveDialog(guard(event), {
      title: "Save original material",
      defaultPath: path.join(app.getPath("downloads"), safeName),
    });
    if (chosen.canceled || !chosen.filePath) return { canceled: true };
    const result = await backend.response(
      "/source-versions/" + identifier(versionId) + "/file",
    );
    if (!result.ok) {
      const body = await result.json();
      throw new Error(body.detail || "Original file could not be downloaded.");
    }
    const staging = chosen.filePath + "." + crypto.randomUUID() + ".part";
    try {
      await pipeline(
        Readable.fromWeb(result.body),
        fs.createWriteStream(staging, { flags: "wx" }),
      );
      await fsp.rename(staging, chosen.filePath);
    } finally {
      await fsp.unlink(staging).catch((error) => {
        if (error.code !== "ENOENT") throw error;
      });
    }
    return { canceled: false };
  });
}

module.exports = { registerStorage };
