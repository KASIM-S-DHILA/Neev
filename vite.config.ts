import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    {
      name: "local-api-boundary",
      configureServer(server) {
        server.middlewares.use((request, response, next) => {
          if (!request.url?.startsWith("/api/")) return next();
          const origin = request.headers.origin;
          const host = request.headers.host;
          const local = /^(127\.0\.0\.1|localhost):5173$/;
          if (
            !host ||
            !local.test(host) ||
            (origin &&
              !/^http:\/\/(127\.0\.0\.1|localhost):5173$/.test(origin)) ||
            request.headers["sec-fetch-site"] === "cross-site"
          ) {
            response.statusCode = 403;
            response.end(
              JSON.stringify({
                detail: "Open StudyLens from its local preview address.",
              }),
            );
            return;
          }
          next();
        });
      },
    },
  ],
  base: "./",
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    watch: {
      ignored: [
        "**/.venv/**",
        "**/tmp/**",
        "**/.electron-cache/**",
        "**/.npm-cache/**",
        "**/__pycache__/**",
      ],
    },
    proxy: process.env.STUDYLENS_API_URL
      ? {
          "/api": {
            target: process.env.STUDYLENS_API_URL,
            headers: {
              Authorization: "Bearer " + process.env.STUDYLENS_API_TOKEN,
            },
            rewrite: (path) => path.replace(/^\/api/, ""),
          },
        }
      : undefined,
  },
});
