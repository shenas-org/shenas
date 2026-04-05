// @ts-check
import { defineConfig } from "astro/config";

export default defineConfig({
  vite: {
    esbuild: {
      target: "es2022",
    },
  },
});
