import { LitElement, html, css } from "lit";
import cytoscape from "cytoscape";
// The vendor bundle re-exports cytoscape-dagre as `dagre` from "cytoscape".
// @ts-expect-error dagre is provided by the vendor bundle, not the real cytoscape package
import { dagre } from "cytoscape";
import {
  gql,
  gqlFull,
  buttonStyles,
  formStyles,
  messageStyles,
  tableStyles,
  renderMessage,
} from "shenas-frontends";

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
    apiBase: { type: String, attribute: "api-base" },
    _entities: { state: true },
    _relationships: { state: true },
    _entityTypes: { state: true },
    _relationshipTypes: { state: true },
    _loading: { state: true },
    _message: { state: true },
    _creating: { state: true },
    _newEntity: { state: true },
    _editing: { state: true },
    _editForm: { state: true },
    _newRel: { state: true },
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
      .edit-panel {
        margin: 0.8rem 0;
        padding: 1rem;
        border: 1px solid var(--shenas-border, #d8d4cc);
        border-radius: 8px;
        background: var(--shenas-bg-secondary, #f3f0eb);
      }
      .edit-panel h4 {
        margin: 0 0 0.8rem;
        font-size: 0.95rem;
        font-weight: 600;
      }
      .form-row {
        display: flex;
        gap: 0.8rem;
        margin-bottom: 0.6rem;
        flex-wrap: wrap;
      }
      .form-row label {
        display: flex;
        flex-direction: column;
        gap: 0.2rem;
        flex: 1 1 140px;
        font-size: 0.8rem;
        color: var(--shenas-text-muted, #666);
      }
      .form-row input,
      .form-row select {
        padding: 0.4rem;
        border: 1px solid var(--shenas-border, #d8d4cc);
        border-radius: 4px;
        background: var(--shenas-bg, #faf8f5);
        color: var(--shenas-text, #2c2c28);
        font-size: 0.9rem;
      }
      .actions {
        display: flex;
        gap: 0.4rem;
        margin-top: 0.6rem;
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

  apiBase = "";
  _entities: Entity[] = [];
  _relationships: EntityRelationshipRow[] = [];
  _entityTypes: EntityTypeInfo[] = [];
  _relationshipTypes: RelationshipTypeInfo[] = [];
  _loading = true;
  _message: Message | null = null;
  _creating = false;
  _newEntity: EntityForm = this._emptyEntityForm();
  _editing: string | null = null;
  _editForm: EntityForm = this._emptyEntityForm();
  _newRel: RelationshipForm = { fromUuid: "", toUuid: "", type: "" };

  private _cy: cytoscape.Core | null = null;
  private _resizeObserver: ResizeObserver | null = null;

  _emptyEntityForm(): EntityForm {
    return { name: "", type: "animal", description: "", birthYear: "" };
  }

  connectedCallback(): void {
    super.connectedCallback();
    this._fetchAll();
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

  async _fetchAll(): Promise<void> {
    this._loading = true;
    try {
      const data = await gql(
        this.apiBase,
        `{
          entities { uuid type name description status birthYear isMe }
          entityRelationships { fromUuid toUuid type description }
          entityTypes { name displayName description icon isHuman }
          entityRelationshipTypes { name displayName inverseName isSymmetric }
        }`,
      );
      this._entities = (data?.entities as Entity[]) || [];
      this._relationships = (data?.entityRelationships as EntityRelationshipRow[]) || [];
      this._entityTypes = (data?.entityTypes as EntityTypeInfo[]) || [];
      this._relationshipTypes = (data?.entityRelationshipTypes as RelationshipTypeInfo[]) || [];
    } catch (e) {
      console.error("Failed to fetch entities:", e);
      this._message = { type: "error", text: "Could not load entities." };
    }
    this._loading = false;
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

  // -- CRUD ---------------------------------------------------------------

  _startCreate(): void {
    this._creating = true;
    this._newEntity = this._emptyEntityForm();
  }

  _cancelCreate(): void {
    this._creating = false;
    this._newEntity = this._emptyEntityForm();
  }

  _updateNewField(field: keyof EntityForm, value: string): void {
    this._newEntity = { ...this._newEntity, [field]: value };
  }

  async _saveCreate(): Promise<void> {
    const form = this._newEntity;
    if (!form.name.trim()) {
      this._message = { type: "error", text: "Name is required." };
      return;
    }
    const { ok, data } = await gqlFull(
      this.apiBase,
      `mutation($input: EntityCreateInput!) {
        createEntity(entityInput: $input) { uuid name }
      }`,
      {
        input: {
          name: form.name.trim(),
          type: form.type,
          description: form.description,
          birthYear: form.birthYear ? parseInt(form.birthYear, 10) : null,
        },
      },
    );
    if (ok && data?.createEntity) {
      this._message = { type: "success", text: "Entity added." };
      this._cancelCreate();
      await this._fetchAll();
    } else {
      this._message = { type: "error", text: "Could not add entity." };
    }
  }

  _startEdit(e: Entity): void {
    this._editing = e.uuid;
    this._editForm = {
      name: e.name,
      type: e.type,
      description: e.description,
      birthYear: e.birthYear !== null ? String(e.birthYear) : "",
    };
  }

  _cancelEdit(): void {
    this._editing = null;
    this._editForm = this._emptyEntityForm();
  }

  _updateEditField(field: keyof EntityForm, value: string): void {
    this._editForm = { ...this._editForm, [field]: value };
  }

  async _saveEdit(): Promise<void> {
    if (!this._editing) return;
    const form = this._editForm;
    const { ok } = await gqlFull(
      this.apiBase,
      `mutation($uuid: String!, $input: EntityUpdateInput!) {
        updateEntity(uuid: $uuid, entityInput: $input) { uuid }
      }`,
      {
        uuid: this._editing,
        input: {
          name: form.name.trim() || null,
          type: form.type || null,
          description: form.description,
          birthYear: form.birthYear ? parseInt(form.birthYear, 10) : null,
        },
      },
    );
    if (ok) {
      this._message = { type: "success", text: "Entity updated." };
      this._cancelEdit();
      await this._fetchAll();
    } else {
      this._message = { type: "error", text: "Could not update entity." };
    }
  }

  async _delete(e: Entity): Promise<void> {
    if (e.isMe) {
      this._message = { type: "error", text: "Cannot delete your own entity." };
      return;
    }
    const { ok, data } = await gqlFull(
      this.apiBase,
      `mutation($uuid: String!) { deleteEntity(uuid: $uuid) { ok } }`,
      { uuid: e.uuid },
    );
    if (ok && (data?.deleteEntity as Record<string, unknown>)?.ok) {
      this._message = { type: "success", text: "Entity removed." };
      await this._fetchAll();
    } else {
      this._message = { type: "error", text: "Could not remove entity." };
    }
  }

  _updateRelField(field: keyof RelationshipForm, value: string): void {
    this._newRel = { ...this._newRel, [field]: value };
  }

  async _addRelationship(): Promise<void> {
    const r = this._newRel;
    if (!r.fromUuid || !r.toUuid || !r.type) {
      this._message = { type: "error", text: "From, to, and type are all required." };
      return;
    }
    if (r.fromUuid === r.toUuid) {
      this._message = { type: "error", text: "Cannot relate an entity to itself." };
      return;
    }
    const { ok } = await gqlFull(
      this.apiBase,
      `mutation($from: String!, $to: String!, $type: String!) {
        createEntityRelationship(fromUuid: $from, toUuid: $to, type: $type) { fromUuid }
      }`,
      { from: r.fromUuid, to: r.toUuid, type: r.type },
    );
    if (ok) {
      this._message = { type: "success", text: "Relationship added." };
      this._newRel = { fromUuid: "", toUuid: "", type: "" };
      await this._fetchAll();
    } else {
      this._message = { type: "error", text: "Could not add relationship." };
    }
  }

  async _deleteRelationship(r: EntityRelationshipRow): Promise<void> {
    const { ok } = await gqlFull(
      this.apiBase,
      `mutation($from: String!, $to: String!, $type: String!) {
        deleteEntityRelationship(fromUuid: $from, toUuid: $to, type: $type) { ok }
      }`,
      { from: r.fromUuid, to: r.toUuid, type: r.type },
    );
    if (ok) {
      this._message = { type: "success", text: "Relationship removed." };
      await this._fetchAll();
    } else {
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
      if (e && !e.isMe) this._startEdit(e);
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

  updated(changed: Map<string, unknown>): void {
    if ((changed.has("_loading") || changed.has("_entities") || changed.has("_relationships")) && !this._loading) {
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
            ${this._creating
              ? ""
              : html`<button @click=${() => this._startCreate()}>Add entity</button>`}
          </div>
          ${this._creating ? this._renderCreateForm() : ""}
          ${this._renderEntitiesTable()}
        </div>

        <div class="section">
          <h3>Relationships</h3>
          ${this._renderRelationshipForm()}
          ${this._renderRelationshipsTable()}
        </div>
      </shenas-page>
    `;
  }

  _renderCreateForm() {
    return html`
      <div class="edit-panel">
        <h4>Add entity</h4>
        <div class="form-row">
          <label
            >Name
            <input
              type="text"
              .value=${this._newEntity.name}
              @input=${(e: InputEvent) => this._updateNewField("name", (e.target as HTMLInputElement).value)}
            />
          </label>
          <label
            >Type
            <select
              .value=${this._newEntity.type}
              @change=${(e: Event) => this._updateNewField("type", (e.target as HTMLSelectElement).value)}
            >
              ${this._entityTypes.map(
                (t) => html`<option value=${t.name} ?selected=${t.name === this._newEntity.type}>${t.displayName}</option>`,
              )}
            </select>
          </label>
          <label
            >Birth year
            <input
              type="number"
              .value=${this._newEntity.birthYear}
              @input=${(e: InputEvent) => this._updateNewField("birthYear", (e.target as HTMLInputElement).value)}
            />
          </label>
        </div>
        <div class="form-row">
          <label style="flex:1"
            >Description
            <input
              type="text"
              .value=${this._newEntity.description}
              @input=${(e: InputEvent) => this._updateNewField("description", (e.target as HTMLInputElement).value)}
            />
          </label>
        </div>
        <div class="actions">
          <button @click=${() => this._saveCreate()}>Add</button>
          <button @click=${() => this._cancelCreate()}>Cancel</button>
        </div>
      </div>
    `;
  }

  _renderEditForm(e: Entity) {
    return html`
      <div class="edit-panel">
        <h4>Edit ${e.name}</h4>
        <div class="form-row">
          <label
            >Name
            <input
              type="text"
              .value=${this._editForm.name}
              @input=${(ev: InputEvent) => this._updateEditField("name", (ev.target as HTMLInputElement).value)}
            />
          </label>
          <label
            >Type
            <select
              .value=${this._editForm.type}
              @change=${(ev: Event) => this._updateEditField("type", (ev.target as HTMLSelectElement).value)}
            >
              ${this._entityTypes.map(
                (t) => html`<option value=${t.name} ?selected=${t.name === this._editForm.type}>${t.displayName}</option>`,
              )}
            </select>
          </label>
          <label
            >Birth year
            <input
              type="number"
              .value=${this._editForm.birthYear}
              @input=${(ev: InputEvent) => this._updateEditField("birthYear", (ev.target as HTMLInputElement).value)}
            />
          </label>
        </div>
        <div class="form-row">
          <label style="flex:1"
            >Description
            <input
              type="text"
              .value=${this._editForm.description}
              @input=${(ev: InputEvent) => this._updateEditField("description", (ev.target as HTMLInputElement).value)}
            />
          </label>
        </div>
        <div class="actions">
          <button @click=${() => this._saveEdit()}>Save</button>
          <button @click=${() => this._cancelEdit()}>Cancel</button>
        </div>
      </div>
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
                <td>
                  ${e.name}${e.isMe ? html`<span class="me-badge">me</span>` : ""}
                </td>
                <td>${this._typeDisplayName(e.type)}</td>
                <td>${e.status}</td>
                <td>
                  <div class="row-actions">
                    ${e.isMe
                      ? ""
                      : html`
                          <button @click=${() => this._startEdit(e)}>Edit</button>
                          <button class="danger" @click=${() => this._delete(e)}>Delete</button>
                        `}
                  </div>
                </td>
              </tr>
              ${this._editing === e.uuid ? html`<tr><td colspan="4">${this._renderEditForm(e)}</td></tr>` : ""}
            `,
          )}
        </tbody>
      </table>
    `;
  }

  _renderRelationshipForm() {
    if (this._entities.length < 2 || this._relationshipTypes.length === 0) {
      return html`<p style="color:var(--shenas-text-faint,#888)">Add at least two entities to start linking them.</p>`;
    }
    return html`
      <div class="edit-panel">
        <h4>Add relationship</h4>
        <div class="form-row">
          <label
            >From
            <select
              .value=${this._newRel.fromUuid}
              @change=${(e: Event) => this._updateRelField("fromUuid", (e.target as HTMLSelectElement).value)}
            >
              <option value="">--</option>
              ${this._entities.map((e) => html`<option value=${e.uuid}>${e.name}</option>`)}
            </select>
          </label>
          <label
            >Type
            <select
              .value=${this._newRel.type}
              @change=${(e: Event) => this._updateRelField("type", (e.target as HTMLSelectElement).value)}
            >
              <option value="">--</option>
              ${this._relationshipTypes.map((t) => html`<option value=${t.name}>${t.displayName}</option>`)}
            </select>
          </label>
          <label
            >To
            <select
              .value=${this._newRel.toUuid}
              @change=${(e: Event) => this._updateRelField("toUuid", (e.target as HTMLSelectElement).value)}
            >
              <option value="">--</option>
              ${this._entities.map((e) => html`<option value=${e.uuid}>${e.name}</option>`)}
            </select>
          </label>
        </div>
        <div class="actions">
          <button @click=${() => this._addRelationship()}>Add</button>
        </div>
      </div>
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
