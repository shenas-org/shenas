import { LitElement, html, css } from "lit";
import cytoscape from "cytoscape";
// The vendor bundle re-exports cytoscape-dagre as `dagre` from "cytoscape".
// @ts-expect-error dagre is provided by the vendor bundle, not the real cytoscape package
import { dagre } from "cytoscape";
import {
  ApolloQueryController,
  ApolloMutationController,
  getClient,
  utilityStyles,
  buttonStyles,
  messageStyles,
  renderMessage,
} from "shenas-frontends";
import type { MessageBanner } from "shenas-frontends";
import { GET_FLOW_DATA, GET_SUGGESTED_DATASETS } from "./graphql/queries.ts";
import { SUGGEST_DATASETS, ACCEPT_DATASET_SUGGESTION, DISMISS_DATASET_SUGGESTION } from "./graphql/mutations.ts";

interface PluginInfo {
  name: string;
  displayName?: string;
  enabled?: boolean;
}

interface Transform {
  id: number;
  transformType: string;
  source: { id: string; schemaName: string; tableName: string };
  target: { id: string; schemaName: string; tableName: string };
  sourcePlugin: string;
  description?: string;
  enabled: boolean;
}

interface CyElement {
  data: Record<string, unknown>;
}

type FlowView = "device" | "entity" | "data";

let _dagreRegistered = false;

class PipelineOverview extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    allPlugins: { type: Object },
    schemaPlugins: { type: Object },
    _empty: { state: true },
    _view: { state: true },
    _suggesting: { state: true },
    _suggestions: { state: true },
    _message: { state: true },
  };

  static styles = [
    utilityStyles,
    buttonStyles,
    messageStyles,
    css`
      :host {
        display: block;
      }
      #cy {
        width: 100%;
        height: calc(100vh - 16rem);
        border: 1px solid var(--shenas-border, #e0e0e0);
        border-radius: 8px;
        background: var(--shenas-bg-secondary, #fafafa);
        box-sizing: border-box;
      }
      .legend {
        display: flex;
        flex-wrap: wrap;
        gap: 0.8rem;
        margin-top: 0.8rem;
        font-size: 0.8rem;
        color: var(--shenas-text-secondary, #666);
      }
      .legend-item {
        display: flex;
        align-items: center;
        gap: 4px;
      }
      .legend-dot {
        width: 10px;
        height: 10px;
        border-radius: 3px;
      }
      .legend-dot.pipe {
        background: var(--shenas-node-pipe, #4a90d9);
      }
      .legend-dot.schema {
        background: var(--shenas-node-schema, #66bb6a);
      }
      .legend-dot.component {
        background: var(--shenas-node-component, #ffa726);
      }
      .legend-dot.model {
        background: var(--shenas-node-model, #ab47bc);
      }
      .legend-line {
        width: 20px;
        height: 2px;
      }
      .legend-line.enabled {
        background: var(--shenas-text-muted, #888);
      }
      .legend-line.disabled {
        background: var(--shenas-text-faint, #aaa);
        border-top: 2px dashed var(--shenas-text-faint, #aaa);
        height: 0;
      }
      .view-switcher {
        display: flex;
        gap: 0;
        margin-bottom: 0.8rem;
        border: 1px solid var(--shenas-border, #e0e0e0);
        border-radius: 6px;
        overflow: hidden;
        width: fit-content;
      }
      .view-switcher button {
        padding: 0.4rem 1rem;
        border: none;
        background: var(--shenas-bg-secondary, #fafafa);
        color: var(--shenas-text-secondary, #666);
        font-size: 0.8rem;
        cursor: pointer;
        border-right: 1px solid var(--shenas-border, #e0e0e0);
      }
      .view-switcher button:last-child {
        border-right: none;
      }
      .view-switcher button.active {
        background: var(--shenas-accent, #728f67);
        color: #fff;
      }
      .view-switcher button:not(.active):hover {
        background: var(--shenas-bg-hover, #f0f0f0);
      }
      .placeholder {
        display: flex;
        align-items: center;
        justify-content: center;
        height: calc(100vh - 10rem);
        border: 1px dashed var(--shenas-border, #e0e0e0);
        border-radius: 8px;
        color: var(--shenas-text-muted, #888);
        font-size: 0.9rem;
      }
      .toolbar {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 0.8rem;
        align-items: center;
      }
      .toolbar button {
        font-size: 0.8rem;
        padding: 0.35rem 0.8rem;
      }
      .suggestions {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin-bottom: 0.8rem;
      }
      .suggestion-chip {
        background: var(--shenas-bg-secondary, #f5f5f5);
        border: 1px solid var(--shenas-border, #ddd);
        border-radius: 6px;
        padding: 0.4rem 0.7rem;
        font-size: 0.8rem;
        display: flex;
        align-items: center;
        gap: 0.4rem;
      }
      .suggestion-chip .name {
        font-weight: 600;
        color: var(--shenas-text, #222);
      }
      .suggestion-chip .meta {
        color: var(--shenas-text-muted, #888);
        font-size: 0.7rem;
      }
      .suggestion-chip .action {
        cursor: pointer;
        border: none;
        background: none;
        padding: 0;
        font-size: 0.9rem;
        line-height: 1;
        opacity: 0.5;
        transition: opacity 0.15s;
      }
      .suggestion-chip .action:hover {
        opacity: 1;
      }
    `,
  ];

  declare apiBase: string;
  declare allPlugins: Record<string, PluginInfo[]>;
  declare schemaPlugins: Record<string, string[]>;
  declare _empty: boolean;
  declare _view: FlowView;
  declare _suggesting: boolean;
  declare _suggestions: Array<{ name: string; title?: string; grain?: string; tableName?: string }>;
  declare _message: MessageBanner | null;
  private _cy: cytoscape.Core | null = null;
  private _elements: CyElement[] | null = null;
  private _resizeObserver: ResizeObserver | null = null;
  private _client = getClient();

  private _overviewQuery = new ApolloQueryController(this, GET_FLOW_DATA, {
    client: this._client,
  });
  private _suggestMutation = new ApolloMutationController(this, SUGGEST_DATASETS, {
    client: this._client,
  });

  get _loading(): boolean {
    return this._overviewQuery.loading;
  }

  constructor() {
    super();
    this.apiBase = "/api";
    this.allPlugins = {};
    this.schemaPlugins = {};
    this._empty = false;
    this._view = "device";
    this._suggesting = false;
    this._suggestions = [];
    this._message = null;
  }

  connectedCallback(): void {
    super.connectedCallback();
    this._fetchSuggestions();
  }

  async _fetchSuggestions(): Promise<void> {
    const { data } = await this._client.query({
      query: GET_SUGGESTED_DATASETS,
      fetchPolicy: "network-only",
    });
    this._suggestions = (data?.suggestedDatasets as typeof this._suggestions) || [];
  }

  async _suggest(): Promise<void> {
    this._suggesting = true;
    this._message = null;
    try {
      const { data, errors } = await this._suggestMutation.mutate();
      if (errors?.length) {
        this._message = { type: "error", text: errors[0].message };
      } else {
        const result = data?.suggestDatasets as Record<string, unknown> | undefined;
        if (result?.ok === false) {
          this._message = { type: "error", text: (result.error as string) || "Suggestion failed" };
        } else {
          const count = (result?.suggestions as unknown[])?.length || 0;
          this._message = { type: "success", text: `Generated ${count} suggestion(s)` };
          await this._fetchSuggestions();
        }
      }
    } catch (e) {
      this._message = { type: "error", text: (e as Error).message };
    }
    this._suggesting = false;
  }

  async _clearSuggestions(): Promise<void> {
    for (const s of this._suggestions) {
      await this._client.mutate({ mutation: DISMISS_DATASET_SUGGESTION, variables: { name: s.name } });
    }
    this._suggestions = [];
    this._message = { type: "success", text: "Suggestions cleared" };
  }

  async _acceptSuggestion(name: string): Promise<void> {
    const { data } = await this._client.mutate({ mutation: ACCEPT_DATASET_SUGGESTION, variables: { name } });
    const result = data?.acceptDatasetSuggestion as { ok: boolean; message: string } | undefined;
    if (result?.ok) {
      this._suggestions = this._suggestions.filter((s) => s.name !== name);
      this._message = { type: "success", text: result.message || "Accepted" };
    } else {
      this._message = { type: "error", text: result?.message || "Accept failed" };
    }
  }

  async _dismissSuggestion(name: string): Promise<void> {
    await this._client.mutate({ mutation: DISMISS_DATASET_SUGGESTION, variables: { name } });
    this._suggestions = this._suggestions.filter((s) => s.name !== name);
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    if (this._cy) {
      this._cy.destroy();
      this._cy = null;
    }
    if (this._resizeObserver) {
      this._resizeObserver.disconnect();
      this._resizeObserver = null;
    }
  }

  private _processQueryData(): void {
    const data = this._overviewQuery.data as Record<string, unknown> | undefined;
    if (!data) return;
    const ap = this.allPlugins || {};
    this._buildElements(
      (ap.source || []) as PluginInfo[],
      (ap.dataset || []) as PluginInfo[],
      (data?.transforms || []) as Transform[],
      this.schemaPlugins || {},
      (ap.dashboard || []) as PluginInfo[],
      Object.fromEntries(
        ((data?.dependencies || []) as Array<{ source: string; targets: string[] }>).map((d) => [d.source, d.targets]),
      ),
      (ap.model || []) as PluginInfo[],
    );
  }

  _buildElements(
    pipes: PluginInfo[],
    schemas: PluginInfo[],
    transforms: Transform[],
    ownership: Record<string, string[]>,
    components: PluginInfo[],
    deps: Record<string, string[]>,
    models: PluginInfo[] = [],
  ): void {
    const elements: CyElement[] = [];
    const nodeIds = new Set<string>();

    // Build reverse lookup: table -> schema plugin name
    const tableToPlugin: Record<string, string> = {};
    for (const [pluginName, tables] of Object.entries(ownership)) {
      for (const table of tables) {
        tableToPlugin[table] = pluginName;
      }
    }

    // Device node (current machine)
    const deviceId = "device:local";
    nodeIds.add(deviceId);
    elements.push({ data: { id: deviceId, label: "This Device", kind: "device" } });

    // Source nodes + Device -> Source edges
    for (const p of pipes) {
      const id = `source:${p.name}`;
      nodeIds.add(id);
      elements.push({
        data: { id, label: p.displayName || p.name, kind: "source", enabled: p.enabled !== false ? "yes" : "no" },
      });
      elements.push({
        data: { id: `edge:device:${p.name}`, source: deviceId, target: id, edgeType: "device" },
      });
    }

    // Dataset nodes
    for (const s of schemas) {
      const id = `dataset:${s.name}`;
      nodeIds.add(id);
      elements.push({
        data: { id, label: s.displayName || s.name, kind: "dataset", enabled: s.enabled !== false ? "yes" : "no" },
      });
    }

    // Dashboard nodes
    for (const c of components) {
      const id = `dashboard:${c.name}`;
      nodeIds.add(id);
      elements.push({
        data: { id, label: c.displayName || c.name, kind: "dashboard", enabled: c.enabled !== false ? "yes" : "no" },
      });
    }

    // Model nodes
    for (const m of models) {
      const id = `model:${m.name}`;
      nodeIds.add(id);
      elements.push({
        data: { id, label: m.displayName || m.name, kind: "model", enabled: m.enabled !== false ? "yes" : "no" },
      });
    }

    // Transform edges (pipe -> schema via data)
    for (const t of transforms) {
      const sourceId = `source:${t.sourcePlugin}`;
      const ownerPlugin = tableToPlugin[t.target.tableName];
      const targetId = ownerPlugin ? `dataset:${ownerPlugin}` : null;
      if (!targetId || !nodeIds.has(sourceId) || !nodeIds.has(targetId)) continue;
      const typeTag = t.transformType ? `[${t.transformType}] ` : "";
      const desc = t.description || `${t.source.tableName} -> ${t.target.tableName}`;
      const full = `${typeTag}${desc}`;
      const label = full.length > 35 ? full.slice(0, 33) + "..." : full;
      elements.push({
        data: {
          id: `transform:${t.id}`,
          source: sourceId,
          target: targetId,
          label,
          enabled: t.enabled ? "yes" : "no",
          sourcePlugin: t.sourcePlugin,
          edgeType: "transform",
        },
      });
    }

    // Track which pipe->schema pairs already have transform edges
    const transformPairs = new Set<string>();
    for (const el of elements) {
      if (el.data.edgeType === "transform") {
        transformPairs.add(`${el.data.source}:${el.data.target}`);
      }
    }

    // Dependency edges (from package metadata)
    const depEdgeIds = new Set<string>();
    for (const [depSource, targets] of Object.entries(deps)) {
      for (const depTarget of targets) {
        const sourceKind = depSource.split(":")[0];
        let edgeSource: string;
        let edgeTarget: string;
        if (sourceKind === "dashboard" || sourceKind === "model") {
          // Component/model depends on schema -> show as schema -> component/model
          edgeSource = depTarget;
          edgeTarget = depSource;
        } else {
          edgeSource = depSource;
          edgeTarget = depTarget;
        }
        if (!nodeIds.has(edgeSource) || !nodeIds.has(edgeTarget)) continue;
        // Skip pipe->schema dep edges when transforms already connect them
        if (sourceKind === "source" && transformPairs.has(`${edgeSource}:${edgeTarget}`)) continue;
        const edgeId = `dep:${edgeSource}:${edgeTarget}`;
        if (depEdgeIds.has(edgeId)) continue;
        depEdgeIds.add(edgeId);
        elements.push({
          data: {
            id: edgeId,
            source: edgeSource,
            target: edgeTarget,
            edgeType: "dependency",
          },
        });
      }
    }

    // Hide non-source nodes that have no edges (no relationships).
    const connectedNodes = new Set<string>();
    for (const el of elements) {
      if (el.data.source) connectedNodes.add(el.data.source as string);
      if (el.data.target) connectedNodes.add(el.data.target as string);
    }
    this._elements = elements.filter(
      (el) => el.data.source || el.data.kind === "source" || connectedNodes.has(el.data.id as string),
    );
    this._empty = this._elements.filter((e) => e.data.source).length === 0;
  }

  _initCytoscape(): void {
    const container = this.renderRoot.querySelector("#cy") as HTMLElement | null;
    if (!container || !this._elements) return;

    if (!_dagreRegistered) {
      cytoscape.use(dagre);
      _dagreRegistered = true;
    }

    if (this._cy) {
      this._cy.destroy();
    }

    this._cy = cytoscape({
      container,
      elements: this._elements,

      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "text-valign": "center",
            "text-halign": "center",
            "font-size": 12,
            color: "#fff",
            "text-wrap": "wrap",
            "text-max-width": 100,
            width: 120,
            height: 40,
            shape: "round-rectangle",
          },
        },
        {
          selector: 'node[kind="device"]',
          style: { "background-color": "#607d8b", shape: "round-rectangle", cursor: "pointer" },
        },
        {
          selector: 'node[kind="source"]',
          style: { "background-color": "#4a90d9", cursor: "pointer" },
        },
        {
          selector: 'node[kind="dataset"]',
          style: { "background-color": "#66bb6a", cursor: "pointer" },
        },
        {
          selector: 'node[kind="dashboard"]',
          style: { "background-color": "#ffa726", cursor: "pointer" },
        },
        {
          selector: 'node[kind="model"]',
          style: { "background-color": "#ab47bc", cursor: "pointer" },
        },
        {
          selector: 'node[enabled="no"]',
          style: { opacity: 0.4, "border-width": 2, "border-color": "#999", "border-style": "dashed" },
        },
        {
          selector: "edge",
          style: {
            "curve-style": "bezier",
            "target-arrow-shape": "triangle",
            "target-arrow-color": "#999",
            "line-color": "#999",
            cursor: "pointer",
            width: 2,
            label: "data(label)",
            "font-size": 9,
            color: "#888",
            "text-rotation": "autorotate",
            "text-margin-y": -8,
          },
        },
        {
          selector: 'edge[enabled="yes"]',
          style: { "line-style": "solid" },
        },
        {
          selector: 'edge[enabled="no"]',
          style: {
            "line-style": "dashed",
            "line-color": "#ccc",
            "target-arrow-color": "#ccc",
            opacity: 0.5,
          },
        },
        {
          selector: 'edge[edgeType="device"]',
          style: {
            "line-style": "solid",
            "line-color": "#90a4ae",
            "target-arrow-color": "#90a4ae",
            width: 1.5,
            label: "",
          },
        },
        {
          selector: 'edge[edgeType="dependency"]',
          style: {
            "line-style": "dotted",
            "line-color": "#bbb",
            "target-arrow-color": "#bbb",
            width: 1.5,
            label: "",
          },
        },
      ] as unknown as cytoscape.StylesheetStyle[],
      layout: {
        name: "dagre",
        rankDir: "LR",
        nodeSep: 60,
        rankSep: 150,
        padding: 30,
      } as unknown as cytoscape.LayoutOptions,
      userZoomingEnabled: true,
      userPanningEnabled: true,
      boxSelectionEnabled: false,
    });

    this._cy.on("tap", "node", (evt) => {
      const data = evt.target.data() as Record<string, string>;
      const name = data.id.substring(data.id.indexOf(":") + 1);
      let path: string | undefined;
      if (data.kind === "source") path = `/settings/source/${name}`;
      else if (data.kind === "dataset") path = `/settings/dataset/${name}`;
      else if (data.kind === "dashboard") path = `/settings/dashboard/${name}`;
      else if (data.kind === "model") path = `/settings/model/${name}`;
      else return;
      this.dispatchEvent(new CustomEvent("navigate", { bubbles: true, composed: true, detail: { path } }));
    });

    this._cy.on("tap", "edge", (evt) => {
      const plugin = evt.target.data("sourcePlugin") as string | undefined;
      if (plugin) {
        this.dispatchEvent(
          new CustomEvent("navigate", {
            bubbles: true,
            composed: true,
            detail: { path: `/settings/source/${plugin}` },
          }),
        );
      }
    });

    if (this._resizeObserver) {
      this._resizeObserver.disconnect();
    }
    this._resizeObserver = new ResizeObserver(() => {
      if (this._cy) {
        this._cy.resize();
        this._cy.fit(undefined, 30);
      }
    });
    this._resizeObserver.observe(container);
  }

  private _setView(view: FlowView): void {
    if (this._view === view) return;
    this._view = view;
    this._elements = null;
    if (this._cy) {
      this._cy.destroy();
      this._cy = null;
    }
  }

  updated(): void {
    if (this._view !== "device") return;
    if (!this._loading && !this._elements) {
      this._processQueryData();
    }
    if (!this._loading && this._elements) {
      requestAnimationFrame(() => this._initCytoscape());
    }
  }

  private _renderDeviceFlow() {
    return html`
      <div id="cy"></div>
      <div class="legend">
        <span class="legend-item"
          ><span class="legend-dot" style="background:#78909c;border-radius:50%"></span> Me</span
        >
        <span class="legend-item"><span class="legend-dot" style="background:#607d8b"></span> Device</span>
        <span class="legend-item"><span class="legend-dot pipe"></span> Source</span>
        <span class="legend-item"><span class="legend-dot schema"></span> Dataset</span>
        <span class="legend-item"><span class="legend-dot component"></span> Dashboard</span>
        <span class="legend-item"><span class="legend-dot model"></span> Model</span>
        <span class="legend-item"><span class="legend-line enabled"></span> Transform</span>
        <span class="legend-item"><span class="legend-line disabled"></span> Disabled</span>
        <span class="legend-item"
          ><span
            class="legend-line"
            style="border-top:2px dotted var(--shenas-text-faint, #aaa);height:0;background:none"
          ></span>
          Dependency</span
        >
      </div>
      ${this._empty ? html`<p class="empty">No connections found. Add transforms in pipe settings.</p>` : ""}
    `;
  }

  render() {
    const view = this._view;
    return html`
      <shenas-page ?loading=${view === "device" && this._loading} loading-text="Loading overview...">
        ${renderMessage(this._message)}
        <div class="view-switcher">
          <button class=${view === "device" ? "active" : ""} @click=${() => this._setView("device")}>
            Device-centric
          </button>
          <button class=${view === "entity" ? "active" : ""} @click=${() => this._setView("entity")}>
            Entity-centric
          </button>
          <button class=${view === "data" ? "active" : ""} @click=${() => this._setView("data")}>Data-centric</button>
        </div>
        <div class="toolbar">
          <button @click=${this._suggest} ?disabled=${this._suggesting}>
            ${this._suggesting ? "Generating..." : "Suggest new Datasets"}
          </button>
          ${this._suggestions.length > 0
            ? html`<button class="danger" @click=${this._clearSuggestions}>Clear suggestions</button>`
            : ""}
        </div>
        ${this._suggestions.length > 0
          ? html`<div class="suggestions">
              ${this._suggestions.map(
                (s) => html`
                  <div class="suggestion-chip">
                    <span class="name">${s.title || s.name}</span>
                    ${s.grain ? html`<span class="meta">${s.grain}</span>` : ""}
                    <button class="action" title="Accept" @click=${() => this._acceptSuggestion(s.name)}>
                      &#10003;
                    </button>
                    <button class="action" title="Dismiss" @click=${() => this._dismissSuggestion(s.name)}>
                      &#10005;
                    </button>
                  </div>
                `,
              )}
            </div>`
          : ""}
        ${view === "device"
          ? this._renderDeviceFlow()
          : view === "entity"
            ? html`<div class="placeholder">Entity-centric flow (coming soon)</div>`
            : html`<div class="placeholder">Data-centric flow (coming soon)</div>`}
      </shenas-page>
    `;
  }
}

customElements.define("shenas-pipeline-overview", PipelineOverview);
