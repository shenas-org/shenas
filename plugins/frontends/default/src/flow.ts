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
import { GET_TRANSFORMS, GET_SUGGESTED_DATASETS, GET_ENTITIES_DATA } from "./graphql/queries.ts";
import { SUGGEST_DATASETS, ACCEPT_DATASET_SUGGESTION, DISMISS_DATASET_SUGGESTION } from "./graphql/mutations.ts";

interface PluginInfo {
  name: string;
  displayName?: string;
  enabled?: boolean;
  entityTypes?: string[];
  entityUuids?: string[];
  tables?: string[];
  totalRows?: number;
}

interface Transform {
  id: number;
  transformType: string;
  source: { id: string; schemaName: string; tableName: string; displayName?: string };
  target: { id: string; schemaName: string; tableName: string; displayName?: string };
  sourcePlugin: string;
  description?: string;
  enabled: boolean;
}

interface FlowEntity {
  uuid: string;
  type: string;
  name: string;
  status: string;
  isMe: boolean;
  sources: string[];
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
        height: calc(100vh - 13rem);
        border: 1px solid var(--shenas-border, #e0e0e0);
        border-radius: 8px;
        background: var(--shenas-bg-secondary, #fafafa);
        box-sizing: border-box;
      }
      .legend {
        display: flex;
        flex-wrap: wrap;
        gap: 0.8rem;
        margin-top: 0.4rem;
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
      .legend-dot.entity {
        background: #78909c;
        border-radius: 50%;
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
      .view-switcher a {
        padding: 0.4rem 1rem;
        border: none;
        background: var(--shenas-bg-secondary, #fafafa);
        color: var(--shenas-text-secondary, #666);
        font-size: 0.8rem;
        cursor: pointer;
        border-right: 1px solid var(--shenas-border, #e0e0e0);
        text-decoration: none;
      }
      .view-switcher a:last-child {
        border-right: none;
      }
      .view-switcher a.active {
        background: var(--shenas-accent, #728f67);
        color: #fff;
      }
      .view-switcher a:not(.active):hover {
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
  declare _empty: boolean;
  declare _view: FlowView;
  declare _suggesting: boolean;
  declare _suggestions: Array<{ name: string; title?: string; grain?: string; tableName?: string }>;
  declare _message: MessageBanner | null;
  private _cy: cytoscape.Core | null = null;
  private _elements: CyElement[] | null = null;
  private _entityFetching = false;
  private _resizeObserver: ResizeObserver | null = null;
  private _client = getClient();

  private _overviewQuery = new ApolloQueryController(this, GET_TRANSFORMS, {
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
    this._empty = false;
    // Derive initial view from URL: /flow/entity, /flow/data, or /flow (device).
    const segment = window.location.pathname.split("/").pop() || "";
    this._view = segment === "entity" || segment === "data" ? segment : "device";
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

  _openPluginPanel(kind: string, name: string): void {
    const panel = document.createElement("shenas-plugin-detail");
    panel.setAttribute("api-base", this.apiBase);
    panel.setAttribute("kind", kind);
    panel.setAttribute("name", name);
    panel.setAttribute("active-tab", "details");
    this.dispatchEvent(
      new CustomEvent("show-panel", { bubbles: true, composed: true, detail: { component: panel, width: 600 } }),
    );
  }

  async _suggest(): Promise<void> {
    this._suggesting = true;
    this._message = null;
    try {
      const { data } = await this._suggestMutation.mutate();
      const payload = data?.suggestDatasets as Record<string, unknown> | undefined;
      if (payload?.ok === false) {
        this._message = { type: "error", text: (payload.error as string) || "Suggestion failed" };
      } else {
        const count = (payload?.suggestions as unknown[])?.length || 0;
        this._message = { type: "success", text: `Generated ${count} suggestion(s)` };
        await this._fetchSuggestions();
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

  private _buildDeviceElements(): void {
    const data = this._overviewQuery.data as Record<string, unknown> | undefined;
    if (!data) return;
    const ap = this.allPlugins || {};
    // Build schema ownership from plugin tables
    const ownership: Record<string, string[]> = {};
    for (const plugins of Object.values(ap)) {
      for (const p of plugins as PluginInfo[]) {
        if (p.tables && p.tables.length > 0) {
          ownership[p.name] = p.tables;
        }
      }
    }
    this._buildElements(
      (ap.source || []) as PluginInfo[],
      (ap.dataset || []) as PluginInfo[],
      (data?.transforms || []) as Transform[],
      ownership,
      (ap.dashboard || []) as PluginInfo[],
      Object.fromEntries(
        ((data?.dependencies || []) as Array<{ source: string; targets: string[] }>).map((d) => [d.source, d.targets]),
      ),
      (ap.model || []) as PluginInfo[],
    );
  }

  _buildElements(
    allSources: PluginInfo[],
    allDatasets: PluginInfo[],
    transforms: Transform[],
    ownership: Record<string, string[]>,
    dashboards: PluginInfo[],
    deps: Record<string, string[]>,
    models: PluginInfo[] = [],
  ): void {
    const elements: CyElement[] = [];
    const nodeIds = new Set<string>();

    // Build reverse lookup: table -> dataset plugin name
    const tableToPlugin: Record<string, string> = {};
    for (const [pluginName, tables] of Object.entries(ownership)) {
      for (const table of tables) {
        tableToPlugin[table] = pluginName;
      }
    }

    // 1. Device node
    const deviceId = "device:local";
    nodeIds.add(deviceId);
    elements.push({ data: { id: deviceId, label: "This Device", kind: "device" } });

    // 2. Sources with data (totalRows > 0) + Device -> Source edges
    const activeSources = new Set<string>();
    for (const source of allSources) {
      if (!source.totalRows || source.totalRows <= 0) continue;
      const id = `source:${source.name}`;
      activeSources.add(source.name);
      nodeIds.add(id);
      elements.push({
        data: {
          id,
          label: source.displayName || source.name,
          kind: "source",
          enabled: source.enabled !== false ? "yes" : "no",
        },
      });
      elements.push({
        data: { id: `edge:device:${source.name}`, source: deviceId, target: id, edgeType: "device" },
      });
    }

    // 3. Datasets connected via transforms from active sources
    const connectedDatasets = new Set<string>();
    const edgePairs = new Set<string>();
    for (const transform of transforms) {
      if (!transform.enabled || !activeSources.has(transform.sourcePlugin)) continue;
      const ownerPlugin = tableToPlugin[transform.target.tableName];
      if (!ownerPlugin) continue;
      const sourceId = `source:${transform.sourcePlugin}`;
      const datasetId = `dataset:${ownerPlugin}`;
      const pair = `${sourceId}:${datasetId}`;
      if (edgePairs.has(pair)) continue;
      edgePairs.add(pair);
      if (!nodeIds.has(datasetId)) {
        const dataset = allDatasets.find((d) => d.name === ownerPlugin);
        nodeIds.add(datasetId);
        elements.push({
          data: {
            id: datasetId,
            label: dataset?.displayName || ownerPlugin,
            kind: "dataset",
            enabled: dataset?.enabled !== false ? "yes" : "no",
          },
        });
      }
      connectedDatasets.add(ownerPlugin);
      elements.push({
        data: { id: `transform:${pair}`, source: sourceId, target: datasetId, edgeType: "transform" },
      });
    }

    // 4. Dashboards and models that depend on connected datasets
    for (const consumer of [...dashboards, ...models]) {
      const kind = dashboards.includes(consumer) ? "dashboard" : "model";
      const consumerId = `${kind}:${consumer.name}`;
      const depTargets = deps[consumerId] || [];
      let added = false;
      for (const target of depTargets) {
        const datasetName = target.replace("dataset:", "");
        if (!connectedDatasets.has(datasetName)) continue;
        if (!added) {
          nodeIds.add(consumerId);
          elements.push({
            data: {
              id: consumerId,
              label: consumer.displayName || consumer.name,
              kind,
              enabled: consumer.enabled !== false ? "yes" : "no",
            },
          });
          added = true;
        }
        elements.push({
          data: { id: `dep:${target}:${consumerId}`, source: target, target: consumerId, edgeType: "dependency" },
        });
      }
    }

    this._elements = elements;
    this._empty = activeSources.size === 0;
  }

  private async _fetchEntityFlow(): Promise<void> {
    const { data } = await this._client.query({ query: GET_ENTITIES_DATA, fetchPolicy: "network-only" });
    const all = (data?.entities || []) as FlowEntity[];
    const entities = all.filter((entity) => entity.isMe || entity.status === "enabled");
    const relationships = (data?.entityRelationships || []) as Array<{
      fromUuid: string;
      toUuid: string;
      type: string;
    }>;
    this._buildEntityElements(entities, relationships);
    this.requestUpdate();
  }

  private _buildEntityElements(
    entities: FlowEntity[],
    relationships: Array<{ fromUuid: string; toUuid: string; type: string }> = [],
  ): void {
    const ap = this.allPlugins || {};
    const sources = (ap.source || []) as PluginInfo[];
    const datasets = (ap.dataset || []) as PluginInfo[];

    const elements: CyElement[] = [];
    const nodeIds = new Set<string>();
    const edgeIds = new Set<string>();

    // Index entities by UUID for lookup.
    const entityByUuid = new Map(entities.map((entity) => [entity.uuid, entity]));

    // Collect entity UUIDs referenced by any plugin.
    const referencedUuids = new Set<string>();
    for (const plugin of [...sources, ...datasets]) {
      for (const uuid of plugin.entityUuids || []) referencedUuids.add(uuid);
    }

    // Entity nodes (center column) -- only entities referenced by a plugin.
    for (const uuid of referencedUuids) {
      const entity = entityByUuid.get(uuid);
      if (!entity) continue;
      const id = `entity:${uuid}`;
      const label = entity.isMe ? "Me" : entity.name;
      nodeIds.add(id);
      elements.push({ data: { id, label, kind: "entity", entityType: entity.type, isMe: entity.isMe ? "yes" : "no" } });
    }

    const addEdge = (edgeId: string, source: string, target: string, edgeType: string) => {
      if (edgeIds.has(edgeId)) return;
      edgeIds.add(edgeId);
      elements.push({ data: { id: edgeId, source, target, edgeType } });
    };

    // Source "is about" Entity -- arrow points from source to entity.
    for (const source of sources) {
      for (const uuid of source.entityUuids || []) {
        if (!nodeIds.has(`entity:${uuid}`)) continue;
        const sourceId = `source:${source.name}`;
        if (!nodeIds.has(sourceId)) {
          nodeIds.add(sourceId);
          elements.push({
            data: {
              id: sourceId,
              label: source.displayName || source.name,
              kind: "source",
              enabled: source.enabled !== false ? "yes" : "no",
            },
          });
        }
        addEdge(`edge:${sourceId}:entity:${uuid}`, sourceId, `entity:${uuid}`, "entity");
      }
    }

    // Dataset "is about" Entity -- arrow points from dataset to entity.
    for (const dataset of datasets) {
      const datasetId = `dataset:${dataset.name}`;
      let added = false;
      for (const uuid of dataset.entityUuids || []) {
        if (!nodeIds.has(`entity:${uuid}`)) continue;
        if (!added) {
          nodeIds.add(datasetId);
          elements.push({
            data: {
              id: datasetId,
              label: dataset.displayName || dataset.name,
              kind: "dataset",
              enabled: dataset.enabled !== false ? "yes" : "no",
            },
          });
          added = true;
        }
        addEdge(`edge:${datasetId}:entity:${uuid}`, datasetId, `entity:${uuid}`, "entity");
      }
    }

    // Dataset "is about" Source -- arrow from dataset to source via transforms.
    const overviewData = this._overviewQuery.data as Record<string, unknown> | undefined;
    const transforms = (overviewData?.transforms || []) as Transform[];
    // Build dataset table -> dataset plugin lookup.
    const tableToDataset = new Map<string, string>();
    for (const dataset of datasets) {
      for (const table of dataset.tables || []) tableToDataset.set(table, dataset.name);
    }
    for (const transform of transforms) {
      if (!transform.enabled) continue;
      const datasetName = tableToDataset.get(transform.target.tableName);
      if (!datasetName) continue;
      const datasetId = `dataset:${datasetName}`;
      if (!nodeIds.has(datasetId)) continue;
      const sourceId = `source:${transform.sourcePlugin}`;
      if (!nodeIds.has(sourceId)) {
        const info = sources.find((source) => source.name === transform.sourcePlugin);
        nodeIds.add(sourceId);
        elements.push({
          data: {
            id: sourceId,
            label: info?.displayName || transform.sourcePlugin,
            kind: "source",
            enabled: info?.enabled !== false ? "yes" : "no",
          },
        });
      }
      addEdge(`edge:${datasetId}:${sourceId}`, datasetId, sourceId, "transform");
    }

    // Entity-to-entity relationship edges.
    for (const rel of relationships) {
      const fromId = `entity:${rel.fromUuid}`;
      const toId = `entity:${rel.toUuid}`;
      if (nodeIds.has(fromId) && nodeIds.has(toId)) {
        addEdge(`rel:${rel.fromUuid}:${rel.toUuid}:${rel.type}`, fromId, toId, "relationship");
      }
    }

    this._elements = elements;
    this._empty = referencedUuids.size === 0;
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
            "font-size": this._view === "entity" ? 9 : 12,
            color: "#fff",
            "text-wrap": "wrap",
            "text-max-width": this._view === "entity" ? 80 : 100,
            width: this._view === "entity" ? 90 : 120,
            height: this._view === "entity" ? 30 : 40,
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
          selector: 'node[kind="entity"]',
          style: {
            "background-color": "#78909c",
            shape: "ellipse",
            width: 80,
            height: 35,
            "font-weight": "bold",
            cursor: "pointer",
          },
        },
        {
          selector: 'node[isMe="yes"]',
          style: {
            "background-color": "#546e7a",
            width: 100,
            height: 45,
            "font-size": 12,
            "border-width": 3,
            "border-color": "#37474f",
          },
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
            width: this._view === "entity" ? 1 : 2,
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
        {
          selector: 'edge[edgeType="entity"]',
          style: {
            "line-style": "solid",
            "line-color": "#78909c",
            "target-arrow-color": "#78909c",
            width: 2,
            label: "",
          },
        },
        {
          selector: 'edge[edgeType="transform"]',
          style: {
            "line-style": "dashed",
            "line-color": "#66bb6a",
            "target-arrow-color": "#66bb6a",
            width: 1.5,
            label: "",
          },
        },
        {
          selector: 'edge[edgeType="relationship"]',
          style: {
            "line-style": "solid",
            "line-color": "#b0bec5",
            "target-arrow-color": "#b0bec5",
            width: 1.5,
            label: "",
          },
        },
      ] as unknown as cytoscape.StylesheetStyle[],
      layout: (this._view === "entity"
        ? {
            name: "cose",
            boundingBox: container
              ? { x1: 0, y1: 0, w: container.clientWidth - 60, h: container.clientHeight - 60 }
              : undefined,
            idealEdgeLength: 100,
            nodeOverlap: 40,
            nodeRepulsion: 60000,
            gravity: 0.1,
            numIter: 2000,
            padding: 30,
            animate: false,
            fit: true,
          }
        : {
            name: "dagre",
            rankDir: "LR",
            nodeSep: 60,
            rankSep: 150,
            padding: 30,
          }) as unknown as cytoscape.LayoutOptions,
      userZoomingEnabled: true,
      userPanningEnabled: true,
      boxSelectionEnabled: false,
    });

    this._cy.on("tap", "node", (evt) => {
      const data = evt.target.data() as Record<string, string>;
      const name = data.id.substring(data.id.indexOf(":") + 1);
      const kind = data.kind as string | undefined;
      if (!kind || !name) return;
      this._openPluginPanel(kind, name);
    });

    this._cy.on("tap", "edge", (evt) => {
      const plugin = evt.target.data("sourcePlugin") as string | undefined;
      if (plugin) {
        this._openPluginPanel("source", plugin);
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
    this._entityFetching = false;
    if (this._cy) {
      this._cy.destroy();
      this._cy = null;
    }
    const path = view === "device" ? "/flow" : `/flow/${view}`;
    window.history.replaceState({}, "", path);
  }

  updated(): void {
    if (this._view === "entity" && !this._elements && !this._entityFetching) {
      this._entityFetching = true;
      this._fetchEntityFlow().finally(() => {
        this._entityFetching = false;
      });
      return;
    }
    if (!this._loading && !this._elements) {
      if (this._view === "device") this._buildDeviceElements();
      else if (this._view === "data") this._buildDataElements();
    }
    if (this._elements) {
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

  private _buildDataElements(): void {
    const ap = this.allPlugins || {};
    const allPluginsList = Object.values(ap).flat() as PluginInfo[];
    const data = this._overviewQuery.data as Record<string, unknown> | undefined;
    const transforms = (data?.transforms || []) as Transform[];

    const elements: CyElement[] = [];
    const nodeIds = new Set<string>();

    // Plugin name -> display name lookup for badge labels.
    const pluginDisplayName = new Map(allPluginsList.map((plugin) => [plugin.name, plugin.displayName || plugin.name]));

    // Determine table kind (source vs dataset) from schema.
    const tableKind = (schemaName: string) => (schemaName === "datasets" ? "dataset" : "source");

    const ensureTableNode = (
      tableName: string,
      displayName: string | undefined,
      schemaName: string,
      pluginName: string,
    ) => {
      const id = `table:${tableName}`;
      if (nodeIds.has(id)) return id;
      nodeIds.add(id);
      const pluginLabel = pluginDisplayName.get(pluginName) || pluginName;
      const shortName = displayName || tableName.replace(/^[^_]+__/, "");
      const label = `${shortName}\n(${pluginLabel})`;
      elements.push({ data: { id, label, kind: tableKind(schemaName) } });
      return id;
    };

    // Build target table -> dataset plugin lookup from table ownership.
    const tableToDataset = new Map<string, string>();
    for (const plugin of allPluginsList) {
      for (const table of plugin.tables || []) tableToDataset.set(table, plugin.name);
    }

    // Transform edges: source table -> target table.
    for (const transform of transforms) {
      if (!transform.enabled) continue;
      const targetPlugin = tableToDataset.get(transform.target.tableName) || "";
      const sourceId = ensureTableNode(
        transform.source.tableName,
        transform.source.displayName,
        transform.source.schemaName,
        transform.sourcePlugin,
      );
      const targetId = ensureTableNode(
        transform.target.tableName,
        transform.target.displayName,
        transform.target.schemaName,
        targetPlugin,
      );
      elements.push({
        data: {
          id: `transform:${transform.id}`,
          source: sourceId,
          target: targetId,
          edgeType: "transform",
          enabled: "yes",
        },
      });
    }

    // Dashboard/model nodes connected to dataset tables via dependencies.
    const deps = Object.fromEntries(
      ((data?.dependencies || []) as Array<{ source: string; targets: string[] }>).map((d) => [d.source, d.targets]),
    );
    const dashboards = (ap.dashboard || []) as PluginInfo[];
    const models = (ap.model || []) as PluginInfo[];
    // Build dataset plugin -> table nodes lookup from what we've created.
    const datasetPluginTables = new Map<string, string[]>();
    for (const id of nodeIds) {
      const tableName = id.replace("table:", "");
      const datasetPlugin = tableToDataset.get(tableName);
      if (datasetPlugin) {
        const list = datasetPluginTables.get(datasetPlugin) || [];
        list.push(id);
        datasetPluginTables.set(datasetPlugin, list);
      }
    }
    for (const consumer of [...dashboards, ...models]) {
      const kind = dashboards.includes(consumer) ? "dashboard" : "model";
      const consumerId = `${kind}:${consumer.name}`;
      const depTargets = deps[consumerId] || [];
      let added = false;
      for (const depTarget of depTargets) {
        const datasetName = depTarget.replace("dataset:", "");
        for (const tableNodeId of datasetPluginTables.get(datasetName) || []) {
          if (!added) {
            nodeIds.add(consumerId);
            elements.push({
              data: {
                id: consumerId,
                label: consumer.displayName || consumer.name,
                kind,
                enabled: consumer.enabled !== false ? "yes" : "no",
              },
            });
            added = true;
          }
          elements.push({
            data: {
              id: `dep:${tableNodeId}:${consumerId}`,
              source: tableNodeId,
              target: consumerId,
              edgeType: "dependency",
            },
          });
        }
      }
    }

    this._elements = elements;
    this._empty = elements.filter((e) => e.data.source).length === 0;
  }

  private _renderEntityFlow() {
    return html`
      <div id="cy"></div>
      <div class="legend">
        <span class="legend-item"
          ><span class="legend-dot" style="background:#78909c;border-radius:50%"></span> Entity</span
        >
        <span class="legend-item"><span class="legend-dot pipe"></span> Source</span>
        <span class="legend-item"><span class="legend-dot schema"></span> Dataset</span>
        <span class="legend-item"><span class="legend-dot component"></span> Dashboard</span>
        <span class="legend-item"><span class="legend-dot model"></span> Model</span>
      </div>
      ${this._empty
        ? html`<p class="empty">No entity types declared. Sources and datasets declare entity_types.</p>`
        : ""}
    `;
  }

  private _renderDataFlow() {
    return html`
      <div id="cy"></div>
      <div class="legend">
        <span class="legend-item"><span class="legend-dot" style="background:#4a90d9"></span> Source table</span>
        <span class="legend-item"><span class="legend-dot" style="background:#66bb6a"></span> Dataset table</span>
        <span class="legend-item"><span class="legend-dot" style="background:#ffa726"></span> Dashboard</span>
        <span class="legend-item"><span class="legend-dot" style="background:#ab47bc"></span> Model</span>
        <span class="legend-item"><span class="legend-line enabled"></span> Transform</span>
        <span class="legend-item"
          ><span
            class="legend-line"
            style="border-top:2px dotted var(--shenas-text-faint, #aaa);height:0;background:none"
          ></span>
          Dependency</span
        >
      </div>
      ${this._empty
        ? html`<p class="empty">No transforms found. Add transforms to connect source tables to dataset tables.</p>`
        : ""}
    `;
  }

  render() {
    const view = this._view;
    return html`
      <shenas-page ?loading=${view === "device" && this._loading} loading-text="Loading overview...">
        ${renderMessage(this._message)}
        <div class="view-switcher">
          <a
            href="/flow"
            class=${view === "device" ? "active" : ""}
            @click=${(e: Event) => {
              e.preventDefault();
              this._setView("device");
            }}
            >Device-centric</a
          >
          <a
            href="/flow/entity"
            class=${view === "entity" ? "active" : ""}
            @click=${(e: Event) => {
              e.preventDefault();
              this._setView("entity");
            }}
            >Entity-centric</a
          >
          <a
            href="/flow/data"
            class=${view === "data" ? "active" : ""}
            @click=${(e: Event) => {
              e.preventDefault();
              this._setView("data");
            }}
            >Data-centric</a
          >
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
            ? this._renderEntityFlow()
            : this._renderDataFlow()}
      </shenas-page>
    `;
  }
}

customElements.define("shenas-pipeline-overview", PipelineOverview);
