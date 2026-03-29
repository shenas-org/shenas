var g=Object.defineProperty;var f=(r,e,t)=>e in r?g(r,e,{enumerable:!0,configurable:!0,writable:!0,value:t}):r[e]=t;var l=(r,e,t)=>f(r,typeof e!="symbol"?e+"":e,t);import{LitElement as b,css as u,html as s}from"lit";class d extends b{constructor(){super(),this.apiBase="/api",this._pipes=[],this._dbStatus=null,this._components=[],this._loading=!0,this._activeTab="database",this._loadedScripts=new Set,this._elementCache=new Map}connectedCallback(){super.connectedCallback(),this._fetchData()}async _fetchData(){this._loading=!0;try{const[e,t,a]=await Promise.all([this._fetch("/plugins/pipe"),this._fetch("/db/status"),this._fetch("/components")]);this._pipes=e||[],this._dbStatus=t,this._components=a||[]}catch(e){console.error("Failed to fetch data:",e)}this._loading=!1}async _fetch(e){const t=await fetch(`${this.apiBase}${e}`);return t.ok?t.json():null}_selectTab(e){this._activeTab=e;const t=this._components.find(a=>a.name===e);if(t&&!this._loadedScripts.has(t.js)){this._loadedScripts=new Set([...this._loadedScripts,t.js]);const a=document.createElement("script");a.type="module",a.src=t.js,document.head.appendChild(a)}}render(){return this._loading?s`<p class="loading">Loading...</p>`:s`
      <div class="header">
        <img src="/static/images/shenas.png" alt="shenas" />
        <h1>shenas</h1>
      </div>

      <div class="tabs" role="tablist">
        ${this._renderTab("database","Database")}
        ${this._renderTab("pipes","Pipes")}
        ${this._components.map(e=>this._renderTab(e.name,e.name))}
        ${this._renderTab("settings","Settings")}
      </div>

      ${this._activeTab==="database"?this._renderDb():""}
      ${this._activeTab==="pipes"?this._renderPipes():""}
      ${this._renderComponentTab()}
      ${this._activeTab==="settings"?s`<shenas-settings api-base="${this.apiBase}"></shenas-settings>`:""}
    `}_renderTab(e,t){return s`
      <button
        class="tab"
        role="tab"
        aria-selected=${this._activeTab===e}
        @click=${()=>this._selectTab(e)}
      >
        ${t}
      </button>
    `}_renderComponentTab(){const e=this._components.find(t=>t.name===this._activeTab);return e?s`
      <div class="component-host">${this._getOrCreateElement(e)}</div>
    `:s``}_getOrCreateElement(e){if(!this._elementCache.has(e.name)){const t=document.createElement(e.tag);t.setAttribute("api-base",this.apiBase),this._elementCache.set(e.name,t)}return this._elementCache.get(e.name)}_renderDb(){const e=this._dbStatus;return e?s`
      <div class="status">
        <p>Path: <code>${e.db_path}</code></p>
        ${e.size_mb!=null?s`<p>Size: ${e.size_mb} MB</p>`:s`<p>Not created yet</p>`}
      </div>
      ${(e.schemas||[]).map(t=>s`
          <h3>${t.name}</h3>
          ${t.tables.map(a=>s`
              <div class="schema-row">
                <span>${a.name}</span>
                <span class="meta">
                  ${a.rows} rows
                  ${a.earliest?s` &middot; ${a.earliest} - ${a.latest}`:""}
                </span>
              </div>
            `)}
        `)}
    `:s`<p class="empty">No database info available</p>`}_renderPipes(){return this._pipes.length===0?s`<p class="empty">No pipes installed</p>`:s`
      <div class="cards">
        ${this._pipes.map(e=>s`
            <div class="card">
              <h3>${e.name}</h3>
              <div class="meta">${e.version}</div>
              ${e.description?s`<div class="desc">${e.description}</div>`:""}
            </div>
          `)}
      </div>
    `}}l(d,"properties",{apiBase:{type:String,attribute:"api-base"},_pipes:{state:!0},_dbStatus:{state:!0},_components:{state:!0},_loading:{state:!0},_activeTab:{state:!0},_loadedScripts:{state:!0}}),l(d,"styles",u`
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
  `);customElements.define("shenas-app",d);const c=[{id:"pipe",label:"Pipes"},{id:"schema",label:"Schemas"},{id:"component",label:"Components"},{id:"ui",label:"UI"}];class p extends b{constructor(){super(),this.apiBase="/api",this._plugins={},this._loading=!0,this._activeKind="pipe",this._actionMessage=null}connectedCallback(){super.connectedCallback(),this._fetchAll()}async _fetchAll(){this._loading=!0;const e={};await Promise.all(c.map(async({id:t})=>{const a=await fetch(`${this.apiBase}/plugins/${t}`);e[t]=a.ok?await a.json():[]})),this._plugins=e,this._loading=!1}async _remove(e,t){this._actionMessage=null;const n=await(await fetch(`${this.apiBase}/plugins/${e}/${t}`,{method:"DELETE"})).json();n.ok?(this._actionMessage={type:"success",text:n.message},await this._fetchAll()):this._actionMessage={type:"error",text:n.message||"Remove failed"}}async _install(e){var m,h;const t=this.shadowRoot.querySelector(`#install-${e}`),a=(m=t==null?void 0:t.value)==null?void 0:m.trim();if(!a)return;this._actionMessage=null;const o=(h=(await(await fetch(`${this.apiBase}/plugins/${e}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({names:[a],skip_verify:!0})})).json()).results)==null?void 0:h[0];o!=null&&o.ok?(this._actionMessage={type:"success",text:o.message},t.value="",await this._fetchAll()):this._actionMessage={type:"error",text:(o==null?void 0:o.message)||"Install failed"}}render(){return this._loading?s`<p class="loading">Loading plugins...</p>`:s`
      ${this._actionMessage?s`<div class="message ${this._actionMessage.type}">
            ${this._actionMessage.text}
          </div>`:""}
      <div class="layout">
        <nav class="sidebar">
          <ul>
            ${c.map(({id:e,label:t})=>s`
                <li>
                  <button
                    aria-selected=${this._activeKind===e}
                    @click=${()=>{this._activeKind=e,this._actionMessage=null}}
                  >
                    ${t}
                    <span style="color:#aaa; font-weight:normal">
                      (${(this._plugins[e]||[]).length})
                    </span>
                  </button>
                </li>
              `)}
          </ul>
        </nav>
        <div class="content">${this._renderKind(this._activeKind)}</div>
      </div>
    `}_renderKind(e){var n;const t=this._plugins[e]||[],a=((n=c.find(i=>i.id===e))==null?void 0:n.label)||e;return s`
      <h3>${a}</h3>
      ${t.length>0?s`
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Version</th>
                  <th>Description</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                ${t.map(i=>s`
                    <tr>
                      <td class="name">${i.name}</td>
                      <td class="version">${i.version}</td>
                      <td class="desc">${i.description||""}</td>
                      <td class="actions">
                        <button
                          class="action remove"
                          @click=${()=>this._remove(e,i.name)}
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  `)}
              </tbody>
            </table>
          `:s`<p class="empty">No ${a.toLowerCase()} installed</p>`}
      <div class="install-row">
        <input
          id="install-${e}"
          type="text"
          placeholder="Plugin name"
          @keydown=${i=>i.key==="Enter"&&this._install(e)}
        />
        <button class="action" @click=${()=>this._install(e)}>
          Install
        </button>
      </div>
    `}}l(p,"properties",{apiBase:{type:String,attribute:"api-base"},_plugins:{state:!0},_loading:{state:!0},_activeKind:{state:!0},_actionMessage:{state:!0}}),l(p,"styles",u`
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
    .sidebar button {
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
    .sidebar button:hover {
      background: #f5f5f5;
      color: #222;
    }
    .sidebar button[aria-selected="true"] {
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
    .loading {
      color: #888;
      font-style: italic;
    }
  `);customElements.define("shenas-settings",p);
