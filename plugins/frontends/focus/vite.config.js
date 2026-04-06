import { defineConfig } from "vite";
import { resolve } from "path";

const repoRoot = resolve(import.meta.dirname, "../../..");
const pythonServer = "http://127.0.0.1:7280";

export default defineConfig({
  build: {
    outDir: "shenas_frontends/focus/static",
    emptyOutDir: false,
    cssCodeSplit: false,
    rollupOptions: {
      input: "src/index.js",
      external: ["lit", /^lit\//, "shenas-frontends", /^\/vendor\//],
      output: {
        entryFileNames: "focus.js",
        assetFileNames: "focus.[ext]",
        format: "es",
      },
    },
  },
  server: {
    port: 5174,
    strictPort: true,
    proxy: {
      "/api": { target: pythonServer, secure: false },
      "/vendor": { target: pythonServer, secure: false },
      "/static": { target: pythonServer, secure: false },
      "/themes": { target: pythonServer, secure: false },
      "/dashboards": { target: pythonServer, secure: false },
    },
    fs: {
      allow: [repoRoot],
    },
  },
  optimizeDeps: {
    exclude: ["lit", "shenas-frontends"],
  },
  plugins: [
    {
      name: "vendor-externals",
      enforce: "pre",
      apply: "serve",
      resolveId(source) {
        const vendorMap = {
          "shenas-frontends": "/vendor/shenas-frontends.js",
          "/vendor/apache-arrow.js": "/vendor/apache-arrow.js",
        };
        if (vendorMap[source]) return { id: vendorMap[source], external: true };
      },
    },
  ],
});
