var I=Object.defineProperty;var F=(h,e,t)=>e in h?I(h,e,{enumerable:!0,configurable:!0,writable:!0,value:t}):h[e]=t;var l=(h,e,t)=>F(h,typeof e!="symbol"?e+"":e,t);import{LitElement as u,css as c,html as a}from"lit";import O,{dagre as q}from"cytoscape";import{Router as L}from"@lit-labs/router";class $ extends u{constructor(){super(),this.open=!1,this.commands=[],this._query="",this._filtered=[],this._selectedIndex=0}updated(e){e.has("open")&&this.open&&(this._query="",this._selectedIndex=0,this._filter(),requestAnimationFrame(()=>{const t=this.renderRoot.querySelector("input");t&&t.focus()})),e.has("commands")&&this._filter()}_filter(){const e=this._query.toLowerCase();e?this._filtered=this.commands.filter(t=>t.label.toLowerCase().includes(e)||t.category.toLowerCase().includes(e)||(t.description||"").toLowerCase().includes(e)):this._filtered=this.commands,this._selectedIndex>=this._filtered.length&&(this._selectedIndex=Math.max(0,this._filtered.length-1))}_onInput(e){this._query=e.target.value,this._selectedIndex=0,this._filter()}_onKeydown(e){if(e.key==="ArrowDown")e.preventDefault(),this._filtered.length>0&&(this._selectedIndex=Math.min(this._selectedIndex+1,this._filtered.length-1)),this._scrollToSelected();else if(e.key==="ArrowUp")e.preventDefault(),this._selectedIndex=Math.max(this._selectedIndex-1,0),this._scrollToSelected();else if(e.key==="Enter"){e.preventDefault();const t=this._filtered[this._selectedIndex];t&&this._execute(t)}else e.key==="Escape"&&this._close()}_scrollToSelected(){requestAnimationFrame(()=>{const e=this.renderRoot.querySelector(".item.selected");e&&e.scrollIntoView({block:"nearest"})})}_execute(e){this.dispatchEvent(new CustomEvent("execute",{detail:e,bubbles:!0,composed:!0}))}_close(){this.dispatchEvent(new CustomEvent("close",{bubbles:!0,composed:!0}))}render(){return this.open?a`
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
          ${this._filtered.length===0?a`<div class="empty">No matching commands</div>`:this._filtered.map((e,t)=>a`
                  <div
                    class="item ${t===this._selectedIndex?"selected":""}"
                    @click=${()=>this._execute(e)}
                    @mouseenter=${()=>{this._selectedIndex=t}}
                  >
                    <span class="item-category">${e.category}</span>
                    <span class="item-label">${e.label}</span>
                    ${e.description?a`<span class="item-desc">${e.description}</span>`:""}
                  </div>
                `)}
        </div>
      </div>
    `:a``}}l($,"properties",{open:{type:Boolean,reflect:!0},commands:{type:Array},_query:{state:!0},_filtered:{state:!0},_selectedIndex:{state:!0}}),l($,"styles",c`
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
  `);customElements.define("shenas-command-palette",$);class w extends u{constructor(){super(),this.enabled=!1,this.toggleable=!1}updated(){this.title=this.enabled?"Enabled":"Disabled"}render(){return a`<div class="track" @click=${this._onClick}><div class="knob"></div></div>`}_onClick(){this.toggleable&&this.dispatchEvent(new CustomEvent("toggle",{bubbles:!0,composed:!0}))}}l(w,"properties",{enabled:{type:Boolean,reflect:!0},toggleable:{type:Boolean,reflect:!0}}),l(w,"styles",c`
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
  `);customElements.define("status-toggle",w);const P=c`
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
`,f=c`
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
`,M=c`
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
`,_=c`
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
`,b=c`
  .loading {
    color: var(--shenas-text-muted, #888);
    font-style: italic;
  }
  .empty {
    color: var(--shenas-text-muted, #888);
    padding: 0.5rem 0;
  }
`,j=c`
  a {
    color: var(--shenas-primary, #0066cc);
    text-decoration: none;
  }
  a:hover {
    text-decoration: underline;
  }
`;class x extends u{constructor(){super(),this.columns=[],this.rows=[],this.rowClass=null,this.actions=null,this.emptyText="No items",this.showAdd=!1}_onAdd(){this.dispatchEvent(new CustomEvent("add",{bubbles:!0,composed:!0}))}render(){const e=typeof this.actions=="function",t=this.showAdd?a`<div class="add-row"><button class="add-btn" title="Add" @click=${this._onAdd}>+</button></div>`:"";return!this.rows||this.rows.length===0?a`<p class="empty">${this.emptyText}</p>${t}`:a`
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
                ${this.columns.map(n=>a`
                  <td class="${n.class||""}">
                    ${n.render?n.render(s):s[n.key]}
                  </td>
                `)}
                ${e?a`<td class="actions-cell">${this.actions(s)}</td>`:""}
              </tr>
            `)}
        </tbody>
      </table>
      ${t}
    `}}l(x,"properties",{columns:{type:Array},rows:{type:Array},rowClass:{type:Object},actions:{type:Object},emptyText:{type:String,attribute:"empty-text"},showAdd:{type:Boolean,attribute:"show-add"}}),l(x,"styles",[P,f,b,c`
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
    `]);customElements.define("shenas-data-list",x);class k extends u{constructor(){super(),this.title="",this.submitLabel="Save"}render(){return a`
      ${this.title?a`<h3>${this.title}</h3>`:""}
      <slot></slot>
      <div class="actions">
        <button @click=${this._onSubmit}>${this.submitLabel}</button>
        <button @click=${this._onCancel}>Cancel</button>
      </div>
    `}_onSubmit(){this.dispatchEvent(new CustomEvent("submit",{bubbles:!0,composed:!0}))}_onCancel(){this.dispatchEvent(new CustomEvent("cancel",{bubbles:!0,composed:!0}))}}l(k,"properties",{title:{type:String},submitLabel:{type:String,attribute:"submit-label"}}),l(k,"styles",[f,c`
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
    `]);customElements.define("shenas-form-panel",k);let A=!1;class S extends u{constructor(){super(),this.apiBase="/api",this._loading=!0,this._empty=!1,this._cy=null,this._elements=null,this._resizeObserver=null}connectedCallback(){super.connectedCallback(),this._fetchData()}disconnectedCallback(){super.disconnectedCallback(),this._cy&&(this._cy.destroy(),this._cy=null),this._resizeObserver&&(this._resizeObserver.disconnect(),this._resizeObserver=null)}async _fetchData(){this._loading=!0;try{const[e,t,s,n]=await Promise.all([fetch(`${this.apiBase}/plugins/pipe`),fetch(`${this.apiBase}/plugins/schema`),fetch(`${this.apiBase}/transforms`),fetch(`${this.apiBase}/db/schema-plugins`)]),i=e.ok?await e.json():[],r=t.ok?await t.json():[],d=s.ok?await s.json():[],o=n.ok?await n.json():{};this._buildElements(i,r,d,o)}catch(e){console.error("Failed to fetch overview data:",e)}this._loading=!1}_buildElements(e,t,s,n){const i=[],r=new Set,d={};for(const[o,p]of Object.entries(n))for(const g of p)d[g]=o;for(const o of e){const p=`pipe:${o.name}`;r.add(p),i.push({data:{id:p,label:o.display_name||o.name,kind:"pipe"}})}for(const o of t){const p=`schema:${o.name}`;r.add(p),i.push({data:{id:p,label:o.display_name||o.name,kind:"schema"}})}for(const o of s){const p=`pipe:${o.source_plugin}`,g=d[o.target_duckdb_table],m=g?`schema:${g}`:null;if(!m||!r.has(p)||!r.has(m))continue;const v=o.description||`${o.source_duckdb_table} -> ${o.target_duckdb_table}`,D=v.length>30?v.slice(0,28)+"...":v;i.push({data:{id:`transform:${o.id}`,source:p,target:m,label:D,enabled:o.enabled?"yes":"no",sourcePlugin:o.source_plugin}})}this._elements=i,this._empty=s.length===0}_initCytoscape(){const e=this.renderRoot.querySelector("#cy");!e||!this._elements||(A||(O.use(q),A=!0),this._cy&&this._cy.destroy(),this._cy=O({container:e,elements:this._elements,style:[{selector:"node",style:{label:"data(label)","text-valign":"center","text-halign":"center","font-size":12,color:"#fff","text-wrap":"wrap","text-max-width":100,width:120,height:40,shape:"round-rectangle"}},{selector:'node[kind="pipe"]',style:{"background-color":"#4a90d9",cursor:"pointer"}},{selector:'node[kind="schema"]',style:{"background-color":"#66bb6a",cursor:"pointer"}},{selector:"edge",style:{"curve-style":"bezier","target-arrow-shape":"triangle","target-arrow-color":"#999","line-color":"#999",cursor:"pointer",width:2,label:"data(label)","font-size":9,color:"#888","text-rotation":"autorotate","text-margin-y":-8}},{selector:'edge[enabled="yes"]',style:{"line-style":"solid"}},{selector:'edge[enabled="no"]',style:{"line-style":"dashed","line-color":"#ccc","target-arrow-color":"#ccc",opacity:.5}}],layout:{name:"dagre",rankDir:"LR",nodeSep:60,rankSep:150,padding:30},userZoomingEnabled:!0,userPanningEnabled:!0,boxSelectionEnabled:!1}),this._cy.on("tap","node",t=>{const s=t.target.data(),n=s.id.substring(s.id.indexOf(":")+1),i=s.kind==="pipe"?`/settings/pipe/${n}`:`/settings/schema/${n}`;this.dispatchEvent(new CustomEvent("navigate",{bubbles:!0,composed:!0,detail:{path:i}}))}),this._cy.on("tap","edge",t=>{const s=t.target.data("sourcePlugin");s&&this.dispatchEvent(new CustomEvent("navigate",{bubbles:!0,composed:!0,detail:{path:`/settings/pipe/${s}`}}))}),this._resizeObserver&&this._resizeObserver.disconnect(),this._resizeObserver=new ResizeObserver(()=>{this._cy&&(this._cy.resize(),this._cy.fit(void 0,30))}),this._resizeObserver.observe(e))}firstUpdated(){!this._loading&&this._elements&&this._initCytoscape()}updated(e){e.has("_loading")&&!this._loading&&this._elements&&requestAnimationFrame(()=>this._initCytoscape())}render(){return this._loading?a`<p class="loading">Loading overview...</p>`:a`
      <div id="cy"></div>
      <div class="legend">
        <span class="legend-item"><span class="legend-dot pipe"></span> Pipe</span>
        <span class="legend-item"><span class="legend-dot schema"></span> Schema</span>
        <span class="legend-item"><span class="legend-line enabled"></span> Transform</span>
        <span class="legend-item"><span class="legend-line disabled"></span> Disabled</span>
      </div>
      ${this._empty?a`<p class="empty">No transforms configured. Add transforms in pipe settings.</p>`:""}
    `}}l(S,"properties",{apiBase:{type:String,attribute:"api-base"},_loading:{state:!0},_empty:{state:!0}}),l(S,"styles",[b,c`
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
      .legend-line {
        width: 20px;
        height: 2px;
      }
      .legend-line.enabled { background: var(--shenas-text-muted, #888); }
      .legend-line.disabled { background: var(--shenas-text-faint, #aaa); border-top: 2px dashed var(--shenas-text-faint, #aaa); height: 0; }
    `]);customElements.define("shenas-pipeline-overview",S);class C extends u{constructor(){super(),this.apiBase="/api",this.pipeName="",this._fields=[],this._instructions="",this._loading=!0,this._message=null,this._needsMfa=!1,this._oauthUrl=null,this._submitting=!1}willUpdate(e){e.has("pipeName")&&this._fetchFields()}async _fetchFields(){if(!this.pipeName)return;this._loading=!0,this._needsMfa=!1,this._oauthUrl=null;const e=await fetch(`${this.apiBase}/auth/${this.pipeName}/fields`);if(e.ok){const t=await e.json();this._fields=t.fields||[],this._instructions=t.instructions||""}this._loading=!1}async _submit(){var n,i;this._submitting=!0,this._message=null;const e={};if(this._needsMfa){const r=this.renderRoot.querySelector("#mfa-code");e.mfa_code=((n=r==null?void 0:r.value)==null?void 0:n.trim())||""}else if(this._oauthUrl)e.auth_complete="true";else for(const r of this._fields){const d=this.renderRoot.querySelector(`#field-${r.name}`),o=(i=d==null?void 0:d.value)==null?void 0:i.trim();o&&(e[r.name]=o)}const s=await(await fetch(`${this.apiBase}/auth/${this.pipeName}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({credentials:e})})).json();this._submitting=!1,s.ok?(this._message={type:"success",text:s.message},this._needsMfa=!1,this._oauthUrl=null):s.needs_mfa?(this._needsMfa=!0,this._message={type:"success",text:"MFA code required"}):s.oauth_url?(this._oauthUrl=s.oauth_url,this._message={type:"success",text:s.message}):(this._message={type:"error",text:s.error||"Authentication failed"},this._needsMfa=!1,this._oauthUrl=null)}render(){return this._loading?a`<p class="loading">Loading auth...</p>`:this._fields.length===0&&!this._instructions?a`<p class="empty">No authentication required for this plugin.</p>`:a`
      ${this._message?a`<div class="message ${this._message.type}">${this._message.text}</div>`:""}
      ${this._instructions?a`<div class="instructions">${this._instructions}</div>`:""}
      ${this._oauthUrl?this._renderOAuth():this._needsMfa?this._renderMfa():this._renderFields()}
    `}_renderFields(){return a`
      ${this._fields.map(e=>a`
        <div class="field">
          <label for="field-${e.name}">${e.prompt}</label>
          <input id="field-${e.name}"
            type="${e.hide?"password":"text"}"
            @keydown=${t=>{t.key==="Enter"&&this._submit()}}
          />
        </div>
      `)}
      <div class="actions">
        <button @click=${this._submit} ?disabled=${this._submitting}>
          ${this._submitting?"Authenticating...":"Authenticate"}
        </button>
      </div>
    `}_renderMfa(){return a`
      <div class="field">
        <label for="mfa-code">MFA Code</label>
        <input id="mfa-code" type="text" autocomplete="one-time-code"
          @keydown=${e=>{e.key==="Enter"&&this._submit()}}
        />
      </div>
      <div class="actions">
        <button @click=${this._submit} ?disabled=${this._submitting}>
          ${this._submitting?"Verifying...":"Verify"}
        </button>
      </div>
    `}_renderOAuth(){return a`
      <p>
        <a class="oauth-link" href="${this._oauthUrl}" target="_blank" rel="noopener">
          Open authorization page
        </a>
      </p>
      <p style="font-size:0.85rem;color:#666">
        After authorizing in your browser, click Complete below.
      </p>
      <div class="actions">
        <button @click=${this._submit} ?disabled=${this._submitting}>
          ${this._submitting?"Completing...":"Complete"}
        </button>
      </div>
    `}}l(C,"properties",{apiBase:{type:String,attribute:"api-base"},pipeName:{type:String,attribute:"pipe-name"},_fields:{state:!0},_instructions:{state:!0},_loading:{state:!0},_message:{state:!0},_needsMfa:{state:!0},_oauthUrl:{state:!0},_submitting:{state:!0}}),l(C,"styles",[f,_,b,c`
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
    `]);customElements.define("shenas-auth",C);class E extends u{constructor(){super(),this.apiBase="/api",this.kind="",this.name="",this._config=null,this._loading=!0,this._message=null,this._editing=null,this._editValue=""}willUpdate(e){(e.has("kind")||e.has("name"))&&this._fetchConfig()}async _fetchConfig(){if(!this.kind||!this.name)return;this._loading=!0;const e=await fetch(`${this.apiBase}/config?kind=${this.kind}&name=${this.name}`);if(e.ok){const t=await e.json();this._config=t.length>0?t[0]:null}else this._config=null;this._loading=!1}_startEdit(e,t){this._editing=e,this._editValue=t||""}_cancelEdit(){this._editing=null,this._editValue=""}async _saveEdit(e){const t=await fetch(`${this.apiBase}/config/${this.kind}/${this.name}`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({key:e,value:this._editValue})});if(t.ok)this._message={type:"success",text:`Updated ${e}`},this._editing=null,await this._fetchConfig();else{const s=await t.json();this._message={type:"error",text:s.detail||"Update failed"}}}render(){return this._loading?a`<p class="loading">Loading config...</p>`:!this._config||this._config.entries.length===0?a`<p class="empty">No configuration settings for this plugin.</p>`:a`
      ${this._message?a`<div class="message ${this._message.type}">${this._message.text}</div>`:""}
      ${this._config.entries.map(e=>this._renderEntry(e))}
    `}_renderEntry(e){const t=this._editing===e.key;return a`
      <div class="config-row">
        <div class="config-key">${e.key}</div>
        ${t?a`
            <div class="edit-row">
              <input class="config-input"
                .value=${this._editValue}
                @input=${s=>{this._editValue=s.target.value}}
                @keydown=${s=>{s.key==="Enter"&&this._saveEdit(e.key),s.key==="Escape"&&this._cancelEdit()}}
              />
              <button @click=${()=>this._saveEdit(e.key)}>Save</button>
              <button @click=${this._cancelEdit}>Cancel</button>
            </div>`:a`
            <div class="config-detail">
              <div class="config-value ${e.value?"":"empty"}"
                @click=${()=>this._startEdit(e.key,e.value)}
                style="cursor: pointer"
                title="Click to edit"
              >${e.value||"not set"}</div>
              ${e.description?a`<div class="config-desc">${e.description}</div>`:""}
            </div>`}
      </div>
    `}}l(E,"properties",{apiBase:{type:String,attribute:"api-base"},kind:{type:String},name:{type:String},_config:{state:!0},_loading:{state:!0},_message:{state:!0},_editing:{state:!0},_editValue:{state:!0}}),l(E,"styles",[f,_,b,c`
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
    `]);customElements.define("shenas-config",E);class z extends u{constructor(){super();l(this,"_router",new L(this,[{path:"/",render:()=>this._renderDynamicHome()},{path:"/settings",render:()=>this._renderSettings("overview")},{path:"/settings/:kind",render:({kind:t})=>this._renderSettings(t)},{path:"/settings/:kind/:name",render:({kind:t,name:s})=>this._renderPluginDetail(t,s)},{path:"/settings/:kind/:name/config",render:({kind:t,name:s})=>this._renderPluginDetail(t,s,"config")},{path:"/settings/:kind/:name/auth",render:({kind:t,name:s})=>this._renderPluginDetail(t,s,"auth")},{path:"/:tab",render:({tab:t})=>this._renderDynamicTab(t)}]));this.apiBase="/api",this._components=[],this._loading=!0,this._loadedScripts=new Set,this._elementCache=new Map,this._leftWidth=160,this._rightWidth=220,this._dbStatus=null,this._inspectTable=null,this._inspectRows=null,this._paletteOpen=!1,this._paletteCommands=[]}connectedCallback(){super.connectedCallback(),this._fetchData(),this.addEventListener("plugin-state-changed",()=>this._refreshComponents()),this.addEventListener("inspect-table",t=>this._inspect(t.detail.schema,t.detail.table)),this.addEventListener("navigate",t=>this._router.goto(t.detail.path)),this._keyHandler=t=>{(t.ctrlKey||t.metaKey)&&t.key==="p"&&(t.preventDefault(),this._togglePalette())},document.addEventListener("keydown",this._keyHandler)}disconnectedCallback(){super.disconnectedCallback(),document.removeEventListener("keydown",this._keyHandler)}async _togglePalette(){if(this._paletteOpen){this._paletteOpen=!1;return}await this._buildCommands(),this._paletteOpen=!0}async _buildCommands(){const t=[];for(const i of this._components)t.push({id:`nav:${i.name}`,category:"Navigate",label:i.display_name||i.name,path:`/${i.name}`});t.push({id:"nav:settings",category:"Navigate",label:"Settings",path:"/settings"}),t.push({id:"nav:dataflow",category:"Navigate",label:"Data Flow",path:"/settings/overview"}),t.push({id:"nav:settings:pipe",category:"Navigate",label:"Settings > Pipes",path:"/settings/pipe"}),t.push({id:"nav:settings:schema",category:"Navigate",label:"Settings > Schemas",path:"/settings/schema"}),t.push({id:"nav:settings:component",category:"Navigate",label:"Settings > Components",path:"/settings/component"}),t.push({id:"nav:settings:ui",category:"Navigate",label:"Settings > UI",path:"/settings/ui"});let s=[],n=[];try{[s,n]=await Promise.all([this._fetch("/plugins/pipe"),this._fetch("/plugins/schema")]),s=s||[],n=n||[]}catch{}for(const i of s){const r=i.display_name||i.name;t.push({id:`nav:pipe:${i.name}`,category:"Pipe",label:r,description:"Open details",path:`/settings/pipe/${i.name}`}),t.push({id:`sync:${i.name}`,category:"Pipe",label:`Sync ${r}`,description:"Run sync now",action:()=>this._syncPipe(i.name)})}for(const i of n)t.push({id:`nav:schema:${i.name}`,category:"Schema",label:i.display_name||i.name,description:"Open details",path:`/settings/schema/${i.name}`});this._paletteCommands=t}async _syncPipe(t){try{await fetch(`${this.apiBase}/sync/${t}`,{method:"POST"})}catch{}}_executePaletteCommand(t){const s=t.detail;s.path?this._router.goto(s.path):s.action&&s.action(),this._paletteOpen=!1}async _refreshComponents(){this._components=await this._fetch("/components")||[]}async _fetchData(){this._loading=!0;try{const[t,s]=await Promise.all([this._fetch("/components"),this._fetch("/db/status")]);this._components=t||[],this._dbStatus=s}catch(t){console.error("Failed to fetch data:",t)}this._loading=!1}async _fetch(t){const s=await fetch(`${this.apiBase}${t}`);return s.ok?s.json():null}_activeTab(){return(window.location.pathname.replace(/^\/+/,"")||"").split("/")[0]||(this._components.length>0?this._components[0].name:"settings")}_startDrag(t){return s=>{s.preventDefault();const n=s.clientX,i=t==="left"?this._leftWidth:this._rightWidth,r=s.target;r.classList.add("dragging");const d=p=>{const g=t==="left"?p.clientX-n:n-p.clientX,m=Math.max(80,Math.min(400,i+g));t==="left"?this._leftWidth=m:this._rightWidth=m},o=()=>{r.classList.remove("dragging"),window.removeEventListener("mousemove",d),window.removeEventListener("mouseup",o)};window.addEventListener("mousemove",d),window.addEventListener("mouseup",o)}}render(){if(this._loading)return a`<p class="loading">Loading...</p>`;const t=this._activeTab();return a`
      <div class="layout">
        <div class="panel-left" style="width: ${this._leftWidth}px">
          <div class="header">
            <img src="/static/images/shenas.png" alt="shenas" />
            <h1>shenas</h1>
          </div>
          <nav class="nav">
            ${this._components.map(s=>this._navItem(s.name,s.display_name||s.name,t))}
            ${this._navItem("settings","Settings",t)}
          </nav>
        </div>
        <div class="divider" @mousedown=${this._startDrag("left")}></div>
        <div class="panel-middle">
          ${this._router.outlet()}
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
    `}_navItem(t,s,n){return a`
      <a class="nav-item" href="/${t}" aria-selected=${n===t}>
        ${s}
      </a>
    `}_renderDynamicHome(){return this._components.length>0?this._renderDynamicTab(this._components[0].name):this._renderSettings("pipe")}_renderDynamicTab(t){const s=this._components.find(n=>n.name===t);if(!s)return a`<p class="empty">Unknown page: ${t}</p>`;if(!this._loadedScripts.has(s.js)){this._loadedScripts=new Set([...this._loadedScripts,s.js]);const n=document.createElement("script");n.type="module",n.src=s.js,document.head.appendChild(n)}return a`<div class="component-host">
      ${this._getOrCreateElement(s)}
    </div>`}_renderPluginDetail(t,s,n="details"){return a`<shenas-plugin-detail
      api-base="${this.apiBase}"
      kind="${t}"
      name="${s}"
      active-tab="${n}"
    ></shenas-plugin-detail>`}_renderSettings(t){return a`<shenas-settings
      api-base="${this.apiBase}"
      active-kind="${t||"overview"}"
      .onNavigate=${s=>{this._router.goto(`/settings/${s}`)}}
    ></shenas-settings>`}async _inspect(t,s){if(!/^[a-zA-Z_]\w*$/.test(t)||!/^[a-zA-Z_]\w*$/.test(s))return;const n=`${t}.${s}`;if(this._inspectTable===n){this._inspectTable=null,this._inspectRows=null;return}this._inspectTable=n,this._inspectRows=null;try{const i=await fetch(`${this.apiBase}/db/preview/${t}/${s}?limit=50`);this._inspectRows=i.ok?await i.json():[]}catch{this._inspectRows=[]}}_renderDbStats(){const t=this._dbStatus;return t?a`
      <div class="db-section">
        <div class="db-meta">
          ${t.size_mb!=null?a`<code>${t.size_mb} MB</code>`:a`<span>Not created</span>`}
        </div>
        ${(t.schemas||[]).map(s=>a`
            <h4>${s.name}</h4>
            ${s.tables.map(n=>a`
                <div class="db-table-row">
                  <span class="db-table-name">${n.name}</span>
                  <span class="db-table-count">${n.rows}</span>
                </div>
                ${n.earliest?a`<span class="db-date-range">${n.earliest} - ${n.latest}</span>`:""}
              `)}
          `)}
      </div>
    `:a`<p class="empty">No database</p>`}_renderInspect(){return a`
      <div class="inspect-header">
        <h4>${this._inspectTable}</h4>
        <button class="inspect-close" title="Close" @click=${()=>{this._inspectTable=null,this._inspectRows=null}}>x</button>
      </div>
      ${this._inspectRows?this._inspectRows.length===0?a`<p class="empty" style="font-size:0.75rem">No rows</p>`:a`
            <div style="overflow-x: auto;">
              <table class="inspect-table">
                <thead>
                  <tr>${Object.keys(this._inspectRows[0]).map(t=>a`<th>${t}</th>`)}</tr>
                </thead>
                <tbody>
                  ${this._inspectRows.map(t=>a`<tr>${Object.keys(t).map(s=>a`<td title="${t[s]??""}">${t[s]??""}</td>`)}</tr>`)}
                </tbody>
              </table>
            </div>
          `:a`<p class="loading" style="font-size:0.75rem">Loading...</p>`}
    `}_getOrCreateElement(t){if(!this._elementCache.has(t.name)){const s=document.createElement(t.tag);s.setAttribute("api-base",this.apiBase),this._elementCache.set(t.name,s)}return this._elementCache.get(t.name)}}l(z,"properties",{apiBase:{type:String,attribute:"api-base"},_components:{state:!0},_loading:{state:!0},_loadedScripts:{state:!0},_leftWidth:{state:!0},_rightWidth:{state:!0},_dbStatus:{state:!0},_inspectTable:{state:!0},_inspectRows:{state:!0},_paletteOpen:{state:!0},_paletteCommands:{state:!0}}),l(z,"styles",[j,b,c`
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
        overflow-y: auto;
        padding: 1.5rem 2rem;
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
        margin-top: 1rem;
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
    `]);customElements.define("shenas-app",z);const y=[{id:"pipe",label:"Pipes"},{id:"schema",label:"Schemas"},{id:"component",label:"Components"},{id:"ui",label:"UI"},{id:"theme",label:"Themes"}];class T extends u{constructor(){super(),this.apiBase="/api",this.activeKind="pipe",this.onNavigate=null,this._plugins={},this._loading=!0,this._actionMessage=null,this._installing=!1}connectedCallback(){super.connectedCallback(),this._fetchAll()}async _fetchAll(){this._loading=!0;const e={};await Promise.all(y.map(async({id:t})=>{const s=await fetch(`${this.apiBase}/plugins/${t}`);e[t]=s.ok?await s.json():[]})),this._plugins=e,this._loading=!1}async _togglePlugin(e,t,s){const n=s?"disable":"enable",r=await(await fetch(`${this.apiBase}/plugins/${e}/${t}/${n}`,{method:"POST"})).json();r.ok||(this._actionMessage={type:"error",text:r.message||`${n} failed`}),await this._fetchAll()}async _install(e){var d,o;const t=this.shadowRoot.querySelector(`#install-${e}`),s=(d=t==null?void 0:t.value)==null?void 0:d.trim();if(!s)return;this._actionMessage=null;const r=(o=(await(await fetch(`${this.apiBase}/plugins/${e}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({names:[s],skip_verify:!0})})).json()).results)==null?void 0:o[0];r!=null&&r.ok?(this._actionMessage={type:"success",text:r.message},this._installing=!1,await this._fetchAll()):this._actionMessage={type:"error",text:(r==null?void 0:r.message)||"Install failed"}}render(){return this._loading?a`<p class="loading">Loading plugins...</p>`:a`
      ${this._actionMessage?a`<div class="message ${this._actionMessage.type}">
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
            ${y.map(({id:e,label:t})=>a`
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
        <div class="content">
          ${this.activeKind==="overview"?a`<shenas-pipeline-overview api-base="${this.apiBase}"></shenas-pipeline-overview>`:this._renderKind(this.activeKind)}
        </div>
      </div>
    `}_renderKind(e){var n;const t=this._plugins[e]||[],s=((n=y.find(i=>i.id===e))==null?void 0:n.label)||e;return a`
      <h3>${s}</h3>
      <shenas-data-list
        .columns=${[{label:"Name",render:i=>a`<a href="/settings/${e}/${i.name}">${i.display_name||i.name}</a>`},{key:"version",label:"Version",class:"mono"},{label:"Added",class:"mono",render:i=>i.added_at?i.added_at.slice(0,10):""},{label:"Status",render:i=>a`<status-toggle ?enabled=${i.enabled!==!1} toggleable @toggle=${()=>this._togglePlugin(e,i.name,i.enabled!==!1)}></status-toggle>`}]}
        .rows=${t}
        .rowClass=${i=>i.enabled===!1?"disabled-row":""}
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
              @keydown=${i=>i.key==="Enter"&&this._install(e)}
              style="width: 100%; padding: 0.4rem 0.6rem; border: 1px solid #ddd; border-radius: 4px; font-size: 0.85rem; box-sizing: border-box;"
            />
          </shenas-form-panel>`:""}
    `}}l(T,"properties",{apiBase:{type:String,attribute:"api-base"},activeKind:{type:String,attribute:"active-kind"},onNavigate:{type:Function},_plugins:{state:!0},_loading:{state:!0},_actionMessage:{state:!0},_installing:{state:!0}}),l(T,"styles",[f,j,_,b,c`
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
    `]);customElements.define("shenas-settings",T);class B extends u{constructor(){super(),this.apiBase="/api",this.kind="",this.name="",this.activeTab="details",this._info=null,this._loading=!0,this._message=null,this._hasConfig=!1,this._hasAuth=!1,this._tables=[],this._syncing=!1}willUpdate(e){(e.has("kind")||e.has("name"))&&this._fetchInfo()}async _fetchInfo(){var i;if(!this.kind||!this.name)return;this._loading=!0,this._message=null;const e=await fetch(`${this.apiBase}/plugins/${this.kind}/${this.name}/info`);this._info=e.ok?await e.json():null;const[t,s,n]=await Promise.all([fetch(`${this.apiBase}/config?kind=${this.kind}&name=${this.name}`),this.kind==="pipe"?fetch(`${this.apiBase}/auth/${this.name}/fields`):Promise.resolve(null),this.kind==="pipe"?fetch(`${this.apiBase}/db/status`):Promise.resolve(null)]);if(t.ok){const r=await t.json();this._hasConfig=r.length>0&&r[0].entries.length>0}if(s!=null&&s.ok){const r=await s.json();this._hasAuth=((i=r.fields)==null?void 0:i.length)>0||!!r.instructions}if(n!=null&&n.ok){const d=((await n.json()).schemas||[]).find(o=>o.name===this.name);this._tables=d?d.tables.filter(o=>!o.name.startsWith("_dlt_")):[]}this._loading=!1}async _toggle(){var n;const e=((n=this._info)==null?void 0:n.enabled)!==!1?"disable":"enable",s=await(await fetch(`${this.apiBase}/plugins/${this.kind}/${this.name}/${e}`,{method:"POST"})).json();this._message={type:s.ok?"success":"error",text:s.message||`${e} failed`},await this._fetchInfo(),this.dispatchEvent(new CustomEvent("plugin-state-changed",{bubbles:!0,composed:!0}))}async _sync(){this._syncing=!0,this._message=null;try{const e=await fetch(`${this.apiBase}/sync/${this.name}`,{method:"POST"});if(!e.ok){const o=await e.json().catch(()=>({}));this._message={type:"error",text:o.detail||`Sync failed (${e.status})`},this._syncing=!1;return}const t=e.body.getReader(),s=new TextDecoder;let n="",i="",r=!1;for(;;){const{done:o,value:p}=await t.read();if(o)break;const g=s.decode(p,{stream:!0});for(const m of g.split(`
`))m.startsWith("event: ")&&(n=m.slice(7).trim()),m.startsWith("data: ")&&(i=m.slice(6));n==="error"&&(r=!0)}let d="Sync complete";try{d=JSON.parse(i).message||d}catch{}this._message={type:r?"error":"success",text:d},r||await this._fetchInfo()}catch(e){this._message={type:"error",text:`Sync failed: ${e.message}`}}this._syncing=!1}async _remove(){const t=await(await fetch(`${this.apiBase}/plugins/${this.kind}/${this.name}`,{method:"DELETE"})).json();t.ok?(window.history.pushState({},"",`/settings/${this.kind}`),window.dispatchEvent(new PopStateEvent("popstate"))):this._message={type:"error",text:t.message||"Remove failed"}}render(){if(this._loading)return a`<p class="loading">Loading...</p>`;if(!this._info)return a`<p>Plugin not found.</p>`;const e=this._info,t=e.enabled!==!1,s=`/settings/${this.kind}/${this.name}`;return a`
      <a class="back" href="/settings/${this.kind}">&larr; Back to ${this.kind}s</a>

      <div class="title-row">
        <h2>${e.display_name||e.name} <span class="kind-badge">${e.kind}</span></h2>
        <div class="title-actions">
          ${this.kind==="pipe"&&t?a`<button @click=${this._sync} ?disabled=${this._syncing}>${this._syncing?"Syncing...":"Sync"}</button>`:""}
          <button class="danger" @click=${this._remove}>Remove</button>
        </div>
      </div>

      ${this._hasConfig||this._hasAuth?a`
          <div class="tabs">
            <a class="tab" href="${s}" aria-selected=${this.activeTab==="details"}>Details</a>
            ${this._hasConfig?a`<a class="tab" href="${s}/config" aria-selected=${this.activeTab==="config"}>Config</a>`:""}
            ${this._hasAuth?a`<a class="tab" href="${s}/auth" aria-selected=${this.activeTab==="auth"}>Auth</a>`:""}
          </div>`:""}

      ${this.activeTab==="config"&&this._hasConfig?a`<shenas-config api-base="${this.apiBase}" kind="${this.kind}" name="${this.name}"></shenas-config>`:this.activeTab==="auth"&&this._hasAuth?a`<shenas-auth api-base="${this.apiBase}" pipe-name="${this.name}"></shenas-auth>`:this._renderDetails(e,t)}

      ${this._message?a`<div class="message ${this._message.type}">
            ${this._message.text}
          </div>`:""}
    `}_renderDetails(e,t){return a`
      ${e.description?a`<div class="description">${e.description}</div>`:""}

      <div class="state-table">
        <div class="state-row">
          <span class="state-label">Status</span>
          <span class="state-value">
            <status-toggle ?enabled=${t} toggleable @toggle=${this._toggle}></status-toggle>
          </span>
        </div>
        ${this._stateRow("Last synced",e.synced_at)}
        ${this._stateRow("Added",e.added_at)}
        ${this._stateRow("Updated",e.updated_at)}
        ${this._stateRow("Status changed",e.status_changed_at)}
      </div>

      ${this.kind==="pipe"?a`
          <h4 class="section-title">Resources</h4>
          <shenas-data-list
            .columns=${[{key:"name",label:"Table",class:"mono"},{key:"rows",label:"Rows",class:"muted"},{label:"Range",class:"muted",render:s=>s.earliest?`${s.earliest} - ${s.latest}`:""}]}
            .rows=${this._tables}
            empty-text="No tables synced yet"
          ></shenas-data-list>`:""}

      ${this.kind==="pipe"?a`
          <h4 class="section-title">Transforms</h4>
          <shenas-transforms api-base="${this.apiBase}" source="${this.name}"></shenas-transforms>`:""}

    `}_stateRow(e,t){return t?a`
      <div class="state-row">
        <span class="state-label">${e}</span>
        <span class="state-value">${t.slice(0,19)}</span>
      </div>
    `:""}}l(B,"properties",{apiBase:{type:String,attribute:"api-base"},kind:{type:String},name:{type:String},activeTab:{type:String,attribute:"active-tab"},_info:{state:!0},_loading:{state:!0},_message:{state:!0},_hasConfig:{state:!0},_hasAuth:{state:!0},_tables:{state:!0},_syncing:{state:!0}}),l(B,"styles",[f,j,_,M,b,c`
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
    `]);customElements.define("shenas-plugin-detail",B);const N="background:none;border:none;cursor:pointer;color:#bbb;font-size:0.7rem;padding:0 2px";class R extends u{constructor(){super(),this.apiBase="/api",this.source="",this._transforms=[],this._loading=!0,this._editing=null,this._editSql="",this._message=null,this._previewRows=null,this._creating=!1,this._newForm=this._emptyForm(),this._dbTables={},this._schemaTables={}}_emptyForm(){return{source_duckdb_table:"",target_duckdb_table:"",description:"",sql:""}}connectedCallback(){super.connectedCallback(),this._fetchAll()}async _fetchAll(){this._loading=!0;const e=this.source?`?source=${this.source}`:"",t=await fetch(`${this.apiBase}/transforms${e}`);this._transforms=t.ok?await t.json():[],this._loading=!1}_inspectTable(e,t){this.dispatchEvent(new CustomEvent("inspect-table",{bubbles:!0,composed:!0,detail:{schema:e,table:t}}))}async _toggle(e){const t=e.enabled?"disable":"enable";await fetch(`${this.apiBase}/transforms/${e.id}/${t}`,{method:"POST"}),await this._fetchAll()}async _delete(e){const s=await(await fetch(`${this.apiBase}/transforms/${e.id}`,{method:"DELETE"})).json();s.ok?(this._message={type:"success",text:s.message},await this._fetchAll()):this._message={type:"error",text:s.detail||s.message||"Delete failed"}}_startEdit(e){this._editing=e.id,this._editSql=e.sql,this._previewRows=null}_cancelEdit(){this._editing=null,this._editSql="",this._previewRows=null}async _saveEdit(){const e=await fetch(`${this.apiBase}/transforms/${this._editing}`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({sql:this._editSql})});if(e.ok)this._message={type:"success",text:"Transform updated"},this._editing=null,await this._fetchAll();else{const t=await e.json();this._message={type:"error",text:t.detail||"Update failed"}}}async _startCreate(){this._creating=!0,this._newForm=this._emptyForm(),this._editing=null,this._previewRows=null;const[e,t]=await Promise.all([fetch(`${this.apiBase}/db/tables`),fetch(`${this.apiBase}/db/schema-tables`)]);this._dbTables=e.ok?await e.json():{},this._schemaTables=t.ok?await t.json():{}}_cancelCreate(){this._creating=!1,this._newForm=this._emptyForm()}_updateNewForm(e,t){this._newForm={...this._newForm,[e]:t}}async _saveCreate(){const e=this._newForm;if(!e.source_duckdb_table||!e.target_duckdb_table||!e.sql){this._message={type:"error",text:"Fill in all required fields"};return}const t=await fetch(`${this.apiBase}/transforms`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({source_duckdb_schema:this.source,source_duckdb_table:e.source_duckdb_table,target_duckdb_schema:"metrics",target_duckdb_table:e.target_duckdb_table,source_plugin:this.source,description:e.description,sql:e.sql})});if(t.ok)this._message={type:"success",text:"Transform created"},this._creating=!1,this._newForm=this._emptyForm(),await this._fetchAll();else{const s=await t.json();this._message={type:"error",text:s.detail||"Create failed"}}}async _preview(){const e=await fetch(`${this.apiBase}/transforms/${this._editing}/test?limit=5`,{method:"POST"});if(e.ok)this._previewRows=await e.json();else{const t=await e.json();this._message={type:"error",text:t.detail||"Preview failed"}}}render(){return this._loading?a`<p class="loading">Loading transforms...</p>`:a`
      ${this._message?a`<div class="message ${this._message.type}">
            ${this._message.text}
          </div>`:""}
      ${this._editing?this._renderEditor():""}
      ${this._creating?this._renderCreateForm():""}
      <shenas-data-list
        ?show-add=${!this._creating&&!this._editing}
        @add=${this._startCreate}
        .columns=${[{key:"id",label:"ID",class:"muted"},{label:"Source",class:"mono",render:e=>a`${e.source_duckdb_schema}.${e.source_duckdb_table} <button style=${N} title="Inspect table" @click=${()=>this._inspectTable(e.source_duckdb_schema,e.source_duckdb_table)}>&#9655;</button>`},{label:"Target",class:"mono",render:e=>a`${e.target_duckdb_schema}.${e.target_duckdb_table} <button style=${N} title="Inspect table" @click=${()=>this._inspectTable(e.target_duckdb_schema,e.target_duckdb_table)}>&#9655;</button>`},{label:"Description",render:e=>a`${e.description||""}${e.is_default?a`<span style="font-size:0.75rem;color:#888;background:#f0f0f0;padding:1px 5px;border-radius:3px;margin-left:4px">default</span>`:""}`},{label:"Status",render:e=>a`<status-toggle ?enabled=${e.enabled} toggleable @toggle=${()=>this._toggle(e)}></status-toggle>`}]}
        .rows=${this._transforms}
        .rowClass=${e=>e.enabled?"":"disabled-row"}
        .actions=${e=>a`
          ${e.is_default?a`<button @click=${()=>this._startEdit(e)}>View</button>`:a`<button @click=${()=>this._startEdit(e)}>Edit</button>`}
          ${e.is_default?"":a`<button class="danger" @click=${()=>this._delete(e)}>Delete</button>`}
        `}
        empty-text="No transforms"
      ></shenas-data-list>
    `}_renderCreateForm(){const e=this._newForm,t=this.source,s=this._dbTables[t]||[],n=Object.values(this._schemaTables||{}).flat();return a`
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
              @change=${i=>this._updateNewForm("source_duckdb_table",i.target.value)}
            >
              <option value="">-- select --</option>
              ${s.map(i=>a`<option value=${i} ?selected=${e.source_duckdb_table===i}>${i}</option>`)}
            </select>
          </label>
          <label>
            Schema table
            <select
              .value=${e.target_duckdb_table}
              @change=${i=>this._updateNewForm("target_duckdb_table",i.target.value)}
            >
              <option value="">-- select --</option>
              ${n.map(i=>a`<option value=${i} ?selected=${e.target_duckdb_table===i}>${i}</option>`)}
            </select>
          </label>
          <label class="form-full">
            Description
            <input
              .value=${e.description}
              @input=${i=>this._updateNewForm("description",i.target.value)}
            />
          </label>
        </div>
        <textarea
          .value=${e.sql}
          @input=${i=>this._updateNewForm("sql",i.target.value)}
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
    `}}l(R,"properties",{apiBase:{type:String,attribute:"api-base"},source:{type:String},_transforms:{state:!0},_loading:{state:!0},_editing:{state:!0},_editSql:{state:!0},_message:{state:!0},_previewRows:{state:!0},_creating:{state:!0},_newForm:{state:!0},_dbTables:{state:!0},_schemaTables:{state:!0}}),l(R,"styles",[P,f,_,b,c`
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
    `]);customElements.define("shenas-transforms",R);
