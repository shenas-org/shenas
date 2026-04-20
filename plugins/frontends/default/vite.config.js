import { defineConfig } from "vite";
import { readdirSync, existsSync } from "fs";
import http from "http";
import { resolve } from "path";

const repoRoot = resolve(import.meta.dirname, "../../..");

/** Auto-discover JS/TS plugins with a vite.config.js and src/index. */
function discoverPlugins(base, urlPrefix) {
  const aliases = {};
  const absBase = resolve(repoRoot, base);
  if (!existsSync(absBase)) return aliases;
  for (const name of readdirSync(absBase)) {
    const dir = resolve(absBase, name);
    if (!existsSync(resolve(dir, "vite.config.js"))) continue;
    const entry = existsSync(resolve(dir, "src/index.ts"))
      ? resolve(dir, "src/index.ts")
      : existsSync(resolve(dir, "src/index.js"))
        ? resolve(dir, "src/index.js")
        : null;
    if (entry) {
      aliases[`/${urlPrefix}/${name}/${name}.js`] = entry;
    }
  }
  return aliases;
}

/** Auto-discover UI plugin source entry points. */
function discoverFrontends() {
  const aliases = {};
  const frontendsBase = resolve(repoRoot, "plugins/frontends");
  if (!existsSync(frontendsBase)) return aliases;
  for (const name of readdirSync(frontendsBase)) {
    const dir = resolve(frontendsBase, name);
    if (name === "core") continue;
    const entry = existsSync(resolve(dir, "src/index.ts"))
      ? resolve(dir, "src/index.ts")
      : existsSync(resolve(dir, "src/index.js"))
        ? resolve(dir, "src/index.js")
        : null;
    if (entry) {
      aliases[`/frontend/${name}/${name}.js`] = entry;
    }
  }
  return aliases;
}

const devAliases = {
  ...discoverFrontends(),
};

const pythonServer = "http://127.0.0.1:7280";

export default defineConfig({
  resolve: {
    // Ensure deps imported by aliased files outside this project (e.g. app/components/)
    // resolve from this project's node_modules, not their own (which may not exist in CI).
    dedupe: ["lit", "echarts", "apache-arrow"],
  },
  test: {
    environment: "happy-dom",
    setupFiles: ["src/__tests__/setup.ts"],
    alias: {
      cytoscape: new URL("src/__tests__/mock-cytoscape.ts", import.meta.url).pathname,
      "/vendor/cytoscape.js": new URL("src/__tests__/mock-cytoscape.ts", import.meta.url).pathname,
      "/vendor/apache-arrow.js": new URL("src/__tests__/mock-arrow.ts", import.meta.url).pathname,
      "/vendor/components.js": new URL("../../../app/components/data-table.ts", import.meta.url).pathname,
      "/vendor/echarts.js": new URL("../../../app/vendor/src/echarts.js", import.meta.url).pathname,
      "shenas-components": new URL("../../../app/components/data-table.ts", import.meta.url).pathname,
      echarts: new URL("../../../app/vendor/node_modules/echarts", import.meta.url).pathname,
      "shenas-frontends": new URL("../../../app/vendor/src/shenas-frontends.ts", import.meta.url).pathname,
      "echarts/core": new URL("node_modules/echarts/core.js", import.meta.url).pathname,
      "echarts/charts": new URL("node_modules/echarts/charts.js", import.meta.url).pathname,
      "echarts/components": new URL("node_modules/echarts/components.js", import.meta.url).pathname,
      "echarts/renderers": new URL("node_modules/echarts/renderers.js", import.meta.url).pathname,
    },
    coverage: {
      provider: "v8",
      include: ["src/**/*.ts"],
      exclude: ["src/__tests__/**", "src/index.ts", "src/*.d.ts"],
    },
  },
  build: {
    outDir: "shenas_frontends/default/static",
    emptyOutDir: false,
    cssCodeSplit: false,
    rollupOptions: {
      input: "src/index.ts",
      external: [
        "lit",
        /^lit\//,
        /^@lit-labs\//,
        "cytoscape",
        /^echarts/,
        "shenas-components",
        "shenas-frontends",
        /^\/vendor\//,
      ],
      output: {
        entryFileNames: "default.js",
        assetFileNames: "default.[ext]",
        format: "es",
        paths: (id) => {
          if (id.startsWith("echarts")) return "/vendor/echarts.js";
        },
      },
    },
  },
  server: {
    host: "127.0.0.1",
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
    exclude: ["lit", "cytoscape", "apache-arrow", "echarts", "shenas-components", "shenas-frontends"],
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
          echarts: "/vendor/echarts.js",
          "shenas-components": "/vendor/components.js",
          "shenas-frontends": "/vendor/shenas-frontends.js",
          "/vendor/apache-arrow.js": "/vendor/apache-arrow.js",
        };
        if (vendorMap[source]) return { id: vendorMap[source], external: true };
        if (source.startsWith("echarts/")) return { id: "/vendor/echarts.js", external: true };
      },
    },
    {
      name: "plugin-aliases",
      configureServer(server) {
        const names = Object.keys(devAliases);
        server.config.logger.info(`  Serving ${names.length} plugins: ${names.join(", ")}`);
        server.middlewares.use((req, res, next) => {
          const path = req.url.split("?")[0];
          // Proxy dashboard JS directly (skip Vite module transform)
          if (path.startsWith("/dashboards/") && path.endsWith(".js")) {
            const proxyReq = http.get(`${pythonServer}${path}`, (proxyRes) => {
              res.setHeader("Content-Type", "application/javascript");
              proxyRes.pipe(res);
            });
            proxyReq.on("error", () => next());
            return;
          }
          // SPA fallback: any GET that isn't an asset, an /api call, or a Vite
          // internal should serve the shell HTML so deep links like
          // /settings/source/garmin work on direct load and refresh.
          const isAsset = /\.[a-z0-9]+$/i.test(path);
          const isInternal =
            path.startsWith("/@") ||
            path.startsWith("/node_modules/") ||
            path.startsWith("/api") ||
            path.startsWith("/vendor") ||
            path.startsWith("/static") ||
            path.startsWith("/themes") ||
            path.startsWith("/dashboards/") ||
            path.startsWith("/frontend/");
          if (req.method === "GET" && !isAsset && !isInternal) {
            const proxyReq = http.get(`${pythonServer}/`, (proxyRes) => {
              let body = "";
              proxyRes.on("data", (chunk) => {
                body += chunk;
              });
              proxyRes.on("end", () => {
                body = body.replace("</head>", '  <script type="module" src="/@vite/client"></script>\n  </head>');
                res.setHeader("Content-Type", "text/html");
                res.end(body);
              });
            });
            proxyReq.on("error", () => next());
            return;
          }
          // Rewrite plugin JS URLs to source files
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
