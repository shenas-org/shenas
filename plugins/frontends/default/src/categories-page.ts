import { LitElement, html, css, nothing } from "lit";
import {
  gql,
  gqlFull,
  renderMessage,
  buttonStyles,
  formStyles,
  messageStyles,
  tableStyles,
} from "shenas-frontends";

interface CategoryValue {
  value: string;
  sortOrder: number;
  color: string | null;
}

interface CategorySet {
  id: string;
  displayName: string;
  description: string;
  values: CategoryValue[];
}

interface Message {
  type: string;
  text: string;
}

class CategoriesPage extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    _sets: { state: true },
    _loading: { state: true },
    _editing: { state: true },
    _creating: { state: true },
    _message: { state: true },
    _newId: { state: true },
    _newName: { state: true },
    _newDesc: { state: true },
    _editValues: { state: true },
    _editName: { state: true },
    _editDesc: { state: true },
    _addValue: { state: true },
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
      .edit-panel {
        margin: 1rem 0;
        padding: 1rem;
        border: 1px solid var(--shenas-border, #e0e0e0);
        border-radius: 8px;
        background: var(--shenas-bg-secondary, #fafafa);
      }
      .edit-panel h3 {
        margin: 0 0 0.8rem;
        font-size: 1rem;
      }
      .value-list {
        display: flex;
        flex-direction: column;
        gap: 0.3rem;
        margin: 0.5rem 0;
      }
      .value-row {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.3rem 0;
      }
      .value-row input[type="text"] {
        flex: 1;
        font-family: monospace;
      }
      .value-row input[type="color"] {
        width: 2rem;
        height: 1.8rem;
        padding: 0;
        border: 1px solid var(--shenas-border-input, #ddd);
        border-radius: 3px;
        cursor: pointer;
      }
      .value-row button {
        padding: 0.2rem 0.5rem;
        font-size: 0.8rem;
      }
      .add-row {
        display: flex;
        gap: 0.5rem;
        margin-top: 0.5rem;
      }
      .add-row input {
        flex: 1;
        font-family: monospace;
      }
      .form-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.5rem 1rem;
        margin-bottom: 0.8rem;
      }
      .form-grid label {
        display: flex;
        flex-direction: column;
        gap: 0.2rem;
      }
      .form-full {
        grid-column: 1 / -1;
      }
      .edit-actions {
        display: flex;
        gap: 0.5rem;
        margin-top: 0.8rem;
      }
      .value-count {
        font-size: 0.8rem;
        color: var(--shenas-text-muted, #888);
      }
      .color-dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 4px;
        vertical-align: middle;
      }
    `,
  ];

  declare apiBase: string;
  declare _sets: CategorySet[];
  declare _loading: boolean;
  declare _editing: string | null;
  declare _creating: boolean;
  declare _message: Message | null;
  declare _newId: string;
  declare _newName: string;
  declare _newDesc: string;
  declare _editValues: CategoryValue[];
  declare _editName: string;
  declare _editDesc: string;
  declare _addValue: string;

  constructor() {
    super();
    this.apiBase = "/api";
    this._sets = [];
    this._loading = true;
    this._editing = null;
    this._creating = false;
    this._message = null;
    this._newId = "";
    this._newName = "";
    this._newDesc = "";
    this._editValues = [];
    this._editName = "";
    this._editDesc = "";
    this._addValue = "";
  }

  connectedCallback(): void {
    super.connectedCallback();
    this._fetchAll();
  }

  async _fetchAll(): Promise<void> {
    this._loading = true;
    const data = await gql(this.apiBase, `{ categorySets }`);
    this._sets = (data?.categorySets as CategorySet[]) || [];
    this._loading = false;
  }

  // -- Create --------------------------------------------------------------

  _startCreate(): void {
    this._creating = true;
    this._editing = null;
    this._newId = "";
    this._newName = "";
    this._newDesc = "";
  }

  _cancelCreate(): void {
    this._creating = false;
  }

  _autoSlug(): void {
    this._newId = this._slugify(this._newName);
  }

  _slugify(s: string): string {
    return s
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");
  }

  async _saveCreate(): Promise<void> {
    if (!this._newId || !this._newName) {
      this._message = { type: "error", text: "ID and name are required" };
      return;
    }
    const { ok } = await gqlFull(
      this.apiBase,
      `mutation($id: String!, $name: String!, $desc: String!) {
        createCategorySet(setId: $id, displayName: $name, description: $desc)
      }`,
      { id: this._newId, name: this._newName, desc: this._newDesc },
    );
    if (ok) {
      this._message = { type: "success", text: `Created "${this._newName}"` };
      this._creating = false;
      await this._fetchAll();
      this._startEdit(this._newId);
    } else {
      this._message = { type: "error", text: "Create failed" };
    }
  }

  // -- Edit ----------------------------------------------------------------

  _startEdit(setId: string): void {
    const s = this._sets.find((x) => x.id === setId);
    if (!s) return;
    this._editing = setId;
    this._creating = false;
    this._editName = s.displayName;
    this._editDesc = s.description;
    this._editValues = [...s.values];
    this._addValue = "";
  }

  _cancelEdit(): void {
    this._editing = null;
  }

  _addValueToList(): void {
    const v = this._addValue.trim();
    if (!v || this._editValues.some((x) => x.value === v)) return;
    this._editValues = [
      ...this._editValues,
      { value: v, sortOrder: this._editValues.length, color: null },
    ];
    this._addValue = "";
  }

  _removeValue(value: string): void {
    this._editValues = this._editValues.filter((v) => v.value !== value);
  }

  _updateValueColor(value: string, color: string): void {
    this._editValues = this._editValues.map((v) =>
      v.value === value ? { ...v, color } : v,
    );
  }

  async _saveEdit(): Promise<void> {
    const valuesJson = JSON.stringify(
      this._editValues.map((v, i) => ({
        value: v.value,
        sortOrder: i,
        color: v.color,
      })),
    );
    const [r1, r2] = await Promise.all([
      gqlFull(
        this.apiBase,
        `mutation($id: String!, $name: String!, $desc: String!) {
          updateCategorySet(setId: $id, displayName: $name, description: $desc)
        }`,
        { id: this._editing, name: this._editName, desc: this._editDesc },
      ),
      gqlFull(
        this.apiBase,
        `mutation($id: String!, $values: String!) {
          updateCategoryValues(setId: $id, values: $values)
        }`,
        { id: this._editing, values: valuesJson },
      ),
    ]);
    if (r1.ok && r2.ok) {
      this._message = { type: "success", text: "Saved" };
      this._editing = null;
      await this._fetchAll();
    } else {
      this._message = { type: "error", text: "Save failed" };
    }
  }

  async _deleteSet(setId: string): Promise<void> {
    const { ok } = await gqlFull(
      this.apiBase,
      `mutation($id: String!) { deleteCategorySet(setId: $id) }`,
      { id: setId },
    );
    if (ok) {
      this._message = { type: "success", text: "Deleted" };
      if (this._editing === setId) this._editing = null;
      await this._fetchAll();
    }
  }

  // -- Render --------------------------------------------------------------

  render() {
    if (this._loading) return html``;
    return html`
      <div>
        ${renderMessage(this._message)}
        ${this._editing ? this._renderEditor() : ""}
        ${this._creating ? this._renderCreateForm() : ""}
        <shenas-data-list
          ?show-add=${!this._creating && !this._editing}
          @add=${() => this._startCreate()}
          .columns=${[
            { key: "displayName", label: "Name" },
            {
              label: "Values",
              render: (s: CategorySet) => html`
                ${s.values.map(
                  (v) => html`${v.color
                    ? html`<span class="color-dot" style="background:${v.color}"></span>`
                    : nothing}${v.value}`,
                ).reduce(
                  (acc: unknown[], cur, i) => (i === 0 ? [cur] : [...acc, ", ", cur]),
                  [],
                )}
                <span class="value-count">(${s.values.length})</span>
              `,
            },
          ]}
          .rows=${this._sets}
          .actions=${(s: CategorySet) => html`
            <button @click=${() => this._startEdit(s.id)}>Edit</button>
            <button class="danger" @click=${() => this._deleteSet(s.id)}>Delete</button>
          `}
          empty-text="No category sets"
        ></shenas-data-list>
      </div>
    `;
  }

  _renderCreateForm() {
    return html`
      <shenas-form-panel title="New category set" submit-label="Create"
        @submit=${this._saveCreate} @cancel=${this._cancelCreate}>
        <div class="form-grid">
          <label class="form-full">
            Name
            <input .value=${this._newName}
              @input=${(e: InputEvent) => { this._newName = (e.target as HTMLInputElement).value; this._autoSlug(); }} />
          </label>
          <label class="form-full">
            Description
            <input .value=${this._newDesc}
              @input=${(e: InputEvent) => { this._newDesc = (e.target as HTMLInputElement).value; }} />
          </label>
        </div>
      </shenas-form-panel>
    `;
  }

  _renderEditor() {
    return html`
      <div class="edit-panel">
        <h3>${this._editName}</h3>
        <div class="form-grid">
          <label>
            Name
            <input .value=${this._editName}
              @input=${(e: InputEvent) => { this._editName = (e.target as HTMLInputElement).value; }} />
          </label>
          <label>
            Description
            <input .value=${this._editDesc}
              @input=${(e: InputEvent) => { this._editDesc = (e.target as HTMLInputElement).value; }} />
          </label>
        </div>
        <strong>Values</strong>
        <div class="value-list">
          ${this._editValues.map(
            (v) => html`
              <div class="value-row">
                <input type="color" .value=${v.color || "#888888"}
                  @input=${(e: InputEvent) => this._updateValueColor(v.value, (e.target as HTMLInputElement).value)} />
                <input type="text" .value=${v.value} readonly />
                <button class="danger" @click=${() => this._removeValue(v.value)}>Remove</button>
              </div>
            `,
          )}
        </div>
        <div class="add-row">
          <input type="text" placeholder="Add value..." .value=${this._addValue}
            @input=${(e: InputEvent) => { this._addValue = (e.target as HTMLInputElement).value; }}
            @keydown=${(e: KeyboardEvent) => { if (e.key === "Enter") { e.preventDefault(); this._addValueToList(); } }} />
          <button @click=${this._addValueToList}>Add</button>
        </div>
        <div class="edit-actions">
          <button @click=${this._saveEdit}>Save</button>
          <button @click=${this._cancelEdit}>Cancel</button>
        </div>
      </div>
    `;
  }
}

customElements.define("shenas-categories", CategoriesPage);
