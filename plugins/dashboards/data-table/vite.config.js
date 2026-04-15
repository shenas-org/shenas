import { defineConfig } from "vite";
import { resolve } from "path";

export default defineConfig({
  resolve: {
    alias: {
      "shenas-frontends": resolve(__dirname, "../../../app/vendor/src/shenas-frontends/dashboard.ts"),
      "shenas-components": resolve(__dirname, "../../../app/components/data-table.ts"),
      lit: resolve(__dirname, "node_modules/lit"),
      "lit/": resolve(__dirname, "node_modules/lit/"),
      "echarts": resolve(__dirname, "node_modules/echarts"),
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
    outDir: "shenas_dashboards/data_table/static",
    emptyOutDir: true,
    cssCodeSplit: false,
    rollupOptions: {
      input: "src/index.ts",
      external: ["lit", /^lit\//, "apache-arrow", "shenas-components", "shenas-frontends"],
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
