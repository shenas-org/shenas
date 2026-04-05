import { defineConfig } from "vite";

export default defineConfig({
  test: {
    environment: "happy-dom",
    setupFiles: ["src/__tests__/setup.js"],
  },
  resolve: {
    alias: {
      "/vendor/apache-arrow.js": new URL("src/__tests__/mock-arrow.js", import.meta.url).pathname,
    },
  },
  build: {
    outDir: "shenas_ui/default/static",
    emptyOutDir: false,
    cssCodeSplit: false,
    rollupOptions: {
      input: "src/index.js",
      external: ["lit", /^lit\//, /^@lit-labs\//, "cytoscape", /^\/vendor\//],
      output: {
        entryFileNames: "default.js",
        assetFileNames: "default.[ext]",
        format: "es",
      },
    },
  },
  server: {
    proxy: {
      "/api": "https://127.0.0.1:7280",
    },
  },
});
