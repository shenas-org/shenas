import { defineConfig } from "vite";

export default defineConfig({
  build: {
    outDir: "shenas_components/dashboard/static",
    emptyOutDir: true,
    cssCodeSplit: false,
    rollupOptions: {
      input: "src/index.js",
      output: {
        entryFileNames: "dashboard.js",
        assetFileNames: "dashboard.[ext]",
        format: "es",
        inlineDynamicImports: true,
      },
    },
  },
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
});
