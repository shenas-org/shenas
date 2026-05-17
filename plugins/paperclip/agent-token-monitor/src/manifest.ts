import type { PaperclipPluginManifestV1 } from "@paperclipai/plugin-sdk";
import { PLUGIN_UI_SLOT_TYPES } from "@paperclipai/plugin-sdk";

const PLUGIN_ID = "shenas.agent-token-monitor";
const PLUGIN_VERSION = "0.1.0";

// Verify the SDK exports the constant we depend on at import time.
void PLUGIN_UI_SLOT_TYPES;

const manifest: PaperclipPluginManifestV1 = {
  id: PLUGIN_ID,
  apiVersion: 1,
  version: PLUGIN_VERSION,
  displayName: "Agent Token Monitor",
  description:
    "Surfaces per-agent monthly token totals and a per-run cost view as a dashboard widget, a dedicated page, and agent detail tabs.",
  author: "shenas.ai",
  categories: ["ui", "automation"],
  capabilities: [
    "agents.read",
    "database.namespace.read",
    "api.routes.register",
    "ui.dashboardWidget.register",
    "ui.page.register",
    "ui.sidebar.register",
    "ui.detailTab.register",
  ],
  entrypoints: {
    worker: "./dist/worker.js",
    ui: "./dist/ui",
  },
  database: {
    migrationsDir: "migrations",
    coreReadTables: ["cost_events", "heartbeat_runs", "agents"],
  },
  apiRoutes: [
    {
      routeKey: "token-totals",
      method: "GET",
      path: "/token-totals",
      auth: "board-or-agent",
      capability: "api.routes.register",
      companyResolution: { from: "query", key: "companyId" },
    },
    {
      routeKey: "runs",
      method: "GET",
      path: "/runs",
      auth: "board-or-agent",
      capability: "api.routes.register",
      companyResolution: { from: "query", key: "companyId" },
    },
  ],
  ui: {
    slots: [
      {
        type: "dashboardWidget",
        id: "token-totals-widget",
        displayName: "Agent Token Totals",
        exportName: "TokenTotalsWidget",
      },
      {
        type: "page",
        id: "runs-page",
        displayName: "Agent Runs",
        exportName: "RunsPage",
        routePath: "agent-runs",
      },
      {
        type: "sidebar",
        id: "runs-sidebar",
        displayName: "Agent Runs",
        exportName: "RunsSidebarLink",
      },
      {
        type: "detailTab",
        id: "agent-tokens-tab",
        displayName: "Tokens",
        exportName: "AgentTokensTab",
        entityTypes: ["agent"],
      },
      {
        type: "detailTab",
        id: "agent-runs-tab",
        displayName: "Runs",
        exportName: "AgentRunsTab",
        entityTypes: ["agent"],
      },
    ],
  },
};

export default manifest;
