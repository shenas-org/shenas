import { defineConfig } from "vite";
import { resolve } from "path";

export default defineConfig({
  resolve: {
    alias: {
      "shenas-frontends": resolve(__dirname, "../../../app/vendor/src/shenas-frontends/arrow.ts"),
      "apache-arrow": resolve(__dirname, "node_modules/apache-arrow"),
    },
  },
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
      external: ["lit", /^lit\//, "apache-arrow", "uplot", "shenas-frontends"],
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
