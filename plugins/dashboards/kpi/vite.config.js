import { defineConfig } from "vite";
import { resolve } from "path";

export default defineConfig({
  resolve: {
    alias: {
      "shenas-frontends": resolve(__dirname, "../../../app/vendor/src/shenas-frontends/dashboard.ts"),
      "apache-arrow": resolve(__dirname, "node_modules/apache-arrow"),
      lit: resolve(__dirname, "node_modules/lit"),
      "lit/": resolve(__dirname, "node_modules/lit/"),
      echarts: resolve(__dirname, "node_modules/echarts"),
    },
  },
  test: {
    environment: "happy-dom",
    setupFiles: ["./src/__tests__/setup-dom-patch.ts"],
    coverage: {
      provider: "v8",
      include: ["src/**/*.ts"],
      exclude: ["src/__tests__/**", "src/index.ts"],
    },
  },
  build: {
    outDir: "shenas_dashboards/kpi_dashboard/static",
    emptyOutDir: true,
    cssCodeSplit: false,
    rollupOptions: {
      input: "src/index.ts",
      external: ["lit", /^lit\//, "apache-arrow", "shenas-frontends", "echarts"],
      output: {
        entryFileNames: "kpi-dashboard.js",
        assetFileNames: "kpi-dashboard.[ext]",
        format: "es",
      },
    },
  },
  server: {
    host: true,
    allowedHosts: true,
    proxy: {
      "/api": "http://127.0.0.1:7280",
    },
  },
});
