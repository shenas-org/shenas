import { defineConfig } from "vite";

export default defineConfig({
  test: {
    environment: "happy-dom",
  },
  build: {
    outDir: "shenas_components/data_table/static",
    emptyOutDir: true,
    cssCodeSplit: false,
    rollupOptions: {
      input: "src/index.js",
      output: {
        entryFileNames: "data-table.js",
        assetFileNames: "data-table.[ext]",
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
