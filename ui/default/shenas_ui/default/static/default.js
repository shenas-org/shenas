var _=Object.defineProperty;var $=(d,t,e)=>t in d?_(d,t,{enumerable:!0,configurable:!0,writable:!0,value:e}):d[t]=e;var o=(d,t,e)=>$(d,typeof t!="symbol"?t+"":t,e);import{LitElement as l,css as c,html as a}from"lit";import{Router as w}from"@lit-labs/router";class h extends l{constructor(){super();o(this,"_router",new w(this,[{path:"/",render:()=>this._renderDb()},{path:"/database",render:()=>this._renderDb()},{path:"/pipes",render:()=>this._renderPipes()},{path:"/settings",render:()=>this._renderSettings("pipe")},{path:"/settings/:kind",render:({kind:e})=>this._renderSettings(e)},{path:"/settings/:kind/:name",render:({kind:e,name:s})=>this._renderPluginDetail(e,s)},{path:"/settings/:kind/:name/transforms",render:({kind:e,name:s})=>this._renderPluginDetail(e,s,"transforms")},{path:"/:tab",render:({tab:e})=>this._renderDynamicTab(e)}]));this.apiBase="/api",this._pipes=[],this._dbStatus=null,this._components=[],this._loading=!0,this._loadedScripts=new Set,this._elementCache=new Map}connectedCallback(){super.connectedCallback(),this._fetchData()}async _fetchData(){this._loading=!0;try{const[e,s,i]=await Promise.all([this._fetch("/plugins/pipe"),this._fetch("/db/status"),this._fetch("/components")]);this._pipes=e||[],this._dbStatus=s,this._components=i||[]}catch(e){console.error("Failed to fetch data:",e)}this._loading=!1}async _fetch(e){const s=await fetch(`${this.apiBase}${e}`);return s.ok?s.json():null}_activeTab(){return(window.location.pathname.replace(/^\/+/,"")||"database").split("/")[0]}render(){if(this._loading)return a`<p class="loading">Loading...</p>`;const e=this._activeTab();return a`
      <div class="header">
        <img src="/static/images/shenas.png" alt="shenas" />
        <h1>shenas</h1>
      </div>

      <div class="tabs" role="tablist">
        ${this._tabLink("database","Database",e)}
        ${this._tabLink("pipes","Pipes",e)}
        ${this._components.map(s=>this._tabLink(s.name,s.name,e))}
        ${this._tabLink("settings","Settings",e)}
      </div>

      ${this._router.outlet()}
    `}_tabLink(e,s,i){return a`
      <a
        class="tab"
        role="tab"
        href="/${e}"
        aria-selected=${i===e}
      >
        ${s}
      </a>
    `}_renderDynamicTab(e){const s=this._components.find(i=>i.name===e);if(!s)return a`<p class="empty">Unknown page: ${e}</p>`;if(!this._loadedScripts.has(s.js)){this._loadedScripts=new Set([...this._loadedScripts,s.js]);const i=document.createElement("script");i.type="module",i.src=s.js,document.head.appendChild(i)}return a`<div class="component-host">
      ${this._getOrCreateElement(s)}
    </div>`}_renderPluginDetail(e,s,i="details"){return a`<shenas-plugin-detail
      api-base="${this.apiBase}"
      kind="${e}"
      name="${s}"
      active-tab="${i}"
    ></shenas-plugin-detail>`}_renderSettings(e){return a`<shenas-settings
      api-base="${this.apiBase}"
      active-kind="${e||"pipe"}"
      .onNavigate=${s=>{this._router.goto(`/settings/${s}`)}}
    ></shenas-settings>`}_getOrCreateElement(e){if(!this._elementCache.has(e.name)){const s=document.createElement(e.tag);s.setAttribute("api-base",this.apiBase),this._elementCache.set(e.name,s)}return this._elementCache.get(e.name)}_renderDb(){const e=this._dbStatus;return e?a`
      <div class="status">
        <p>Path: <code>${e.db_path}</code></p>
        ${e.size_mb!=null?a`<p>Size: ${e.size_mb} MB</p>`:a`<p>Not created yet</p>`}
      </div>
      ${(e.schemas||[]).map(s=>a`
          <h3>${s.name}</h3>
          ${s.tables.map(i=>a`
              <div class="schema-row">
                <span>${i.name}</span>
                <span class="meta">
                  ${i.rows} rows
                  ${i.earliest?a` &middot; ${i.earliest} - ${i.latest}`:""}
                </span>
              </div>
            `)}
        `)}
    `:a`<p class="empty">No database info available</p>`}_renderPipes(){return this._pipes.length===0?a`<p class="empty">No pipes installed</p>`:a`
      <div class="cards">
        ${this._pipes.map(e=>a`
            <div class="card">
              <h3>${e.display_name||e.name}</h3>
              <div class="meta">${e.version}</div>
              ${e.description?a`<div class="desc">${e.description}</div>`:""}
            </div>
          `)}
      </div>
    `}}o(h,"properties",{apiBase:{type:String,attribute:"api-base"},_pipes:{state:!0},_dbStatus:{state:!0},_components:{state:!0},_loading:{state:!0},_loadedScripts:{state:!0}}),o(h,"styles",c`
    :host {
      display: block;
      max-width: 960px;
      margin: 0 auto;
      padding: 2rem 1rem;
      color: #222;
    }
    .header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 1.5rem;
    }
    .header img {
      width: 48px;
      height: 48px;
    }
    .header h1 {
      margin: 0;
      font-size: 1.5rem;
    }
    .tabs {
      display: flex;
      gap: 0;
      border-bottom: 2px solid #e0e0e0;
      margin-bottom: 1.5rem;
    }
    .tab {
      padding: 0.6rem 1.2rem;
      cursor: pointer;
      border: none;
      background: none;
      font-size: 0.95rem;
      color: #666;
      border-bottom: 2px solid transparent;
      margin-bottom: -2px;
      transition: color 0.15s, border-color 0.15s;
      text-decoration: none;
    }
    .tab:hover {
      color: #222;
    }
    .tab[aria-selected="true"] {
      color: #222;
      border-bottom-color: #0066cc;
      font-weight: 600;
    }
    .cards {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 1rem;
      margin: 1rem 0;
    }
    .card {
      border: 1px solid #e0e0e0;
      border-radius: 8px;
      padding: 1rem;
      background: #fff;
    }
    .card h3 {
      margin: 0 0 0.5rem;
      font-size: 1rem;
    }
    .card .meta {
      color: #888;
      font-size: 0.85rem;
    }
    .card .desc {
      margin-top: 0.5rem;
      font-size: 0.85rem;
      color: #555;
    }
    .status {
      font-size: 0.9rem;
      color: #555;
    }
    .status code {
      background: #f0f0f0;
      padding: 2px 6px;
      border-radius: 3px;
    }
    .schema-row {
      display: flex;
      justify-content: space-between;
      padding: 0.3rem 0;
      border-bottom: 1px solid #f0f0f0;
    }
    .schema-row:last-child {
      border-bottom: none;
    }
    a {
      color: #0066cc;
      text-decoration: none;
    }
    a:hover {
      text-decoration: underline;
    }
    .loading {
      color: #888;
      font-style: italic;
    }
    .empty {
      color: #888;
      padding: 1rem 0;
    }
    .component-host {
      margin-top: 1rem;
    }
  `);customElements.define("shenas-app",h);const p=[{id:"pipe",label:"Pipes"},{id:"schema",label:"Schemas"},{id:"component",label:"Components"},{id:"ui",label:"UI"}];class m extends l{constructor(){super(),this.apiBase="/api",this.activeKind="pipe",this.onNavigate=null,this._plugins={},this._loading=!0,this._actionMessage=null}connectedCallback(){super.connectedCallback(),this._fetchAll()}async _fetchAll(){this._loading=!0;const t={};await Promise.all(p.map(async({id:e})=>{const s=await fetch(`${this.apiBase}/plugins/${e}`);t[e]=s.ok?await s.json():[]})),this._plugins=t,this._loading=!1}async _remove(t,e){this._actionMessage=null;const i=await(await fetch(`${this.apiBase}/plugins/${t}/${e}`,{method:"DELETE"})).json();i.ok?(this._actionMessage={type:"success",text:i.message},await this._fetchAll()):this._actionMessage={type:"error",text:i.message||"Remove failed"}}async _toggleEnabled(t,e,s){this._actionMessage=null;const i=s?"disable":"enable",n=await(await fetch(`${this.apiBase}/plugins/${t}/${e}/${i}`,{method:"POST"})).json();n.ok?(this._actionMessage={type:"success",text:n.message},await this._fetchAll()):this._actionMessage={type:"error",text:n.message||`${i} failed`}}async _install(t){var b,f;const e=this.shadowRoot.querySelector(`#install-${t}`),s=(b=e==null?void 0:e.value)==null?void 0:b.trim();if(!s)return;this._actionMessage=null;const n=(f=(await(await fetch(`${this.apiBase}/plugins/${t}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({names:[s],skip_verify:!0})})).json()).results)==null?void 0:f[0];n!=null&&n.ok?(this._actionMessage={type:"success",text:n.message},e.value="",await this._fetchAll()):this._actionMessage={type:"error",text:(n==null?void 0:n.message)||"Install failed"}}render(){return this._loading?a`<p class="loading">Loading plugins...</p>`:a`
      ${this._actionMessage?a`<div class="message ${this._actionMessage.type}">
            ${this._actionMessage.text}
          </div>`:""}
      <div class="layout">
        <nav class="sidebar">
          <ul>
            ${p.map(({id:t,label:e})=>a`
                <li>
                  <a
                    href="/settings/${t}"
                    aria-selected=${this.activeKind===t}
                  >
                    ${e}
                    <span style="color:#aaa; font-weight:normal">
                      (${(this._plugins[t]||[]).length})
                    </span>
                  </a>
                </li>
              `)}
          </ul>
        </nav>
        <div class="content">${this._renderKind(this.activeKind)}</div>
      </div>
    `}_renderKind(t){var i;const e=this._plugins[t]||[],s=((i=p.find(r=>r.id===t))==null?void 0:i.label)||t;return a`
      <h3>${s}</h3>
      ${e.length>0?a`
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Version</th>
                  <th>Added</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                ${e.map(r=>a`
                    <tr style="${r.enabled===!1?"opacity: 0.5":""}">
                      <td class="name"><a href="/settings/${t}/${r.name}">${r.display_name||r.name}</a></td>
                      <td class="version">${r.version}</td>
                      <td class="version">${r.added_at?r.added_at.slice(0,10):""}</td>
                      <td class="status-cell">
                        <span class="status-dot ${r.enabled===!1?"red":"green"}"></span>
                      </td>
                    </tr>
                  `)}
              </tbody>
            </table>
          `:a`<p class="empty">No ${s.toLowerCase()} installed</p>`}
      <div class="install-row">
        <input
          id="install-${t}"
          type="text"
          placeholder="Plugin name"
          @keydown=${r=>r.key==="Enter"&&this._install(t)}
        />
        <button class="action" @click=${()=>this._install(t)}>
          Install
        </button>
      </div>
    `}}o(m,"properties",{apiBase:{type:String,attribute:"api-base"},activeKind:{type:String,attribute:"active-kind"},onNavigate:{type:Function},_plugins:{state:!0},_loading:{state:!0},_actionMessage:{state:!0}}),o(m,"styles",c`
    :host {
      display: block;
    }
    .layout {
      display: flex;
      gap: 2rem;
    }
    .sidebar {
      min-width: 140px;
      flex-shrink: 0;
    }
    .sidebar ul {
      list-style: none;
      padding: 0;
      margin: 0;
    }
    .sidebar li {
      margin: 0;
    }
    .sidebar a {
      display: block;
      width: 100%;
      text-align: left;
      padding: 0.5rem 0.8rem;
      border: none;
      background: none;
      cursor: pointer;
      font-size: 0.9rem;
      color: #666;
      border-radius: 4px;
      border-left: 3px solid transparent;
    }
    .sidebar a:hover {
      background: #f5f5f5;
      color: #222;
    }
    .sidebar a[aria-selected="true"] {
      background: #f0f4ff;
      color: #222;
      font-weight: 600;
      border-left-color: #0066cc;
    }
    .content {
      flex: 1;
      min-width: 0;
    }
    .content h3 {
      font-size: 1rem;
      margin: 0 0 1rem;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9rem;
    }
    th {
      text-align: left;
      padding: 0.4rem 0.6rem;
      color: #666;
      font-weight: 500;
      border-bottom: 1px solid #e0e0e0;
    }
    td {
      padding: 0.4rem 0.6rem;
      border-bottom: 1px solid #f0f0f0;
    }
    .name {
      font-weight: 600;
    }
    .name a {
      color: #0066cc;
      text-decoration: none;
    }
    .name a:hover {
      text-decoration: underline;
    }
    .version {
      color: #888;
      font-family: monospace;
      font-size: 0.85rem;
    }
    .desc {
      color: #555;
      max-width: 300px;
    }
    .actions {
      white-space: nowrap;
    }
    button.action {
      padding: 0.3rem 0.7rem;
      border: 1px solid #ddd;
      border-radius: 4px;
      background: #fff;
      cursor: pointer;
      font-size: 0.8rem;
      margin-left: 0.3rem;
    }
    button.action:hover {
      background: #f5f5f5;
    }
    button.remove {
      color: #c00;
      border-color: #e8c0c0;
    }
    button.remove:hover {
      background: #fef0f0;
    }
    .install-row {
      display: flex;
      gap: 0.5rem;
      margin-top: 1rem;
      align-items: center;
    }
    .install-row input {
      padding: 0.4rem 0.6rem;
      border: 1px solid #ddd;
      border-radius: 4px;
      font-size: 0.85rem;
      flex: 1;
      max-width: 200px;
    }
    .message {
      padding: 0.5rem 0.8rem;
      border-radius: 4px;
      margin-bottom: 1rem;
      font-size: 0.85rem;
    }
    .message.success {
      background: #e8f5e9;
      color: #2e7d32;
    }
    .message.error {
      background: #fce4ec;
      color: #c62828;
    }
    .empty {
      color: #888;
      padding: 0.5rem 0;
    }
    .status-dot {
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 50%;
    }
    .status-dot.green {
      background: #2e7d32;
    }
    .status-dot.red {
      background: #c62828;
    }
    .loading {
      color: #888;
      font-style: italic;
    }
  `);customElements.define("shenas-settings",m);class g extends l{constructor(){super(),this.apiBase="/api",this.kind="",this.name="",this.activeTab="details",this._info=null,this._loading=!0,this._message=null}willUpdate(t){(t.has("kind")||t.has("name"))&&this._fetchInfo()}async _fetchInfo(){if(!this.kind||!this.name)return;this._loading=!0,this._message=null;const t=await fetch(`${this.apiBase}/plugins/${this.kind}/${this.name}/info`);this._info=t.ok?await t.json():null,this._loading=!1}async _toggle(){var i;const t=((i=this._info)==null?void 0:i.enabled)!==!1?"disable":"enable",s=await(await fetch(`${this.apiBase}/plugins/${this.kind}/${this.name}/${t}`,{method:"POST"})).json();this._message={type:s.ok?"success":"error",text:s.message||`${t} failed`},await this._fetchInfo()}async _remove(){const e=await(await fetch(`${this.apiBase}/plugins/${this.kind}/${this.name}`,{method:"DELETE"})).json();e.ok?(window.history.pushState({},"",`/settings/${this.kind}`),window.dispatchEvent(new PopStateEvent("popstate"))):this._message={type:"error",text:e.message||"Remove failed"}}render(){if(this._loading)return a`<p class="loading">Loading...</p>`;if(!this._info)return a`<p>Plugin not found.</p>`;const t=this._info,e=t.enabled!==!1,s=`/settings/${this.kind}/${this.name}`;return a`
      <a class="back" href="/settings/${this.kind}">&larr; Back to ${this.kind}s</a>

      <h2>${t.display_name||t.name}</h2>
      <span class="kind-badge">${t.kind}</span>

      <div class="detail-tabs">
        <a class="detail-tab" href="${s}" aria-selected=${this.activeTab==="details"}>Details</a>
        ${this.kind==="pipe"?a`<a class="detail-tab" href="${s}/transforms" aria-selected=${this.activeTab==="transforms"}>Transforms</a>`:""}
      </div>

      ${this.activeTab==="transforms"?a`<shenas-transforms api-base="${this.apiBase}" source="${this.name}"></shenas-transforms>`:this._renderDetails(t,e)}

      ${this._message?a`<div class="message ${this._message.type}">
            ${this._message.text}
          </div>`:""}
    `}_renderDetails(t,e){return a`
      ${t.description?a`<div class="description">${t.description}</div>`:""}

      <div class="state-table">
        <div class="state-row">
          <span class="state-label">Status</span>
          <span class="state-value">
            <span class="status-dot ${e?"green":"red"}"></span>
          </span>
        </div>
        ${this._stateRow("Added",t.added_at)}
        ${this._stateRow("Updated",t.updated_at)}
        ${this._stateRow("Status changed",t.status_changed_at)}
      </div>

      <div class="actions">
        <button @click=${this._toggle}>
          ${e?"Disable":"Enable"}
        </button>
        <button class="danger" @click=${this._remove}>Remove</button>
      </div>
    `}_stateRow(t,e){return e?a`
      <div class="state-row">
        <span class="state-label">${t}</span>
        <span class="state-value">${e.slice(0,19)}</span>
      </div>
    `:""}}o(g,"properties",{apiBase:{type:String,attribute:"api-base"},kind:{type:String},name:{type:String},activeTab:{type:String,attribute:"active-tab"},_info:{state:!0},_loading:{state:!0},_message:{state:!0}}),o(g,"styles",c`
    :host {
      display: block;
    }
    .back {
      color: #0066cc;
      text-decoration: none;
      font-size: 0.9rem;
      display: inline-block;
      margin-bottom: 1rem;
    }
    .back:hover {
      text-decoration: underline;
    }
    h2 {
      margin: 0 0 0.3rem;
      font-size: 1.3rem;
    }
    .kind-badge {
      display: inline-block;
      background: #f0f0f0;
      color: #555;
      padding: 0.15rem 0.5rem;
      border-radius: 3px;
      font-size: 0.8rem;
      margin-bottom: 1rem;
    }
    .description {
      color: #444;
      line-height: 1.6;
      margin: 1rem 0;
      white-space: pre-line;
    }
    .state-table {
      margin: 1.5rem 0;
    }
    .state-row {
      display: flex;
      padding: 0.4rem 0;
      border-bottom: 1px solid #f0f0f0;
      font-size: 0.9rem;
    }
    .state-row:last-child {
      border-bottom: none;
    }
    .state-label {
      width: 120px;
      color: #888;
      flex-shrink: 0;
    }
    .state-value {
      color: #333;
    }
    .enabled {
      color: #2e7d32;
      font-weight: 600;
    }
    .disabled {
      color: #c62828;
      font-weight: 600;
    }
    .status-dot {
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      margin-right: 6px;
      vertical-align: middle;
    }
    .status-dot.green {
      background: #2e7d32;
    }
    .status-dot.red {
      background: #c62828;
    }
    .actions {
      display: flex;
      gap: 0.6rem;
      margin-top: 1.5rem;
    }
    button {
      padding: 0.5rem 1rem;
      border: 1px solid #ddd;
      border-radius: 4px;
      background: #fff;
      cursor: pointer;
      font-size: 0.9rem;
    }
    button:hover {
      background: #f5f5f5;
    }
    button.danger {
      color: #c00;
      border-color: #e8c0c0;
    }
    button.danger:hover {
      background: #fef0f0;
    }
    .detail-tabs {
      display: flex;
      gap: 0;
      border-bottom: 2px solid #e0e0e0;
      margin: 1rem 0;
    }
    .detail-tab {
      padding: 0.5rem 1rem;
      border: none;
      background: none;
      cursor: pointer;
      font-size: 0.9rem;
      color: #666;
      border-bottom: 2px solid transparent;
      margin-bottom: -2px;
      text-decoration: none;
    }
    .detail-tab:hover {
      color: #222;
    }
    .detail-tab[aria-selected="true"] {
      color: #222;
      border-bottom-color: #0066cc;
      font-weight: 600;
    }
    .message {
      padding: 0.5rem 0.8rem;
      border-radius: 4px;
      margin-top: 1rem;
      font-size: 0.85rem;
    }
    .message.success {
      background: #e8f5e9;
      color: #2e7d32;
    }
    .message.error {
      background: #fce4ec;
      color: #c62828;
    }
    .loading {
      color: #888;
      font-style: italic;
    }
  `);customElements.define("shenas-plugin-detail",g);class u extends l{constructor(){super(),this.apiBase="/api",this.source="",this._transforms=[],this._loading=!0,this._editing=null,this._editSql="",this._message=null,this._previewRows=null}connectedCallback(){super.connectedCallback(),this._fetchAll()}async _fetchAll(){this._loading=!0;const t=this.source?`?source=${this.source}`:"",e=await fetch(`${this.apiBase}/transforms${t}`);this._transforms=e.ok?await e.json():[],this._loading=!1}async _toggle(t){const e=t.enabled?"disable":"enable";await fetch(`${this.apiBase}/transforms/${t.id}/${e}`,{method:"POST"}),await this._fetchAll()}async _delete(t){const s=await(await fetch(`${this.apiBase}/transforms/${t.id}`,{method:"DELETE"})).json();s.ok?(this._message={type:"success",text:s.message},await this._fetchAll()):this._message={type:"error",text:s.detail||s.message||"Delete failed"}}_startEdit(t){this._editing=t.id,this._editSql=t.sql,this._previewRows=null}_cancelEdit(){this._editing=null,this._editSql="",this._previewRows=null}async _saveEdit(){const t=await fetch(`${this.apiBase}/transforms/${this._editing}`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({sql:this._editSql})});if(t.ok)this._message={type:"success",text:"Transform updated"},this._editing=null,await this._fetchAll();else{const e=await t.json();this._message={type:"error",text:e.detail||"Update failed"}}}async _preview(){const t=await fetch(`${this.apiBase}/transforms/${this._editing}/test?limit=5`,{method:"POST"});if(t.ok)this._previewRows=await t.json();else{const e=await t.json();this._message={type:"error",text:e.detail||"Preview failed"}}}render(){return this._loading?a`<p class="loading">Loading transforms...</p>`:a`
      ${this._message?a`<div class="message ${this._message.type}">
            ${this._message.text}
          </div>`:""}
      ${this._editing?this._renderEditor():""}
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Source</th>
            <th>Target</th>
            <th>Description</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          ${this._transforms.map(t=>a`
              <tr class="${t.enabled?"":"disabled-row"}">
                <td class="id">${t.id}</td>
                <td class="mapping">
                  ${t.source_duckdb_schema}.${t.source_duckdb_table}
                </td>
                <td class="mapping">
                  ${t.target_duckdb_schema}.${t.target_duckdb_table}
                </td>
                <td class="desc">
                  ${t.description||""}
                  ${t.is_default?a`<span class="default-badge">default</span>`:""}
                </td>
                <td class="status">
                  <span class="status-dot ${t.enabled?"green":"red"}"></span>
                </td>
                <td class="actions">
                  ${t.is_default?a`<button @click=${()=>this._startEdit(t)}>View</button>`:a`<button @click=${()=>this._startEdit(t)}>Edit</button>`}
                  <button @click=${()=>this._toggle(t)}>
                    ${t.enabled?"Disable":"Enable"}
                  </button>
                  ${t.is_default?"":a`<button
                        class="danger"
                        @click=${()=>this._delete(t)}
                      >
                        Delete
                      </button>`}
                </td>
              </tr>
            `)}
        </tbody>
      </table>
    `}_renderEditor(){const t=this._transforms.find(s=>s.id===this._editing);if(!t)return"";const e=t.is_default;return a`
      <div class="edit-panel">
        <h3>
          ${e?"View":"Edit"}: ${t.source_duckdb_schema}.${t.source_duckdb_table} ->
          ${t.target_duckdb_schema}.${t.target_duckdb_table}
        </h3>
        <textarea
          .value=${this._editSql}
          @input=${s=>this._editSql=s.target.value}
          ?readonly=${e}
          class="${e?"readonly":""}"
        ></textarea>
        <div class="edit-actions">
          ${e?"":a`<button @click=${this._saveEdit}>Save</button>`}
          <button @click=${this._preview}>Preview</button>
          <button @click=${this._cancelEdit}>${e?"Close":"Cancel"}</button>
        </div>
        ${this._previewRows?this._renderPreview():""}
      </div>
    `}_renderPreview(){if(!this._previewRows||this._previewRows.length===0)return a`<p class="loading">No preview rows</p>`;const t=Object.keys(this._previewRows[0]);return a`
      <div class="preview-table">
        <table>
          <thead>
            <tr>
              ${t.map(e=>a`<th>${e}</th>`)}
            </tr>
          </thead>
          <tbody>
            ${this._previewRows.map(e=>a`
                <tr>
                  ${t.map(s=>a`<td>${e[s]}</td>`)}
                </tr>
              `)}
          </tbody>
        </table>
      </div>
    `}}o(u,"properties",{apiBase:{type:String,attribute:"api-base"},source:{type:String},_transforms:{state:!0},_loading:{state:!0},_editing:{state:!0},_editSql:{state:!0},_message:{state:!0},_previewRows:{state:!0}}),o(u,"styles",c`
    :host {
      display: block;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9rem;
    }
    th {
      text-align: left;
      padding: 0.4rem 0.6rem;
      color: #666;
      font-weight: 500;
      border-bottom: 1px solid #e0e0e0;
    }
    td {
      padding: 0.4rem 0.6rem;
      border-bottom: 1px solid #f0f0f0;
    }
    .id {
      color: #888;
      width: 40px;
    }
    .mapping {
      font-family: monospace;
      font-size: 0.85rem;
    }
    .desc {
      color: #555;
    }
    .status {
      font-size: 0.85rem;
    }
    .status-dot {
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      margin-right: 4px;
      vertical-align: middle;
    }
    .status-dot.green {
      background: #2e7d32;
    }
    .status-dot.red {
      background: #c62828;
    }
    .actions {
      white-space: nowrap;
    }
    button {
      padding: 0.3rem 0.6rem;
      border: 1px solid #ddd;
      border-radius: 4px;
      background: #fff;
      cursor: pointer;
      font-size: 0.8rem;
      margin-left: 0.3rem;
    }
    button:hover {
      background: #f5f5f5;
    }
    button.danger {
      color: #c00;
      border-color: #e8c0c0;
    }
    .default-badge {
      font-size: 0.75rem;
      color: #888;
      background: #f0f0f0;
      padding: 1px 5px;
      border-radius: 3px;
      margin-left: 4px;
    }
    .edit-panel {
      margin: 1rem 0;
      padding: 1rem;
      border: 1px solid #e0e0e0;
      border-radius: 8px;
      background: #fafafa;
    }
    .edit-panel h3 {
      margin: 0 0 0.8rem;
      font-size: 1rem;
    }
    textarea {
      width: 100%;
      min-height: 120px;
      font-family: monospace;
      font-size: 0.85rem;
      padding: 0.5rem;
      border: 1px solid #ddd;
      border-radius: 4px;
      resize: vertical;
      box-sizing: border-box;
    }
    textarea.readonly {
      background: #f5f5f5;
      color: #666;
      cursor: default;
    }
    .edit-actions {
      display: flex;
      gap: 0.5rem;
      margin-top: 0.8rem;
    }
    .preview-table {
      margin-top: 1rem;
      max-height: 300px;
      overflow: auto;
    }
    .preview-table table {
      font-size: 0.8rem;
    }
    .message {
      padding: 0.5rem 0.8rem;
      border-radius: 4px;
      margin-bottom: 1rem;
      font-size: 0.85rem;
    }
    .message.success {
      background: #e8f5e9;
      color: #2e7d32;
    }
    .message.error {
      background: #fce4ec;
      color: #c62828;
    }
    .loading {
      color: #888;
      font-style: italic;
    }
    .disabled-row {
      opacity: 0.5;
    }
  `);customElements.define("shenas-transforms",u);
