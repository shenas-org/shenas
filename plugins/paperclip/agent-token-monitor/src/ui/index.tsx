import { useState } from "react";
import {
  usePluginData,
  type PluginWidgetProps,
  type PluginPageProps,
  type PluginSidebarProps,
  type PluginDetailTabProps,
} from "@paperclipai/plugin-sdk/ui";

// ── helpers ──────────────────────────────────────────────────────────────────

function fmt(n: number): string {
  return new Intl.NumberFormat("en-US").format(n);
}

function fmtUsd(n: number | null | undefined): string {
  if (n == null) return "—";
  return `$${n.toFixed(4)}`;
}

function fmtTs(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

// ── shared types ──────────────────────────────────────────────────────────────

type AgentTokenRow = {
  agentId: string;
  agentName: string;
  inputTokensMonthly: number;
  cachedInputTokensMonthly: number;
  outputTokensMonthly: number;
  subscriptionRunCount: number;
  apiRunCount: number;
};

type RunRow = {
  id: string;
  agentId: string;
  agentName: string;
  status: string;
  model: string | null;
  inputTokens: number;
  cachedInputTokens: number;
  outputTokens: number;
  costUsd: number | null;
  startedAt: string | null;
  finishedAt: string | null;
};

type SortKey = "startedAt" | "costUsd";
type SortDir = "asc" | "desc";

// ── dashboard widget ──────────────────────────────────────────────────────────

export function TokenTotalsWidget({ context }: PluginWidgetProps) {
  const { data, loading, error } = usePluginData<{ rows: AgentTokenRow[] }>("token-totals", {
    companyId: context.companyId ?? "",
  });

  if (loading) {
    return <div style={styles.widget}>Loading token totals…</div>;
  }
  if (error) {
    return <div style={styles.widget}>Error: {error.message}</div>;
  }

  const rows = data?.rows ?? [];

  return (
    <section style={styles.widget}>
      <div style={styles.widgetHeader}>
        <strong>Agent Tokens / Month</strong>
        <span style={styles.muted}>current UTC month</span>
      </div>
      {rows.length === 0 ? (
        <div style={styles.muted}>No token events recorded this month.</div>
      ) : (
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>Agent</th>
              <th style={{ ...styles.th, textAlign: "right" }}>Input</th>
              <th style={{ ...styles.th, textAlign: "right" }}>Cached</th>
              <th style={{ ...styles.th, textAlign: "right" }}>Output</th>
              <th style={{ ...styles.th, textAlign: "right" }}>Sub runs</th>
              <th style={{ ...styles.th, textAlign: "right" }}>API runs</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.agentId}>
                <td style={styles.td}>{row.agentName}</td>
                <td style={{ ...styles.td, textAlign: "right" }}>{fmt(row.inputTokensMonthly)}</td>
                <td style={{ ...styles.td, textAlign: "right" }}>{fmt(row.cachedInputTokensMonthly)}</td>
                <td style={{ ...styles.td, textAlign: "right" }}>{fmt(row.outputTokensMonthly)}</td>
                <td style={{ ...styles.td, textAlign: "right" }}>{fmt(row.subscriptionRunCount)}</td>
                <td style={{ ...styles.td, textAlign: "right" }}>{fmt(row.apiRunCount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

// ── runs page ─────────────────────────────────────────────────────────────────

export function RunsPage({ context }: PluginPageProps) {
  const [agentFilter, setAgentFilter] = useState<string>("");
  const [sortKey, setSortKey] = useState<SortKey>("startedAt");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const companyId = context.companyId ?? "";
  const queryParams: Record<string, string> = { companyId };
  if (agentFilter) queryParams.agentId = agentFilter;

  const { data, loading, error } = usePluginData<{ rows: RunRow[] }>("runs", queryParams);
  const { data: totalsData } = usePluginData<{ rows: AgentTokenRow[] }>("token-totals", {
    companyId,
  });

  const agents = totalsData?.rows ?? [];

  return (
    <div style={styles.page}>
      <div style={styles.pageHeader}>
        <h2 style={{ margin: 0 }}>Agent Runs</h2>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <label htmlFor="agent-filter" style={styles.muted}>
            Agent:
          </label>
          <select
            id="agent-filter"
            value={agentFilter}
            onChange={(e) => setAgentFilter(e.target.value)}
            style={styles.select}
          >
            <option value="">All agents</option>
            {agents.map((a) => (
              <option key={a.agentId} value={a.agentId}>
                {a.agentName}
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading && <div style={styles.muted}>Loading runs…</div>}
      {error && <div>Error: {error.message}</div>}

      {!loading && !error && (
        <RunsTable
          rows={data?.rows ?? []}
          sortKey={sortKey}
          sortDir={sortDir}
          onSort={(key) => {
            if (sortKey === key) {
              setSortDir((d) => (d === "asc" ? "desc" : "asc"));
            } else {
              setSortKey(key);
              setSortDir("desc");
            }
          }}
        />
      )}
    </div>
  );
}

// ── sidebar link ──────────────────────────────────────────────────────────────

export function RunsSidebarLink(_props: PluginSidebarProps) {
  return <span>Agent Runs</span>;
}

// ── agent detail tabs ─────────────────────────────────────────────────────────

export function AgentTokensTab({ context }: PluginDetailTabProps) {
  const agentId = context.entityId;
  const companyId = context.companyId ?? "";

  const { data, loading, error } = usePluginData<{ rows: AgentTokenRow[] }>("token-totals", {
    companyId,
    agentId,
  });

  if (loading) return <div style={styles.tabContent}>Loading…</div>;
  if (error) return <div style={styles.tabContent}>Error: {error.message}</div>;

  const row = data?.rows?.[0];

  return (
    <div style={styles.tabContent}>
      <div style={styles.cardHeader}>
        <strong>Monthly Token Usage</strong>
        <span style={styles.muted}>current UTC month</span>
      </div>
      {!row ? (
        <div style={styles.muted}>No token events recorded this month.</div>
      ) : (
        <table style={styles.table}>
          <tbody>
            <tr>
              <td style={styles.tdLabel}>Input tokens</td>
              <td style={{ ...styles.td, textAlign: "right" }}>{fmt(row.inputTokensMonthly)}</td>
            </tr>
            <tr>
              <td style={styles.tdLabel}>Cached input tokens</td>
              <td style={{ ...styles.td, textAlign: "right" }}>{fmt(row.cachedInputTokensMonthly)}</td>
            </tr>
            <tr>
              <td style={styles.tdLabel}>Output tokens</td>
              <td style={{ ...styles.td, textAlign: "right" }}>{fmt(row.outputTokensMonthly)}</td>
            </tr>
            <tr>
              <td style={styles.tdLabel}>Subscription runs</td>
              <td style={{ ...styles.td, textAlign: "right" }}>{fmt(row.subscriptionRunCount)}</td>
            </tr>
            <tr>
              <td style={styles.tdLabel}>API / metered runs</td>
              <td style={{ ...styles.td, textAlign: "right" }}>{fmt(row.apiRunCount)}</td>
            </tr>
          </tbody>
        </table>
      )}
    </div>
  );
}

export function AgentRunsTab({ context }: PluginDetailTabProps) {
  const agentId = context.entityId;
  const companyId = context.companyId ?? "";
  const [sortKey, setSortKey] = useState<SortKey>("startedAt");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const { data, loading, error } = usePluginData<{ rows: RunRow[] }>("runs", {
    companyId,
    agentId,
  });

  return (
    <div style={styles.tabContent}>
      {loading && <div style={styles.muted}>Loading runs…</div>}
      {error && <div>Error: {error.message}</div>}
      {!loading && !error && (
        <RunsTable
          rows={data?.rows ?? []}
          sortKey={sortKey}
          sortDir={sortDir}
          onSort={(key) => {
            if (sortKey === key) {
              setSortDir((d) => (d === "asc" ? "desc" : "asc"));
            } else {
              setSortKey(key);
              setSortDir("desc");
            }
          }}
        />
      )}
    </div>
  );
}

// ── shared runs table ─────────────────────────────────────────────────────────

function RunsTable({
  rows,
  sortKey,
  sortDir,
  onSort,
}: {
  rows: RunRow[];
  sortKey: SortKey;
  sortDir: SortDir;
  onSort: (key: SortKey) => void;
}) {
  const sorted = [...rows].sort((a, b) => {
    let cmp = 0;
    if (sortKey === "costUsd") {
      cmp = (a.costUsd ?? -1) - (b.costUsd ?? -1);
    } else {
      cmp = (a.startedAt ?? "").localeCompare(b.startedAt ?? "");
    }
    return sortDir === "asc" ? cmp : -cmp;
  });

  function indicator(key: SortKey) {
    if (sortKey !== key) return null;
    return sortDir === "asc" ? " ↑" : " ↓";
  }

  return (
    <div style={{ overflowX: "auto" }}>
      <table style={styles.table}>
        <thead>
          <tr>
            <th style={{ ...styles.th, cursor: "pointer" }} onClick={() => onSort("startedAt")}>
              Timestamp{indicator("startedAt")}
            </th>
            <th style={styles.th}>Status</th>
            <th style={styles.th}>Model</th>
            <th style={{ ...styles.th, textAlign: "right" }}>Input tokens</th>
            <th style={{ ...styles.th, textAlign: "right" }}>Cached tokens</th>
            <th style={{ ...styles.th, textAlign: "right" }}>Output tokens</th>
            <th
              style={{ ...styles.th, textAlign: "right", cursor: "pointer" }}
              onClick={() => onSort("costUsd")}
            >
              Cost USD{indicator("costUsd")}
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.length === 0 ? (
            <tr>
              <td colSpan={7} style={{ ...styles.td, textAlign: "center", ...styles.muted }}>
                No runs found.
              </td>
            </tr>
          ) : (
            sorted.map((row) => (
              <tr key={row.id}>
                <td style={styles.td}>{fmtTs(row.startedAt)}</td>
                <td style={styles.td}>{row.status}</td>
                <td style={styles.td}>{row.model ?? "—"}</td>
                <td style={{ ...styles.td, textAlign: "right" }}>{fmt(row.inputTokens)}</td>
                <td style={{ ...styles.td, textAlign: "right" }}>{fmt(row.cachedInputTokens)}</td>
                <td style={{ ...styles.td, textAlign: "right" }}>{fmt(row.outputTokens)}</td>
                <td style={{ ...styles.td, textAlign: "right" }}>{fmtUsd(row.costUsd)}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

// ── styles ────────────────────────────────────────────────────────────────────

const styles: Record<string, React.CSSProperties> = {
  widget: {
    padding: "0.75rem",
    display: "grid",
    gap: "0.5rem",
  },
  widgetHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "baseline",
    gap: "0.5rem",
  },
  tabContent: {
    padding: "1rem",
    display: "grid",
    gap: "0.75rem",
  },
  cardHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "baseline",
    gap: "0.5rem",
  },
  page: {
    padding: "1.5rem",
    display: "grid",
    gap: "1rem",
  },
  pageHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: "1rem",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
    fontSize: "0.875rem",
  },
  th: {
    padding: "0.375rem 0.75rem",
    textAlign: "left",
    borderBottom: "1px solid currentColor",
    whiteSpace: "nowrap",
  },
  td: {
    padding: "0.375rem 0.75rem",
    borderBottom: "1px solid rgba(128,128,128,0.2)",
    whiteSpace: "nowrap",
  },
  tdLabel: {
    padding: "0.375rem 0.75rem",
    borderBottom: "1px solid rgba(128,128,128,0.2)",
    whiteSpace: "nowrap",
    opacity: 0.75,
    fontSize: "0.875rem",
  },
  muted: {
    opacity: 0.6,
    fontSize: "0.8125rem",
  },
  select: {
    padding: "0.25rem 0.5rem",
    borderRadius: "4px",
  },
};
