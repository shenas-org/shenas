import type { PaperclipPluginManifestV1 } from "@paperclipai/plugin-sdk";

const manifest: PaperclipPluginManifestV1 = {
  id: "shenas.spend-telemetry",
  apiVersion: 1,
  version: "0.1.0",
  displayName: "Spend Telemetry",
  description: "Per-issue and per-run spend dashboards surfacing cost_events data for shenas.",
  author: "shenas.ai",
  categories: ["ui", "automation"],
  capabilities: [
    "agents.read",
    "issues.read",
    "database.namespace.read",
    "api.routes.register",
    "ui.detailTab.register",
    "ui.dashboardWidget.register",
  ],
  entrypoints: {
    worker: "./dist/worker.js",
    ui: "./dist/ui",
  },
  database: {
    migrationsDir: "migrations",
    coreReadTables: ["cost_events", "heartbeat_runs", "agents", "issues"],
  },
  // UI slots are wired in SHE-603 (detail tab) and SHE-604 (dashboard widget).
  ui: {
    slots: [],
  },
};

export default manifest;
