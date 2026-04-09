import { defineConfig } from "vite";

export default defineConfig({
  test: {
    environment: "happy-dom",
    coverage: {
      provider: "v8",
      include: ["src/**/*.ts"],
      exclude: ["src/__tests__/**", "src/index.ts"],
    },
  },
  build: {
    outDir: "shenas_dashboards/fitness_dashboard/static",
    emptyOutDir: true,
    cssCodeSplit: false,
    rollupOptions: {
      input: "src/index.ts",
      external: ["lit", /^lit\//, "apache-arrow", "uplot"],
      output: {
        entryFileNames: "fitness-dashboard.js",
        assetFileNames: "fitness-dashboard.[ext]",
        format: "es",
      },
    },
  },
  server: {
    proxy: {
      "/api": "http://127.0.0.1:7280",
    },
  },
});
