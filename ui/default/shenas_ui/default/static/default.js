var o=Object.defineProperty;var d=(i,e,t)=>e in i?o(i,e,{enumerable:!0,configurable:!0,writable:!0,value:t}):i[e]=t;var r=(i,e,t)=>d(i,typeof e!="symbol"?e+"":e,t);import{LitElement as c,css as p,html as a}from"lit";class n extends c{constructor(){super(),this.apiBase="/api",this._pipes=[],this._dbStatus=null,this._components=[],this._loading=!0,this._activeTab="database",this._loadedScripts=new Set,this._elementCache=new Map}connectedCallback(){super.connectedCallback(),this._fetchData()}async _fetchData(){this._loading=!0;try{const[e,t,s]=await Promise.all([this._fetch("/plugins/pipe"),this._fetch("/db/status"),this._fetch("/components")]);this._pipes=e||[],this._dbStatus=t,this._components=s||[]}catch(e){console.error("Failed to fetch data:",e)}this._loading=!1}async _fetch(e){const t=await fetch(`${this.apiBase}${e}`);return t.ok?t.json():null}_selectTab(e){this._activeTab=e;const t=this._components.find(s=>s.name===e);if(t&&!this._loadedScripts.has(t.js)){this._loadedScripts=new Set([...this._loadedScripts,t.js]);const s=document.createElement("script");s.type="module",s.src=t.js,document.head.appendChild(s)}}render(){return this._loading?a`<p class="loading">Loading...</p>`:a`
      <div class="header">
        <img src="/static/images/shenas.png" alt="shenas" />
        <h1>shenas</h1>
      </div>

      <div class="tabs" role="tablist">
        ${this._renderTab("database","Database")}
        ${this._renderTab("pipes","Pipes")}
        ${this._components.map(e=>this._renderTab(e.name,e.name))}
      </div>

      ${this._activeTab==="database"?this._renderDb():""}
      ${this._activeTab==="pipes"?this._renderPipes():""}
      ${this._renderComponentTab()}
    `}_renderTab(e,t){return a`
      <button
        class="tab"
        role="tab"
        aria-selected=${this._activeTab===e}
        @click=${()=>this._selectTab(e)}
      >
        ${t}
      </button>
    `}_renderComponentTab(){const e=this._components.find(t=>t.name===this._activeTab);return e?a`
      <div class="component-host">${this._getOrCreateElement(e)}</div>
    `:a``}_getOrCreateElement(e){if(!this._elementCache.has(e.name)){const t=document.createElement(e.tag);t.setAttribute("api-base",this.apiBase),this._elementCache.set(e.name,t)}return this._elementCache.get(e.name)}_renderDb(){const e=this._dbStatus;return e?a`
      <div class="status">
        <p>Path: <code>${e.db_path}</code></p>
        ${e.size_mb!=null?a`<p>Size: ${e.size_mb} MB</p>`:a`<p>Not created yet</p>`}
      </div>
      ${(e.schemas||[]).map(t=>a`
          <h3>${t.name}</h3>
          ${t.tables.map(s=>a`
              <div class="schema-row">
                <span>${s.name}</span>
                <span class="meta">
                  ${s.rows} rows
                  ${s.earliest?a` &middot; ${s.earliest} - ${s.latest}`:""}
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
    `}}r(n,"properties",{apiBase:{type:String,attribute:"api-base"},_pipes:{state:!0},_dbStatus:{state:!0},_components:{state:!0},_loading:{state:!0},_activeTab:{state:!0},_loadedScripts:{state:!0}}),r(n,"styles",p`
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
  `);customElements.define("shenas-app",n);
