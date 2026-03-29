var b=Object.defineProperty;var f=(n,s,e)=>s in n?b(n,s,{enumerable:!0,configurable:!0,writable:!0,value:e}):n[s]=e;var l=(n,s,e)=>f(n,typeof s!="symbol"?s+"":s,e);import{LitElement as g,css as u,html as a}from"lit";import{Router as _}from"@lit-labs/router";class c extends g{constructor(){super();l(this,"_router",new _(this,[{path:"/",render:()=>this._renderDb()},{path:"/database",render:()=>this._renderDb()},{path:"/pipes",render:()=>this._renderPipes()},{path:"/settings",render:()=>this._renderSettings("pipe")},{path:"/settings/:kind",render:({kind:e})=>this._renderSettings(e)},{path:"/:tab",render:({tab:e})=>this._renderDynamicTab(e)}]));this.apiBase="/api",this._pipes=[],this._dbStatus=null,this._components=[],this._loading=!0,this._loadedScripts=new Set,this._elementCache=new Map}connectedCallback(){super.connectedCallback(),this._fetchData()}async _fetchData(){this._loading=!0;try{const[e,t,i]=await Promise.all([this._fetch("/plugins/pipe"),this._fetch("/db/status"),this._fetch("/components")]);this._pipes=e||[],this._dbStatus=t,this._components=i||[]}catch(e){console.error("Failed to fetch data:",e)}this._loading=!1}async _fetch(e){const t=await fetch(`${this.apiBase}${e}`);return t.ok?t.json():null}_activeTab(){return(window.location.pathname.replace(/^\/+/,"")||"database").split("/")[0]}render(){if(this._loading)return a`<p class="loading">Loading...</p>`;const e=this._activeTab();return a`
      <div class="header">
        <img src="/static/images/shenas.png" alt="shenas" />
        <h1>shenas</h1>
      </div>

      <div class="tabs" role="tablist">
        ${this._tabLink("database","Database",e)}
        ${this._tabLink("pipes","Pipes",e)}
        ${this._components.map(t=>this._tabLink(t.name,t.name,e))}
        ${this._tabLink("settings","Settings",e)}
      </div>

      ${this._router.outlet()}
    `}_tabLink(e,t,i){return a`
      <a
        class="tab"
        role="tab"
        href="/${e}"
        aria-selected=${i===e}
      >
        ${t}
      </a>
    `}_renderDynamicTab(e){const t=this._components.find(i=>i.name===e);if(!t)return a`<p class="empty">Unknown page: ${e}</p>`;if(!this._loadedScripts.has(t.js)){this._loadedScripts=new Set([...this._loadedScripts,t.js]);const i=document.createElement("script");i.type="module",i.src=t.js,document.head.appendChild(i)}return a`<div class="component-host">
      ${this._getOrCreateElement(t)}
    </div>`}_renderSettings(e){return a`<shenas-settings
      api-base="${this.apiBase}"
      active-kind="${e||"pipe"}"
      .onNavigate=${t=>{this._router.goto(`/settings/${t}`)}}
    ></shenas-settings>`}_getOrCreateElement(e){if(!this._elementCache.has(e.name)){const t=document.createElement(e.tag);t.setAttribute("api-base",this.apiBase),this._elementCache.set(e.name,t)}return this._elementCache.get(e.name)}_renderDb(){const e=this._dbStatus;return e?a`
      <div class="status">
        <p>Path: <code>${e.db_path}</code></p>
        ${e.size_mb!=null?a`<p>Size: ${e.size_mb} MB</p>`:a`<p>Not created yet</p>`}
      </div>
      ${(e.schemas||[]).map(t=>a`
          <h3>${t.name}</h3>
          ${t.tables.map(i=>a`
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
              <h3>${e.name}</h3>
              <div class="meta">${e.version}</div>
              ${e.description?a`<div class="desc">${e.description}</div>`:""}
            </div>
          `)}
      </div>
    `}}l(c,"properties",{apiBase:{type:String,attribute:"api-base"},_pipes:{state:!0},_dbStatus:{state:!0},_components:{state:!0},_loading:{state:!0},_loadedScripts:{state:!0}}),l(c,"styles",u`
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
  `);customElements.define("shenas-app",c);const d=[{id:"pipe",label:"Pipes"},{id:"schema",label:"Schemas"},{id:"component",label:"Components"},{id:"ui",label:"UI"}];class p extends g{constructor(){super(),this.apiBase="/api",this.activeKind="pipe",this.onNavigate=null,this._plugins={},this._loading=!0,this._actionMessage=null}connectedCallback(){super.connectedCallback(),this._fetchAll()}async _fetchAll(){this._loading=!0;const s={};await Promise.all(d.map(async({id:e})=>{const t=await fetch(`${this.apiBase}/plugins/${e}`);s[e]=t.ok?await t.json():[]})),this._plugins=s,this._loading=!1}async _remove(s,e){this._actionMessage=null;const i=await(await fetch(`${this.apiBase}/plugins/${s}/${e}`,{method:"DELETE"})).json();i.ok?(this._actionMessage={type:"success",text:i.message},await this._fetchAll()):this._actionMessage={type:"error",text:i.message||"Remove failed"}}async _install(s){var h,m;const e=this.shadowRoot.querySelector(`#install-${s}`),t=(h=e==null?void 0:e.value)==null?void 0:h.trim();if(!t)return;this._actionMessage=null;const o=(m=(await(await fetch(`${this.apiBase}/plugins/${s}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({names:[t],skip_verify:!0})})).json()).results)==null?void 0:m[0];o!=null&&o.ok?(this._actionMessage={type:"success",text:o.message},e.value="",await this._fetchAll()):this._actionMessage={type:"error",text:(o==null?void 0:o.message)||"Install failed"}}render(){return this._loading?a`<p class="loading">Loading plugins...</p>`:a`
      ${this._actionMessage?a`<div class="message ${this._actionMessage.type}">
            ${this._actionMessage.text}
          </div>`:""}
      <div class="layout">
        <nav class="sidebar">
          <ul>
            ${d.map(({id:s,label:e})=>a`
                <li>
                  <a
                    href="/settings/${s}"
                    aria-selected=${this.activeKind===s}
                  >
                    ${e}
                    <span style="color:#aaa; font-weight:normal">
                      (${(this._plugins[s]||[]).length})
                    </span>
                  </a>
                </li>
              `)}
          </ul>
        </nav>
        <div class="content">${this._renderKind(this.activeKind)}</div>
      </div>
    `}_renderKind(s){var i;const e=this._plugins[s]||[],t=((i=d.find(r=>r.id===s))==null?void 0:i.label)||s;return a`
      <h3>${t}</h3>
      ${e.length>0?a`
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
                ${e.map(r=>a`
                    <tr>
                      <td class="name">${r.name}</td>
                      <td class="version">${r.version}</td>
                      <td class="desc">${r.description||""}</td>
                      <td class="actions">
                        <button
                          class="action remove"
                          @click=${()=>this._remove(s,r.name)}
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  `)}
              </tbody>
            </table>
          `:a`<p class="empty">No ${t.toLowerCase()} installed</p>`}
      <div class="install-row">
        <input
          id="install-${s}"
          type="text"
          placeholder="Plugin name"
          @keydown=${r=>r.key==="Enter"&&this._install(s)}
        />
        <button class="action" @click=${()=>this._install(s)}>
          Install
        </button>
      </div>
    `}}l(p,"properties",{apiBase:{type:String,attribute:"api-base"},activeKind:{type:String,attribute:"active-kind"},onNavigate:{type:Function},_plugins:{state:!0},_loading:{state:!0},_actionMessage:{state:!0}}),l(p,"styles",u`
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
