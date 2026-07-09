import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The API serves the built app at /app/, so assets must resolve under that
// base. Output goes into app/frontend so FastAPI can serve it as static files.
export default defineConfig({
  base: "/app/",
  plugins: [react()],
  build: {
    outDir: "../app/frontend",
    emptyOutDir: true,
  },
  server: {
    // For `npm run dev`, proxy API calls to the local FastAPI instance.
    proxy: {
      "/agent": "http://localhost:8000",
      "/documents": "http://localhost:8000",
      "/business": "http://localhost:8000",
      "/runs": "http://localhost:8000",
      "/evals": "http://localhost:8000",
    },
  },
});
