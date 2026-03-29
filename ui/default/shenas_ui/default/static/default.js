var z=Object.defineProperty;var B=(d,e,t)=>e in d?z(d,e,{enumerable:!0,configurable:!0,writable:!0,value:t}):d[e]=t;var r=(d,e,t)=>B(d,typeof e!="symbol"?e+"":e,t);import{LitElement as c,css as l,html as a}from"lit";import{Router as j}from"@lit-labs/router";class g extends c{constructor(){super(),this.enabled=!1}updated(){this.title=this.enabled?"Enabled":"Disabled"}render(){return a``}}r(g,"properties",{enabled:{type:Boolean,reflect:!0}}),r(g,"styles",l`
    :host {
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      vertical-align: middle;
    }
    :host([enabled]) {
      background: #2e7d32;
    }
    :host(:not([enabled])) {
      background: #c62828;
    }
  `);customElements.define("status-dot",g);const C=l`
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
`,m=l`
  button {
    padding: 0.3rem 0.7rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    background: #fff;
    cursor: pointer;
    font-size: 0.8rem;
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
`,D=l`
  .tabs {
    display: flex;
    gap: 0;
    border-bottom: 2px solid #e0e0e0;
    margin: 1rem 0;
  }
  .tab {
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
  .tab:hover {
    color: #222;
  }
  .tab[aria-selected="true"] {
    color: #222;
    border-bottom-color: #0066cc;
    font-weight: 600;
  }
`,x=l`
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
`,u=l`
  .loading {
    color: #888;
    font-style: italic;
  }
  .empty {
    color: #888;
    padding: 0.5rem 0;
  }
`,k=l`
  a {
    color: #0066cc;
    text-decoration: none;
  }
  a:hover {
    text-decoration: underline;
  }
`;class _ extends c{constructor(){super(),this.columns=[],this.rows=[],this.rowClass=null,this.actions=null,this.emptyText="No items",this.showAdd=!1}_onAdd(){this.dispatchEvent(new CustomEvent("add",{bubbles:!0,composed:!0}))}render(){const e=typeof this.actions=="function",t=this.showAdd?a`<div class="add-row"><button class="add-btn" title="Add" @click=${this._onAdd}>+</button></div>`:"";return!this.rows||this.rows.length===0?a`<p class="empty">${this.emptyText}</p>${t}`:a`
      <table>
        <thead>
          <tr>
            ${this.columns.map(s=>a`<th>${s.label}</th>`)}
            ${e?a`<th></th>`:""}
          </tr>
        </thead>
        <tbody>
          ${this.rows.map(s=>a`
              <tr class="${this.rowClass?this.rowClass(s):""}">
                ${this.columns.map(i=>a`
                  <td class="${i.class||""}">
                    ${i.render?i.render(s):s[i.key]}
                  </td>
                `)}
                ${e?a`<td class="actions-cell">${this.actions(s)}</td>`:""}
              </tr>
            `)}
        </tbody>
      </table>
      ${t}
    `}}r(_,"properties",{columns:{type:Array},rows:{type:Array},rowClass:{type:Object},actions:{type:Object},emptyText:{type:String,attribute:"empty-text"},showAdd:{type:Boolean,attribute:"show-add"}}),r(_,"styles",[C,m,u,l`
      :host {
        display: block;
      }
      .mono {
        font-family: monospace;
        font-size: 0.85rem;
      }
      .muted {
        color: #888;
      }
      .actions-cell {
        white-space: nowrap;
      }
      .disabled-row {
        opacity: 0.5;
      }
      .add-row {
        display: flex;
        justify-content: flex-end;
        margin-top: 0.5rem;
      }
      .add-btn {
        width: 28px;
        height: 28px;
        border-radius: 50%;
        border: 1px solid #ddd;
        background: #fff;
        color: #666;
        font-size: 1.1rem;
        line-height: 1;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0;
      }
      .add-btn:hover {
        background: #f0f4ff;
        color: #0066cc;
        border-color: #0066cc;
      }
    `]);customElements.define("shenas-data-list",_);class f extends c{constructor(){super(),this.title="",this.submitLabel="Save"}render(){return a`
      ${this.title?a`<h3>${this.title}</h3>`:""}
      <slot></slot>
      <div class="actions">
        <button @click=${this._onSubmit}>${this.submitLabel}</button>
        <button @click=${this._onCancel}>Cancel</button>
      </div>
    `}_onSubmit(){this.dispatchEvent(new CustomEvent("submit",{bubbles:!0,composed:!0}))}_onCancel(){this.dispatchEvent(new CustomEvent("cancel",{bubbles:!0,composed:!0}))}}r(f,"properties",{title:{type:String},submitLabel:{type:String,attribute:"submit-label"}}),r(f,"styles",[m,l`
      :host {
        display: block;
        margin: 1rem 0;
        padding: 1rem;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        background: #fafafa;
      }
      h3 {
        margin: 0 0 0.8rem;
        font-size: 1rem;
      }
      .actions {
        display: flex;
        justify-content: flex-end;
        gap: 0.5rem;
        margin-top: 0.8rem;
      }
    `]);customElements.define("shenas-form-panel",f);class $ extends c{constructor(){super();r(this,"_router",new j(this,[{path:"/",render:()=>this._renderDynamicHome()},{path:"/settings",render:()=>this._renderSettings("pipe")},{path:"/settings/:kind",render:({kind:t})=>this._renderSettings(t)},{path:"/settings/:kind/:name",render:({kind:t,name:s})=>this._renderPluginDetail(t,s)},{path:"/settings/:kind/:name/transforms",render:({kind:t,name:s})=>this._renderPluginDetail(t,s,"transforms")},{path:"/:tab",render:({tab:t})=>this._renderDynamicTab(t)}]));this.apiBase="/api",this._components=[],this._loading=!0,this._loadedScripts=new Set,this._elementCache=new Map,this._leftWidth=160,this._rightWidth=220,this._dbStatus=null}connectedCallback(){super.connectedCallback(),this._fetchData(),this.addEventListener("plugin-state-changed",()=>this._refreshComponents())}async _refreshComponents(){this._components=await this._fetch("/components")||[]}async _fetchData(){this._loading=!0;try{const[t,s]=await Promise.all([this._fetch("/components"),this._fetch("/db/status")]);this._components=t||[],this._dbStatus=s}catch(t){console.error("Failed to fetch data:",t)}this._loading=!1}async _fetch(t){const s=await fetch(`${this.apiBase}${t}`);return s.ok?s.json():null}_activeTab(){return(window.location.pathname.replace(/^\/+/,"")||"").split("/")[0]||(this._components.length>0?this._components[0].name:"settings")}_startDrag(t){return s=>{s.preventDefault();const i=s.clientX,n=t==="left"?this._leftWidth:this._rightWidth,o=s.target;o.classList.add("dragging");const h=S=>{const T=t==="left"?S.clientX-i:i-S.clientX,E=Math.max(80,Math.min(400,n+T));t==="left"?this._leftWidth=E:this._rightWidth=E},p=()=>{o.classList.remove("dragging"),window.removeEventListener("mousemove",h),window.removeEventListener("mouseup",p)};window.addEventListener("mousemove",h),window.addEventListener("mouseup",p)}}render(){if(this._loading)return a`<p class="loading">Loading...</p>`;const t=this._activeTab();return a`
      <div class="layout">
        <div class="panel-left" style="width: ${this._leftWidth}px">
          <div class="header">
            <img src="/static/images/shenas.png" alt="shenas" />
            <h1>shenas</h1>
          </div>
          <nav class="nav">
            ${this._components.map(s=>this._navItem(s.name,s.name,t))}
            ${this._navItem("settings","Settings",t)}
          </nav>
        </div>
        <div class="divider" @mousedown=${this._startDrag("left")}></div>
        <div class="panel-middle">
          ${this._router.outlet()}
        </div>
        <div class="divider" @mousedown=${this._startDrag("right")}></div>
        <div class="panel-right" style="width: ${this._rightWidth}px">
          ${this._renderDbStats()}
        </div>
      </div>
    `}_navItem(t,s,i){return a`
      <a class="nav-item" href="/${t}" aria-selected=${i===t}>
        ${s}
      </a>
    `}_renderDynamicHome(){return this._components.length>0?this._renderDynamicTab(this._components[0].name):this._renderSettings("pipe")}_renderDynamicTab(t){const s=this._components.find(i=>i.name===t);if(!s)return a`<p class="empty">Unknown page: ${t}</p>`;if(!this._loadedScripts.has(s.js)){this._loadedScripts=new Set([...this._loadedScripts,s.js]);const i=document.createElement("script");i.type="module",i.src=s.js,document.head.appendChild(i)}return a`<div class="component-host">
      ${this._getOrCreateElement(s)}
    </div>`}_renderPluginDetail(t,s,i="details"){return a`<shenas-plugin-detail
      api-base="${this.apiBase}"
      kind="${t}"
      name="${s}"
      active-tab="${i}"
    ></shenas-plugin-detail>`}_renderSettings(t){return a`<shenas-settings
      api-base="${this.apiBase}"
      active-kind="${t||"pipe"}"
      .onNavigate=${s=>{this._router.goto(`/settings/${s}`)}}
    ></shenas-settings>`}_renderDbStats(){const t=this._dbStatus;return t?a`
      <div class="db-section">
        <div class="db-meta">
          ${t.size_mb!=null?a`<code>${t.size_mb} MB</code>`:a`<span>Not created</span>`}
        </div>
        ${(t.schemas||[]).map(s=>a`
            <h4>${s.name}</h4>
            ${s.tables.map(i=>a`
                <div class="db-table-row">
                  <span class="db-table-name">${i.name}</span>
                  <span class="db-table-count">${i.rows}</span>
                </div>
                ${i.earliest?a`<span class="db-date-range">${i.earliest} - ${i.latest}</span>`:""}
              `)}
          `)}
      </div>
    `:a`<p class="empty">No database</p>`}_getOrCreateElement(t){if(!this._elementCache.has(t.name)){const s=document.createElement(t.tag);s.setAttribute("api-base",this.apiBase),this._elementCache.set(t.name,s)}return this._elementCache.get(t.name)}}r($,"properties",{apiBase:{type:String,attribute:"api-base"},_components:{state:!0},_loading:{state:!0},_loadedScripts:{state:!0},_leftWidth:{state:!0},_rightWidth:{state:!0},_dbStatus:{state:!0}}),r($,"styles",[k,u,l`
      :host {
        display: block;
        height: 100vh;
        color: #222;
      }
      .layout {
        display: flex;
        height: 100%;
      }
      .panel-left {
        flex-shrink: 0;
        overflow-y: auto;
        padding: 1.5rem 1rem;
        border-right: 1px solid #e0e0e0;
      }
      .panel-middle {
        flex: 1;
        min-width: 0;
        overflow-y: auto;
        padding: 1.5rem 2rem;
      }
      .panel-right {
        flex-shrink: 0;
        overflow-y: auto;
        padding: 1.5rem 1rem;
        border-left: 1px solid #e0e0e0;
      }
      .divider {
        width: 4px;
        cursor: col-resize;
        background: transparent;
        flex-shrink: 0;
      }
      .divider:hover,
      .divider.dragging {
        background: #d0d0d0;
      }
      .header {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 8px;
        margin-bottom: 1.5rem;
      }
      .header img {
        width: 64px;
        height: 64px;
      }
      .header h1 {
        margin: 0;
        font-size: 1.2rem;
      }
      .nav {
        display: flex;
        flex-direction: column;
        gap: 2px;
      }
      .nav-item {
        display: block;
        padding: 0.5rem 0.8rem;
        font-size: 0.9rem;
        color: #666;
        text-decoration: none;
        border-radius: 4px;
        border: none;
        background: none;
        cursor: pointer;
        text-align: left;
      }
      .nav-item:hover {
        background: #f5f5f5;
        color: #222;
      }
      .nav-item[aria-selected="true"] {
        background: #f0f4ff;
        color: #222;
        font-weight: 600;
      }
      .component-host {
        margin-top: 1rem;
      }
      .db-section h4 {
        font-size: 0.75rem;
        text-transform: uppercase;
        color: #888;
        letter-spacing: 0.05em;
        margin: 1rem 0 0.4rem;
      }
      .db-section h4:first-child {
        margin-top: 0;
      }
      .db-meta {
        font-size: 0.8rem;
        color: #666;
        margin: 0 0 0.8rem;
      }
      .db-meta code {
        background: #f0f0f0;
        padding: 1px 4px;
        border-radius: 2px;
        font-size: 0.75rem;
      }
      .db-table-row {
        display: flex;
        justify-content: space-between;
        padding: 0.2rem 0;
        font-size: 0.8rem;
        border-bottom: 1px solid #f5f5f5;
      }
      .db-table-row:last-child {
        border-bottom: none;
      }
      .db-table-name {
        color: #333;
      }
      .db-table-count {
        color: #888;
        font-size: 0.75rem;
      }
      .db-date-range {
        font-size: 0.7rem;
        color: #aaa;
        display: block;
      }
    `]);customElements.define("shenas-app",$);const b=[{id:"pipe",label:"Pipes"},{id:"schema",label:"Schemas"},{id:"component",label:"Components"},{id:"ui",label:"UI"}];class w extends c{constructor(){super(),this.apiBase="/api",this.activeKind="pipe",this.onNavigate=null,this._plugins={},this._loading=!0,this._actionMessage=null,this._installing=!1}connectedCallback(){super.connectedCallback(),this._fetchAll()}async _fetchAll(){this._loading=!0;const e={};await Promise.all(b.map(async({id:t})=>{const s=await fetch(`${this.apiBase}/plugins/${t}`);e[t]=s.ok?await s.json():[]})),this._plugins=e,this._loading=!1}async _remove(e,t){this._actionMessage=null;const i=await(await fetch(`${this.apiBase}/plugins/${e}/${t}`,{method:"DELETE"})).json();i.ok?(this._actionMessage={type:"success",text:i.message},await this._fetchAll()):this._actionMessage={type:"error",text:i.message||"Remove failed"}}async _toggleEnabled(e,t,s){this._actionMessage=null;const i=s?"disable":"enable",o=await(await fetch(`${this.apiBase}/plugins/${e}/${t}/${i}`,{method:"POST"})).json();o.ok?(this._actionMessage={type:"success",text:o.message},await this._fetchAll()):this._actionMessage={type:"error",text:o.message||`${i} failed`}}async _install(e){var h,p;const t=this.shadowRoot.querySelector(`#install-${e}`),s=(h=t==null?void 0:t.value)==null?void 0:h.trim();if(!s)return;this._actionMessage=null;const o=(p=(await(await fetch(`${this.apiBase}/plugins/${e}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({names:[s],skip_verify:!0})})).json()).results)==null?void 0:p[0];o!=null&&o.ok?(this._actionMessage={type:"success",text:o.message},this._installing=!1,await this._fetchAll()):this._actionMessage={type:"error",text:(o==null?void 0:o.message)||"Install failed"}}render(){return this._loading?a`<p class="loading">Loading plugins...</p>`:a`
      ${this._actionMessage?a`<div class="message ${this._actionMessage.type}">
            ${this._actionMessage.text}
          </div>`:""}
      <div class="layout">
        <nav class="sidebar">
          <ul>
            ${b.map(({id:e,label:t})=>a`
                <li>
                  <a
                    href="/settings/${e}"
                    aria-selected=${this.activeKind===e}
                  >
                    ${t}
                    <span style="color:#aaa; font-weight:normal">
                      (${(this._plugins[e]||[]).length})
                    </span>
                  </a>
                </li>
              `)}
          </ul>
        </nav>
        <div class="content">${this._renderKind(this.activeKind)}</div>
      </div>
    `}_renderKind(e){var i;const t=this._plugins[e]||[],s=((i=b.find(n=>n.id===e))==null?void 0:i.label)||e;return a`
      <h3>${s}</h3>
      <shenas-data-list
        .columns=${[{label:"Name",render:n=>a`<a href="/settings/${e}/${n.name}">${n.display_name||n.name}</a>`},{key:"version",label:"Version",class:"mono"},{label:"Added",class:"mono",render:n=>n.added_at?n.added_at.slice(0,10):""},{label:"Status",render:n=>a`<status-dot ?enabled=${n.enabled!==!1}></status-dot>`}]}
        .rows=${t}
        .rowClass=${n=>n.enabled===!1?"disabled-row":""}
        ?show-add=${!this._installing}
        @add=${()=>{this._installing=!0}}
        empty-text="No ${s.toLowerCase()} installed"
      ></shenas-data-list>
      ${this._installing?a`<shenas-form-panel
            title="Install new plugin"
            submit-label="Install"
            @submit=${()=>this._install(e)}
            @cancel=${()=>{this._installing=!1}}
          >
            <input
              id="install-${e}"
              type="text"
              placeholder="Plugin name"
              @keydown=${n=>n.key==="Enter"&&this._install(e)}
              style="width: 100%; padding: 0.4rem 0.6rem; border: 1px solid #ddd; border-radius: 4px; font-size: 0.85rem; box-sizing: border-box;"
            />
          </shenas-form-panel>`:""}
    `}}r(w,"properties",{apiBase:{type:String,attribute:"api-base"},activeKind:{type:String,attribute:"active-kind"},onNavigate:{type:Function},_plugins:{state:!0},_loading:{state:!0},_actionMessage:{state:!0},_installing:{state:!0}}),r(w,"styles",[m,k,x,u,l`
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
    `]);customElements.define("shenas-settings",w);class v extends c{constructor(){super(),this.apiBase="/api",this.kind="",this.name="",this.activeTab="details",this._info=null,this._loading=!0,this._message=null}willUpdate(e){(e.has("kind")||e.has("name"))&&this._fetchInfo()}async _fetchInfo(){if(!this.kind||!this.name)return;this._loading=!0,this._message=null;const e=await fetch(`${this.apiBase}/plugins/${this.kind}/${this.name}/info`);this._info=e.ok?await e.json():null,this._loading=!1}async _toggle(){var i;const e=((i=this._info)==null?void 0:i.enabled)!==!1?"disable":"enable",s=await(await fetch(`${this.apiBase}/plugins/${this.kind}/${this.name}/${e}`,{method:"POST"})).json();this._message={type:s.ok?"success":"error",text:s.message||`${e} failed`},await this._fetchInfo(),this.dispatchEvent(new CustomEvent("plugin-state-changed",{bubbles:!0,composed:!0}))}async _remove(){const t=await(await fetch(`${this.apiBase}/plugins/${this.kind}/${this.name}`,{method:"DELETE"})).json();t.ok?(window.history.pushState({},"",`/settings/${this.kind}`),window.dispatchEvent(new PopStateEvent("popstate"))):this._message={type:"error",text:t.message||"Remove failed"}}render(){if(this._loading)return a`<p class="loading">Loading...</p>`;if(!this._info)return a`<p>Plugin not found.</p>`;const e=this._info,t=e.enabled!==!1,s=`/settings/${this.kind}/${this.name}`;return a`
      <a class="back" href="/settings/${this.kind}">&larr; Back to ${this.kind}s</a>

      <h2>${e.display_name||e.name}</h2>
      <span class="kind-badge">${e.kind}</span>

      <div class="tabs">
        <a class="tab" href="${s}" aria-selected=${this.activeTab==="details"}>Details</a>
        ${this.kind==="pipe"?a`<a class="tab" href="${s}/transforms" aria-selected=${this.activeTab==="transforms"}>Transforms</a>`:""}
      </div>

      ${this.activeTab==="transforms"?a`<shenas-transforms api-base="${this.apiBase}" source="${this.name}"></shenas-transforms>`:this._renderDetails(e,t)}

      ${this._message?a`<div class="message ${this._message.type}">
            ${this._message.text}
          </div>`:""}
    `}_renderDetails(e,t){return a`
      ${e.description?a`<div class="description">${e.description}</div>`:""}

      <div class="state-table">
        <div class="state-row">
          <span class="state-label">Status</span>
          <span class="state-value">
            <status-dot ?enabled=${t}></status-dot>
          </span>
        </div>
        ${this._stateRow("Added",e.added_at)}
        ${this._stateRow("Updated",e.updated_at)}
        ${this._stateRow("Status changed",e.status_changed_at)}
      </div>

      <div class="actions">
        <button @click=${this._toggle}>
          ${t?"Disable":"Enable"}
        </button>
        <button class="danger" @click=${this._remove}>Remove</button>
      </div>
    `}_stateRow(e,t){return t?a`
      <div class="state-row">
        <span class="state-label">${e}</span>
        <span class="state-value">${t.slice(0,19)}</span>
      </div>
    `:""}}r(v,"properties",{apiBase:{type:String,attribute:"api-base"},kind:{type:String},name:{type:String},activeTab:{type:String,attribute:"active-tab"},_info:{state:!0},_loading:{state:!0},_message:{state:!0}}),r(v,"styles",[m,k,x,D,u,l`
      :host {
        display: block;
      }
      .back {
        font-size: 0.9rem;
        display: inline-block;
        margin-bottom: 1rem;
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
      .actions {
        display: flex;
        gap: 0.6rem;
        margin-top: 1.5rem;
      }
      button {
        padding: 0.5rem 1rem;
        font-size: 0.9rem;
      }
    `]);customElements.define("shenas-plugin-detail",v);class y extends c{constructor(){super(),this.apiBase="/api",this.source="",this._transforms=[],this._loading=!0,this._editing=null,this._editSql="",this._message=null,this._previewRows=null,this._creating=!1,this._newForm=this._emptyForm(),this._dbTables={},this._schemaTables={}}_emptyForm(){return{source_duckdb_table:"",target_duckdb_table:"",description:"",sql:""}}connectedCallback(){super.connectedCallback(),this._fetchAll()}async _fetchAll(){this._loading=!0;const e=this.source?`?source=${this.source}`:"",t=await fetch(`${this.apiBase}/transforms${e}`);this._transforms=t.ok?await t.json():[],this._loading=!1}async _toggle(e){const t=e.enabled?"disable":"enable";await fetch(`${this.apiBase}/transforms/${e.id}/${t}`,{method:"POST"}),await this._fetchAll()}async _delete(e){const s=await(await fetch(`${this.apiBase}/transforms/${e.id}`,{method:"DELETE"})).json();s.ok?(this._message={type:"success",text:s.message},await this._fetchAll()):this._message={type:"error",text:s.detail||s.message||"Delete failed"}}_startEdit(e){this._editing=e.id,this._editSql=e.sql,this._previewRows=null}_cancelEdit(){this._editing=null,this._editSql="",this._previewRows=null}async _saveEdit(){const e=await fetch(`${this.apiBase}/transforms/${this._editing}`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({sql:this._editSql})});if(e.ok)this._message={type:"success",text:"Transform updated"},this._editing=null,await this._fetchAll();else{const t=await e.json();this._message={type:"error",text:t.detail||"Update failed"}}}async _startCreate(){this._creating=!0,this._newForm=this._emptyForm(),this._editing=null,this._previewRows=null;const[e,t]=await Promise.all([fetch(`${this.apiBase}/db/tables`),fetch(`${this.apiBase}/db/schema-tables`)]);this._dbTables=e.ok?await e.json():{},this._schemaTables=t.ok?await t.json():{}}_cancelCreate(){this._creating=!1,this._newForm=this._emptyForm()}_updateNewForm(e,t){this._newForm={...this._newForm,[e]:t}}async _saveCreate(){const e=this._newForm;if(!e.source_duckdb_table||!e.target_duckdb_table||!e.sql){this._message={type:"error",text:"Fill in all required fields"};return}const t=await fetch(`${this.apiBase}/transforms`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({source_duckdb_schema:this.source,source_duckdb_table:e.source_duckdb_table,target_duckdb_schema:"metrics",target_duckdb_table:e.target_duckdb_table,source_plugin:this.source,description:e.description,sql:e.sql})});if(t.ok)this._message={type:"success",text:"Transform created"},this._creating=!1,this._newForm=this._emptyForm(),await this._fetchAll();else{const s=await t.json();this._message={type:"error",text:s.detail||"Create failed"}}}async _preview(){const e=await fetch(`${this.apiBase}/transforms/${this._editing}/test?limit=5`,{method:"POST"});if(e.ok)this._previewRows=await e.json();else{const t=await e.json();this._message={type:"error",text:t.detail||"Preview failed"}}}render(){return this._loading?a`<p class="loading">Loading transforms...</p>`:a`
      ${this._message?a`<div class="message ${this._message.type}">
            ${this._message.text}
          </div>`:""}
      ${this._editing?this._renderEditor():""}
      ${this._creating?this._renderCreateForm():""}
      <shenas-data-list
        ?show-add=${!this._creating&&!this._editing}
        @add=${this._startCreate}
        .columns=${[{key:"id",label:"ID",class:"muted"},{label:"Source",class:"mono",render:e=>`${e.source_duckdb_schema}.${e.source_duckdb_table}`},{label:"Target",class:"mono",render:e=>`${e.target_duckdb_schema}.${e.target_duckdb_table}`},{label:"Description",render:e=>a`${e.description||""}${e.is_default?a`<span class="default-badge">default</span>`:""}`},{label:"Status",render:e=>a`<status-dot ?enabled=${e.enabled}></status-dot>`}]}
        .rows=${this._transforms}
        .rowClass=${e=>e.enabled?"":"disabled-row"}
        .actions=${e=>a`
          ${e.is_default?a`<button @click=${()=>this._startEdit(e)}>View</button>`:a`<button @click=${()=>this._startEdit(e)}>Edit</button>`}
          <button @click=${()=>this._toggle(e)}>
            ${e.enabled?"Disable":"Enable"}
          </button>
          ${e.is_default?"":a`<button class="danger" @click=${()=>this._delete(e)}>Delete</button>`}
        `}
        empty-text="No transforms"
      ></shenas-data-list>
    `}_renderCreateForm(){const e=this._newForm,t=this.source,s=this._dbTables[t]||[],i=Object.values(this._schemaTables||{}).flat();return a`
      <shenas-form-panel
        title="New transform"
        submit-label="Create"
        @submit=${this._saveCreate}
        @cancel=${this._cancelCreate}
      >
        <div class="form-grid">
          <label>
            Pipe table
            <select
              .value=${e.source_duckdb_table}
              @change=${n=>this._updateNewForm("source_duckdb_table",n.target.value)}
            >
              <option value="">-- select --</option>
              ${s.map(n=>a`<option value=${n} ?selected=${e.source_duckdb_table===n}>${n}</option>`)}
            </select>
          </label>
          <label>
            Schema table
            <select
              .value=${e.target_duckdb_table}
              @change=${n=>this._updateNewForm("target_duckdb_table",n.target.value)}
            >
              <option value="">-- select --</option>
              ${i.map(n=>a`<option value=${n} ?selected=${e.target_duckdb_table===n}>${n}</option>`)}
            </select>
          </label>
          <label class="form-full">
            Description
            <input
              .value=${e.description}
              @input=${n=>this._updateNewForm("description",n.target.value)}
            />
          </label>
        </div>
        <textarea
          .value=${e.sql}
          @input=${n=>this._updateNewForm("sql",n.target.value)}
          placeholder="SELECT ... FROM ${t}.${e.source_duckdb_table||"table_name"}"
        ></textarea>
      </shenas-form-panel>
    `}_renderEditor(){const e=this._transforms.find(s=>s.id===this._editing);if(!e)return"";const t=e.is_default;return a`
      <div class="edit-panel">
        <h3>
          ${t?"View":"Edit"}: ${e.source_duckdb_schema}.${e.source_duckdb_table} ->
          ${e.target_duckdb_schema}.${e.target_duckdb_table}
        </h3>
        <textarea
          .value=${this._editSql}
          @input=${s=>this._editSql=s.target.value}
          ?readonly=${t}
          class="${t?"readonly":""}"
        ></textarea>
        <div class="edit-actions">
          ${t?"":a`<button @click=${this._saveEdit}>Save</button>`}
          <button @click=${this._preview}>Preview</button>
          <button @click=${this._cancelEdit}>${t?"Close":"Cancel"}</button>
        </div>
        ${this._previewRows?this._renderPreview():""}
      </div>
    `}_renderPreview(){if(!this._previewRows||this._previewRows.length===0)return a`<p class="loading">No preview rows</p>`;const e=Object.keys(this._previewRows[0]);return a`
      <div class="preview-table">
        <table>
          <thead>
            <tr>
              ${e.map(t=>a`<th>${t}</th>`)}
            </tr>
          </thead>
          <tbody>
            ${this._previewRows.map(t=>a`
                <tr>
                  ${e.map(s=>a`<td>${t[s]}</td>`)}
                </tr>
              `)}
          </tbody>
        </table>
      </div>
    `}}r(y,"properties",{apiBase:{type:String,attribute:"api-base"},source:{type:String},_transforms:{state:!0},_loading:{state:!0},_editing:{state:!0},_editSql:{state:!0},_message:{state:!0},_previewRows:{state:!0},_creating:{state:!0},_newForm:{state:!0},_dbTables:{state:!0},_schemaTables:{state:!0}}),r(y,"styles",[C,m,x,u,l`
      :host {
        display: block;
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
      .disabled-row {
        opacity: 0.5;
      }
      .form-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.5rem 1rem;
        margin-bottom: 0.8rem;
      }
      .form-grid label {
        font-size: 0.8rem;
        color: #666;
        display: flex;
        flex-direction: column;
        gap: 0.2rem;
      }
      .form-grid input,
      .form-grid select {
        padding: 0.35rem 0.5rem;
        border: 1px solid #ddd;
        border-radius: 4px;
        font-size: 0.85rem;
        font-family: monospace;
      }
      .form-full {
        grid-column: 1 / -1;
      }
    `]);customElements.define("shenas-transforms",y);
