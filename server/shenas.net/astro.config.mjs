// @ts-check
import { defineConfig } from "astro/config";

export default defineConfig({
  vite: {
    esbuild: {
      target: "es2022",
    },
    server: {
      proxy: {
        "/api": "http://localhost:8000",
      },
    },
  },
});
