import { defineConfig } from "vite";
import { readdirSync, existsSync } from "fs";
import http from "http";
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

/** Auto-discover UI plugin source entry points. */
function discoverFrontends() {
  const aliases = {};
  const frontendsBase = resolve(repoRoot, "plugins/frontends");
  if (!existsSync(frontendsBase)) return aliases;
  for (const name of readdirSync(frontendsBase)) {
    const dir = resolve(frontendsBase, name);
    if (name === "core") continue;
    if (existsSync(resolve(dir, "src/index.js"))) {
      aliases[`/frontend/${name}/${name}.js`] = resolve(dir, "src/index.js");
    }
  }
  return aliases;
}

const devAliases = {
  ...discoverFrontends(),
  ...discoverPlugins("plugins/dashboards", "dashboards"),
};

const pythonServer = "http://127.0.0.1:7280";


export default defineConfig({
  test: {
    environment: "happy-dom",
    setupFiles: ["src/__tests__/setup.js"],
    alias: {
      "/vendor/apache-arrow.js": new URL("src/__tests__/mock-arrow.js", import.meta.url).pathname,
      "shenas-frontends": new URL("../../../app/vendor/src/shenas-frontends.js", import.meta.url).pathname,
    },
  },
  build: {
    outDir: "shenas_frontends/default/static",
    emptyOutDir: false,
    cssCodeSplit: false,
    rollupOptions: {
      input: "src/index.js",
      external: ["lit", /^lit\//, /^@lit-labs\//, "cytoscape", "shenas-frontends", /^\/vendor\//],
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
    exclude: ["lit", "cytoscape", "apache-arrow", "uplot", "shenas-frontends"],
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
          "shenas-frontends": "/vendor/shenas-frontends.js",
          "/vendor/apache-arrow.js": "/vendor/apache-arrow.js",
        };
        if (vendorMap[source]) return { id: vendorMap[source], external: true };
      },
    },
    {
      name: "plugin-aliases",
      configureServer(server) {
        const names = Object.keys(devAliases);
        server.config.logger.info(`  Serving ${names.length} plugins: ${names.join(", ")}`);
        server.middlewares.use((req, res, next) => {
          // Serve active UI HTML from Python server (respects DB-enabled UI)
          const path = req.url.split("?")[0];
          if (path === "/" || path === "/index.html") {
            const proxyReq = http.get(`${pythonServer}/`, (proxyRes) => {
              let body = "";
              proxyRes.on("data", (chunk) => { body += chunk; });
              proxyRes.on("end", () => {
                // Inject Vite client for HMR
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
