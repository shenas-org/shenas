import { defineConfig } from "vite";

export default defineConfig({
  test: {
    environment: "happy-dom",
    coverage: {
      provider: "v8",
      include: ["src/shenas-frontends/**/*.ts"],
      exclude: ["src/__tests__/**", "src/shenas-frontends.ts"],
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      treeshake: false,
      preserveEntrySignatures: "exports-only",
      input: {
        lit: "src/lit.js",
        "apache-arrow": "src/apache-arrow.js",
        echarts: "src/echarts.js",
        cytoscape: "src/cytoscape.js",
        components: "src/components.ts",
        "shenas-frontends": "src/shenas-frontends.ts",
      },
      external(id, importer) {
        // Only externalize lit for shenas-frontends and components (not for lit.js itself)
        if (/^\/vendor\//.test(id)) return true;
        const needsLitExternal = importer && (importer.includes("shenas-frontends") || importer.includes("components"));
        if ((id === "lit" || /^lit\//.test(id) || /^@lit-labs\//.test(id)) && needsLitExternal) return true;
        // Externalize shenas-frontends for components (it's loaded separately)
        if (id === "shenas-frontends" && importer?.includes("components")) return true;
        // Externalize echarts for components
        if (/^echarts/.test(id) && importer?.includes("components")) return true;
        return false;
      },
      output: {
        entryFileNames: "[name].js",
        chunkFileNames: "chunks/[name]-[hash].js",
        format: "es",
        paths: {
          lit: "/vendor/lit.js",
          "lit/decorators.js": "/vendor/lit.js",
          "lit/directives/unsafe-html.js": "/vendor/lit.js",
          "shenas-frontends": "/vendor/shenas-frontends.js",
          "echarts/core": "/vendor/echarts.js",
          "echarts/charts": "/vendor/echarts.js",
          "echarts/components": "/vendor/echarts.js",
          "echarts/renderers": "/vendor/echarts.js",
        },
      },
    },
  },
});
