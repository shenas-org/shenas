import { LitElement, html, css } from "lit";
import cytoscape from "cytoscape";
// The vendor bundle re-exports cytoscape-dagre as `dagre` from "cytoscape".
// @ts-expect-error dagre is provided by the vendor bundle, not the real cytoscape package
import { dagre } from "cytoscape";
import { gql, utilityStyles } from "shenas-frontends";

interface PluginInfo {
  name: string;
  displayName?: string;
  enabled?: boolean;
}

interface Transform {
  id: number;
  sourceDuckdbSchema: string;
  sourceDuckdbTable: string;
  targetDuckdbSchema: string;
  targetDuckdbTable: string;
  sourcePlugin: string;
  description?: string;
  enabled: boolean;
}

interface CyElement {
  data: Record<string, unknown>;
}

let _dagreRegistered = false;

class PipelineOverview extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    allPlugins: { type: Object },
    schemaPlugins: { type: Object },
    _loading: { state: true },
    _empty: { state: true },
  };

  static styles = [
    utilityStyles,
    css`
      :host {
        display: block;
      }
      #cy {
        width: 100%;
        height: calc(100vh - 10rem);
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
    `,
  ];

  declare apiBase: string;
  declare allPlugins: Record<string, PluginInfo[]>;
  declare schemaPlugins: Record<string, string[]>;
  declare _loading: boolean;
  declare _empty: boolean;
  private _cy: cytoscape.Core | null = null;
  private _elements: CyElement[] | null = null;
  private _resizeObserver: ResizeObserver | null = null;

  constructor() {
    super();
    this.apiBase = "/api";
    this.allPlugins = {};
    this.schemaPlugins = {};
    this._loading = true;
    this._empty = false;
  }

  connectedCallback(): void {
    super.connectedCallback();
    this._fetchData();
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

  async _fetchData(): Promise<void> {
    this._loading = true;
    try {
      // Only fetch transforms + dependencies (plugins and schemaPlugins come from parent)
      const data = await gql(
        this.apiBase,
        `{
        transforms { id sourceDuckdbSchema sourceDuckdbTable targetDuckdbSchema targetDuckdbTable sourcePlugin enabled }
        dependencies
      }`,
      );
      const ap = this.allPlugins || {};
      this._buildElements(
        (ap.source || []) as PluginInfo[],
        (ap.dataset || []) as PluginInfo[],
        (data?.transforms || []) as Transform[],
        this.schemaPlugins || {},
        (ap.dashboard || []) as PluginInfo[],
        (data?.dependencies || {}) as Record<string, string[]>,
        (ap.model || []) as PluginInfo[],
      );
    } catch (e) {
      console.error("Failed to fetch overview data:", e);
    }
    this._loading = false;
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

    // Pipe nodes
    for (const p of pipes) {
      const id = `pipe:${p.name}`;
      nodeIds.add(id);
      elements.push({
        data: { id, label: p.displayName || p.name, kind: "source", enabled: p.enabled !== false ? "yes" : "no" },
      });
    }

    // Schema nodes
    for (const s of schemas) {
      const id = `schema:${s.name}`;
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
      const sourceId = `pipe:${t.sourcePlugin}`;
      const ownerPlugin = tableToPlugin[t.targetDuckdbTable];
      const targetId = ownerPlugin ? `schema:${ownerPlugin}` : null;
      if (!targetId || !nodeIds.has(sourceId) || !nodeIds.has(targetId)) continue;
      const desc = t.description || `${t.sourceDuckdbTable} -> ${t.targetDuckdbTable}`;
      const label = desc.length > 30 ? desc.slice(0, 28) + "..." : desc;
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

    this._elements = elements;
    this._empty = elements.filter((e) => e.data.source).length === 0;
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

  firstUpdated(): void {
    if (!this._loading && this._elements) {
      this._initCytoscape();
    }
  }

  updated(changed: Map<string, unknown>): void {
    if (changed.has("_loading") && !this._loading && this._elements) {
      requestAnimationFrame(() => this._initCytoscape());
    }
  }

  render() {
    return html`
      <shenas-page ?loading=${this._loading} loading-text="Loading overview...">
        <div id="cy"></div>
        <div class="legend">
          <span class="legend-item"><span class="legend-dot pipe"></span> Pipe</span>
          <span class="legend-item"><span class="legend-dot schema"></span> Schema</span>
          <span class="legend-item"><span class="legend-dot component"></span> Component</span>
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
      </shenas-page>
    `;
  }
}

customElements.define("shenas-pipeline-overview", PipelineOverview);
