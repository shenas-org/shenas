import { LitElement, html, css, render } from "lit";
import cytoscape from "cytoscape";
// The vendor bundle re-exports cytoscape-dagre as `dagre` from "cytoscape".
// @ts-expect-error dagre is provided by the vendor bundle, not the real cytoscape package
import { dagre } from "cytoscape";
import { entityNodeStyles, ENTITY_EDGE_STYLES, ENTITY_NODE_DEFAULT_COLOR } from "./graph-styles.ts";
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
import { GET_ENTITIES_DATA, GET_ENTITY_WITH_STATEMENTS } from "./graphql/queries.ts";
import {
  CREATE_ENTITY,
  UPDATE_ENTITY,
  DELETE_ENTITY,
  CREATE_ENTITY_RELATIONSHIP,
  DELETE_ENTITY_RELATIONSHIP,
  SET_ENTITY_STATUS,
  CREATE_PROPERTY,
  UPSERT_STATEMENT,
  DELETE_STATEMENT,
} from "./graphql/mutations.ts";

interface Statement {
  entityId: string;
  propertyId: string;
  value: string;
  valueLabel: string | null;
  rank: string;
  source: string;
  propertyLabel: string | null;
  datatype: string | null;
}

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
  domainTypes: string[];
  rangeTypes: string[];
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
  private _createPropertyMutation = new ApolloMutationController(this, CREATE_PROPERTY, { client: getClient() });
  private _upsertStatementMutation = new ApolloMutationController(this, UPSERT_STATEMENT, { client: getClient() });
  private _deleteStatementMutation = new ApolloMutationController(this, DELETE_STATEMENT, { client: getClient() });

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
    const current: EntityForm = entity
      ? {
          name: entity.name,
          type: entity.type,
          description: entity.description,
          pickedUuid: null,
        }
      : this._emptyEntityForm();

    const panel = document.createElement("div");
    panel.style.padding = "1rem";

    const SENTINEL = "__new__";
    let showNewNameField = false;

    const typeOptions = this._entityTypes
      .filter((entityType) => !entityType.isAbstract)
      .map((entityType) => ({ value: entityType.name, label: entityType.displayName }));

    const renderPanel = () => {
      const candidates = this._disabledOfType(current.type);
      const hasCandidates = !isEdit && candidates.length > 0;

      const candidateOptions = hasCandidates
        ? [...candidates.map((c) => ({ value: c.uuid, label: c.name })), { value: SENTINEL, label: "Create new..." }]
        : [];

      render(
        html`
          <shenas-form-panel
            title=${isEdit ? `Edit ${entity!.name}` : "Add entity"}
            submit-label=${isEdit ? "Save" : "Add"}
            @submit=${() => {
              if (isEdit) void this._saveEntityEdit(entity!.uuid, current);
              else void this._saveEntityCreate(current);
            }}
            @cancel=${() => this._closePanel()}
          >
            <shenas-dropdown
              label="Type"
              .options=${typeOptions}
              value=${current.type}
              @change=${(e: CustomEvent) => {
                current.type = e.detail.value;
                current.name = "";
                current.pickedUuid = null;
                showNewNameField = false;
                renderPanel();
              }}
            ></shenas-dropdown>
            ${isEdit
              ? html`<shenas-field
                  label="Name"
                  value=${current.name}
                  @change=${(e: CustomEvent) => {
                    current.name = e.detail.value;
                    current.pickedUuid = null;
                  }}
                ></shenas-field>`
              : hasCandidates
                ? html`
                    <shenas-dropdown
                      label="Name"
                      placeholder="Pick an existing ${this._typeDisplayName(current.type)}..."
                      .options=${candidateOptions}
                      value=${current.pickedUuid || (showNewNameField ? SENTINEL : "")}
                      @change=${(e: CustomEvent) => {
                        const value = e.detail.value;
                        if (value === SENTINEL) {
                          showNewNameField = true;
                          current.pickedUuid = null;
                          current.name = "";
                          renderPanel();
                        } else {
                          showNewNameField = false;
                          const match = candidates.find((c) => c.uuid === value);
                          current.pickedUuid = value || null;
                          current.name = match?.name ?? "";
                          renderPanel();
                        }
                      }}
                    ></shenas-dropdown>
                    ${showNewNameField
                      ? html`<shenas-field
                          label=""
                          placeholder="New ${this._typeDisplayName(current.type)} name"
                          value=${current.name}
                          @change=${(e: CustomEvent) => {
                            current.name = e.detail.value;
                            current.pickedUuid = null;
                          }}
                        ></shenas-field>`
                      : ""}
                  `
                : html`<shenas-field
                    label="Name"
                    value=${current.name}
                    @change=${(e: CustomEvent) => {
                      current.name = e.detail.value;
                      current.pickedUuid = null;
                    }}
                  ></shenas-field>`}
            <shenas-field
              label="Description"
              value=${current.description}
              @change=${(e: CustomEvent) => {
                current.description = e.detail.value;
              }}
            ></shenas-field>
          </shenas-form-panel>
          ${isEdit
            ? html`<hr style="margin:1.2rem 0" />
                <div id="statements-section"></div>`
            : ""}
        `,
        panel,
      );
    };
    renderPanel();

    if (isEdit && entity) {
      void this._renderStatementsSection(panel, entity.uuid);
    }

    this._panelEl = panel;
    this.dispatchEvent(
      new CustomEvent("show-panel", { bubbles: true, composed: true, detail: { component: panel, width: 420 } }),
    );
  }

  /**
   * Fetch + render the entity's statements inside the open detail panel.
   */
  async _renderStatementsSection(panel: HTMLElement, entityId: string): Promise<void> {
    const section = panel.querySelector("#statements-section") as HTMLDivElement | null;
    if (!section) return;
    section.innerHTML = '<div style="opacity:0.6">Loading statements...</div>';
    let statements: Statement[] = [];
    try {
      const res = await getClient().query({
        query: GET_ENTITY_WITH_STATEMENTS,
        variables: { uuid: entityId },
        fetchPolicy: "network-only",
      });
      statements = (res.data?.entity?.statements as Statement[]) ?? [];
    } catch (err) {
      section.innerHTML = `<div style="color:#c00">Failed to load statements: ${this._escape(String(err))}</div>`;
      return;
    }

    const rows = statements
      .map((s) => {
        const label = s.propertyLabel || s.propertyId;
        const value = s.valueLabel || s.value;
        const sourceTag =
          s.source !== "user" ? ` <span style="opacity:0.5;font-size:0.85em">[${this._escape(s.source)}]</span>` : "";
        return `
          <div style="display:flex;justify-content:space-between;gap:0.5rem;padding:0.25rem 0;border-bottom:1px solid #eee">
            <div><strong>${this._escape(label)}</strong>${sourceTag}<br/><span style="opacity:0.85">${this._escape(value)}</span></div>
            <button data-pid="${this._escape(s.propertyId)}" data-val="${this._escape(s.value)}" class="del-stmt" title="Delete" style="border:none;background:none;cursor:pointer;color:#c00">x</button>
          </div>
        `;
      })
      .join("");

    section.innerHTML = `
      <h4 style="margin:0.4rem 0">Statements</h4>
      <div id="stmt-list">${rows || '<div style="opacity:0.5">No statements yet.</div>'}</div>
      <div style="margin-top:0.6rem;display:flex;gap:0.4rem;align-items:flex-end">
        <label style="flex:1">Property<br/>
          <input id="stmt-label" type="text" style="width:100%" placeholder="e.g. Nickname" />
        </label>
        <label style="flex:1">Value<br/>
          <input id="stmt-value" type="text" style="width:100%" />
        </label>
        <button id="stmt-add">Add</button>
      </div>
    `;

    section.querySelectorAll(".del-stmt").forEach((el) => {
      el.addEventListener("click", async (e) => {
        const btn = e.currentTarget as HTMLButtonElement;
        const propertyId = btn.dataset.pid as string;
        const value = btn.dataset.val as string;
        await this._deleteStatementMutation.mutate({ variables: { entityId, propertyId, value } });
        await this._renderStatementsSection(panel, entityId);
      });
    });

    const addBtn = section.querySelector("#stmt-add") as HTMLButtonElement;
    addBtn.addEventListener("click", async () => {
      const labelEl = section.querySelector("#stmt-label") as HTMLInputElement;
      const valueEl = section.querySelector("#stmt-value") as HTMLInputElement;
      const label = labelEl.value.trim();
      const value = valueEl.value.trim();
      if (!label || !value) return;
      const propRes = await this._createPropertyMutation.mutate({
        variables: { propertyInput: { label, datatype: "string" } },
      });
      const propertyId = (propRes?.data as { createProperty?: { id?: string } } | undefined)?.createProperty?.id;
      if (!propertyId) return;
      await this._upsertStatementMutation.mutate({
        variables: { statementInput: { entityId, propertyId, value, valueLabel: value } },
      });
      labelEl.value = "";
      valueEl.value = "";
      await this._renderStatementsSection(panel, entityId);
    });
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

    const form: RelationshipForm = { fromUuid: "", toUuid: "", type: "" };
    const panel = document.createElement("div");
    panel.style.padding = "1rem";

    const rerender = () => {
      const entityOptions = this._entities.map((entity) => ({ value: entity.uuid, label: entity.name }));
      const fromEntity = this._entities.find((entity) => entity.uuid === form.fromUuid);
      const toEntity = this._entities.find((entity) => entity.uuid === form.toUuid);
      const fromType = fromEntity?.type || "";
      const toType = toEntity?.type || "";

      // Filter relationship types by domain/range constraints.
      // A type matches if its domain_types is empty (any) or includes the from entity's type,
      // AND its range_types is empty (any) or includes the to entity's type.
      const filteredRelTypes = this._relationshipTypes.filter((relType) => {
        if (fromType && relType.domainTypes.length > 0 && !relType.domainTypes.includes(fromType)) return false;
        if (toType && relType.rangeTypes.length > 0 && !relType.rangeTypes.includes(toType)) return false;
        return true;
      });
      const relTypeOptions = filteredRelTypes.map((relType) => ({ value: relType.name, label: relType.displayName }));

      // Reset type if it's no longer in the filtered list
      if (form.type && !filteredRelTypes.some((relType) => relType.name === form.type)) {
        form.type = "";
      }

      render(
        html`
          <shenas-form-panel
            title="Add relationship"
            submit-label="Add"
            @submit=${() => void this._saveRelationship(form)}
            @cancel=${() => this._closePanel()}
          >
            <shenas-dropdown
              label="From"
              placeholder="--"
              .options=${entityOptions}
              value=${form.fromUuid}
              @change=${(e: CustomEvent) => {
                form.fromUuid = e.detail.value;
                rerender();
              }}
            ></shenas-dropdown>
            <shenas-dropdown
              label="Type"
              placeholder="--"
              .options=${relTypeOptions}
              value=${form.type}
              @change=${(e: CustomEvent) => {
                form.type = e.detail.value;
              }}
            ></shenas-dropdown>
            <shenas-dropdown
              label="To"
              placeholder="--"
              .options=${entityOptions}
              value=${form.toUuid}
              @change=${(e: CustomEvent) => {
                form.toUuid = e.detail.value;
                rerender();
              }}
            ></shenas-dropdown>
          </shenas-form-panel>
        `,
        panel,
      );
    };

    rerender();
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

  _openRelationshipPanelPrefilled(fromUuid: string, toUuid: string): void {
    if (this._relationshipTypes.length === 0) {
      this._message = { type: "error", text: "No relationship types available." };
      return;
    }

    const entityOptions = this._entities.map((e) => ({ value: e.uuid, label: e.name }));
    const relTypeOptions = this._relationshipTypes.map((t) => ({ value: t.name, label: t.displayName }));
    const form: RelationshipForm = { fromUuid, toUuid, type: relTypeOptions[0]?.value || "" };

    const panel = document.createElement("div");
    panel.style.padding = "1rem";

    render(
      html`
        <shenas-form-panel
          title="Add relationship"
          submit-label="Add"
          @submit=${() => void this._saveRelationship(form)}
          @cancel=${() => this._closePanel()}
        >
          <shenas-dropdown
            label="From"
            .options=${entityOptions}
            value=${form.fromUuid}
            @change=${(e: CustomEvent) => {
              form.fromUuid = e.detail.value;
            }}
          ></shenas-dropdown>
          <shenas-dropdown
            label="Type"
            .options=${relTypeOptions}
            value=${form.type}
            @change=${(e: CustomEvent) => {
              form.type = e.detail.value;
            }}
          ></shenas-dropdown>
          <shenas-dropdown
            label="To"
            .options=${entityOptions}
            value=${form.toUuid}
            @change=${(e: CustomEvent) => {
              form.toUuid = e.detail.value;
            }}
          ></shenas-dropdown>
        </shenas-form-panel>
      `,
      panel,
    );

    this._panelEl = panel;
    this.dispatchEvent(
      new CustomEvent("show-panel", { bubbles: true, composed: true, detail: { component: panel, width: 420 } }),
    );
  }

  _openRelationshipDetailPanel(rel: EntityRelationshipRow): void {
    const fromEntity = this._entityByUuid(rel.fromUuid);
    const toEntity = this._entityByUuid(rel.toUuid);
    const relType = this._relationshipTypes.find((t) => t.name === rel.type);
    const fromLabel = fromEntity?.name || rel.fromUuid;
    const toLabel = toEntity?.name || rel.toUuid;
    const typeLabel = relType?.displayName || rel.type;

    const panel = document.createElement("div");
    panel.style.padding = "1rem";
    const _lbl = "display:flex;flex-direction:column;gap:0.2rem;font-size:0.85rem;margin-bottom:0.8rem";
    const _val = "padding:0.4rem;border:1px solid #eee;border-radius:4px;background:#f9f9f9;font-size:0.9rem";
    panel.innerHTML = `
      <h3 style="margin:0 0 1rem;font-size:1rem">Relationship</h3>
      <div style="${_lbl}">
        <span style="font-weight:600">From</span>
        <span style="${_val}">${this._escape(fromLabel)}</span>
      </div>
      <div style="${_lbl}">
        <span style="font-weight:600">Type</span>
        <span style="${_val}">${this._escape(typeLabel)}</span>
      </div>
      <div style="${_lbl}">
        <span style="font-weight:600">To</span>
        <span style="${_val}">${this._escape(toLabel)}</span>
      </div>
      ${rel.description ? `<div style="${_lbl}"><span style="font-weight:600">Description</span><span style="${_val}">${this._escape(rel.description)}</span></div>` : ""}
      <div style="display:flex;gap:0.5rem;margin-top:1rem">
        <button id="delete-btn" style="padding:0.4rem 1rem;border:1px solid #c00;border-radius:4px;cursor:pointer;background:#fff;color:#c00">Delete</button>
        <button id="close-btn" style="padding:0.4rem 1rem;border:1px solid #ccc;border-radius:4px;cursor:pointer;background:#fff">Close</button>
      </div>
    `;
    panel.querySelector("#delete-btn")?.addEventListener("click", async () => {
      await this._deleteRelationship(rel);
      this._closePanel();
    });
    panel.querySelector("#close-btn")?.addEventListener("click", () => this._closePanel());

    this._panelEl = panel;
    this.dispatchEvent(
      new CustomEvent("show-panel", { bubbles: true, composed: true, detail: { component: panel, width: 380 } }),
    );
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
    const enabledEntities = this._entities.filter((entity) => entity.status === "enabled");
    const byUuid: Record<string, Entity> = {};
    for (const entity of enabledEntities) byUuid[entity.uuid] = entity;

    for (const entity of enabledEntities) {
      elements.push({
        data: {
          id: entity.uuid,
          label: entity.name + (entity.isMe ? " (me)" : ""),
          kind: entity.type,
          isMe: entity.isMe ? "yes" : "no",
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
            "background-color": ENTITY_NODE_DEFAULT_COLOR,
          },
        },
        ...entityNodeStyles(),
        ...ENTITY_EDGE_STYLES,
        {
          selector: "edge:active",
          style: {
            "line-color": "#728f67",
            "target-arrow-color": "#728f67",
            width: 3,
          },
        },
        {
          selector: ".ghost-edge",
          style: {
            "line-color": "#728f67",
            "target-arrow-color": "#728f67",
            "line-style": "dashed",
            width: 2,
            opacity: 0.6,
          },
        },
      ] as unknown as cytoscape.StylesheetStyle[],
      layout: {
        name: "cose",
        boundingBox: container ? { x1: 0, y1: 0, w: container.clientWidth, h: container.clientHeight } : undefined,
        idealEdgeLength: 120,
        nodeOverlap: 30,
        nodeRepulsion: 40000,
        gravity: 0.25,
        numIter: 2000,
        padding: 30,
        animate: false,
        fit: true,
      } as unknown as cytoscape.LayoutOptions,
      userZoomingEnabled: true,
      userPanningEnabled: true,
    });

    // Pin Me to center after layout.
    if (meUuid) {
      const meNode = this._cy.getElementById(meUuid);
      if (meNode.length > 0) {
        meNode.position({ x: container.clientWidth / 2, y: container.clientHeight / 2 });
        meNode.lock();
        this._cy.fit(undefined, 20);
      }
    }

    // -- Single-click: edit entity / view relationship -----------------------
    this._cy.on("tap", "node", (evt) => {
      const uuid = evt.target.id();
      const e = this._entityByUuid(uuid);
      if (e) this._openEntityPanel(e);
    });

    this._cy.on("tap", "edge", (evt) => {
      const edgeId = evt.target.id() as string;
      const parts = edgeId.split(":");
      if (parts.length >= 4) {
        const rel = this._relationships.find(
          (r) => r.fromUuid === parts[1] && r.toUuid === parts[2] && r.type === parts.slice(3).join(":"),
        );
        if (rel) this._openRelationshipDetailPanel(rel);
      }
    });

    // -- Double-click on canvas: add entity ---------------------------------
    this._cy.on("tap", (evt) => {
      if (evt.target === this._cy) {
        // Tap on empty canvas -- open add-entity panel
        this._openEntityPanel();
      }
    });

    // -- Drag from node to node: add relationship ---------------------------
    let dragSource: string | null = null;
    let ghostEdge: string | null = null;

    this._cy.on("cxttapstart", "node", (evt) => {
      // Right-click drag starts a connection attempt
      dragSource = evt.target.id();
      // Add a temporary ghost edge for visual feedback
      ghostEdge = `ghost_${Date.now()}`;
      this._cy!.add({
        group: "edges",
        data: { id: ghostEdge, source: dragSource, target: dragSource, label: "" },
        classes: "ghost-edge",
      });
    });

    this._cy.on("cxtdrag", (evt) => {
      if (!dragSource || !ghostEdge || !this._cy) return;
      // Move ghost edge target to the nearest node under the pointer
      const pos = evt.position;
      const nearest = this._cy!.nodes().filter(
        (n) =>
          n.boundingBox().x1 <= pos.x &&
          pos.x <= n.boundingBox().x2 &&
          n.boundingBox().y1 <= pos.y &&
          pos.y <= n.boundingBox().y2,
      )[0];
      if (nearest && nearest.id() !== dragSource) {
        const edge = this._cy.getElementById(ghostEdge);
        edge.move({ target: nearest.id() });
      }
    });

    this._cy.on("cxttapend", (evt) => {
      if (!dragSource || !this._cy) return;
      // Clean up ghost edge
      if (ghostEdge) {
        const edge = this._cy.getElementById(ghostEdge);
        if (edge.length) edge.remove();
        ghostEdge = null;
      }
      // Find the target node under the pointer
      const pos = evt.position;
      const nearest = this._cy!.nodes().filter(
        (n) =>
          n.boundingBox().x1 <= pos.x &&
          pos.x <= n.boundingBox().x2 &&
          n.boundingBox().y1 <= pos.y &&
          pos.y <= n.boundingBox().y2,
      )[0];
      if (nearest && nearest.id() !== dragSource) {
        const targetUuid = nearest.id();
        this._openRelationshipPanelPrefilled(dragSource, targetUuid);
      }
      dragSource = null;
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

    render(
      html`
        <h3 style="margin-top:0">
          ${displayName} entities
          <span style="color:var(--shenas-text-faint,#888);font-weight:normal">(${entities.length})</span>
        </h3>
        ${entities.length === 0
          ? html`<p style="color:var(--shenas-text-faint,#888)">No entities of type ${displayName} yet.</p>`
          : html`
              <ul style="list-style:none;padding:0;margin:0">
                ${entities.map(
                  (e) => html`
                    <li
                      style="padding:0.4rem 0.6rem;margin-bottom:0.3rem;border:1px solid var(--shenas-border,#d8d4cc);border-radius:4px;cursor:${e.isMe
                        ? "default"
                        : "pointer"}"
                      @click=${() => {
                        if (!e.isMe) this._openEntityPanel(e);
                      }}
                    >
                      <div style="display:flex;justify-content:space-between;align-items:center;gap:0.5rem">
                        <span>
                          ${e.name || "(unnamed)"}
                          ${e.isMe ? html`<span class="me-badge" style="margin-left:0.3rem">me</span>` : ""}
                        </span>
                        <span style="color:var(--shenas-text-faint,#888);font-size:0.85rem">${e.status}</span>
                      </div>
                    </li>
                  `,
                )}
              </ul>
            `}
      `,
      panel,
    );

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
              return html`${e.name}${e.isMe
                ? html`<shenas-badge variant="success" style="margin-left:0.4rem">me</shenas-badge>`
                : ""}`;
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
                >${this._typeDisplayName(e.type)}</a
              >`;
            },
          },
        ]}
        .rows=${this._entities.filter((e) => e.status === "enabled") as unknown as Record<string, unknown>[]}
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
