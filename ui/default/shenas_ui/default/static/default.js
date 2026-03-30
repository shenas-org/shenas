var U=Object.defineProperty;var W=(u,t,e)=>t in u?U(u,t,{enumerable:!0,configurable:!0,writable:!0,value:e}):u[t]=e;var c=(u,t,e)=>W(u,typeof t!="symbol"?t+"":t,e);import{LitElement as f,css as m,html as i}from"lit";import F,{dagre as K}from"cytoscape";import{Router as V}from"@lit-labs/router";class S extends f{constructor(){super(),this.open=!1,this.commands=[],this._query="",this._filtered=[],this._selectedIndex=0}updated(t){t.has("open")&&this.open&&(this._query="",this._selectedIndex=0,this._filter(),requestAnimationFrame(()=>{const e=this.renderRoot.querySelector("input");e&&e.focus()})),t.has("commands")&&this._filter()}_filter(){const t=this._query.toLowerCase();t?this._filtered=this.commands.filter(e=>e.label.toLowerCase().includes(t)||e.category.toLowerCase().includes(t)||(e.description||"").toLowerCase().includes(t)):this._filtered=this.commands,this._selectedIndex>=this._filtered.length&&(this._selectedIndex=Math.max(0,this._filtered.length-1))}_onInput(t){this._query=t.target.value,this._selectedIndex=0,this._filter()}_onKeydown(t){if(t.key==="ArrowDown")t.preventDefault(),this._filtered.length>0&&(this._selectedIndex=Math.min(this._selectedIndex+1,this._filtered.length-1)),this._scrollToSelected();else if(t.key==="ArrowUp")t.preventDefault(),this._selectedIndex=Math.max(this._selectedIndex-1,0),this._scrollToSelected();else if(t.key==="Enter"){t.preventDefault();const e=this._filtered[this._selectedIndex];e&&this._execute(e)}else t.key==="Escape"&&this._close()}_scrollToSelected(){requestAnimationFrame(()=>{const t=this.renderRoot.querySelector(".item.selected");t&&t.scrollIntoView({block:"nearest"})})}_execute(t){this.dispatchEvent(new CustomEvent("execute",{detail:t,bubbles:!0,composed:!0}))}_close(){this.dispatchEvent(new CustomEvent("close",{bubbles:!0,composed:!0}))}render(){return this.open?i`
      <div class="backdrop" @click=${this._close}></div>
      <div class="panel">
        <div class="input-row">
          <span class="search-icon">></span>
          <input
            type="text"
            placeholder="Type a command..."
            .value=${this._query}
            @input=${this._onInput}
            @keydown=${this._onKeydown}
          />
          <span class="hint">esc</span>
        </div>
        <div class="results">
          ${this._filtered.length===0?i`<div class="empty">No matching commands</div>`:this._filtered.map((t,e)=>i`
                  <div
                    class="item ${e===this._selectedIndex?"selected":""}"
                    @click=${()=>this._execute(t)}
                    @mouseenter=${()=>{this._selectedIndex=e}}
                  >
                    <span class="item-category">${t.category}</span>
                    <span class="item-label">${t.label}</span>
                    ${t.description?i`<span class="item-desc">${t.description}</span>`:""}
                  </div>
                `)}
        </div>
      </div>
    `:i``}}c(S,"properties",{open:{type:Boolean,reflect:!0},commands:{type:Array},_query:{state:!0},_filtered:{state:!0},_selectedIndex:{state:!0}}),c(S,"styles",m`
    :host {
      display: none;
    }
    :host([open]) {
      display: block;
      position: fixed;
      inset: 0;
      z-index: 10000;
    }
    .backdrop {
      position: absolute;
      inset: 0;
      background: rgba(0, 0, 0, 0.4);
    }
    .panel {
      position: relative;
      width: 90%;
      max-width: 560px;
      margin: 80px auto 0;
      background: var(--shenas-bg, #fff);
      border-radius: 8px;
      box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
      display: flex;
      flex-direction: column;
      max-height: 60vh;
      overflow: hidden;
    }
    .input-row {
      display: flex;
      align-items: center;
      padding: 0 1rem;
      border-bottom: 1px solid var(--shenas-border, #e0e0e0);
    }
    .search-icon {
      color: var(--shenas-text-faint, #aaa);
      font-size: 0.9rem;
      margin-right: 0.5rem;
    }
    input {
      flex: 1;
      padding: 0.8rem 0;
      border: none;
      font-size: 0.95rem;
      outline: none;
      background: transparent;
      color: var(--shenas-text, #222);
    }
    .hint {
      font-size: 0.7rem;
      color: var(--shenas-text-faint, #aaa);
      font-family: monospace;
    }
    .results {
      flex: 1;
      overflow-y: auto;
      min-height: 0;
    }
    .item {
      padding: 0.5rem 1rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.85rem;
    }
    .item:hover,
    .item.selected {
      background: var(--shenas-bg-selected, #f0f4ff);
    }
    .item-category {
      color: var(--shenas-text-muted, #888);
      font-size: 0.75rem;
      min-width: 60px;
    }
    .item-label {
      flex: 1;
      color: var(--shenas-text, #222);
    }
    .item-desc {
      color: var(--shenas-text-faint, #aaa);
      font-size: 0.75rem;
      max-width: 200px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .empty {
      padding: 1.5rem;
      text-align: center;
      color: var(--shenas-text-muted, #888);
      font-size: 0.85rem;
    }
  `);customElements.define("shenas-command-palette",S);class E extends f{constructor(){super(),this.enabled=!1,this.toggleable=!1}updated(){this.title=this.enabled?"Enabled":"Disabled"}render(){return i`<div class="track" @click=${this._onClick}><div class="knob"></div></div>`}_onClick(){this.toggleable&&this.dispatchEvent(new CustomEvent("toggle",{bubbles:!0,composed:!0}))}}c(E,"properties",{enabled:{type:Boolean,reflect:!0},toggleable:{type:Boolean,reflect:!0}}),c(E,"styles",m`
    :host {
      display: inline-block;
      vertical-align: middle;
    }
    .track {
      width: 28px;
      height: 16px;
      border-radius: 8px;
      background: var(--shenas-error, #c62828);
      position: relative;
      transition: background 0.2s;
    }
    :host([enabled]) .track {
      background: var(--shenas-success, #2e7d32);
    }
    .knob {
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: var(--shenas-bg, #fff);
      position: absolute;
      top: 2px;
      left: 2px;
      transition: left 0.2s;
    }
    :host([enabled]) .knob {
      left: 14px;
    }
    :host([toggleable]) .track {
      cursor: pointer;
    }
    :host([toggleable]:hover) .track {
      opacity: 0.85;
    }
  `);customElements.define("status-toggle",E);const M=m`
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
  }
  th {
    text-align: left;
    padding: 0.4rem 0.6rem;
    color: var(--shenas-text-secondary, #666);
    font-weight: 500;
    border-bottom: 1px solid var(--shenas-border, #e0e0e0);
  }
  td {
    padding: 0.4rem 0.6rem;
    border-bottom: 1px solid var(--shenas-border-light, #f0f0f0);
  }
`,x=m`
  button {
    padding: 0.3rem 0.7rem;
    border: 1px solid var(--shenas-border-input, #ddd);
    border-radius: 4px;
    background: var(--shenas-bg, #fff);
    color: var(--shenas-text, #222);
    cursor: pointer;
    font-size: 0.8rem;
  }
  button:hover {
    background: var(--shenas-bg-hover, #f5f5f5);
  }
  button.danger {
    color: var(--shenas-danger, #c00);
    border-color: var(--shenas-danger-border, #e8c0c0);
  }
  button.danger:hover {
    background: var(--shenas-danger-bg, #fef0f0);
  }
`,J=m`
  .tabs {
    display: flex;
    gap: 0;
    border-bottom: 2px solid var(--shenas-border, #e0e0e0);
    margin: 1rem 0;
  }
  .tab {
    padding: 0.5rem 1rem;
    border: none;
    background: none;
    cursor: pointer;
    font-size: 0.9rem;
    color: var(--shenas-text-secondary, #666);
    border-bottom: 2px solid transparent;
    margin-bottom: -2px;
    text-decoration: none;
  }
  .tab:hover {
    color: var(--shenas-text, #222);
  }
  .tab[aria-selected="true"] {
    color: var(--shenas-text, #222);
    border-bottom-color: var(--shenas-primary, #0066cc);
    font-weight: 600;
  }
`,T=m`
  .message {
    padding: 0.5rem 0.8rem;
    border-radius: 4px;
    margin-bottom: 1rem;
    font-size: 0.85rem;
  }
  .message.success {
    background: var(--shenas-success-bg, #e8f5e9);
    color: var(--shenas-success, #2e7d32);
  }
  .message.error {
    background: var(--shenas-error-bg, #fce4ec);
    color: var(--shenas-error, #c62828);
  }
`,y=m`
  .loading {
    color: var(--shenas-text-muted, #888);
    font-style: italic;
  }
  .empty {
    color: var(--shenas-text-muted, #888);
    padding: 0.5rem 0;
  }
`,N=m`
  a {
    color: var(--shenas-primary, #0066cc);
    text-decoration: none;
  }
  a:hover {
    text-decoration: underline;
  }
`;class z extends f{constructor(){super(),this.columns=[],this.rows=[],this.rowClass=null,this.actions=null,this.emptyText="No items",this.showAdd=!1}_onAdd(){this.dispatchEvent(new CustomEvent("add",{bubbles:!0,composed:!0}))}render(){const t=typeof this.actions=="function",e=this.showAdd?i`<div class="add-row"><button class="add-btn" title="Add" @click=${this._onAdd}>+</button></div>`:"";return!this.rows||this.rows.length===0?i`<p class="empty">${this.emptyText}</p>${e}`:i`
      <table>
        <thead>
          <tr>
            ${this.columns.map(s=>i`<th>${s.label}</th>`)}
            ${t?i`<th></th>`:""}
          </tr>
        </thead>
        <tbody>
          ${this.rows.map(s=>i`
              <tr class="${this.rowClass?this.rowClass(s):""}">
                ${this.columns.map(a=>i`
                  <td class="${a.class||""}">
                    ${a.render?a.render(s):s[a.key]}
                  </td>
                `)}
                ${t?i`<td class="actions-cell">${this.actions(s)}</td>`:""}
              </tr>
            `)}
        </tbody>
      </table>
      ${e}
    `}}c(z,"properties",{columns:{type:Array},rows:{type:Array},rowClass:{type:Object},actions:{type:Object},emptyText:{type:String,attribute:"empty-text"},showAdd:{type:Boolean,attribute:"show-add"}}),c(z,"styles",[M,x,y,m`
      :host {
        display: block;
      }
      .mono {
        font-family: monospace;
        font-size: 0.85rem;
      }
      .muted {
        color: var(--shenas-text-muted, #888);
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
        width: 30px;
        height: 30px;
        border-radius: 50%;
        border: 2px solid var(--shenas-primary, #0066cc);
        background: var(--shenas-bg, #fff);
        color: var(--shenas-primary, #0066cc);
        font-size: 1.2rem;
        font-weight: 600;
        line-height: 1;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0;
        transition: background 0.15s, color 0.15s;
      }
      .add-btn:hover {
        background: var(--shenas-primary, #0066cc);
        color: var(--shenas-bg, #fff);
      }
    `]);customElements.define("shenas-data-list",z);class P extends f{constructor(){super(),this.title="",this.submitLabel="Save"}render(){return i`
      ${this.title?i`<h3>${this.title}</h3>`:""}
      <slot></slot>
      <div class="actions">
        <button @click=${this._onSubmit}>${this.submitLabel}</button>
        <button @click=${this._onCancel}>Cancel</button>
      </div>
    `}_onSubmit(){this.dispatchEvent(new CustomEvent("submit",{bubbles:!0,composed:!0}))}_onCancel(){this.dispatchEvent(new CustomEvent("cancel",{bubbles:!0,composed:!0}))}}c(P,"properties",{title:{type:String},submitLabel:{type:String,attribute:"submit-label"}}),c(P,"styles",[x,m`
      :host {
        display: block;
        margin: 1rem 0;
        padding: 1rem;
        border: 1px solid var(--shenas-border, #e0e0e0);
        border-radius: 8px;
        background: var(--shenas-bg-secondary, #fafafa);
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
    `]);customElements.define("shenas-form-panel",P);let L=!1;class B extends f{constructor(){super(),this.apiBase="/api",this._loading=!0,this._empty=!1,this._cy=null,this._elements=null,this._resizeObserver=null}connectedCallback(){super.connectedCallback(),this._fetchData()}disconnectedCallback(){super.disconnectedCallback(),this._cy&&(this._cy.destroy(),this._cy=null),this._resizeObserver&&(this._resizeObserver.disconnect(),this._resizeObserver=null)}async _fetchData(){this._loading=!0;try{const[t,e,s,a,n,r]=await Promise.all([fetch(`${this.apiBase}/plugins/pipe`),fetch(`${this.apiBase}/plugins/schema`),fetch(`${this.apiBase}/transforms`),fetch(`${this.apiBase}/db/schema-plugins`),fetch(`${this.apiBase}/plugins/component`),fetch(`${this.apiBase}/dependencies`)]),l=t.ok?await t.json():[],d=e.ok?await e.json():[],g=s.ok?await s.json():[],p=a.ok?await a.json():{},h=n.ok?await n.json():[],o=r.ok?await r.json():{};this._buildElements(l,d,g,p,h,o)}catch(t){console.error("Failed to fetch overview data:",t)}this._loading=!1}_buildElements(t,e,s,a,n,r){const l=[],d=new Set,g={};for(const[o,b]of Object.entries(a))for(const $ of b)g[$]=o;for(const o of t){const b=`pipe:${o.name}`;d.add(b),l.push({data:{id:b,label:o.display_name||o.name,kind:"pipe",enabled:o.enabled!==!1?"yes":"no"}})}for(const o of e){const b=`schema:${o.name}`;d.add(b),l.push({data:{id:b,label:o.display_name||o.name,kind:"schema",enabled:o.enabled!==!1?"yes":"no"}})}for(const o of n){const b=`component:${o.name}`;d.add(b),l.push({data:{id:b,label:o.display_name||o.name,kind:"component",enabled:o.enabled!==!1?"yes":"no"}})}for(const o of s){const b=`pipe:${o.source_plugin}`,$=g[o.target_duckdb_table],k=$?`schema:${$}`:null;if(!k||!d.has(b)||!d.has(k))continue;const _=o.description||`${o.source_duckdb_table} -> ${o.target_duckdb_table}`,v=_.length>30?_.slice(0,28)+"...":_;l.push({data:{id:`transform:${o.id}`,source:b,target:k,label:v,enabled:o.enabled?"yes":"no",sourcePlugin:o.source_plugin,edgeType:"transform"}})}const p=new Set;for(const o of l)o.data.edgeType==="transform"&&p.add(`${o.data.source}:${o.data.target}`);const h=new Set;for(const[o,b]of Object.entries(r))for(const $ of b){const k=o.split(":")[0];let _,v;if(k==="component"?(_=$,v=o):(_=o,v=$),!d.has(_)||!d.has(v)||k==="pipe"&&p.has(`${_}:${v}`))continue;const C=`dep:${_}:${v}`;h.has(C)||(h.add(C),l.push({data:{id:C,source:_,target:v,edgeType:"dependency"}}))}this._elements=l,this._empty=l.filter(o=>o.data.source).length===0}_initCytoscape(){const t=this.renderRoot.querySelector("#cy");!t||!this._elements||(L||(F.use(K),L=!0),this._cy&&this._cy.destroy(),this._cy=F({container:t,elements:this._elements,style:[{selector:"node",style:{label:"data(label)","text-valign":"center","text-halign":"center","font-size":12,color:"#fff","text-wrap":"wrap","text-max-width":100,width:120,height:40,shape:"round-rectangle"}},{selector:'node[kind="pipe"]',style:{"background-color":"#4a90d9",cursor:"pointer"}},{selector:'node[kind="schema"]',style:{"background-color":"#66bb6a",cursor:"pointer"}},{selector:'node[kind="component"]',style:{"background-color":"#ffa726",cursor:"pointer"}},{selector:'node[enabled="no"]',style:{opacity:.4,"border-width":2,"border-color":"#999","border-style":"dashed"}},{selector:"edge",style:{"curve-style":"bezier","target-arrow-shape":"triangle","target-arrow-color":"#999","line-color":"#999",cursor:"pointer",width:2,label:"data(label)","font-size":9,color:"#888","text-rotation":"autorotate","text-margin-y":-8}},{selector:'edge[enabled="yes"]',style:{"line-style":"solid"}},{selector:'edge[enabled="no"]',style:{"line-style":"dashed","line-color":"#ccc","target-arrow-color":"#ccc",opacity:.5}},{selector:'edge[edgeType="dependency"]',style:{"line-style":"dotted","line-color":"#bbb","target-arrow-color":"#bbb",width:1.5,label:""}}],layout:{name:"dagre",rankDir:"LR",nodeSep:60,rankSep:150,padding:30},userZoomingEnabled:!0,userPanningEnabled:!0,boxSelectionEnabled:!1}),this._cy.on("tap","node",e=>{const s=e.target.data(),a=s.id.substring(s.id.indexOf(":")+1);let n;if(s.kind==="pipe")n=`/settings/pipe/${a}`;else if(s.kind==="schema")n=`/settings/schema/${a}`;else if(s.kind==="component")n=`/settings/component/${a}`;else return;this.dispatchEvent(new CustomEvent("navigate",{bubbles:!0,composed:!0,detail:{path:n}}))}),this._cy.on("tap","edge",e=>{const s=e.target.data("sourcePlugin");s&&this.dispatchEvent(new CustomEvent("navigate",{bubbles:!0,composed:!0,detail:{path:`/settings/pipe/${s}`}}))}),this._resizeObserver&&this._resizeObserver.disconnect(),this._resizeObserver=new ResizeObserver(()=>{this._cy&&(this._cy.resize(),this._cy.fit(void 0,30))}),this._resizeObserver.observe(t))}firstUpdated(){!this._loading&&this._elements&&this._initCytoscape()}updated(t){t.has("_loading")&&!this._loading&&this._elements&&requestAnimationFrame(()=>this._initCytoscape())}render(){return this._loading?i`<p class="loading">Loading overview...</p>`:i`
      <div id="cy"></div>
      <div class="legend">
        <span class="legend-item"><span class="legend-dot pipe"></span> Pipe</span>
        <span class="legend-item"><span class="legend-dot schema"></span> Schema</span>
        <span class="legend-item"><span class="legend-dot component"></span> Component</span>
        <span class="legend-item"><span class="legend-line enabled"></span> Transform</span>
        <span class="legend-item"><span class="legend-line disabled"></span> Disabled</span>
        <span class="legend-item"><span class="legend-line" style="border-top:2px dotted var(--shenas-text-faint, #aaa);height:0;background:none"></span> Dependency</span>
      </div>
      ${this._empty?i`<p class="empty">No connections found. Add transforms in pipe settings.</p>`:""}
    `}}c(B,"properties",{apiBase:{type:String,attribute:"api-base"},_loading:{state:!0},_empty:{state:!0}}),c(B,"styles",[y,m`
      :host {
        display: flex;
        flex-direction: column;
        height: 100%;
      }
      #cy {
        width: 100%;
        flex: 1;
        min-height: 200px;
        border: 1px solid var(--shenas-border, #e0e0e0);
        border-radius: 8px;
        background: var(--shenas-bg-secondary, #fafafa);
        box-sizing: border-box;
      }
      .legend {
        display: flex;
        gap: 1.5rem;
        margin-top: 0.8rem;
        font-size: 0.8rem;
        color: var(--shenas-text-secondary, #666);
      }
      .legend-item {
        display: flex;
        align-items: center;
        gap: 4px;
      }
      .legend-dot {
        width: 10px;
        height: 10px;
        border-radius: 3px;
      }
      .legend-dot.pipe { background: var(--shenas-node-pipe, #4a90d9); }
      .legend-dot.schema { background: var(--shenas-node-schema, #66bb6a); }
      .legend-dot.component { background: var(--shenas-node-component, #ffa726); }
      .legend-line {
        width: 20px;
        height: 2px;
      }
      .legend-line.enabled { background: var(--shenas-text-muted, #888); }
      .legend-line.disabled { background: var(--shenas-text-faint, #aaa); border-top: 2px dashed var(--shenas-text-faint, #aaa); height: 0; }
    `]);customElements.define("shenas-pipeline-overview",B);class I extends f{constructor(){super(),this.apiBase="/api",this.pipeName="",this._fields=[],this._instructions="",this._loading=!0,this._message=null,this._needsMfa=!1,this._oauthUrl=null,this._submitting=!1}willUpdate(t){t.has("pipeName")&&this._fetchFields()}async _fetchFields(){if(!this.pipeName)return;this._loading=!0,this._needsMfa=!1,this._oauthUrl=null;const t=await fetch(`${this.apiBase}/auth/${this.pipeName}/fields`);if(t.ok){const e=await t.json();this._fields=e.fields||[],this._instructions=e.instructions||""}this._loading=!1}async _submit(){var a,n;this._submitting=!0,this._message=null;const t={};if(this._needsMfa){const r=this.renderRoot.querySelector("#mfa-code");t.mfa_code=((a=r==null?void 0:r.value)==null?void 0:a.trim())||""}else if(this._oauthUrl)t.auth_complete="true";else for(const r of this._fields){const l=this.renderRoot.querySelector(`#field-${r.name}`),d=(n=l==null?void 0:l.value)==null?void 0:n.trim();d&&(t[r.name]=d)}const s=await(await fetch(`${this.apiBase}/auth/${this.pipeName}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({credentials:t})})).json();this._submitting=!1,s.ok?(this._message={type:"success",text:s.message},this._needsMfa=!1,this._oauthUrl=null):s.needs_mfa?(this._needsMfa=!0,this._message={type:"success",text:"MFA code required"}):s.oauth_url?(this._oauthUrl=s.oauth_url,this._message={type:"success",text:s.message}):(this._message={type:"error",text:s.error||"Authentication failed"},this._needsMfa=!1,this._oauthUrl=null)}render(){return this._loading?i`<p class="loading">Loading auth...</p>`:this._fields.length===0&&!this._instructions?i`<p class="empty">No authentication required for this plugin.</p>`:i`
      ${this._message?i`<div class="message ${this._message.type}">${this._message.text}</div>`:""}
      ${this._instructions?i`<div class="instructions">${this._instructions}</div>`:""}
      ${this._oauthUrl?this._renderOAuth():this._needsMfa?this._renderMfa():this._renderFields()}
    `}_renderFields(){return i`
      ${this._fields.map(t=>i`
        <div class="field">
          <label for="field-${t.name}">${t.prompt}</label>
          <input id="field-${t.name}"
            type="${t.hide?"password":"text"}"
            @keydown=${e=>{e.key==="Enter"&&this._submit()}}
          />
        </div>
      `)}
      <div class="actions">
        <button @click=${this._submit} ?disabled=${this._submitting}>
          ${this._submitting?"Authenticating...":"Authenticate"}
        </button>
      </div>
    `}_renderMfa(){return i`
      <div class="field">
        <label for="mfa-code">MFA Code</label>
        <input id="mfa-code" type="text" autocomplete="one-time-code"
          @keydown=${t=>{t.key==="Enter"&&this._submit()}}
        />
      </div>
      <div class="actions">
        <button @click=${this._submit} ?disabled=${this._submitting}>
          ${this._submitting?"Verifying...":"Verify"}
        </button>
      </div>
    `}_renderOAuth(){return i`
      <p>
        <a class="oauth-link" href="${this._oauthUrl}" target="_blank" rel="noopener">
          Open authorization page
        </a>
      </p>
      <p style="font-size:0.85rem;color:var(--shenas-text-secondary, #666)">
        After authorizing in your browser, click Complete below.
      </p>
      <div class="actions">
        <button @click=${this._submit} ?disabled=${this._submitting}>
          ${this._submitting?"Completing...":"Complete"}
        </button>
      </div>
    `}}c(I,"properties",{apiBase:{type:String,attribute:"api-base"},pipeName:{type:String,attribute:"pipe-name"},_fields:{state:!0},_instructions:{state:!0},_loading:{state:!0},_message:{state:!0},_needsMfa:{state:!0},_oauthUrl:{state:!0},_submitting:{state:!0}}),c(I,"styles",[x,T,y,m`
      :host {
        display: block;
      }
      .instructions {
        font-size: 0.85rem;
        color: var(--shenas-text-secondary, #666);
        line-height: 1.6;
        margin-bottom: 1rem;
        white-space: pre-line;
      }
      .field {
        margin-bottom: 0.8rem;
      }
      .field label {
        display: block;
        font-size: 0.8rem;
        color: var(--shenas-text-secondary, #666);
        margin-bottom: 0.2rem;
      }
      .field input {
        width: 100%;
        padding: 0.4rem 0.6rem;
        border: 1px solid var(--shenas-border-input, #ddd);
        border-radius: 4px;
        font-size: 0.85rem;
        box-sizing: border-box;
      }
      .actions {
        display: flex;
        justify-content: flex-end;
        gap: 0.5rem;
        margin-top: 1rem;
      }
      .oauth-link {
        display: inline-block;
        margin-top: 0.5rem;
        color: var(--shenas-primary, #0066cc);
      }
    `]);customElements.define("shenas-auth",I);class O extends f{constructor(){super(),this.apiBase="/api",this.kind="",this.name="",this._config=null,this._loading=!0,this._message=null,this._editing=null,this._editValue=""}willUpdate(t){(t.has("kind")||t.has("name"))&&this._fetchConfig()}async _fetchConfig(){if(!this.kind||!this.name)return;this._loading=!0;const t=await fetch(`${this.apiBase}/config?kind=${this.kind}&name=${this.name}`);if(t.ok){const e=await t.json();this._config=e.length>0?e[0]:null}else this._config=null;this._loading=!1}_startEdit(t,e){this._editing=t,this._editValue=e||""}_cancelEdit(){this._editing=null,this._editValue=""}async _saveEdit(t){const e=await fetch(`${this.apiBase}/config/${this.kind}/${this.name}`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({key:t,value:this._editValue})});if(e.ok)this._message={type:"success",text:`Updated ${t}`},this._editing=null,await this._fetchConfig();else{const s=await e.json();this._message={type:"error",text:s.detail||"Update failed"}}}render(){return this._loading?i`<p class="loading">Loading config...</p>`:!this._config||this._config.entries.length===0?i`<p class="empty">No configuration settings for this plugin.</p>`:i`
      ${this._message?i`<div class="message ${this._message.type}">${this._message.text}</div>`:""}
      ${this._config.entries.map(t=>this._renderEntry(t))}
    `}_renderEntry(t){const e=this._editing===t.key;return i`
      <div class="config-row">
        <div class="config-key">${t.key}</div>
        ${e?i`
            <div class="edit-row">
              <input class="config-input"
                .value=${this._editValue}
                @input=${s=>{this._editValue=s.target.value}}
                @keydown=${s=>{s.key==="Enter"&&this._saveEdit(t.key),s.key==="Escape"&&this._cancelEdit()}}
              />
              <button @click=${()=>this._saveEdit(t.key)}>Save</button>
              <button @click=${this._cancelEdit}>Cancel</button>
            </div>`:i`
            <div class="config-detail">
              <div class="config-value ${t.value?"":"empty"}"
                @click=${()=>this._startEdit(t.key,t.value)}
                style="cursor: pointer"
                title="Click to edit"
              >${t.value||"not set"}</div>
              ${t.description?i`<div class="config-desc">${t.description}</div>`:""}
            </div>`}
      </div>
    `}}c(O,"properties",{apiBase:{type:String,attribute:"api-base"},kind:{type:String},name:{type:String},_config:{state:!0},_loading:{state:!0},_message:{state:!0},_editing:{state:!0},_editValue:{state:!0}}),c(O,"styles",[x,T,y,m`
      :host {
        display: block;
      }
      .config-row {
        display: flex;
        align-items: center;
        padding: 0.5rem 0;
        border-bottom: 1px solid var(--shenas-border-light, #f0f0f0);
        font-size: 0.9rem;
        gap: 1rem;
      }
      .config-row:last-child {
        border-bottom: none;
      }
      .config-key {
        min-width: 140px;
        font-weight: 600;
        color: var(--shenas-text, #222);
        flex-shrink: 0;
      }
      .config-value {
        flex: 1;
        color: var(--shenas-text-secondary, #666);
        font-family: monospace;
        font-size: 0.85rem;
      }
      .config-value.empty {
        color: var(--shenas-text-faint, #aaa);
        font-style: italic;
        font-family: inherit;
      }
      .config-desc {
        font-size: 0.8rem;
        color: var(--shenas-text-muted, #888);
        margin-top: 0.2rem;
      }
      .config-detail {
        flex: 1;
      }
      input.config-input {
        width: 100%;
        padding: 0.3rem 0.5rem;
        border: 1px solid var(--shenas-border-input, #ddd);
        border-radius: 4px;
        font-size: 0.85rem;
        font-family: monospace;
        box-sizing: border-box;
      }
      .edit-row {
        display: flex;
        gap: 0.4rem;
        align-items: center;
        flex: 1;
      }
    `]);customElements.define("shenas-config",O);const w=[{id:"pipe",label:"Pipes"},{id:"schema",label:"Schemas"},{id:"component",label:"Components"},{id:"ui",label:"UI"},{id:"theme",label:"Themes"}];class j extends f{constructor(){super();c(this,"_router",new V(this,[{path:"/",render:()=>this._renderDynamicHome()},{path:"/settings",render:()=>this._renderSettings("overview")},{path:"/settings/:kind",render:({kind:e})=>this._renderSettings(e)},{path:"/settings/:kind/:name",render:({kind:e,name:s})=>this._renderPluginDetail(e,s)},{path:"/settings/:kind/:name/config",render:({kind:e,name:s})=>this._renderPluginDetail(e,s,"config")},{path:"/settings/:kind/:name/auth",render:({kind:e,name:s})=>this._renderPluginDetail(e,s,"auth")},{path:"/:tab",render:({tab:e})=>this._renderDynamicTab(e)}]));c(this,"_nextTabId",1);c(this,"_saveWorkspaceTimer",null);this.apiBase="/api",this._components=[],this._loading=!0,this._loadedScripts=new Set,this._elementCache=new Map,this._leftWidth=160,this._rightWidth=220,this._dbStatus=null,this._inspectTable=null,this._inspectRows=null,this._paletteOpen=!1,this._paletteCommands=[],this._navPaletteOpen=!1,this._navCommands=[],this._registeredCommands=new Map,this._tabs=[],this._activeTabId=null}connectedCallback(){super.connectedCallback(),this._fetchData(),this.addEventListener("plugin-state-changed",()=>this._refreshComponents()),this.addEventListener("inspect-table",e=>this._inspect(e.detail.schema,e.detail.table)),this.addEventListener("navigate",e=>this._navigateTo(e.detail.path,e.detail.label)),this.addEventListener("register-command",e=>{const{componentId:s,commands:a}=e.detail;!a||a.length===0?this._registeredCommands.delete(s):this._registeredCommands.set(s,a)}),this._keyHandler=e=>{(e.ctrlKey||e.metaKey)&&e.key==="p"?(e.preventDefault(),this._togglePalette()):(e.ctrlKey||e.metaKey)&&e.key==="o"?(e.preventDefault(),this._toggleNavPalette()):(e.ctrlKey||e.metaKey)&&e.key==="w"?(e.preventDefault(),this._activeTabId!=null&&this._closeTab(this._activeTabId)):(e.ctrlKey||e.metaKey)&&e.key==="t"&&(e.preventDefault(),this._addTab())},document.addEventListener("keydown",this._keyHandler)}disconnectedCallback(){super.disconnectedCallback(),document.removeEventListener("keydown",this._keyHandler)}_togglePalette(){if(this._paletteOpen){this._paletteOpen=!1;return}this._navPaletteOpen=!1,this._buildCommands(),this._paletteOpen=!0}async _toggleNavPalette(){if(this._navPaletteOpen){this._navPaletteOpen=!1;return}this._paletteOpen=!1,await this._buildNavCommands(),this._navPaletteOpen=!0}async _buildNavCommands(){const e=[];for(const a of this._components)e.push({id:`nav:${a.name}`,category:"Page",label:a.display_name||a.name,path:`/${a.name}`});e.push({id:"nav:dataflow",category:"Settings",label:"Data Flow",path:"/settings/overview"});for(const a of w)e.push({id:`nav:settings:${a.id}`,category:"Settings",label:a.label,path:`/settings/${a.id}`});let s=[];try{s=(await Promise.all(w.map(async n=>(await this._fetch(`/plugins/${n.id}`)||[]).map(l=>({...l,kind:n.id,kindLabel:n.label}))))).flat()}catch{}for(const a of s)e.push({id:`nav:${a.kind}:${a.name}`,category:a.kindLabel,label:a.display_name||a.name,path:`/settings/${a.kind}/${a.name}`});this._navCommands=e}async _registerGlobalCommands(){const e=[];try{for(const s of w){const a=await this._fetch(`/plugins/${s.id}`)||[];for(const n of a){const r=n.display_name||n.name,l=n.enabled!==!1;e.push({id:`toggle:${s.id}:${n.name}`,category:s.label,label:`${l?"Disable":"Enable"} ${r}`,action:async()=>{const d=l?"disable":"enable";await fetch(`${this.apiBase}/plugins/${s.id}/${n.name}/${d}`,{method:"POST"}),await this._registerGlobalCommands()}}),s.id==="pipe"&&l&&e.push({id:`sync:${n.name}`,category:"Pipe",label:`Sync ${r}`,action:()=>fetch(`${this.apiBase}/sync/${n.name}`,{method:"POST"})})}}e.push({id:"sync:all",category:"Pipe",label:"Sync All Pipes",action:()=>fetch(`${this.apiBase}/sync`,{method:"POST"})}),e.push({id:"seed:transforms",category:"Transform",label:"Seed Default Transforms",action:()=>fetch(`${this.apiBase}/transforms/seed`,{method:"POST"})})}catch{}this._registeredCommands.set("global",e)}_buildCommands(){const e=[];for(const s of this._registeredCommands.values())e.push(...s);this._paletteCommands=e}_executePaletteCommand(e){const s=e.detail;s.path?this._openTab(s.path,s.label):s.action&&s.action(),this._paletteOpen=!1,this._navPaletteOpen=!1}_navigateTo(e,s){if(this._tabs.length===0||!this._activeTabId){this._openTab(e,s);return}const a=s||this._labelForPath(e);this._tabs=this._tabs.map(n=>n.id===this._activeTabId?{...n,path:e,label:a}:n),this._router.goto(e),this._saveWorkspace()}_openTab(e,s){const a=this._nextTabId++;this._tabs=[...this._tabs,{id:a,path:e,label:s||this._labelForPath(e)}],this._activeTabId=a,this._router.goto(e),this._saveWorkspace()}async _addTab(){await this._buildNavCommands(),this._navPaletteOpen=!0}_closeTab(e){const s=this._tabs.findIndex(n=>n.id===e);if(s===-1)return;const a=this._tabs.filter(n=>n.id!==e);if(this._tabs=a,this._activeTabId===e)if(a.length>0){const n=a[Math.min(s,a.length-1)];this._activeTabId=n.id,this._router.goto(n.path)}else this._activeTabId=null,window.history.pushState({},"","/");this._saveWorkspace()}_switchTab(e){const s=this._tabs.find(a=>a.id===e);s&&(this._activeTabId=e,window.history.pushState({},"",s.path),this._router.goto(s.path),this._saveWorkspace())}_saveWorkspace(){clearTimeout(this._saveWorkspaceTimer),this._saveWorkspaceTimer=setTimeout(()=>{const e={tabs:this._tabs,activeTabId:this._activeTabId,nextTabId:this._nextTabId};fetch(`${this.apiBase}/workspace`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify(e)}).catch(()=>{})},300)}async _loadWorkspace(){try{const e=await fetch(`${this.apiBase}/workspace`);if(!e.ok)return;const s=await e.json();if(s.tabs&&s.tabs.length>0){this._tabs=s.tabs,this._activeTabId=s.activeTabId||s.tabs[0].id,this._nextTabId=s.nextTabId||Math.max(...s.tabs.map(r=>r.id))+1;const a=window.location.pathname;if(a&&a!=="/"&&!this._tabs.some(r=>r.path===a)){this._openTab(a);return}const n=this._tabs.find(r=>r.id===this._activeTabId);n&&this._router.goto(n.path)}else{const a=window.location.pathname;a&&a!=="/"&&this._openTab(a)}}catch{const e=window.location.pathname;e&&e!=="/"&&this._openTab(e)}}_labelForPath(e){const s=e.replace(/^\/+/,"");if(!s||s==="settings"||s==="settings/overview")return"Data Flow";const a=s.split("/");if(a[0]==="settings"){if(a.length===2){const r=w.find(l=>l.id===a[1]);return r?r.label:a[1]}if(a.length>=3)return a[2]}const n=this._components.find(r=>r.name===a[0]);return n?n.display_name||n.name:a[0]}async _refreshComponents(){this._components=await this._fetch("/components")||[]}async _fetchData(){this._loading=!0;try{const[e,s]=await Promise.all([this._fetch("/components"),this._fetch("/db/status")]);this._components=e||[],this._dbStatus=s}catch(e){console.error("Failed to fetch data:",e)}this._loading=!1,this._registerGlobalCommands(),await this._loadWorkspace()}async _fetch(e){const s=await fetch(`${this.apiBase}${e}`);return s.ok?s.json():null}_activeTab(){return(window.location.pathname.replace(/^\/+/,"")||"").split("/")[0]||(this._components.length>0?this._components[0].name:"settings")}_startDrag(e){return s=>{s.preventDefault();const a=s.clientX,n=e==="left"?this._leftWidth:this._rightWidth,r=s.target;r.classList.add("dragging");const l=g=>{const p=e==="left"?g.clientX-a:a-g.clientX,h=Math.max(80,Math.min(400,n+p));e==="left"?this._leftWidth=h:this._rightWidth=h},d=()=>{r.classList.remove("dragging"),window.removeEventListener("mousemove",l),window.removeEventListener("mouseup",d)};window.addEventListener("mousemove",l),window.addEventListener("mouseup",d)}}render(){if(this._loading)return i`<p class="loading">Loading...</p>`;const e=this._activeTab();return i`
      <div class="layout">
        <div class="panel-left" style="width: ${this._leftWidth}px">
          <div class="header">
            <img src="/static/images/shenas.png" alt="shenas" />
            <h1>shenas</h1>
          </div>
          <nav class="nav">
            ${this._components.map(s=>this._navItem(s.name,s.display_name||s.name,e))}
            ${this._navItem("settings","Settings",e)}
          </nav>
        </div>
        <div class="divider" @mousedown=${this._startDrag("left")}></div>
        <div class="panel-middle">
          ${this._tabs.length>0?i`
              <div class="tab-bar">
                ${this._tabs.map(s=>i`
                  <div class="tab-item ${s.id===this._activeTabId?"active":""}"
                    @click=${()=>this._switchTab(s.id)}>
                    <span>${s.label}</span>
                    <button class="tab-close" @click=${a=>{a.stopPropagation(),this._closeTab(s.id)}}>x</button>
                  </div>
                `)}
                <button class="tab-add" title="New tab" @click=${this._addTab}>+</button>
              </div>
              <div class="tab-content">
                ${this._router.outlet()}
              </div>`:i`
              <div class="empty-state">
                <img src="/static/images/shenas.png" alt="shenas" />
                <p>Open a page from the sidebar or press Ctrl+O</p>
              </div>`}
        </div>
        <div class="divider" @mousedown=${this._startDrag("right")}></div>
        <div class="panel-right" style="width: ${this._rightWidth}px">
          ${this._inspectTable?this._renderInspect():this._renderDbStats()}
        </div>
      </div>
      <shenas-command-palette
        ?open=${this._paletteOpen}
        .commands=${this._paletteCommands}
        @execute=${this._executePaletteCommand}
        @close=${()=>{this._paletteOpen=!1}}
      ></shenas-command-palette>
      <shenas-command-palette
        ?open=${this._navPaletteOpen}
        .commands=${this._navCommands}
        @execute=${this._executePaletteCommand}
        @close=${()=>{this._navPaletteOpen=!1}}
      ></shenas-command-palette>
    `}_navItem(e,s,a){return i`
      <a class="nav-item" href="/${e}" aria-selected=${a===e}
        @click=${n=>{n.preventDefault(),n.ctrlKey||n.metaKey?this._openTab(`/${e}`,s):this._navigateTo(`/${e}`,s)}}>
        ${s}
      </a>
    `}_renderDynamicHome(){return this._components.length>0?this._renderDynamicTab(this._components[0].name):this._renderSettings("pipe")}_renderDynamicTab(e){const s=this._components.find(a=>a.name===e);if(!s)return i`<p class="empty">Unknown page: ${e}</p>`;if(!this._loadedScripts.has(s.js)){this._loadedScripts=new Set([...this._loadedScripts,s.js]);const a=document.createElement("script");a.type="module",a.src=s.js,document.head.appendChild(a)}return i`<div class="component-host">
      ${this._getOrCreateElement(s)}
    </div>`}_renderPluginDetail(e,s,a="details"){return i`<shenas-plugin-detail
      api-base="${this.apiBase}"
      kind="${e}"
      name="${s}"
      active-tab="${a}"
    ></shenas-plugin-detail>`}_renderSettings(e){return i`<shenas-settings
      api-base="${this.apiBase}"
      active-kind="${e||"overview"}"
      .onNavigate=${s=>{this._navigateTo(`/settings/${s}`)}}
    ></shenas-settings>`}async _inspect(e,s){if(!/^[a-zA-Z_]\w*$/.test(e)||!/^[a-zA-Z_]\w*$/.test(s))return;const a=`${e}.${s}`;if(this._inspectTable===a){this._inspectTable=null,this._inspectRows=null;return}this._inspectTable=a,this._inspectRows=null;try{const n=await fetch(`${this.apiBase}/db/preview/${e}/${s}?limit=50`);this._inspectRows=n.ok?await n.json():[]}catch{this._inspectRows=[]}}_renderDbStats(){const e=this._dbStatus;return e?i`
      <div class="db-section">
        <div class="db-meta">
          ${e.size_mb!=null?i`<code>${e.size_mb} MB</code>`:i`<span>Not created</span>`}
        </div>
        ${(e.schemas||[]).map(s=>i`
            <h4>${s.name}</h4>
            ${s.tables.map(a=>i`
                <div class="db-table-row">
                  <span class="db-table-name">${a.name}</span>
                  <span class="db-table-count">${a.rows}</span>
                </div>
                ${a.earliest?i`<span class="db-date-range">${a.earliest} - ${a.latest}</span>`:""}
              `)}
          `)}
      </div>
    `:i`<p class="empty">No database</p>`}_renderInspect(){return i`
      <div class="inspect-header">
        <h4>${this._inspectTable}</h4>
        <button class="inspect-close" title="Close" @click=${()=>{this._inspectTable=null,this._inspectRows=null}}>x</button>
      </div>
      ${this._inspectRows?this._inspectRows.length===0?i`<p class="empty" style="font-size:0.75rem">No rows</p>`:i`
            <div style="overflow-x: auto;">
              <table class="inspect-table">
                <thead>
                  <tr>${Object.keys(this._inspectRows[0]).map(e=>i`<th>${e}</th>`)}</tr>
                </thead>
                <tbody>
                  ${this._inspectRows.map(e=>i`<tr>${Object.keys(e).map(s=>i`<td title="${e[s]??""}">${e[s]??""}</td>`)}</tr>`)}
                </tbody>
              </table>
            </div>
          `:i`<p class="loading" style="font-size:0.75rem">Loading...</p>`}
    `}_getOrCreateElement(e){if(!this._elementCache.has(e.name)){const s=document.createElement(e.tag);s.setAttribute("api-base",this.apiBase),this._elementCache.set(e.name,s)}return this._elementCache.get(e.name)}}c(j,"properties",{apiBase:{type:String,attribute:"api-base"},_components:{state:!0},_loading:{state:!0},_loadedScripts:{state:!0},_leftWidth:{state:!0},_rightWidth:{state:!0},_dbStatus:{state:!0},_inspectTable:{state:!0},_inspectRows:{state:!0},_paletteOpen:{state:!0},_paletteCommands:{state:!0},_navPaletteOpen:{state:!0},_navCommands:{state:!0},_tabs:{state:!0},_activeTabId:{state:!0}}),c(j,"styles",[N,y,m`
      :host {
        display: block;
        height: 100vh;
        color: var(--shenas-text, #222);
      }
      .layout {
        display: flex;
        height: 100%;
      }
      .panel-left {
        flex-shrink: 0;
        overflow-y: auto;
        padding: 1.5rem 1rem;
        border-right: 1px solid var(--shenas-border, #e0e0e0);
      }
      .panel-middle {
        flex: 1;
        min-width: 0;
        display: flex;
        flex-direction: column;
        overflow: hidden;
      }
      .tab-bar {
        display: flex;
        align-items: flex-end;
        background: var(--shenas-bg-secondary, #fafafa);
        border-bottom: 1px solid var(--shenas-border, #e0e0e0);
        overflow-x: auto;
        overflow-y: hidden;
        scrollbar-width: none;
        flex-shrink: 0;
        padding: 0 4px;
        min-height: 36px;
      }
      .tab-bar::-webkit-scrollbar {
        display: none;
      }
      .tab-item {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 6px 14px;
        font-size: 0.8rem;
        color: var(--shenas-text-muted, #888);
        cursor: pointer;
        white-space: nowrap;
        user-select: none;
        border-radius: 8px 8px 0 0;
        margin-bottom: -1px;
        border: 1px solid transparent;
        border-bottom: none;
        position: relative;
      }
      .tab-item:hover {
        color: var(--shenas-text-secondary, #666);
        background: var(--shenas-bg-hover, #f5f5f5);
      }
      .tab-item.active {
        color: var(--shenas-text, #222);
        background: var(--shenas-bg, #fff);
        border-color: var(--shenas-border, #e0e0e0);
        font-weight: 500;
      }
      .tab-close {
        background: none;
        border: none;
        cursor: pointer;
        color: var(--shenas-text-faint, #aaa);
        font-size: 0.65rem;
        width: 16px;
        height: 16px;
        padding: 0;
        line-height: 1;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        opacity: 0;
        transition: opacity 0.1s;
      }
      .tab-item:hover .tab-close,
      .tab-item.active .tab-close {
        opacity: 1;
      }
      .tab-close:hover {
        color: var(--shenas-text, #222);
        background: var(--shenas-border-light, #f0f0f0);
      }
      .tab-add {
        background: none;
        border: none;
        cursor: pointer;
        color: var(--shenas-text-faint, #aaa);
        font-size: 0.85rem;
        padding: 6px 8px;
        line-height: 1;
        border-radius: 4px;
        margin-bottom: 2px;
      }
      .tab-add:hover {
        color: var(--shenas-text, #222);
        background: var(--shenas-bg-hover, #f5f5f5);
      }
      .tab-content {
        flex: 1;
        overflow-y: auto;
        padding: 1.5rem 2rem;
      }
      .empty-state {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 1rem;
        color: var(--shenas-text-faint, #aaa);
      }
      .empty-state img {
        width: 128px;
        height: 128px;
        opacity: 0.3;
      }
      .empty-state p {
        font-size: 0.9rem;
      }
      .panel-right {
        flex-shrink: 0;
        overflow-y: auto;
        padding: 1.5rem 1rem;
        border-left: 1px solid var(--shenas-border, #e0e0e0);
      }
      .divider {
        width: 4px;
        cursor: col-resize;
        background: transparent;
        flex-shrink: 0;
      }
      .divider:hover,
      .divider.dragging {
        background: var(--shenas-border, #e0e0e0);
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
        color: var(--shenas-text-secondary, #666);
        text-decoration: none;
        border-radius: 4px;
        border: none;
        background: none;
        cursor: pointer;
        text-align: left;
      }
      .nav-item:hover {
        background: var(--shenas-bg-hover, #f5f5f5);
        color: var(--shenas-text, #222);
      }
      .nav-item[aria-selected="true"] {
        background: var(--shenas-bg-selected, #f0f4ff);
        color: var(--shenas-text, #222);
        font-weight: 600;
      }
      .component-host {
        height: calc(100vh - 4rem);
      }
      .db-section h4 {
        font-size: 0.75rem;
        text-transform: uppercase;
        color: var(--shenas-text-muted, #888);
        letter-spacing: 0.05em;
        margin: 1rem 0 0.4rem;
      }
      .db-section h4:first-child {
        margin-top: 0;
      }
      .db-meta {
        font-size: 0.8rem;
        color: var(--shenas-text-secondary, #666);
        margin: 0 0 0.8rem;
      }
      .db-meta code {
        background: var(--shenas-border-light, #f0f0f0);
        padding: 1px 4px;
        border-radius: 2px;
        font-size: 0.75rem;
      }
      .db-table-row {
        display: flex;
        justify-content: space-between;
        padding: 0.2rem 0;
        font-size: 0.8rem;
        border-bottom: 1px solid var(--shenas-border-light, #f0f0f0);
      }
      .db-table-row:last-child {
        border-bottom: none;
      }
      .db-table-name {
        color: var(--shenas-text, #222);
      }
      .db-table-count {
        color: var(--shenas-text-muted, #888);
        font-size: 0.75rem;
      }
      .db-date-range {
        font-size: 0.7rem;
        color: var(--shenas-text-faint, #aaa);
        display: block;
      }
      .inspect-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.5rem;
      }
      .inspect-header h4 {
        margin: 0;
        font-size: 0.85rem;
        color: var(--shenas-text, #222);
        text-transform: none;
        letter-spacing: normal;
      }
      .inspect-close {
        background: none;
        border: none;
        cursor: pointer;
        color: var(--shenas-text-muted, #888);
        font-size: 1rem;
        padding: 0;
        line-height: 1;
      }
      .inspect-close:hover {
        color: var(--shenas-text, #222);
      }
      .inspect-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.7rem;
        table-layout: auto;
      }
      .inspect-table th {
        text-align: left;
        padding: 0.25rem 0.4rem;
        color: var(--shenas-text-secondary, #666);
        font-weight: 500;
        border-bottom: 1px solid var(--shenas-border, #e0e0e0);
        white-space: nowrap;
      }
      .inspect-table td {
        padding: 0.2rem 0.4rem;
        border-bottom: 1px solid var(--shenas-border-light, #f0f0f0);
        max-width: 120px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    `]);customElements.define("shenas-app",j);class D extends f{constructor(){super(),this.apiBase="/api",this.activeKind="pipe",this.onNavigate=null,this._plugins={},this._loading=!0,this._actionMessage=null,this._installing=!1}connectedCallback(){super.connectedCallback(),this._fetchAll()}async _fetchAll(){this._loading=!0;const t={};await Promise.all(w.map(async({id:e})=>{const s=await fetch(`${this.apiBase}/plugins/${e}`);t[e]=s.ok?await s.json():[]})),this._plugins=t,this._loading=!1}async _togglePlugin(t,e,s){const a=s?"disable":"enable",r=await(await fetch(`${this.apiBase}/plugins/${t}/${e}/${a}`,{method:"POST"})).json();r.ok||(this._actionMessage={type:"error",text:r.message||`${a} failed`}),t==="theme"&&await this._applyActiveTheme(),await this._fetchAll()}async _applyActiveTheme(){const t=await fetch(`${this.apiBase}/theme`);if(!t.ok)return;const{css:e}=await t.json();let s=document.querySelector("link[data-shenas-theme]");e?(s||(s=document.createElement("link"),s.rel="stylesheet",s.setAttribute("data-shenas-theme",""),document.head.appendChild(s)),s.href=e):s&&s.remove()}async _install(t){var l,d;const e=this.shadowRoot.querySelector(`#install-${t}`),s=(l=e==null?void 0:e.value)==null?void 0:l.trim();if(!s)return;this._actionMessage=null;const r=(d=(await(await fetch(`${this.apiBase}/plugins/${t}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({names:[s],skip_verify:!0})})).json()).results)==null?void 0:d[0];r!=null&&r.ok?(this._actionMessage={type:"success",text:r.message},this._installing=!1,await this._fetchAll()):this._actionMessage={type:"error",text:(r==null?void 0:r.message)||"Install failed"}}render(){return this._loading?i`<p class="loading">Loading plugins...</p>`:i`
      ${this._actionMessage?i`<div class="message ${this._actionMessage.type}">
            ${this._actionMessage.text}
          </div>`:""}
      <div class="layout">
        <nav class="sidebar">
          <ul>
            <li>
              <a href="/settings/overview" aria-selected=${this.activeKind==="overview"}>
                Data Flow
              </a>
            </li>
            ${w.map(({id:t,label:e})=>i`
                <li>
                  <a
                    href="/settings/${t}"
                    aria-selected=${this.activeKind===t}
                  >
                    ${e}
                    <span style="color:var(--shenas-text-faint, #aaa); font-weight:normal">
                      (${(this._plugins[t]||[]).length})
                    </span>
                  </a>
                </li>
              `)}
          </ul>
        </nav>
        <div class="content">
          ${this.activeKind==="overview"?i`<shenas-pipeline-overview api-base="${this.apiBase}"></shenas-pipeline-overview>`:this._renderKind(this.activeKind)}
        </div>
      </div>
    `}_renderKind(t){var a;const e=this._plugins[t]||[],s=((a=w.find(n=>n.id===t))==null?void 0:a.label)||t;return i`
      <h3>${s}</h3>
      <shenas-data-list
        .columns=${[{label:"Name",render:n=>i`<a href="/settings/${t}/${n.name}">${n.display_name||n.name}</a>`},{key:"version",label:"Version",class:"mono"},{label:"Added",class:"mono",render:n=>n.added_at?n.added_at.slice(0,10):""},{label:"Status",render:n=>i`<status-toggle ?enabled=${n.enabled!==!1} toggleable @toggle=${()=>this._togglePlugin(t,n.name,n.enabled!==!1)}></status-toggle>`}]}
        .rows=${e}
        .rowClass=${n=>n.enabled===!1?"disabled-row":""}
        ?show-add=${!this._installing}
        @add=${()=>{this._installing=!0}}
        empty-text="No ${s.toLowerCase()} installed"
      ></shenas-data-list>
      ${this._installing?i`<shenas-form-panel
            title="Install new plugin"
            submit-label="Install"
            @submit=${()=>this._install(t)}
            @cancel=${()=>{this._installing=!1}}
          >
            <input
              id="install-${t}"
              type="text"
              placeholder="Plugin name"
              @keydown=${n=>n.key==="Enter"&&this._install(t)}
              style="width: 100%; padding: 0.4rem 0.6rem; border: 1px solid var(--shenas-border-input, #ddd); border-radius: 4px; font-size: 0.85rem; box-sizing: border-box; background: var(--shenas-bg, #fff); color: var(--shenas-text, #222);"
            />
          </shenas-form-panel>`:""}
    `}}c(D,"properties",{apiBase:{type:String,attribute:"api-base"},activeKind:{type:String,attribute:"active-kind"},onNavigate:{type:Function},_plugins:{state:!0},_loading:{state:!0},_actionMessage:{state:!0},_installing:{state:!0}}),c(D,"styles",[x,N,T,y,m`
      :host {
        display: block;
        height: 100%;
      }
      .layout {
        display: flex;
        gap: 2rem;
        height: 100%;
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
        color: var(--shenas-text-secondary, #666);
        border-radius: 4px;
        border-left: 3px solid transparent;
      }
      .sidebar a:hover {
        background: var(--shenas-bg-hover, #f5f5f5);
        color: var(--shenas-text, #222);
      }
      .sidebar a[aria-selected="true"] {
        background: var(--shenas-bg-selected, #f0f4ff);
        color: var(--shenas-text, #222);
        font-weight: 600;
        border-left-color: var(--shenas-primary, #0066cc);
      }
      .content {
        flex: 1;
        min-width: 0;
        display: flex;
        flex-direction: column;
      }
      .content h3 {
        font-size: 1rem;
        margin: 0 0 1rem;
      }
    `]);customElements.define("shenas-settings",D);class R extends f{constructor(){super(),this.apiBase="/api",this.kind="",this.name="",this.activeTab="details",this._info=null,this._loading=!0,this._message=null,this._hasConfig=!1,this._hasAuth=!1,this._tables=[],this._syncing=!1,this._schemaTransforms=[]}willUpdate(t){(t.has("kind")||t.has("name"))&&this._fetchInfo()}async _fetchInfo(){var g;if(!this.kind||!this.name)return;this._loading=!0,this._message=null;const t=await fetch(`${this.apiBase}/plugins/${this.kind}/${this.name}/info`);this._info=t.ok?await t.json():null;const e=this.kind==="pipe"||this.kind==="schema",[s,a,n,r,l]=await Promise.all([fetch(`${this.apiBase}/config?kind=${this.kind}&name=${this.name}`),this.kind==="pipe"?fetch(`${this.apiBase}/auth/${this.name}/fields`):Promise.resolve(null),e?fetch(`${this.apiBase}/db/status`):Promise.resolve(null),this.kind==="schema"?fetch(`${this.apiBase}/db/schema-plugins`):Promise.resolve(null),this.kind==="schema"?fetch(`${this.apiBase}/transforms`):Promise.resolve(null)]);if(s.ok){const p=await s.json();this._hasConfig=p.length>0&&p[0].entries.length>0}if(a!=null&&a.ok){const p=await a.json();this._hasAuth=((g=p.fields)==null?void 0:g.length)>0||!!p.instructions}const d=r!=null&&r.ok?(await r.json())[this.name]||[]:[];if(n!=null&&n.ok){const p=await n.json();if(this.kind==="pipe"){const h=(p.schemas||[]).find(o=>o.name===this.name);this._tables=h?h.tables.filter(o=>!o.name.startsWith("_dlt_")):[]}else if(this.kind==="schema"){const h=(p.schemas||[]).find(o=>o.name==="metrics");this._tables=h?h.tables.filter(o=>d.includes(o.name)):[]}}if(l!=null&&l.ok){const p=await l.json();this._schemaTransforms=p.filter(h=>d.includes(h.target_duckdb_table))}this._loading=!1,this._registerCommands()}_registerCommands(){if(!this._info)return;const t=this._info.display_name||this.name,e=[{id:`remove:${this.kind}:${this.name}`,category:"Plugin",label:`Remove ${t}`,action:()=>this._remove()}];this.dispatchEvent(new CustomEvent("register-command",{bubbles:!0,composed:!0,detail:{componentId:`plugin-detail:${this.kind}:${this.name}`,commands:e}}))}async _toggle(){var a;const t=((a=this._info)==null?void 0:a.enabled)!==!1?"disable":"enable",s=await(await fetch(`${this.apiBase}/plugins/${this.kind}/${this.name}/${t}`,{method:"POST"})).json();this._message={type:s.ok?"success":"error",text:s.message||`${t} failed`},await this._fetchInfo(),this.dispatchEvent(new CustomEvent("plugin-state-changed",{bubbles:!0,composed:!0}))}async _sync(){this._syncing=!0,this._message=null;try{const t=await fetch(`${this.apiBase}/sync/${this.name}`,{method:"POST"});if(!t.ok){const d=await t.json().catch(()=>({}));this._message={type:"error",text:d.detail||`Sync failed (${t.status})`},this._syncing=!1;return}const e=t.body.getReader(),s=new TextDecoder;let a="",n="",r=!1;for(;;){const{done:d,value:g}=await e.read();if(d)break;const p=s.decode(g,{stream:!0});for(const h of p.split(`
`))h.startsWith("event: ")&&(a=h.slice(7).trim()),h.startsWith("data: ")&&(n=h.slice(6));a==="error"&&(r=!0)}let l="Sync complete";try{l=JSON.parse(n).message||l}catch{}this._message={type:r?"error":"success",text:l},r||await this._fetchInfo()}catch(t){this._message={type:"error",text:`Sync failed: ${t.message}`}}this._syncing=!1}async _remove(){const e=await(await fetch(`${this.apiBase}/plugins/${this.kind}/${this.name}`,{method:"DELETE"})).json();e.ok?(window.history.pushState({},"",`/settings/${this.kind}`),window.dispatchEvent(new PopStateEvent("popstate"))):this._message={type:"error",text:e.message||"Remove failed"}}render(){if(this._loading)return i`<p class="loading">Loading...</p>`;if(!this._info)return i`<p>Plugin not found.</p>`;const t=this._info,e=t.enabled!==!1,s=`/settings/${this.kind}/${this.name}`;return i`
      <a class="back" href="/settings/${this.kind}">&larr; Back to ${this.kind}s</a>

      <div class="title-row">
        <h2>${t.display_name||t.name} <span class="kind-badge">${t.kind}</span></h2>
        <div class="title-actions">
          ${this.kind==="pipe"&&e?i`<button @click=${this._sync} ?disabled=${this._syncing}>${this._syncing?"Syncing...":"Sync"}</button>`:""}
          <button class="danger" @click=${this._remove}>Remove</button>
        </div>
      </div>

      ${this._hasConfig||this._hasAuth?i`
          <div class="tabs">
            <a class="tab" href="${s}" aria-selected=${this.activeTab==="details"}>Details</a>
            ${this._hasConfig?i`<a class="tab" href="${s}/config" aria-selected=${this.activeTab==="config"}>Config</a>`:""}
            ${this._hasAuth?i`<a class="tab" href="${s}/auth" aria-selected=${this.activeTab==="auth"}>Auth</a>`:""}
          </div>`:""}

      ${this.activeTab==="config"&&this._hasConfig?i`<shenas-config api-base="${this.apiBase}" kind="${this.kind}" name="${this.name}"></shenas-config>`:this.activeTab==="auth"&&this._hasAuth?i`<shenas-auth api-base="${this.apiBase}" pipe-name="${this.name}"></shenas-auth>`:this._renderDetails(t,e)}

      ${this._message?i`<div class="message ${this._message.type}">
            ${this._message.text}
          </div>`:""}
    `}_renderDetails(t,e){return i`
      ${t.description?i`<div class="description">${t.description}</div>`:""}

      <div class="state-table">
        <div class="state-row">
          <span class="state-label">Status</span>
          <span class="state-value">
            <status-toggle ?enabled=${e} toggleable @toggle=${this._toggle}></status-toggle>
          </span>
        </div>
        ${this._stateRow("Last synced",t.synced_at)}
        ${this._stateRow("Added",t.added_at)}
        ${this._stateRow("Updated",t.updated_at)}
        ${this._stateRow("Status changed",t.status_changed_at)}
      </div>

      ${this.kind==="pipe"||this.kind==="schema"?i`
          <h4 class="section-title">Resources</h4>
          <shenas-data-list
            .columns=${[{key:"name",label:"Table",class:"mono"},{key:"rows",label:"Rows",class:"muted"},{label:"Range",class:"muted",render:s=>s.earliest?`${s.earliest} - ${s.latest}`:""}]}
            .rows=${this._tables}
            empty-text="No tables synced yet"
          ></shenas-data-list>`:""}

      ${this.kind==="pipe"?i`
          <h4 class="section-title">Transforms</h4>
          <shenas-transforms api-base="${this.apiBase}" source="${this.name}"></shenas-transforms>`:""}

      ${this.kind==="schema"&&this._schemaTransforms.length>0?i`
          <h4 class="section-title">Transforms</h4>
          <shenas-data-list
            .columns=${[{key:"id",label:"ID",class:"muted"},{label:"Source",class:"mono",render:s=>`${s.source_duckdb_schema}.${s.source_duckdb_table}`},{label:"Target",class:"mono",render:s=>`${s.target_duckdb_schema}.${s.target_duckdb_table}`},{label:"Description",render:s=>s.description||""},{label:"Status",render:s=>i`<status-toggle ?enabled=${s.enabled}></status-toggle>`}]}
            .rows=${this._schemaTransforms}
            .rowClass=${s=>s.enabled?"":"disabled-row"}
            empty-text="No transforms"
          ></shenas-data-list>`:""}

    `}_stateRow(t,e){return e?i`
      <div class="state-row">
        <span class="state-label">${t}</span>
        <span class="state-value">${e.slice(0,19)}</span>
      </div>
    `:""}}c(R,"properties",{apiBase:{type:String,attribute:"api-base"},kind:{type:String},name:{type:String},activeTab:{type:String,attribute:"active-tab"},_info:{state:!0},_loading:{state:!0},_message:{state:!0},_hasConfig:{state:!0},_hasAuth:{state:!0},_tables:{state:!0},_syncing:{state:!0},_schemaTransforms:{state:!0}}),c(R,"styles",[x,N,T,J,y,m`
      :host {
        display: block;
      }
      .back {
        font-size: 0.9rem;
        display: inline-block;
        margin-bottom: 1rem;
      }
      .title-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      .title-actions {
        display: flex;
        gap: 0.5rem;
      }
      h2 {
        margin: 0;
        font-size: 1.3rem;
      }
      .kind-badge {
        background: var(--shenas-border-light, #f0f0f0);
        color: var(--shenas-text-secondary, #666);
        padding: 0.15rem 0.5rem;
        border-radius: 3px;
        font-size: 0.65rem;
        font-weight: 400;
        vertical-align: middle;
        margin-left: 0.3rem;
      }
      .description {
        color: var(--shenas-text-secondary, #666);
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
        border-bottom: 1px solid var(--shenas-border-light, #f0f0f0);
        font-size: 0.9rem;
      }
      .state-row:last-child {
        border-bottom: none;
      }
      .state-label {
        width: 120px;
        color: var(--shenas-text-muted, #888);
        flex-shrink: 0;
      }
      .state-value {
        color: var(--shenas-text, #222);
      }
      button {
        padding: 0.5rem 1rem;
        font-size: 0.9rem;
      }
      .section-title {
        font-size: 0.8rem;
        text-transform: uppercase;
        color: var(--shenas-text-muted, #888);
        letter-spacing: 0.05em;
        margin: 1.5rem 0 0.5rem;
      }
    `]);customElements.define("shenas-plugin-detail",R);const q="background:none;border:none;cursor:pointer;color:var(--shenas-text-faint, #aaa);font-size:0.7rem;padding:0 2px";class A extends f{constructor(){super(),this.apiBase="/api",this.source="",this._transforms=[],this._loading=!0,this._editing=null,this._editSql="",this._message=null,this._previewRows=null,this._creating=!1,this._newForm=this._emptyForm(),this._dbTables={},this._schemaTables={}}_emptyForm(){return{source_duckdb_table:"",target_duckdb_table:"",description:"",sql:""}}connectedCallback(){super.connectedCallback(),this._fetchAll()}async _fetchAll(){this._loading=!0;const t=this.source?`?source=${this.source}`:"",e=await fetch(`${this.apiBase}/transforms${t}`);this._transforms=e.ok?await e.json():[],this._loading=!1,this._registerCommands()}_registerCommands(){const t=[];for(const e of this._transforms){const s=e.description||`${e.source_duckdb_table} -> ${e.target_duckdb_table}`;t.push({id:`transform:toggle:${e.id}`,category:"Transform",label:`${e.enabled?"Disable":"Enable"} #${e.id}`,description:s,action:()=>this._toggle(e)}),e.is_default||t.push({id:`transform:delete:${e.id}`,category:"Transform",label:`Delete #${e.id}`,description:s,action:()=>this._delete(e)})}this.dispatchEvent(new CustomEvent("register-command",{bubbles:!0,composed:!0,detail:{componentId:`transforms:${this.source}`,commands:t}}))}_inspectTable(t,e){this.dispatchEvent(new CustomEvent("inspect-table",{bubbles:!0,composed:!0,detail:{schema:t,table:e}}))}async _toggle(t){const e=t.enabled?"disable":"enable";await fetch(`${this.apiBase}/transforms/${t.id}/${e}`,{method:"POST"}),await this._fetchAll()}async _delete(t){const s=await(await fetch(`${this.apiBase}/transforms/${t.id}`,{method:"DELETE"})).json();s.ok?(this._message={type:"success",text:s.message},await this._fetchAll()):this._message={type:"error",text:s.detail||s.message||"Delete failed"}}_startEdit(t){this._editing=t.id,this._editSql=t.sql,this._previewRows=null}_cancelEdit(){this._editing=null,this._editSql="",this._previewRows=null}async _saveEdit(){const t=await fetch(`${this.apiBase}/transforms/${this._editing}`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({sql:this._editSql})});if(t.ok)this._message={type:"success",text:"Transform updated"},this._editing=null,await this._fetchAll();else{const e=await t.json();this._message={type:"error",text:e.detail||"Update failed"}}}async _startCreate(){this._creating=!0,this._newForm=this._emptyForm(),this._editing=null,this._previewRows=null;const[t,e]=await Promise.all([fetch(`${this.apiBase}/db/tables`),fetch(`${this.apiBase}/db/schema-tables`)]);this._dbTables=t.ok?await t.json():{},this._schemaTables=e.ok?await e.json():{}}_cancelCreate(){this._creating=!1,this._newForm=this._emptyForm()}_updateNewForm(t,e){this._newForm={...this._newForm,[t]:e}}async _saveCreate(){const t=this._newForm;if(!t.source_duckdb_table||!t.target_duckdb_table||!t.sql){this._message={type:"error",text:"Fill in all required fields"};return}const e=await fetch(`${this.apiBase}/transforms`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({source_duckdb_schema:this.source,source_duckdb_table:t.source_duckdb_table,target_duckdb_schema:"metrics",target_duckdb_table:t.target_duckdb_table,source_plugin:this.source,description:t.description,sql:t.sql})});if(e.ok)this._message={type:"success",text:"Transform created"},this._creating=!1,this._newForm=this._emptyForm(),await this._fetchAll();else{const s=await e.json();this._message={type:"error",text:s.detail||"Create failed"}}}async _preview(){const t=await fetch(`${this.apiBase}/transforms/${this._editing}/test?limit=5`,{method:"POST"});if(t.ok)this._previewRows=await t.json();else{const e=await t.json();this._message={type:"error",text:e.detail||"Preview failed"}}}render(){return this._loading?i`<p class="loading">Loading transforms...</p>`:i`
      ${this._message?i`<div class="message ${this._message.type}">
            ${this._message.text}
          </div>`:""}
      ${this._editing?this._renderEditor():""}
      ${this._creating?this._renderCreateForm():""}
      <shenas-data-list
        ?show-add=${!this._creating&&!this._editing}
        @add=${this._startCreate}
        .columns=${[{key:"id",label:"ID",class:"muted"},{label:"Source",class:"mono",render:t=>i`${t.source_duckdb_schema}.${t.source_duckdb_table} <button style=${q} title="Inspect table" @click=${()=>this._inspectTable(t.source_duckdb_schema,t.source_duckdb_table)}>&#9655;</button>`},{label:"Target",class:"mono",render:t=>i`${t.target_duckdb_schema}.${t.target_duckdb_table} <button style=${q} title="Inspect table" @click=${()=>this._inspectTable(t.target_duckdb_schema,t.target_duckdb_table)}>&#9655;</button>`},{label:"Description",render:t=>i`${t.description||""}${t.is_default?i`<span style="font-size:0.75rem;color:var(--shenas-text-muted, #888);background:var(--shenas-border-light, #f0f0f0);padding:1px 5px;border-radius:3px;margin-left:4px">default</span>`:""}`},{label:"Status",render:t=>i`<status-toggle ?enabled=${t.enabled} toggleable @toggle=${()=>this._toggle(t)}></status-toggle>`}]}
        .rows=${this._transforms}
        .rowClass=${t=>t.enabled?"":"disabled-row"}
        .actions=${t=>i`
          ${t.is_default?i`<button @click=${()=>this._startEdit(t)}>View</button>`:i`<button @click=${()=>this._startEdit(t)}>Edit</button>`}
          ${t.is_default?"":i`<button class="danger" @click=${()=>this._delete(t)}>Delete</button>`}
        `}
        empty-text="No transforms"
      ></shenas-data-list>
    `}_renderCreateForm(){const t=this._newForm,e=this.source,s=this._dbTables[e]||[],a=Object.values(this._schemaTables||{}).flat();return i`
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
              .value=${t.source_duckdb_table}
              @change=${n=>this._updateNewForm("source_duckdb_table",n.target.value)}
            >
              <option value="">-- select --</option>
              ${s.map(n=>i`<option value=${n} ?selected=${t.source_duckdb_table===n}>${n}</option>`)}
            </select>
          </label>
          <label>
            Schema table
            <select
              .value=${t.target_duckdb_table}
              @change=${n=>this._updateNewForm("target_duckdb_table",n.target.value)}
            >
              <option value="">-- select --</option>
              ${a.map(n=>i`<option value=${n} ?selected=${t.target_duckdb_table===n}>${n}</option>`)}
            </select>
          </label>
          <label class="form-full">
            Description
            <input
              .value=${t.description}
              @input=${n=>this._updateNewForm("description",n.target.value)}
            />
          </label>
        </div>
        <textarea
          .value=${t.sql}
          @input=${n=>this._updateNewForm("sql",n.target.value)}
          placeholder="SELECT ... FROM ${e}.${t.source_duckdb_table||"table_name"}"
        ></textarea>
      </shenas-form-panel>
    `}_renderEditor(){const t=this._transforms.find(s=>s.id===this._editing);if(!t)return"";const e=t.is_default;return i`
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
          ${e?"":i`<button @click=${this._saveEdit}>Save</button>`}
          <button @click=${this._preview}>Preview</button>
          <button @click=${this._cancelEdit}>${e?"Close":"Cancel"}</button>
        </div>
        ${this._previewRows?this._renderPreview():""}
      </div>
    `}_renderPreview(){if(!this._previewRows||this._previewRows.length===0)return i`<p class="loading">No preview rows</p>`;const t=Object.keys(this._previewRows[0]);return i`
      <div class="preview-table">
        <table>
          <thead>
            <tr>
              ${t.map(e=>i`<th>${e}</th>`)}
            </tr>
          </thead>
          <tbody>
            ${this._previewRows.map(e=>i`
                <tr>
                  ${t.map(s=>i`<td>${e[s]}</td>`)}
                </tr>
              `)}
          </tbody>
        </table>
      </div>
    `}}c(A,"properties",{apiBase:{type:String,attribute:"api-base"},source:{type:String},_transforms:{state:!0},_loading:{state:!0},_editing:{state:!0},_editSql:{state:!0},_message:{state:!0},_previewRows:{state:!0},_creating:{state:!0},_newForm:{state:!0},_dbTables:{state:!0},_schemaTables:{state:!0}}),c(A,"styles",[M,x,T,y,m`
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
      textarea {
        width: 100%;
        min-height: 120px;
        font-family: monospace;
        font-size: 0.85rem;
        padding: 0.5rem;
        border: 1px solid var(--shenas-border-input, #ddd);
        border-radius: 4px;
        resize: vertical;
        box-sizing: border-box;
      }
      textarea.readonly {
        background: var(--shenas-bg-hover, #f5f5f5);
        color: var(--shenas-text-secondary, #666);
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
        color: var(--shenas-text-secondary, #666);
        display: flex;
        flex-direction: column;
        gap: 0.2rem;
      }
      .form-grid input,
      .form-grid select {
        padding: 0.35rem 0.5rem;
        border: 1px solid var(--shenas-border-input, #ddd);
        border-radius: 4px;
        font-size: 0.85rem;
        font-family: monospace;
      }
      .form-full {
        grid-column: 1 / -1;
      }
    `]);customElements.define("shenas-transforms",A);
