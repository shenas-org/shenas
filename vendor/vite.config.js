import { defineConfig } from "vite";

export default defineConfig({
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      treeshake: false,
      input: {
        lit: "src/lit.js",
        "apache-arrow": "src/apache-arrow.js",
        uplot: "src/uplot.js",
      },
      output: {
        entryFileNames: "[name].js",
        chunkFileNames: "chunks/[name]-[hash].js",
        format: "es",
      },
    },
  },
});
