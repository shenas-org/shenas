import { defineConfig } from "vite";

export default defineConfig({
  test: {
    environment: "happy-dom",
  },
  build: {
    outDir: "shenas_dashboards/data_table/static",
    emptyOutDir: true,
    cssCodeSplit: false,
    rollupOptions: {
      input: "src/index.js",
      external: ["lit", /^lit\//, "apache-arrow"],
      output: {
        entryFileNames: "data-table.js",
        assetFileNames: "data-table.[ext]",
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
