import { defineConfig } from "vite";

export default defineConfig({
  test: {
    environment: "happy-dom",
  },
  build: {
    outDir: "shenas_ui/default/static",
    emptyOutDir: true,
    cssCodeSplit: false,
    rollupOptions: {
      input: "src/index.js",
      output: {
        entryFileNames: "default.js",
        assetFileNames: "default.[ext]",
        format: "es",
        inlineDynamicImports: true,
      },
    },
  },
  server: {
    proxy: {
      "/api": "https://127.0.0.1:7280",
    },
  },
});
