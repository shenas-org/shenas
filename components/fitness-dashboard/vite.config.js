import { defineConfig } from "vite";

export default defineConfig({
  test: {
    environment: "happy-dom",
  },
  build: {
    outDir: "shenas_components/fitness_dashboard/static",
    emptyOutDir: true,
    cssCodeSplit: false,
    rollupOptions: {
      input: "src/index.js",
      output: {
        entryFileNames: "fitness-dashboard.js",
        assetFileNames: "fitness-dashboard.[ext]",
        format: "es",
        inlineDynamicImports: true,
      },
    },
  },
  server: {
    proxy: {
      "/api": "http://127.0.0.1:7280",
    },
  },
});
