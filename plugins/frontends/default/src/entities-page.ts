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
} from "./graphql/mutations.ts";

interface Entity {
  uuid: string;
  type: string;
  name: string;
  description: string;
  status: string;
  birthYear: number | null;
  isMe: boolean;
}

interface EntityTypeInfo {
  name: string;
  displayName: string;
  description: string;
  icon: string;
  isHuman: boolean;
}

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
  birthYear: string;
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
}

let _dagreRegistered = false;

class EntitiesPage extends LitElement {
  static properties = {
    _message: { state: true },
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
        height: 320px;
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
        height: 320px;
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
    `,
  ];

  declare _message: Message | null;

  private _cy: cytoscape.Core | null = null;
  private _resizeObserver: ResizeObserver | null = null;

  private _entitiesQuery = new ApolloQueryController(this, GET_ENTITIES_DATA, { client: getClient() });
  private _createEntityMutation = new ApolloMutationController(this, CREATE_ENTITY, { client: getClient() });
  private _updateEntityMutation = new ApolloMutationController(this, UPDATE_ENTITY, { client: getClient() });
  private _deleteEntityMutation = new ApolloMutationController(this, DELETE_ENTITY, { client: getClient() });
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
  }

  _emptyEntityForm(): EntityForm {
    return { name: "", type: "animal", description: "", birthYear: "" };
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

  /** Open the right panel to create a new entity, or edit ``entity`` if given. */
  _openEntityPanel(entity?: Entity): void {
    const isEdit = !!entity;
    const form: EntityForm = entity
      ? {
          name: entity.name,
          type: entity.type,
          description: entity.description,
          birthYear: entity.birthYear !== null ? String(entity.birthYear) : "",
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
        Name<br/>
        <input id="f-name" type="text" style="width:100%" value="${this._escape(form.name)}" />
      </label>
      <label style="display:block;margin-bottom:0.6rem">
        Type<br/>
        <select id="f-type" style="width:100%">${typeOptions}</select>
      </label>
      <label style="display:block;margin-bottom:0.6rem">
        Birth year<br/>
        <input id="f-birth" type="number" style="width:100%" value="${this._escape(form.birthYear)}" />
      </label>
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
    const bindInput = (id: string, field: keyof EntityForm) => {
      panel.querySelector(`#${id}`)?.addEventListener("input", (e) => {
        current[field] = (e.target as HTMLInputElement).value;
      });
    };
    bindInput("f-name", "name");
    bindInput("f-birth", "birthYear");
    bindInput("f-desc", "description");
    panel.querySelector("#f-type")?.addEventListener("change", (e) => {
      current.type = (e.target as HTMLSelectElement).value;
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
            birthYear: form.birthYear ? parseInt(form.birthYear, 10) : null,
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
            birthYear: form.birthYear ? parseInt(form.birthYear, 10) : null,
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
    if (this._entities.length === 0) return;

    if (!_dagreRegistered) {
      cytoscape.use(dagre);
      _dagreRegistered = true;
    }

    if (this._cy) {
      this._cy.destroy();
    }

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

    if (this._resizeObserver) this._resizeObserver.disconnect();
    this._resizeObserver = new ResizeObserver(() => {
      if (this._cy) {
        this._cy.resize();
        this._cy.fit(undefined, 20);
      }
    });
    this._resizeObserver.observe(container);
  }

  firstUpdated(): void {
    if (!this._loading && this._entities.length > 0) {
      this._initCytoscape();
    }
  }

  updated(): void {
    if (!this._loading && this._entities.length > 0) {
      requestAnimationFrame(() => this._initCytoscape());
    }
  }

  // -- Render -------------------------------------------------------------

  render() {
    return html`
      <shenas-page ?loading=${this._loading} loading-text="Loading entities...">
        ${renderMessage(this._message)}
        ${this._entities.length === 0
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
    if (this._entities.length === 0) {
      return html`<p style="color:var(--shenas-text-faint,#888)">No entities yet.</p>`;
    }
    return html`
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          ${this._entities.map(
            (e) => html`
              <tr>
                <td>${e.name}${e.isMe ? html`<span class="me-badge">me</span>` : ""}</td>
                <td>${this._typeDisplayName(e.type)}</td>
                <td>${e.status}</td>
                <td>
                  <div class="row-actions">
                    ${e.isMe
                      ? ""
                      : html`
                          <button @click=${() => this._openEntityPanel(e)}>Edit</button>
                          <button class="danger" @click=${() => this._delete(e)}>Delete</button>
                        `}
                  </div>
                </td>
              </tr>
            `,
          )}
        </tbody>
      </table>
    `;
  }

  _renderRelationshipsTable() {
    if (this._relationships.length === 0) {
      return html`<p style="color:var(--shenas-text-faint,#888)">No relationships yet.</p>`;
    }
    return html`
      <table>
        <thead>
          <tr>
            <th>From</th>
            <th>Type</th>
            <th>To</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          ${this._relationships.map((r) => {
            const from = this._entityByUuid(r.fromUuid);
            const to = this._entityByUuid(r.toUuid);
            return html`
              <tr>
                <td>${from ? from.name : r.fromUuid.slice(0, 8)}</td>
                <td>${this._relTypeDisplayName(r.type)}</td>
                <td>${to ? to.name : r.toUuid.slice(0, 8)}</td>
                <td>
                  <div class="row-actions">
                    <button class="danger" @click=${() => this._deleteRelationship(r)}>Delete</button>
                  </div>
                </td>
              </tr>
            `;
          })}
        </tbody>
      </table>
    `;
  }
}

customElements.define("shenas-entities", EntitiesPage);
