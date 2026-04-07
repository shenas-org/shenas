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
        uplot: "src/uplot.js",
        cytoscape: "src/cytoscape.js",
        "shenas-frontends": "src/shenas-frontends.ts",
      },
      external(id, importer) {
        // Only externalize lit for shenas-frontends (not for lit.js itself)
        if (/^\/vendor\//.test(id)) return true;
        if ((id === "lit" || /^lit\//.test(id)) && importer?.includes("shenas-frontends")) return true;
        return false;
      },
      output: {
        entryFileNames: "[name].js",
        chunkFileNames: "chunks/[name]-[hash].js",
        format: "es",
      },
    },
  },
});
