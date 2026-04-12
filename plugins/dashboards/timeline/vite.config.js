import { defineConfig } from "vite";
import { resolve } from "path";

export default defineConfig({
  resolve: {
    alias: {
      "shenas-frontends": resolve(__dirname, "../../../app/vendor/src/shenas-frontends/dashboard.ts"),
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
    outDir: "shenas_dashboards/timeline/static",
    emptyOutDir: true,
    cssCodeSplit: false,
    rollupOptions: {
      input: "src/index.ts",
      external: ["lit", /^lit\//, "apache-arrow", "shenas-frontends"],
      output: {
        entryFileNames: "timeline.js",
        assetFileNames: "timeline.[ext]",
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
