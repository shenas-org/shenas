import { LitElement, html, css } from "lit";
import cytoscape from "cytoscape";
// The vendor bundle re-exports cytoscape-dagre as `dagre` from "cytoscape".
// @ts-expect-error dagre is provided by the vendor bundle, not the real cytoscape package
import { dagre } from "cytoscape";
import {
  ApolloQueryController,
  ApolloMutationController,
  getClient,
  buttonStyles,
  formStyles,
  messageStyles,
  tableStyles,
  renderMessage,
} from "shenas-frontends";
import { GET_ENTITIES_DATA } from "./graphql/queries.ts";
import {
  CREATE_ENTITY,
  UPDATE_ENTITY,
  DELETE_ENTITY,
  CREATE_ENTITY_RELATIONSHIP,
  DELETE_ENTITY_RELATIONSHIP,
  SET_ENTITY_STATUS,
} from "./graphql/mutations.ts";

interface Entity {
  uuid: string;
  type: string;
  name: string;
  description: string;
  status: string;
  isMe: boolean;
}

interface EntityTypeInfo {
  name: string;
  displayName: string;
  description: string;
  icon: string;
  parent: string | null;
  isAbstract: boolean;
}

type GraphView = "entities" | "types";

interface EntityRelationshipRow {
  fromUuid: string;
  toUuid: string;
  type: string;
  description: string;
}

interface RelationshipTypeInfo {
  name: string;
  displayName: string;
  inverseName: string | null;
  isSymmetric: boolean;
}

interface EntityForm {
  name: string;
  type: string;
  description: string;
  /** When set, the user picked an existing disabled entity instead of creating one. */
  pickedUuid: string | null;
}

interface RelationshipForm {
  fromUuid: string;
  toUuid: string;
  type: string;
}

interface Message {
  type: string;
  text: string;
}

interface CyElement {
  data: Record<string, unknown>;
  selectable?: boolean;
  grabbable?: boolean;
}

let _dagreRegistered = false;

class EntitiesPage extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    activeView: { type: String, attribute: "active-view" },
    _message: { state: true },
    _view: { state: true },
  };

  static styles = [
    tableStyles,
    buttonStyles,
    formStyles,
    messageStyles,
    css`
      :host {
        display: block;
      }
      #cy {
        width: 100%;
        height: max(320px, 50vh);
        border: 1px solid var(--shenas-border, #d8d4cc);
        border-radius: 8px;
        background: var(--shenas-bg-secondary, #f3f0eb);
        box-sizing: border-box;
        margin-bottom: 1.5rem;
      }
      .empty-graph {
        display: flex;
        align-items: center;
        justify-content: center;
        height: max(320px, 50vh);
        color: var(--shenas-text-faint, #888);
        font-size: 0.9rem;
      }
      .section {
        margin-top: 1.5rem;
      }
      .section h3 {
        margin: 0 0 0.6rem;
        font-size: 1rem;
        font-weight: 600;
      }
      table {
        margin-top: 0.4rem;
      }
      td .row-actions {
        display: flex;
        gap: 0.3rem;
        justify-content: flex-end;
      }
      .me-badge {
        display: inline-block;
        padding: 1px 6px;
        border-radius: 3px;
        background: var(--shenas-accent-soft, #e8efe4);
        color: var(--shenas-primary, #728f67);
        font-size: 0.7rem;
        font-weight: 600;
        margin-left: 0.4rem;
      }
      .view-toggle {
        display: flex;
        gap: 2px;
        justify-content: flex-end;
        margin-bottom: 0.4rem;
      }
      .view-toggle button {
        background: none;
        border: 1px solid var(--shenas-border, #ddd);
        border-radius: 3px;
        padding: 4px 10px;
        cursor: pointer;
        color: var(--shenas-text-muted, #999);
        font-size: 0.75rem;
        line-height: 1;
      }
      .view-toggle button:hover {
        background: var(--shenas-bg-secondary, #f0f0f0);
        color: var(--shenas-text, #555);
      }
      .view-toggle button[aria-pressed="true"] {
        background: var(--shenas-primary, #728f67);
        color: #fff;
        border-color: var(--shenas-primary, #728f67);
      }
    `,
  ];

  declare apiBase: string;
  declare activeView: string;
  declare _message: Message | null;
  declare _view: GraphView;

  private _cy: cytoscape.Core | null = null;
  private _resizeObserver: ResizeObserver | null = null;

  private _entitiesQuery = new ApolloQueryController(this, GET_ENTITIES_DATA, { client: getClient() });
  private _createEntityMutation = new ApolloMutationController(this, CREATE_ENTITY, { client: getClient() });
  private _updateEntityMutation = new ApolloMutationController(this, UPDATE_ENTITY, { client: getClient() });
  private _deleteEntityMutation = new ApolloMutationController(this, DELETE_ENTITY, { client: getClient() });
  private _setEntityStatusMutation = new ApolloMutationController(this, SET_ENTITY_STATUS, { client: getClient() });
  private _createRelMutation = new ApolloMutationController(this, CREATE_ENTITY_RELATIONSHIP, { client: getClient() });
  private _deleteRelMutation = new ApolloMutationController(this, DELETE_ENTITY_RELATIONSHIP, { client: getClient() });

  get _loading(): boolean {
    return this._entitiesQuery.loading;
  }

  get _entities(): Entity[] {
    return ((this._entitiesQuery.data as Record<string, unknown>)?.entities as Entity[]) || [];
  }

  get _relationships(): EntityRelationshipRow[] {
    return (
      ((this._entitiesQuery.data as Record<string, unknown>)?.entityRelationships as EntityRelationshipRow[]) || []
    );
  }

  get _entityTypes(): EntityTypeInfo[] {
    return ((this._entitiesQuery.data as Record<string, unknown>)?.entityTypes as EntityTypeInfo[]) || [];
  }

  get _relationshipTypes(): RelationshipTypeInfo[] {
    return (
      ((this._entitiesQuery.data as Record<string, unknown>)?.entityRelationshipTypes as RelationshipTypeInfo[]) || []
    );
  }

  // The DOM element currently hosted in the right panel (create/edit entity
  // or create relationship). Tracked so save/cancel handlers can update it
  // in place and close the panel when done.
  private _panelEl: HTMLDivElement | null = null;

  constructor() {
    super();
    this._message = null;
    this._view = "entities";
    this.activeView = "";
  }

  willUpdate(changed: Map<string, unknown>): void {
    if (changed.has("activeView")) {
      this._view = this.activeView === "types" ? "types" : "entities";
    }
  }

  _setView(v: GraphView): void {
    this.dispatchEvent(
      new CustomEvent("navigate", {
        bubbles: true,
        composed: true,
        detail: { path: v === "types" ? "/settings/entities/types" : "/settings/entities" },
      }),
    );
  }

  _emptyEntityForm(): EntityForm {
    return { name: "", type: "animal", description: "", pickedUuid: null };
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

  _meUuid(): string | null {
    const me = this._entities.find((e) => e.isMe);
    return me ? me.uuid : null;
  }

  _entityByUuid(uuid: string): Entity | undefined {
    return this._entities.find((e) => e.uuid === uuid);
  }

  _typeDisplayName(name: string): string {
    const t = this._entityTypes.find((x) => x.name === name);
    return t ? t.displayName : name;
  }

  _relTypeDisplayName(name: string): string {
    const t = this._relationshipTypes.find((x) => x.name === name);
    return t ? t.displayName : name;
  }

  // -- CRUD: entity panel -------------------------------------------------

  /** Disabled entities of ``type`` that the user hasn't yet included in the graph. */
  _disabledOfType(type: string): Entity[] {
    return this._entities.filter((e) => e.type === type && e.status === "disabled" && !e.isMe);
  }

  /** Open the right panel to create a new entity, or edit ``entity`` if given.
   *
   * Create flow:
   *   1. Pick a type.
   *   2. If any disabled entities of that type exist, the Name row becomes
   *      a dropdown of those plus a "Create new..." option; otherwise it's
   *      a freetext input.
   *   3. Picking an existing row flips its status to enabled via
   *      setEntityStatus; typing a new name routes through createEntity.
   */
  _openEntityPanel(entity?: Entity): void {
    const isEdit = !!entity;
    const form: EntityForm = entity
      ? {
          name: entity.name,
          type: entity.type,
          description: entity.description,
          pickedUuid: null,
        }
      : this._emptyEntityForm();

    const typeOptions = this._entityTypes
      .map(
        (t) =>
          `<option value="${t.name}"${t.name === form.type ? " selected" : ""}>${this._escape(t.displayName)}</option>`,
      )
      .join("");

    const panel = document.createElement("div");
    panel.style.padding = "1rem";
    panel.innerHTML = `
      <h3 style="margin-top:0">${isEdit ? `Edit ${this._escape(entity!.name)}` : "Add entity"}</h3>
      <label style="display:block;margin-bottom:0.6rem">
        Type<br/>
        <select id="f-type" style="width:100%">${typeOptions}</select>
      </label>
      <div id="name-row"></div>
      <label style="display:block;margin-bottom:0.6rem">
        Description<br/>
        <input id="f-desc" type="text" style="width:100%" value="${this._escape(form.description)}" />
      </label>
      <div style="display:flex;gap:0.5rem;margin-top:1rem">
        <button id="save-btn">${isEdit ? "Save" : "Add"}</button>
        <button id="cancel-btn">Cancel</button>
      </div>
    `;

    const current: EntityForm = { ...form };

    const renderNameRow = () => {
      const row = panel.querySelector("#name-row") as HTMLDivElement;
      if (isEdit) {
        // Edit mode: always a text field bound to the entity's current name.
        row.innerHTML = `
          <label style="display:block;margin-bottom:0.6rem">
            Name<br/>
            <input id="f-name" type="text" style="width:100%" value="${this._escape(current.name)}" />
          </label>
        `;
        row.querySelector("#f-name")?.addEventListener("input", (e) => {
          current.name = (e.target as HTMLInputElement).value;
          current.pickedUuid = null;
        });
        return;
      }
      const candidates = this._disabledOfType(current.type);
      if (candidates.length === 0) {
        row.innerHTML = `
          <label style="display:block;margin-bottom:0.6rem">
            Name<br/>
            <input id="f-name" type="text" style="width:100%" value="${this._escape(current.name)}" />
          </label>
        `;
        row.querySelector("#f-name")?.addEventListener("input", (e) => {
          current.name = (e.target as HTMLInputElement).value;
          current.pickedUuid = null;
        });
        return;
      }
      // Have disabled candidates: show a dropdown + "Create new..." sentinel.
      const SENTINEL = "__new__";
      const options = candidates.map((c) => `<option value="${c.uuid}">${this._escape(c.name)}</option>`).join("");
      row.innerHTML = `
        <label style="display:block;margin-bottom:0.6rem">
          Name<br/>
          <select id="f-pick" style="width:100%">
            <option value="" selected disabled>Pick an existing ${this._escape(this._typeDisplayName(current.type))}...</option>
            ${options}
            <option value="${SENTINEL}">Create new...</option>
          </select>
          <input
            id="f-name"
            type="text"
            style="width:100%;margin-top:0.4rem;display:none"
            placeholder="New ${this._escape(this._typeDisplayName(current.type))} name"
            value=""
          />
        </label>
      `;
      current.name = "";
      current.pickedUuid = null;
      const nameInput = row.querySelector("#f-name") as HTMLInputElement;
      row.querySelector("#f-pick")?.addEventListener("change", (e) => {
        const value = (e.target as HTMLSelectElement).value;
        if (value === SENTINEL) {
          nameInput.style.display = "block";
          nameInput.focus();
          current.pickedUuid = null;
          current.name = nameInput.value;
        } else {
          nameInput.style.display = "none";
          const match = candidates.find((c) => c.uuid === value);
          current.pickedUuid = value || null;
          current.name = match?.name ?? "";
        }
      });
      nameInput.addEventListener("input", (e) => {
        current.name = (e.target as HTMLInputElement).value;
        current.pickedUuid = null;
      });
    };

    renderNameRow();

    panel.querySelector("#f-desc")?.addEventListener("input", (e) => {
      current.description = (e.target as HTMLInputElement).value;
    });
    panel.querySelector("#f-type")?.addEventListener("change", (e) => {
      current.type = (e.target as HTMLSelectElement).value;
      // Rebuild the name row since candidates depend on the type.
      renderNameRow();
    });
    panel.querySelector("#save-btn")?.addEventListener("click", () => {
      if (isEdit) void this._saveEntityEdit(entity!.uuid, current);
      else void this._saveEntityCreate(current);
    });
    panel.querySelector("#cancel-btn")?.addEventListener("click", () => this._closePanel());

    this._panelEl = panel;
    this.dispatchEvent(
      new CustomEvent("show-panel", { bubbles: true, composed: true, detail: { component: panel, width: 420 } }),
    );
  }

  _closePanel(): void {
    this._panelEl = null;
    this.dispatchEvent(new CustomEvent("close-panel", { bubbles: true, composed: true }));
  }

  _escape(s: string): string {
    return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);
  }

  async _saveEntityCreate(form: EntityForm): Promise<void> {
    // Path A: user picked an existing disabled entity -- flip it to enabled.
    if (form.pickedUuid) {
      try {
        await this._setEntityStatusMutation.mutate({
          variables: { uuid: form.pickedUuid, status: "enabled" },
        });
        this._message = { type: "success", text: "Entity added to graph." };
        this._closePanel();
        this._entitiesQuery.refetch();
      } catch {
        this._message = { type: "error", text: "Could not enable entity." };
      }
      return;
    }
    // Path B: create a new user entity.
    if (!form.name.trim()) {
      this._message = { type: "error", text: "Name is required." };
      return;
    }
    try {
      const { data } = await this._createEntityMutation.mutate({
        variables: {
          input: {
            name: form.name.trim(),
            type: form.type,
            description: form.description,
          },
        },
      });
      if (data?.createEntity) {
        this._message = { type: "success", text: "Entity added." };
        this._closePanel();
        this._entitiesQuery.refetch();
      } else {
        this._message = { type: "error", text: "Could not add entity." };
      }
    } catch {
      this._message = { type: "error", text: "Could not add entity." };
    }
  }

  async _saveEntityEdit(uuid: string, form: EntityForm): Promise<void> {
    try {
      await this._updateEntityMutation.mutate({
        variables: {
          uuid,
          input: {
            name: form.name.trim() || null,
            type: form.type || null,
            description: form.description,
          },
        },
      });
      this._message = { type: "success", text: "Entity updated." };
      this._closePanel();
      this._entitiesQuery.refetch();
    } catch {
      this._message = { type: "error", text: "Could not update entity." };
    }
  }

  async _delete(e: Entity): Promise<void> {
    if (e.isMe) {
      this._message = { type: "error", text: "Cannot delete your own entity." };
      return;
    }
    try {
      const { data } = await this._deleteEntityMutation.mutate({
        variables: { uuid: e.uuid },
      });
      if ((data?.deleteEntity as Record<string, unknown>)?.ok) {
        this._message = { type: "success", text: "Entity removed." };
        this._entitiesQuery.refetch();
      } else {
        this._message = { type: "error", text: "Could not remove entity." };
      }
    } catch {
      this._message = { type: "error", text: "Could not remove entity." };
    }
  }

  // -- CRUD: relationship panel -------------------------------------------

  _openRelationshipPanel(): void {
    if (this._entities.length < 2 || this._relationshipTypes.length === 0) {
      this._message = { type: "error", text: "Add at least two entities and a relationship type first." };
      return;
    }
    const entityOptions = ['<option value="">--</option>']
      .concat(this._entities.map((e) => `<option value="${e.uuid}">${this._escape(e.name)}</option>`))
      .join("");
    const typeOptions = ['<option value="">--</option>']
      .concat(this._relationshipTypes.map((t) => `<option value="${t.name}">${this._escape(t.displayName)}</option>`))
      .join("");

    const panel = document.createElement("div");
    panel.style.padding = "1rem";
    panel.innerHTML = `
      <h3 style="margin-top:0">Add relationship</h3>
      <label style="display:block;margin-bottom:0.6rem">
        From<br/>
        <select id="r-from" style="width:100%">${entityOptions}</select>
      </label>
      <label style="display:block;margin-bottom:0.6rem">
        Type<br/>
        <select id="r-type" style="width:100%">${typeOptions}</select>
      </label>
      <label style="display:block;margin-bottom:0.6rem">
        To<br/>
        <select id="r-to" style="width:100%">${entityOptions}</select>
      </label>
      <div style="display:flex;gap:0.5rem;margin-top:1rem">
        <button id="save-btn">Add</button>
        <button id="cancel-btn">Cancel</button>
      </div>
    `;

    const form: RelationshipForm = { fromUuid: "", toUuid: "", type: "" };
    panel.querySelector("#r-from")?.addEventListener("change", (e) => {
      form.fromUuid = (e.target as HTMLSelectElement).value;
    });
    panel.querySelector("#r-to")?.addEventListener("change", (e) => {
      form.toUuid = (e.target as HTMLSelectElement).value;
    });
    panel.querySelector("#r-type")?.addEventListener("change", (e) => {
      form.type = (e.target as HTMLSelectElement).value;
    });
    panel.querySelector("#save-btn")?.addEventListener("click", () => void this._saveRelationship(form));
    panel.querySelector("#cancel-btn")?.addEventListener("click", () => this._closePanel());

    this._panelEl = panel;
    this.dispatchEvent(
      new CustomEvent("show-panel", { bubbles: true, composed: true, detail: { component: panel, width: 420 } }),
    );
  }

  async _saveRelationship(r: RelationshipForm): Promise<void> {
    if (!r.fromUuid || !r.toUuid || !r.type) {
      this._message = { type: "error", text: "From, to, and type are all required." };
      return;
    }
    if (r.fromUuid === r.toUuid) {
      this._message = { type: "error", text: "Cannot relate an entity to itself." };
      return;
    }
    try {
      await this._createRelMutation.mutate({
        variables: { from: r.fromUuid, to: r.toUuid, type: r.type },
      });
      this._message = { type: "success", text: "Relationship added." };
      this._closePanel();
      this._entitiesQuery.refetch();
    } catch {
      this._message = { type: "error", text: "Could not add relationship." };
    }
  }

  async _deleteRelationship(r: EntityRelationshipRow): Promise<void> {
    try {
      const { data } = await this._deleteRelMutation.mutate({
        variables: { from: r.fromUuid, to: r.toUuid, type: r.type },
      });
      if ((data?.deleteEntityRelationship as Record<string, unknown>)?.ok) {
        this._message = { type: "success", text: "Relationship removed." };
        this._entitiesQuery.refetch();
      } else {
        this._message = { type: "error", text: "Could not remove relationship." };
      }
    } catch {
      this._message = { type: "error", text: "Could not remove relationship." };
    }
  }

  // -- Cytoscape ego graph ------------------------------------------------

  _buildHierarchyElements(): CyElement[] {
    const elements: CyElement[] = [];
    for (const t of this._entityTypes) {
      elements.push({
        data: {
          id: `type:${t.name}`,
          label: t.displayName,
          isAbstract: t.isAbstract ? "yes" : "no",
        },
        // Abstract types stay scaffolding -- not selectable, not draggable.
        selectable: !t.isAbstract,
        grabbable: !t.isAbstract,
      });
      if (t.parent) {
        elements.push({
          data: {
            id: `typeedge:${t.parent}:${t.name}`,
            source: `type:${t.parent}`,
            target: `type:${t.name}`,
          },
        });
      }
    }
    return elements;
  }

  _buildGraphElements(): CyElement[] {
    const elements: CyElement[] = [];
    const byUuid: Record<string, Entity> = {};
    for (const e of this._entities) byUuid[e.uuid] = e;

    for (const e of this._entities) {
      elements.push({
        data: {
          id: e.uuid,
          label: e.name + (e.isMe ? " (me)" : ""),
          kind: e.type,
          isMe: e.isMe ? "yes" : "no",
        },
      });
    }
    for (const r of this._relationships) {
      if (!byUuid[r.fromUuid] || !byUuid[r.toUuid]) continue;
      elements.push({
        data: {
          id: `rel:${r.fromUuid}:${r.toUuid}:${r.type}`,
          source: r.fromUuid,
          target: r.toUuid,
          label: this._relTypeDisplayName(r.type),
        },
      });
    }
    return elements;
  }

  _initCytoscape(): void {
    const container = this.renderRoot.querySelector("#cy") as HTMLElement | null;
    if (!container) return;

    if (!_dagreRegistered) {
      cytoscape.use(dagre);
      _dagreRegistered = true;
    }

    if (this._cy) {
      this._cy.destroy();
    }

    if (this._view === "types") {
      this._initTypeHierarchy(container);
    } else {
      if (this._entities.length === 0) return;
      this._initEntityGraph(container);
    }

    if (this._resizeObserver) this._resizeObserver.disconnect();
    this._resizeObserver = new ResizeObserver(() => {
      if (this._cy) {
        this._cy.resize();
        this._cy.fit(undefined, 20);
      }
    });
    this._resizeObserver.observe(container);
  }

  _initEntityGraph(container: HTMLElement): void {
    const meUuid = this._meUuid();

    this._cy = cytoscape({
      container,
      elements: this._buildGraphElements(),
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "text-valign": "center",
            "text-halign": "center",
            "font-size": 11,
            color: "#fff",
            "text-wrap": "wrap",
            "text-max-width": 90,
            width: 110,
            height: 40,
            shape: "round-rectangle",
            "background-color": "#8a9a84",
          },
        },
        { selector: 'node[kind="human"]', style: { "background-color": "#728f67" } },
        { selector: 'node[kind="animal"]', style: { "background-color": "#c98a5c" } },
        { selector: 'node[kind="residence"]', style: { "background-color": "#6b8ab0" } },
        { selector: 'node[kind="vehicle"]', style: { "background-color": "#7a7a9c" } },
        { selector: 'node[kind="device"]', style: { "background-color": "#9a6b8a" } },
        { selector: 'node[kind="organization"]', style: { "background-color": "#8a7a6b" } },
        {
          selector: 'node[isMe="yes"]',
          style: { "border-width": 3, "border-color": "#2c2c28" },
        },
        {
          selector: "edge",
          style: {
            "curve-style": "bezier",
            "target-arrow-shape": "triangle",
            "target-arrow-color": "#999",
            "line-color": "#999",
            width: 2,
            label: "data(label)",
            "font-size": 9,
            color: "#666",
            "text-rotation": "autorotate",
            "text-margin-y": -8,
          },
        },
      ] as unknown as cytoscape.StylesheetStyle[],
      layout: {
        name: "concentric",
        concentric: (n: cytoscape.NodeSingular) => (n.id() === meUuid ? 10 : 1),
        levelWidth: () => 1,
        minNodeSpacing: 60,
        padding: 30,
      } as unknown as cytoscape.LayoutOptions,
      userZoomingEnabled: true,
      userPanningEnabled: true,
    });

    this._cy.on("tap", "node", (evt) => {
      const uuid = evt.target.id();
      const e = this._entityByUuid(uuid);
      if (e && !e.isMe) this._openEntityPanel(e);
    });
  }

  /** Open the right panel with every entity of ``typeName``. */
  _openTypeEntitiesPanel(typeName: string): void {
    const displayName = this._typeDisplayName(typeName);
    const entities = this._entities
      .filter((e) => e.type === typeName)
      .sort((a, b) => (a.name || "").localeCompare(b.name || ""));

    const panel = document.createElement("div");
    panel.style.padding = "1rem";
    const body =
      entities.length === 0
        ? `<p style="color:var(--shenas-text-faint,#888)">No entities of type ${this._escape(displayName)} yet.</p>`
        : `
          <ul style="list-style:none;padding:0;margin:0">
            ${entities
              .map(
                (e) => `
                  <li
                    data-uuid="${e.uuid}"
                    style="padding:0.4rem 0.6rem;margin-bottom:0.3rem;border:1px solid var(--shenas-border,#d8d4cc);border-radius:4px;cursor:pointer"
                  >
                    <div style="display:flex;justify-content:space-between;align-items:center;gap:0.5rem">
                      <span>
                        ${this._escape(e.name || "(unnamed)")}
                        ${e.isMe ? '<span class="me-badge" style="margin-left:0.3rem">me</span>' : ""}
                      </span>
                      <span style="color:var(--shenas-text-faint,#888);font-size:0.85rem">${this._escape(e.status)}</span>
                    </div>
                  </li>
                `,
              )
              .join("")}
          </ul>
        `;
    panel.innerHTML = `
      <h3 style="margin-top:0">${this._escape(displayName)} entities <span style="color:var(--shenas-text-faint,#888);font-weight:normal">(${entities.length})</span></h3>
      ${body}
    `;

    for (const li of Array.from(panel.querySelectorAll<HTMLLIElement>("li[data-uuid]"))) {
      li.addEventListener("click", () => {
        const uuid = li.dataset.uuid;
        const e = entities.find((x) => x.uuid === uuid);
        if (e && !e.isMe) this._openEntityPanel(e);
      });
    }

    this._panelEl = panel;
    this.dispatchEvent(
      new CustomEvent("show-panel", { bubbles: true, composed: true, detail: { component: panel, width: 420 } }),
    );
  }

  _initTypeHierarchy(container: HTMLElement): void {
    if (this._entityTypes.length === 0) return;

    this._cy = cytoscape({
      container,
      elements: this._buildHierarchyElements(),
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "text-valign": "center",
            "text-halign": "center",
            "font-size": 11,
            color: "#fff",
            "text-wrap": "wrap",
            "text-max-width": 90,
            width: 110,
            height: 36,
            shape: "round-rectangle",
            "background-color": "#8a9a84",
          },
        },
        {
          selector: 'node[isAbstract="yes"]',
          style: {
            "background-color": "#aaa",
            "border-width": 2,
            "border-style": "dashed",
            "border-color": "#888",
            // Abstract types are non-instantiable scaffolding, not clickable.
            events: "no",
          },
        },
        {
          selector: "edge",
          style: {
            "curve-style": "bezier",
            "target-arrow-shape": "triangle",
            "target-arrow-color": "#999",
            "line-color": "#999",
            width: 2,
          },
        },
      ] as unknown as cytoscape.StylesheetStyle[],
      layout: {
        name: "dagre",
        rankDir: "TB",
        spacingFactor: 1.2,
        padding: 30,
      } as unknown as cytoscape.LayoutOptions,
      userZoomingEnabled: true,
      userPanningEnabled: true,
    });

    // Clicking a type node opens the right panel with all entities of that type.
    this._cy.on("tap", "node", (evt) => {
      const id = evt.target.id();
      if (!id.startsWith("type:")) return;
      this._openTypeEntitiesPanel(id.slice("type:".length));
    });
  }

  firstUpdated(): void {
    if (!this._loading) {
      this._initCytoscape();
    }
  }

  updated(): void {
    if (!this._loading) {
      requestAnimationFrame(() => this._initCytoscape());
    }
  }

  // -- Render -------------------------------------------------------------

  render() {
    return html`
      <shenas-page ?loading=${this._loading} loading-text="Loading entities...">
        ${renderMessage(this._message)}
        <div class="view-toggle">
          <button aria-pressed=${this._view === "entities"} @click=${() => this._setView("entities")}>Entities</button>
          <button aria-pressed=${this._view === "types"} @click=${() => this._setView("types")}>Type Hierarchy</button>
        </div>
        ${this._view === "entities" && this._entities.length === 0
          ? html`<div class="empty-graph">No entities yet.</div>`
          : html`<div id="cy"></div>`}

        <div class="section">
          <h3>Entities</h3>
          <div style="display:flex;justify-content:flex-end;margin-bottom:0.4rem">
            <button @click=${() => this._openEntityPanel()}>Add entity</button>
          </div>
          ${this._renderEntitiesTable()}
        </div>

        <div class="section">
          <h3>Relationships</h3>
          <div style="display:flex;justify-content:flex-end;margin-bottom:0.4rem">
            <button @click=${() => this._openRelationshipPanel()}>Add relationship</button>
          </div>
          ${this._renderRelationshipsTable()}
        </div>
      </shenas-page>
    `;
  }

  _renderEntitiesTable() {
    return html`
      <shenas-data-list
        .columns=${[
          {
            key: "name",
            label: "Name",
            render: (row: Record<string, unknown>) => {
              const e = row as unknown as Entity;
              return html`${e.name}${e.isMe ? html`<span class="me-badge">me</span>` : ""}`;
            },
          },
          {
            key: "type",
            label: "Type",
            render: (row: Record<string, unknown>) => {
              const e = row as unknown as Entity;
              return html`<a
                href="#"
                @click=${(ev: Event) => {
                  ev.preventDefault();
                  this._openTypeEntitiesPanel(e.type);
                }}
                style="color:var(--shenas-accent,#6b8ab0);text-decoration:none"
                >${this._typeDisplayName(e.type)}</a
              >`;
            },
          },
          { key: "status", label: "Status" },
        ]}
        .rows=${this._entities as unknown as Record<string, unknown>[]}
        .actions=${(row: Record<string, unknown>) => {
          const e = row as unknown as Entity;
          return e.isMe
            ? ""
            : html`
                <button @click=${() => this._openEntityPanel(e)}>Edit</button>
                <button class="danger" @click=${() => this._delete(e)}>Delete</button>
              `;
        }}
        empty-text="No entities yet."
      ></shenas-data-list>
    `;
  }

  _renderRelationshipsTable() {
    return html`
      <shenas-data-list
        .columns=${[
          {
            key: "from",
            label: "From",
            render: (row: Record<string, unknown>) => {
              const r = row as unknown as EntityRelationshipRow;
              const from = this._entityByUuid(r.fromUuid);
              return from ? from.name : r.fromUuid.slice(0, 8);
            },
          },
          {
            key: "type",
            label: "Type",
            render: (row: Record<string, unknown>) =>
              this._relTypeDisplayName((row as unknown as EntityRelationshipRow).type),
          },
          {
            key: "to",
            label: "To",
            render: (row: Record<string, unknown>) => {
              const r = row as unknown as EntityRelationshipRow;
              const to = this._entityByUuid(r.toUuid);
              return to ? to.name : r.toUuid.slice(0, 8);
            },
          },
        ]}
        .rows=${this._relationships as unknown as Record<string, unknown>[]}
        .actions=${(row: Record<string, unknown>) => {
          const r = row as unknown as EntityRelationshipRow;
          return html`<button class="danger" @click=${() => this._deleteRelationship(r)}>Delete</button>`;
        }}
        empty-text="No relationships yet."
      ></shenas-data-list>
    `;
  }
}

customElements.define("shenas-entities", EntitiesPage);
