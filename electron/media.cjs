const { app, protocol } = require("electron");

protocol.registerSchemesAsPrivileged([{ scheme: "studylens-media", privileges: {
  standard: true, secure: true, stream: true, supportFetchAPI: true,
} }]);

function registerMedia(getWindow, getBackend) {
  const bind = () => protocol.handle("studylens-media", async (request) => {
    try {
      const window = getWindow();
      if (!window || window.isDestroyed()) return new Response("Unavailable", {status: 503});
      const current = new URL(window.webContents.getURL());
      // Chromium serializes its local-file initiator as file://, while the
      // WHATWG URL.origin property returns null for that same URL.
      const allowedOrigin = current.protocol === "file:" ? "file://" : current.origin;
      if (request.initiatorOrigin != null && String(request.initiatorOrigin) !== allowedOrigin)
        return new Response("Denied", {status: 403});
      const url = new URL(request.url);
      const match = /^\/([a-zA-Z0-9_-]{1,200})\/([a-zA-Z0-9_-]{1,200})$/.exec(url.pathname);
      if (url.hostname !== "original" || url.port || url.username || url.password || url.search || url.hash || !match)
        return new Response("Invalid media source", {status: 400});
      if (!["GET", "HEAD"].includes(request.method)) return new Response("Read only", {status: 405});
      const range = request.headers.get("range");
      const backend = await getBackend();
      return await backend.response(`/workspaces/${match[1]}/source-versions/${match[2]}/playback`, {
        method: request.method, headers: range ? {Range: range} : {}, signal: request.signal,
      });
    } catch {
      return new Response("Video playback is unavailable. Reopen Neev or save the original.", {status: 503});
    }
  });
  if (app.isReady()) bind();
  else app.whenReady().then(bind);
}

module.exports = { registerMedia };
