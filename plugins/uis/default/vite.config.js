import { defineConfig } from "vite";
import { readdirSync, existsSync } from "fs";
import { resolve } from "path";

const repoRoot = resolve(import.meta.dirname, "../../..");

/** Auto-discover JS plugins with a vite.config.js and src/index.js. */
function discoverPlugins(base, urlPrefix) {
  const aliases = {};
  const absBase = resolve(repoRoot, base);
  if (!existsSync(absBase)) return aliases;
  for (const name of readdirSync(absBase)) {
    const dir = resolve(absBase, name);
    if (existsSync(resolve(dir, "vite.config.js")) && existsSync(resolve(dir, "src/index.js"))) {
      aliases[`/${urlPrefix}/${name}/${name}.js`] = resolve(dir, "src/index.js");
    }
  }
  return aliases;
}

const devAliases = {
  "/ui/default/default.js": resolve(import.meta.dirname, "src/index.js"),
  ...discoverPlugins("plugins/components", "components"),
};

const pythonServer = "https://127.0.0.1:7280";

export default defineConfig({
  test: {
    environment: "happy-dom",
    setupFiles: ["src/__tests__/setup.js"],
  },
  resolve: {
    alias: {
      "/vendor/apache-arrow.js": new URL("src/__tests__/mock-arrow.js", import.meta.url).pathname,
    },
  },
  build: {
    outDir: "shenas_ui/default/static",
    emptyOutDir: false,
    cssCodeSplit: false,
    rollupOptions: {
      input: "src/index.js",
      external: ["lit", /^lit\//, /^@lit-labs\//, "cytoscape", /^\/vendor\//],
      output: {
        entryFileNames: "default.js",
        assetFileNames: "default.[ext]",
        format: "es",
      },
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": { target: pythonServer, secure: false },
      "/vendor": { target: pythonServer, secure: false },
      "/static": { target: pythonServer, secure: false },
      "/themes": { target: pythonServer, secure: false },
    },
    fs: {
      allow: [repoRoot],
    },
  },
  optimizeDeps: {
    exclude: ["lit", "cytoscape", "apache-arrow", "uplot"],
  },
  plugins: [
    {
      name: "vendor-externals",
      enforce: "pre",
      apply: "serve",
      resolveId(source) {
        const vendorMap = {
          cytoscape: "/vendor/cytoscape.js",
          "apache-arrow": "/vendor/apache-arrow.js",
          uplot: "/vendor/uplot.js",
        };
        if (vendorMap[source]) return { id: vendorMap[source], external: true };
      },
    },
    {
      name: "plugin-aliases",
      configureServer(server) {
        const names = Object.keys(devAliases);
        server.config.logger.info(`  Serving ${names.length} plugins: ${names.join(", ")}`);
        // Runs before Vite's internal middlewares (SPA fallback etc.)
        server.middlewares.use((req, _res, next) => {
          const alias = devAliases[req.url];
          if (alias) {
            req.url = "/@fs/" + resolve(alias);
          }
          next();
        });
      },
    },
  ],
});
