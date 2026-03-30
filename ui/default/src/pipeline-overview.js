import { LitElement, html, css } from "lit";
import cytoscape, { dagre } from "cytoscape";
import { utilityStyles } from "./shared-styles.js";

let _dagreRegistered = false;

class PipelineOverview extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    _loading: { state: true },
    _empty: { state: true },
  };

  static styles = [
    utilityStyles,
    css`
      :host {
        display: flex;
        flex-direction: column;
        height: 100%;
      }
      #cy {
        width: 100%;
        flex: 1;
        min-height: 200px;
        border: 1px solid var(--shenas-border, #e0e0e0);
        border-radius: 8px;
        background: var(--shenas-bg-secondary, #fafafa);
        box-sizing: border-box;
      }
      .legend {
        display: flex;
        gap: 1.5rem;
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
      .legend-dot.pipe { background: var(--shenas-node-pipe, #4a90d9); }
      .legend-dot.schema { background: var(--shenas-node-schema, #66bb6a); }
      .legend-dot.component { background: var(--shenas-node-component, #ffa726); }
      .legend-line {
        width: 20px;
        height: 2px;
      }
      .legend-line.enabled { background: var(--shenas-text-muted, #888); }
      .legend-line.disabled { background: var(--shenas-text-faint, #aaa); border-top: 2px dashed var(--shenas-text-faint, #aaa); height: 0; }
    `,
  ];

  constructor() {
    super();
    this.apiBase = "/api";
    this._loading = true;
    this._empty = false;
    this._cy = null;
    this._elements = null;
    this._resizeObserver = null;
  }

  connectedCallback() {
    super.connectedCallback();
    this._fetchData();
  }

  disconnectedCallback() {
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

  async _fetchData() {
    this._loading = true;
    try {
      const [pipesResp, schemasResp, transformsResp, ownershipResp, componentsResp, depsResp] = await Promise.all([
        fetch(`${this.apiBase}/plugins/pipe`),
        fetch(`${this.apiBase}/plugins/schema`),
        fetch(`${this.apiBase}/transforms`),
        fetch(`${this.apiBase}/db/schema-plugins`),
        fetch(`${this.apiBase}/plugins/component`),
        fetch(`${this.apiBase}/dependencies`),
      ]);
      const pipes = pipesResp.ok ? await pipesResp.json() : [];
      const schemas = schemasResp.ok ? await schemasResp.json() : [];
      const transforms = transformsResp.ok ? await transformsResp.json() : [];
      const ownership = ownershipResp.ok ? await ownershipResp.json() : {};
      const components = componentsResp.ok ? await componentsResp.json() : [];
      const deps = depsResp.ok ? await depsResp.json() : {};
      this._buildElements(pipes, schemas, transforms, ownership, components, deps);
    } catch (e) {
      console.error("Failed to fetch overview data:", e);
    }
    this._loading = false;
  }

  _buildElements(pipes, schemas, transforms, ownership, components, deps) {
    const elements = [];
    const nodeIds = new Set();

    // Build reverse lookup: table -> schema plugin name
    const tableToPlugin = {};
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
        data: { id, label: p.display_name || p.name, kind: "pipe", enabled: p.enabled !== false ? "yes" : "no" },
      });
    }

    // Schema nodes
    for (const s of schemas) {
      const id = `schema:${s.name}`;
      nodeIds.add(id);
      elements.push({
        data: { id, label: s.display_name || s.name, kind: "schema", enabled: s.enabled !== false ? "yes" : "no" },
      });
    }

    // Component nodes
    for (const c of components) {
      const id = `component:${c.name}`;
      nodeIds.add(id);
      elements.push({
        data: { id, label: c.display_name || c.name, kind: "component", enabled: c.enabled !== false ? "yes" : "no" },
      });
    }

    // Transform edges (pipe -> schema via data)
    for (const t of transforms) {
      const sourceId = `pipe:${t.source_plugin}`;
      const ownerPlugin = tableToPlugin[t.target_duckdb_table];
      const targetId = ownerPlugin ? `schema:${ownerPlugin}` : null;
      if (!targetId || !nodeIds.has(sourceId) || !nodeIds.has(targetId)) continue;
      const desc = t.description || `${t.source_duckdb_table} -> ${t.target_duckdb_table}`;
      const label = desc.length > 30 ? desc.slice(0, 28) + "..." : desc;
      elements.push({
        data: {
          id: `transform:${t.id}`,
          source: sourceId,
          target: targetId,
          label,
          enabled: t.enabled ? "yes" : "no",
          sourcePlugin: t.source_plugin,
          edgeType: "transform",
        },
      });
    }

    // Track which pipe->schema pairs already have transform edges
    const transformPairs = new Set();
    for (const el of elements) {
      if (el.data.edgeType === "transform") {
        transformPairs.add(`${el.data.source}:${el.data.target}`);
      }
    }

    // Dependency edges (from package metadata)
    const depEdgeIds = new Set();
    for (const [depSource, targets] of Object.entries(deps)) {
      for (const depTarget of targets) {
        const sourceKind = depSource.split(":")[0];
        let edgeSource, edgeTarget;
        if (sourceKind === "component") {
          // Component depends on schema -> show as schema -> component
          edgeSource = depTarget;
          edgeTarget = depSource;
        } else {
          edgeSource = depSource;
          edgeTarget = depTarget;
        }
        if (!nodeIds.has(edgeSource) || !nodeIds.has(edgeTarget)) continue;
        // Skip pipe->schema dep edges when transforms already connect them
        if (sourceKind === "pipe" && transformPairs.has(`${edgeSource}:${edgeTarget}`)) continue;
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

  _initCytoscape() {
    const container = this.renderRoot.querySelector("#cy");
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
          selector: 'node[kind="pipe"]',
          style: { "background-color": "#4a90d9", "cursor": "pointer" },
        },
        {
          selector: 'node[kind="schema"]',
          style: { "background-color": "#66bb6a", "cursor": "pointer" },
        },
        {
          selector: 'node[kind="component"]',
          style: { "background-color": "#ffa726", "cursor": "pointer" },
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
            "cursor": "pointer",
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
      ],
      layout: {
        name: "dagre",
        rankDir: "LR",
        nodeSep: 60,
        rankSep: 150,
        padding: 30,
      },
      userZoomingEnabled: true,
      userPanningEnabled: true,
      boxSelectionEnabled: false,
    });

    this._cy.on("tap", "node", (evt) => {
      const data = evt.target.data();
      const name = data.id.substring(data.id.indexOf(":") + 1);
      let path;
      if (data.kind === "pipe") path = `/settings/pipe/${name}`;
      else if (data.kind === "schema") path = `/settings/schema/${name}`;
      else if (data.kind === "component") path = `/settings/component/${name}`;
      else return;
      this.dispatchEvent(new CustomEvent("navigate", { bubbles: true, composed: true, detail: { path } }));
    });

    this._cy.on("tap", "edge", (evt) => {
      const plugin = evt.target.data("sourcePlugin");
      if (plugin) {
        this.dispatchEvent(new CustomEvent("navigate", { bubbles: true, composed: true, detail: { path: `/settings/pipe/${plugin}` } }));
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

  firstUpdated() {
    if (!this._loading && this._elements) {
      this._initCytoscape();
    }
  }

  updated(changed) {
    if (changed.has("_loading") && !this._loading && this._elements) {
      requestAnimationFrame(() => this._initCytoscape());
    }
  }

  render() {
    if (this._loading) {
      return html`<p class="loading">Loading overview...</p>`;
    }

    return html`
      <div id="cy"></div>
      <div class="legend">
        <span class="legend-item"><span class="legend-dot pipe"></span> Pipe</span>
        <span class="legend-item"><span class="legend-dot schema"></span> Schema</span>
        <span class="legend-item"><span class="legend-dot component"></span> Component</span>
        <span class="legend-item"><span class="legend-line enabled"></span> Transform</span>
        <span class="legend-item"><span class="legend-line disabled"></span> Disabled</span>
        <span class="legend-item"><span class="legend-line" style="border-top:2px dotted var(--shenas-text-faint, #aaa);height:0;background:none"></span> Dependency</span>
      </div>
      ${this._empty ? html`<p class="empty">No connections found. Add transforms in pipe settings.</p>` : ""}
    `;
  }
}

customElements.define("shenas-pipeline-overview", PipelineOverview);
