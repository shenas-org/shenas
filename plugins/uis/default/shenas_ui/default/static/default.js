var Q=Object.defineProperty;var Y=(l,e,t)=>e in l?Q(l,e,{enumerable:!0,configurable:!0,writable:!0,value:t}):l[e]=t;var d=(l,e,t)=>Y(l,typeof e!="symbol"?e+"":e,t);import{LitElement as g,css as m,html as n}from"lit";import V,{dagre as ee}from"cytoscape";import{Router as te}from"@lit-labs/router";class D extends g{constructor(){super(),this.open=!1,this.commands=[],this._query="",this._filtered=[],this._selectedIndex=0}updated(e){e.has("open")&&this.open&&(this._query="",this._selectedIndex=0,this._filter(),requestAnimationFrame(()=>{const t=this.renderRoot.querySelector("input");t&&t.focus()})),e.has("commands")&&this._filter()}_filter(){const e=this._query.toLowerCase();e?this._filtered=this.commands.filter(t=>t.label.toLowerCase().includes(e)||t.category.toLowerCase().includes(e)||(t.description||"").toLowerCase().includes(e)):this._filtered=this.commands,this._selectedIndex>=this._filtered.length&&(this._selectedIndex=Math.max(0,this._filtered.length-1))}_onInput(e){this._query=e.target.value,this._selectedIndex=0,this._filter()}_onKeydown(e){if(e.key==="ArrowDown")e.preventDefault(),this._filtered.length>0&&(this._selectedIndex=Math.min(this._selectedIndex+1,this._filtered.length-1)),this._scrollToSelected();else if(e.key==="ArrowUp")e.preventDefault(),this._selectedIndex=Math.max(this._selectedIndex-1,0),this._scrollToSelected();else if(e.key==="Enter"){e.preventDefault();const t=this._filtered[this._selectedIndex];t&&this._execute(t)}else e.key==="Escape"&&this._close()}_scrollToSelected(){requestAnimationFrame(()=>{const e=this.renderRoot.querySelector(".item.selected");e&&e.scrollIntoView({block:"nearest"})})}_execute(e){this.dispatchEvent(new CustomEvent("execute",{detail:e,bubbles:!0,composed:!0}))}_close(){this.dispatchEvent(new CustomEvent("close",{bubbles:!0,composed:!0}))}render(){return this.open?n`
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
          ${this._filtered.length===0?n`<div class="empty">No matching commands</div>`:this._filtered.map((e,t)=>n`
                  <div
                    class="item ${t===this._selectedIndex?"selected":""}"
                    @click=${()=>this._execute(e)}
                    @mouseenter=${()=>{this._selectedIndex=t}}
                  >
                    <span class="item-category">${e.category}</span>
                    <span class="item-label">${e.label}</span>
                    ${e.description?n`<span class="item-desc">${e.description}</span>`:""}
                  </div>
                `)}
        </div>
      </div>
    `:n``}}d(D,"properties",{open:{type:Boolean,reflect:!0},commands:{type:Array},_query:{state:!0},_filtered:{state:!0},_selectedIndex:{state:!0}}),d(D,"styles",m`
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
  `);customElements.define("shenas-command-palette",D);const Z=m`
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
`,se=m`
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
`,E=m`
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
`,B=m`
  .field {
    margin-bottom: 0.8rem;
  }
  .field label {
    display: block;
    font-size: 0.8rem;
    color: var(--shenas-text-secondary, #666);
    margin-bottom: 0.2rem;
  }
  .field input,
  .field select {
    width: 100%;
    padding: 0.4rem 0.6rem;
    border: 1px solid var(--shenas-border-input, #ddd);
    border-radius: 4px;
    font-size: 0.85rem;
    box-sizing: border-box;
    background: var(--shenas-bg, #fff);
    color: var(--shenas-text, #222);
  }
  .actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
    margin-top: 1rem;
  }
`,C=m`
  .loading {
    color: var(--shenas-text-muted, #888);
    font-style: italic;
  }
  .empty {
    color: var(--shenas-text-muted, #888);
    padding: 0.5rem 0;
  }
`,H=m`
  a {
    color: var(--shenas-primary, #0066cc);
    text-decoration: none;
  }
  a:hover {
    text-decoration: underline;
  }
`;class N extends g{constructor(){super(),this.loading=!1,this.empty=!1,this.loadingText="Loading...",this.emptyText="No data",this.displayName=""}updated(e){e.has("displayName")&&this.displayName&&this.dispatchEvent(new CustomEvent("page-title",{bubbles:!0,composed:!0,detail:{title:this.displayName}}))}render(){return this.loading?n`<p class="loading">${this.loadingText}</p>`:this.empty?n`<p class="empty">${this.emptyText}</p>`:n`<slot></slot>`}}d(N,"properties",{loading:{type:Boolean,reflect:!0},empty:{type:Boolean,reflect:!0},loadingText:{type:String,attribute:"loading-text"},emptyText:{type:String,attribute:"empty-text"},displayName:{type:String,attribute:"display-name"}}),d(N,"styles",[C,m`
      :host([loading]), :host([empty]) {
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 100vh;
      }
      .loading, .empty {
        color: var(--shenas-text-muted, #888);
      }
    `]);customElements.define("shenas-page",N);class O extends g{constructor(){super(),this.enabled=!1,this.toggleable=!1}updated(){this.title=this.enabled?"Enabled":"Disabled"}render(){return n`<div class="track" @click=${this._onClick}><div class="knob"></div></div>`}_onClick(){this.toggleable&&this.dispatchEvent(new CustomEvent("toggle",{bubbles:!0,composed:!0}))}}d(O,"properties",{enabled:{type:Boolean,reflect:!0},toggleable:{type:Boolean,reflect:!0}}),d(O,"styles",m`
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
  `);customElements.define("status-toggle",O);class I extends g{constructor(){super(),this.columns=[],this.rows=[],this.rowClass=null,this.actions=null,this.emptyText="No items",this.showAdd=!1}_onAdd(){this.dispatchEvent(new CustomEvent("add",{bubbles:!0,composed:!0}))}render(){const e=typeof this.actions=="function",t=this.showAdd?n`<div class="add-row"><button class="add-btn" title="Add" @click=${this._onAdd}>+</button></div>`:"";return!this.rows||this.rows.length===0?n`<p class="empty">${this.emptyText}</p>${t}`:n`
      <table>
        <thead>
          <tr>
            ${this.columns.map(s=>n`<th>${s.label}</th>`)}
            ${e?n`<th></th>`:""}
          </tr>
        </thead>
        <tbody>
          ${this.rows.map(s=>n`
              <tr class="${this.rowClass?this.rowClass(s):""}">
                ${this.columns.map(a=>n`
                  <td class="${a.class||""}">
                    ${a.render?a.render(s):s[a.key]}
                  </td>
                `)}
                ${e?n`<td class="actions-cell">${this.actions(s)}</td>`:""}
              </tr>
            `)}
        </tbody>
      </table>
      ${t}
    `}}d(I,"properties",{columns:{type:Array},rows:{type:Array},rowClass:{type:Object},actions:{type:Object},emptyText:{type:String,attribute:"empty-text"},showAdd:{type:Boolean,attribute:"show-add"}}),d(I,"styles",[Z,x,C,m`
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
    `]);customElements.define("shenas-data-list",I);class P extends g{constructor(){super(),this.title="",this.submitLabel="Save"}render(){return n`
      ${this.title?n`<h3>${this.title}</h3>`:""}
      <slot></slot>
      <div class="actions">
        <button @click=${this._onSubmit}>${this.submitLabel}</button>
        <button @click=${this._onCancel}>Cancel</button>
      </div>
    `}_onSubmit(){this.dispatchEvent(new CustomEvent("submit",{bubbles:!0,composed:!0}))}_onCancel(){this.dispatchEvent(new CustomEvent("cancel",{bubbles:!0,composed:!0}))}}d(P,"properties",{title:{type:String},submitLabel:{type:String,attribute:"submit-label"}}),d(P,"styles",[x,m`
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
    `]);customElements.define("shenas-form-panel",P);async function h(l,e,t={}){const{method:s="GET",json:a,...i}=t,o={method:s,...i};a!==void 0&&(o.headers={"Content-Type":"application/json",...i.headers},o.body=JSON.stringify(a));const r=await fetch(`${l}${e}`,o);return r.ok?r.json():(console.warn(`apiFetch ${s} ${e} failed: ${r.status}`),null)}async function $(l,e,t={}){const{method:s="GET",json:a,...i}=t,o={method:s,...i};a!==void 0&&(o.headers={"Content-Type":"application/json",...i.headers},o.body=JSON.stringify(a));const r=await fetch(`${l}${e}`,o),p=await r.json().catch(()=>null);return{ok:r.ok,status:r.status,data:p}}function z(l){return l?n`<div class="message ${l.type}">${l.text}</div>`:""}function X(l,e,t){l.dispatchEvent(new CustomEvent("register-command",{bubbles:!0,composed:!0,detail:{componentId:e,commands:t}}))}let G=!1;class A extends g{constructor(){super(),this.apiBase="/api",this._loading=!0,this._empty=!1,this._cy=null,this._elements=null,this._resizeObserver=null}connectedCallback(){super.connectedCallback(),this._fetchData()}disconnectedCallback(){super.disconnectedCallback(),this._cy&&(this._cy.destroy(),this._cy=null),this._resizeObserver&&(this._resizeObserver.disconnect(),this._resizeObserver=null)}async _fetchData(){this._loading=!0;try{const[e,t,s,a,i,o]=await Promise.all([h(this.apiBase,"/plugins/pipe"),h(this.apiBase,"/plugins/schema"),h(this.apiBase,"/transforms"),h(this.apiBase,"/db/schema-plugins"),h(this.apiBase,"/plugins/component"),h(this.apiBase,"/dependencies")]);this._buildElements(e||[],t||[],s||[],a||{},i||[],o||{})}catch(e){console.error("Failed to fetch overview data:",e)}this._loading=!1}_buildElements(e,t,s,a,i,o){const r=[],p=new Set,f={};for(const[c,u]of Object.entries(a))for(const T of u)f[T]=c;for(const c of e){const u=`pipe:${c.name}`;p.add(u),r.push({data:{id:u,label:c.display_name||c.name,kind:"pipe",enabled:c.enabled!==!1?"yes":"no"}})}for(const c of t){const u=`schema:${c.name}`;p.add(u),r.push({data:{id:u,label:c.display_name||c.name,kind:"schema",enabled:c.enabled!==!1?"yes":"no"}})}for(const c of i){const u=`component:${c.name}`;p.add(u),r.push({data:{id:u,label:c.display_name||c.name,kind:"component",enabled:c.enabled!==!1?"yes":"no"}})}for(const c of s){const u=`pipe:${c.source_plugin}`,T=f[c.target_duckdb_table],S=T?`schema:${T}`:null;if(!S||!p.has(u)||!p.has(S))continue;const v=c.description||`${c.source_duckdb_table} -> ${c.target_duckdb_table}`,k=v.length>30?v.slice(0,28)+"...":v;r.push({data:{id:`transform:${c.id}`,source:u,target:S,label:k,enabled:c.enabled?"yes":"no",sourcePlugin:c.source_plugin,edgeType:"transform"}})}const w=new Set;for(const c of r)c.data.edgeType==="transform"&&w.add(`${c.data.source}:${c.data.target}`);const _=new Set;for(const[c,u]of Object.entries(o))for(const T of u){const S=c.split(":")[0];let v,k;if(S==="component"?(v=T,k=c):(v=c,k=T),!p.has(v)||!p.has(k)||S==="pipe"&&w.has(`${v}:${k}`))continue;const R=`dep:${v}:${k}`;_.has(R)||(_.add(R),r.push({data:{id:R,source:v,target:k,edgeType:"dependency"}}))}this._elements=r,this._empty=r.filter(c=>c.data.source).length===0}_initCytoscape(){const e=this.renderRoot.querySelector("#cy");!e||!this._elements||(G||(V.use(ee),G=!0),this._cy&&this._cy.destroy(),this._cy=V({container:e,elements:this._elements,style:[{selector:"node",style:{label:"data(label)","text-valign":"center","text-halign":"center","font-size":12,color:"#fff","text-wrap":"wrap","text-max-width":100,width:120,height:40,shape:"round-rectangle"}},{selector:'node[kind="pipe"]',style:{"background-color":"#4a90d9",cursor:"pointer"}},{selector:'node[kind="schema"]',style:{"background-color":"#66bb6a",cursor:"pointer"}},{selector:'node[kind="component"]',style:{"background-color":"#ffa726",cursor:"pointer"}},{selector:'node[enabled="no"]',style:{opacity:.4,"border-width":2,"border-color":"#999","border-style":"dashed"}},{selector:"edge",style:{"curve-style":"bezier","target-arrow-shape":"triangle","target-arrow-color":"#999","line-color":"#999",cursor:"pointer",width:2,label:"data(label)","font-size":9,color:"#888","text-rotation":"autorotate","text-margin-y":-8}},{selector:'edge[enabled="yes"]',style:{"line-style":"solid"}},{selector:'edge[enabled="no"]',style:{"line-style":"dashed","line-color":"#ccc","target-arrow-color":"#ccc",opacity:.5}},{selector:'edge[edgeType="dependency"]',style:{"line-style":"dotted","line-color":"#bbb","target-arrow-color":"#bbb",width:1.5,label:""}}],layout:{name:"dagre",rankDir:"LR",nodeSep:60,rankSep:150,padding:30},userZoomingEnabled:!0,userPanningEnabled:!0,boxSelectionEnabled:!1}),this._cy.on("tap","node",t=>{const s=t.target.data(),a=s.id.substring(s.id.indexOf(":")+1);let i;if(s.kind==="pipe")i=`/settings/pipe/${a}`;else if(s.kind==="schema")i=`/settings/schema/${a}`;else if(s.kind==="component")i=`/settings/component/${a}`;else return;this.dispatchEvent(new CustomEvent("navigate",{bubbles:!0,composed:!0,detail:{path:i}}))}),this._cy.on("tap","edge",t=>{const s=t.target.data("sourcePlugin");s&&this.dispatchEvent(new CustomEvent("navigate",{bubbles:!0,composed:!0,detail:{path:`/settings/pipe/${s}`}}))}),this._resizeObserver&&this._resizeObserver.disconnect(),this._resizeObserver=new ResizeObserver(()=>{this._cy&&(this._cy.resize(),this._cy.fit(void 0,30))}),this._resizeObserver.observe(e))}firstUpdated(){!this._loading&&this._elements&&this._initCytoscape()}updated(e){e.has("_loading")&&!this._loading&&this._elements&&requestAnimationFrame(()=>this._initCytoscape())}render(){return n`
      <shenas-page ?loading=${this._loading} loading-text="Loading overview...">
        <div id="cy"></div>
        <div class="legend">
          <span class="legend-item"><span class="legend-dot pipe"></span> Pipe</span>
          <span class="legend-item"><span class="legend-dot schema"></span> Schema</span>
          <span class="legend-item"><span class="legend-dot component"></span> Component</span>
          <span class="legend-item"><span class="legend-line enabled"></span> Transform</span>
          <span class="legend-item"><span class="legend-line disabled"></span> Disabled</span>
          <span class="legend-item"><span class="legend-line" style="border-top:2px dotted var(--shenas-text-faint, #aaa);height:0;background:none"></span> Dependency</span>
        </div>
        ${this._empty?n`<p class="empty">No connections found. Add transforms in pipe settings.</p>`:""}
      </shenas-page>
    `}}d(A,"properties",{apiBase:{type:String,attribute:"api-base"},_loading:{state:!0},_empty:{state:!0}}),d(A,"styles",[C,m`
      :host {
        display: block;
      }
      #cy {
        width: 100%;
        height: calc(100vh - 10rem);
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
    `]);customElements.define("shenas-pipeline-overview",A);class L extends g{constructor(){super(),this.apiBase="/api",this.pipeName="",this._fields=[],this._instructions="",this._loading=!0,this._message=null,this._needsMfa=!1,this._oauthUrl=null,this._submitting=!1,this._stored=[]}willUpdate(e){e.has("pipeName")&&this._fetchFields()}async _fetchFields(){if(!this.pipeName)return;this._loading=!0,this._needsMfa=!1,this._oauthUrl=null;const e=await h(this.apiBase,`/auth/${this.pipeName}/fields`);e&&(this._fields=e.fields||[],this._instructions=e.instructions||"",this._stored=e.stored||[]),this._loading=!1}async _submit(){var s,a;this._submitting=!0,this._message=null;const e={};if(this._needsMfa){const i=this.renderRoot.querySelector("#mfa-code");e.mfa_code=((s=i==null?void 0:i.value)==null?void 0:s.trim())||""}else if(this._oauthUrl)e.auth_complete="true";else for(const i of this._fields){const o=this.renderRoot.querySelector(`#field-${i.name}`),r=(a=o==null?void 0:o.value)==null?void 0:a.trim();r&&(e[i.name]=r)}const{data:t}=await $(this.apiBase,`/auth/${this.pipeName}`,{method:"POST",json:{credentials:e}});this._submitting=!1,t.ok?(this._message={type:"success",text:t.message},this._needsMfa=!1,this._oauthUrl=null,this._fetchFields()):t.needs_mfa?(this._needsMfa=!0,this._message={type:"success",text:"MFA code required"}):t.oauth_url?(this._oauthUrl=t.oauth_url,this._message={type:"success",text:t.message}):(this._message={type:"error",text:t.error||"Authentication failed"},this._needsMfa=!1,this._oauthUrl=null)}render(){const e=this._fields.length===0&&!this._instructions;return n`
      <shenas-page ?loading=${this._loading} ?empty=${e}
        loading-text="Loading auth..." empty-text="No authentication required for this plugin.">
        ${z(this._message)}
        ${this._stored.length>0?n`<div class="stored-creds">
              ${this._stored.map(t=>n`<div class="stored-item">&#10003; ${t} configured</div>`)}
            </div>`:""}
        ${this._instructions?n`<div class="instructions">${this._instructions}</div>`:""}
        ${this._oauthUrl?this._renderOAuth():this._needsMfa?this._renderMfa():this._renderFields()}
      </shenas-page>
    `}_renderFields(){return n`
      ${this._fields.map(e=>n`
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
    `}_renderMfa(){return n`
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
    `}_renderOAuth(){return n`
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
    `}}d(L,"properties",{apiBase:{type:String,attribute:"api-base"},pipeName:{type:String,attribute:"pipe-name"},_fields:{state:!0},_instructions:{state:!0},_loading:{state:!0},_message:{state:!0},_needsMfa:{state:!0},_oauthUrl:{state:!0},_submitting:{state:!0},_stored:{state:!0}}),d(L,"styles",[x,B,E,m`
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
      .oauth-link {
        display: inline-block;
        margin-top: 0.5rem;
        color: var(--shenas-primary, #0066cc);
      }
      .stored-creds {
        margin-bottom: 1rem;
        padding: 0.6rem 0.8rem;
        background: var(--shenas-success-bg, #e8f5e9);
        border-radius: 4px;
        font-size: 0.85rem;
        color: var(--shenas-success, #2e7d32);
      }
      .stored-item {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.15rem 0;
      }
    `]);customElements.define("shenas-auth",L);const b=class b extends g{constructor(){super(),this.apiBase="/api",this.kind="",this.name="",this._config=null,this._loading=!0,this._message=null,this._editing=null,this._editValue="",this._freqNum="",this._freqUnit="hours"}willUpdate(e){(e.has("kind")||e.has("name"))&&this._fetchConfig()}async _fetchConfig(){if(!this.kind||!this.name)return;this._loading=!0;const e=await h(this.apiBase,`/config?kind=${this.kind}&name=${this.name}`);this._config=e&&e.length>0?e[0]:null,this._loading=!1}_startEdit(e,t){if(this._editing=e,this._editValue=t||"",b._DURATION_FIELDS.has(e)&&t){const s=parseFloat(t);s>=1440&&s%1440===0?(this._freqNum=String(s/1440),this._freqUnit="days"):s>=60&&s%60===0?(this._freqNum=String(s/60),this._freqUnit="hours"):s>=1?(this._freqNum=String(s),this._freqUnit="minutes"):(this._freqNum=String(s*60),this._freqUnit="seconds")}else b._DURATION_FIELDS.has(e)&&(this._freqNum="",this._freqUnit="hours")}_cancelEdit(){this._editing=null,this._editValue=""}_freqToMinutes(){const e=parseFloat(this._freqNum);return isNaN(e)||e<=0?null:String(Math.round(e*b._UNIT_MULTIPLIERS[this._freqUnit]))}_formatFreq(e){const t=parseFloat(e);return isNaN(t)?e:t>=1440&&t%1440===0?`${t/1440} day${t/1440!==1?"s":""}`:t>=60&&t%60===0?`${t/60} hour${t/60!==1?"s":""}`:t>=1?`${t} minute${t!==1?"s":""}`:`${t*60} second${t*60!==1?"s":""}`}async _saveEdit(e){const t=b._DURATION_FIELDS.has(e)?this._freqToMinutes():this._editValue;if(b._DURATION_FIELDS.has(e)&&t===null){this._message={type:"error",text:"Enter a positive number"};return}const{ok:s,data:a}=await $(this.apiBase,`/config/${this.kind}/${this.name}`,{method:"PUT",json:{key:e,value:t}});s?(this._message={type:"success",text:`Updated ${e}`},this._editing=null,await this._fetchConfig()):this._message={type:"error",text:(a==null?void 0:a.detail)||"Update failed"}}render(){var t;const e=!this._config||this._config.entries.length===0;return n`
      <shenas-page ?loading=${this._loading} ?empty=${e}
        loading-text="Loading config..." empty-text="No configuration settings for this plugin.">
        ${z(this._message)}
        ${(t=this._config)==null?void 0:t.entries.map(s=>this._renderEntry(s))}
      </shenas-page>
    `}_renderFreqEdit(e){return n`
      <div class="edit-row">
        <input class="config-input" type="number" min="0" step="any" style="width: 80px"
          .value=${this._freqNum}
          @input=${t=>{this._freqNum=t.target.value}}
          @keydown=${t=>{t.key==="Enter"&&this._saveEdit(e.key),t.key==="Escape"&&this._cancelEdit()}}
        />
        <select @change=${t=>{this._freqUnit=t.target.value}}>
          ${Object.keys(b._UNIT_MULTIPLIERS).map(t=>n`
            <option value=${t} ?selected=${this._freqUnit===t}>${t}</option>
          `)}
        </select>
        <button @click=${()=>this._saveEdit(e.key)}>Save</button>
        <button @click=${this._cancelEdit}>Cancel</button>
      </div>`}_renderEntry(e){const t=this._editing===e.key,s=b._DURATION_FIELDS.has(e.key),a=s&&e.value?this._formatFreq(e.value):e.value;return n`
      <div class="config-row">
        <div class="config-key">${e.label||e.key}</div>
        ${t?s?this._renderFreqEdit(e):n`
            <div class="edit-row">
              <input class="config-input"
                .value=${this._editValue}
                @input=${i=>{this._editValue=i.target.value}}
                @keydown=${i=>{i.key==="Enter"&&this._saveEdit(e.key),i.key==="Escape"&&this._cancelEdit()}}
              />
              <button @click=${()=>this._saveEdit(e.key)}>Save</button>
              <button @click=${this._cancelEdit}>Cancel</button>
            </div>`:n`
            <div class="config-detail">
              <div class="config-value ${a?"":"empty"}"
                @click=${()=>this._startEdit(e.key,e.value)}
                style="cursor: pointer"
                title="Click to edit"
              >${a||"not set"}</div>
              ${e.description?n`<div class="config-desc">${e.description}</div>`:""}
            </div>`}
      </div>
    `}};d(b,"properties",{apiBase:{type:String,attribute:"api-base"},kind:{type:String},name:{type:String},_config:{state:!0},_loading:{state:!0},_message:{state:!0},_editing:{state:!0},_editValue:{state:!0},_freqNum:{state:!0},_freqUnit:{state:!0}}),d(b,"styles",[x,B,E,m`
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
      .config-input {
        font-family: monospace;
      }
      .edit-row {
        display: flex;
        gap: 0.4rem;
        align-items: center;
        flex: 1;
      }
    `]),d(b,"_UNIT_MULTIPLIERS",{seconds:1/60,minutes:1,hours:60,days:1440}),d(b,"_DURATION_FIELDS",new Set(["sync_frequency","lookback_period"]));let F=b;customElements.define("shenas-config",F);function ae(l){if(!l)return null;const e=l.split("+").map(t=>t.trim().toLowerCase());return{ctrl:e.includes("ctrl")||e.includes("cmd"),shift:e.includes("shift"),alt:e.includes("alt"),key:e.filter(t=>!["ctrl","cmd","shift","alt"].includes(t))[0]||""}}function ie(l){const e=[];(l.ctrlKey||l.metaKey)&&e.push("Ctrl"),l.shiftKey&&e.push("Shift"),l.altKey&&e.push("Alt");const t=l.key.length===1?l.key.toUpperCase():l.key;return["Control","Shift","Alt","Meta"].includes(l.key)||e.push(t),e.join("+")}function ne(l,e){const t=ae(e);return!t||!t.key?!1:(l.ctrlKey||l.metaKey)===t.ctrl&&l.shiftKey===t.shift&&l.altKey===t.alt&&l.key.toLowerCase()===t.key}const y=[{id:"pipe",label:"Pipes"},{id:"schema",label:"Schemas"},{id:"component",label:"Components"},{id:"ui",label:"UI"},{id:"theme",label:"Themes"}];class q extends g{constructor(){super(),this.apiBase="/api",this.actions=[],this._bindings={},this._recording=null,this._recordedKey="",this._conflict=null,this._loading=!0,this._filter=""}connectedCallback(){super.connectedCallback(),this._loadBindings(),this._boundKeydown=e=>this._onKeydown(e),document.addEventListener("keydown",this._boundKeydown,!0)}disconnectedCallback(){super.disconnectedCallback(),document.removeEventListener("keydown",this._boundKeydown,!0)}async _loadBindings(){this._loading=!0,this._bindings=await h(this.apiBase,"/hotkeys")||{},this._loading=!1}async _saveBinding(e,t){t?await h(this.apiBase,`/hotkeys/${e}`,{method:"PUT",json:{binding:t}}):await h(this.apiBase,`/hotkeys/${e}`,{method:"DELETE"}),this.dispatchEvent(new CustomEvent("hotkeys-changed",{bubbles:!0,composed:!0}))}_startRecording(e){this._recording=e,this._recordedKey="",this._conflict=null}_stopRecording(){this._recording=null,this._recordedKey="",this._conflict=null}_onKeydown(e){if(!this._recording)return;if(e.preventDefault(),e.stopPropagation(),e.key==="Escape"){this._stopRecording();return}if(["Control","Shift","Alt","Meta"].includes(e.key))return;const t=ie(e);this._recordedKey=t;const s=Object.entries(this._bindings).find(([a,i])=>i===t&&a!==this._recording);this._conflict=s?s[0]:null}async _applyRecording(){!this._recordedKey||!this._recording||(this._conflict&&(this._bindings={...this._bindings,[this._conflict]:""},await this._saveBinding(this._conflict,"")),this._bindings={...this._bindings,[this._recording]:this._recordedKey},await this._saveBinding(this._recording,this._recordedKey),this._stopRecording())}async _clearBinding(e){this._bindings={...this._bindings,[e]:""},await this._saveBinding(e,"")}async _resetDefaults(){await h(this.apiBase,"/hotkeys/reset",{method:"POST"}),await this._loadBindings(),this.dispatchEvent(new CustomEvent("hotkeys-changed",{bubbles:!0,composed:!0}))}_getActionLabel(e){const t=this.actions.find(s=>s.id===e);return t?t.label:e}_getActionCategory(e){const t=this.actions.find(s=>s.id===e);return t?t.category:""}render(){if(this._loading)return n`<p class="loading">Loading hotkeys...</p>`;const e=this._filter.toLowerCase(),t=this.actions.filter(s=>!e||s.label.toLowerCase().includes(e)||s.category.toLowerCase().includes(e));return n`
      <div class="toolbar">
        <button @click=${this._resetDefaults}>Reset to Defaults</button>
        <input class="filter-input" type="text" placeholder="Filter actions..."
          .value=${this._filter} @input=${s=>{this._filter=s.target.value}} />
      </div>
      ${t.map(s=>this._renderRow(s.id,s.label,s.category))}
    `}_renderRow(e,t,s){const a=this._bindings[e]||"",i=this._recording===e,o=this._conflict?this._getActionLabel(this._conflict):"";return n`
      <div class="hotkey-row">
        <span class="hotkey-category">${s}</span>
        <span class="hotkey-label">${t}</span>
        <span class="hotkey-binding">
          ${i?n`
              <span class="recording">${this._recordedKey||"Press a key..."}</span>
              ${this._conflict?n`<span class="conflict">Conflicts with ${o}</span>`:""}
              <button @click=${this._applyRecording} ?disabled=${!this._recordedKey}>Save</button>
              <button @click=${this._stopRecording}>Cancel</button>
            `:n`
              ${a?n`<span class="kbd">${a}</span>`:n`<span class="unbound">-</span>`}
              <button class="edit-btn" @click=${()=>this._startRecording(e)}>Edit</button>
              ${a?n`<button class="edit-btn" @click=${()=>this._clearBinding(e)}>Clear</button>`:""}
            `}
        </span>
      </div>
    `}}d(q,"properties",{apiBase:{type:String,attribute:"api-base"},actions:{type:Array},_bindings:{state:!0},_recording:{state:!0},_recordedKey:{state:!0},_conflict:{state:!0},_loading:{state:!0},_filter:{state:!0}}),d(q,"styles",[x,E,C,m`
      :host {
        display: block;
      }
      .toolbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
      }
      .filter-input {
        padding: 0.3rem 0.6rem;
        border: 1px solid var(--shenas-border-input, #ddd);
        border-radius: 4px;
        font-size: 0.85rem;
        width: 200px;
        background: var(--shenas-bg, #fff);
        color: var(--shenas-text, #222);
      }
      .hotkey-row {
        display: flex;
        align-items: center;
        padding: 0.5rem 0;
        border-bottom: 1px solid var(--shenas-border-light, #f0f0f0);
        font-size: 0.85rem;
      }
      .hotkey-row:last-child {
        border-bottom: none;
      }
      .hotkey-category {
        min-width: 70px;
        color: var(--shenas-text-muted, #888);
        font-size: 0.75rem;
      }
      .hotkey-label {
        flex: 1;
        color: var(--shenas-text, #222);
      }
      .hotkey-binding {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
      }
      .kbd {
        display: inline-block;
        padding: 2px 8px;
        background: var(--shenas-bg-secondary, #fafafa);
        border: 1px solid var(--shenas-border, #e0e0e0);
        border-radius: 4px;
        font-family: monospace;
        font-size: 0.8rem;
        color: var(--shenas-text, #222);
        min-width: 20px;
        text-align: center;
      }
      .unbound {
        color: var(--shenas-text-faint, #aaa);
        font-size: 0.75rem;
      }
      .edit-btn {
        background: none;
        border: none;
        cursor: pointer;
        color: var(--shenas-text-faint, #aaa);
        font-size: 0.75rem;
        padding: 2px 6px;
      }
      .edit-btn:hover {
        color: var(--shenas-primary, #0066cc);
      }
      .recording {
        padding: 2px 8px;
        background: var(--shenas-bg-selected, #f0f4ff);
        border: 2px solid var(--shenas-primary, #0066cc);
        border-radius: 4px;
        font-family: monospace;
        font-size: 0.8rem;
        color: var(--shenas-primary, #0066cc);
        min-width: 80px;
        text-align: center;
      }
      .conflict {
        font-size: 0.75rem;
        color: var(--shenas-error, #c62828);
        margin-left: 0.5rem;
      }
    `]);customElements.define("shenas-hotkeys",q);class K extends g{constructor(){super(),this.apiBase="/api",this._activeTab="logs",this._logs=[],this._spans=[],this._loading=!0,this._search="",this._severity="",this._expanded=null,this._live=!1,this._logSource=null,this._spanSource=null}connectedCallback(){super.connectedCallback(),this.dispatchEvent(new CustomEvent("page-title",{bubbles:!0,composed:!0,detail:{title:"Logs"}})),this._fetchBoth(),this._connectStreams()}disconnectedCallback(){super.disconnectedCallback(),this._disconnectStreams(),clearTimeout(this._searchTimer)}_connectStreams(){const e=this.apiBase.startsWith("http")?this.apiBase:`${location.origin}${this.apiBase}`;this._logSource=new EventSource(`${e}/stream/logs`),this._logSource.onmessage=t=>{try{const s=JSON.parse(t.data);this._logs=[s,...this._logs].slice(0,500)}catch{}},this._logSource.onopen=()=>{this._live=!0},this._logSource.onerror=()=>{this._live=!1},this._spanSource=new EventSource(`${e}/stream/spans`),this._spanSource.onmessage=t=>{try{const s=JSON.parse(t.data);this._spans=[s,...this._spans].slice(0,500)}catch{}}}_disconnectStreams(){this._logSource&&(this._logSource.close(),this._logSource=null),this._spanSource&&(this._spanSource.close(),this._spanSource=null),this._live=!1}async _fetchBoth(){this._loading=!0;const e=this.pipe?`?pipe=${encodeURIComponent(this.pipe)}`:"";try{const[t,s]=await Promise.all([fetch(`${this.apiBase}/logs${e}`),fetch(`${this.apiBase}/spans${e}`)]);t.ok&&(this._logs=await t.json()),s.ok&&(this._spans=await s.json())}catch{}this._loading=!1}async _fetch(){this._loading=!0,this._expanded=null;const e=new URLSearchParams;this._search&&e.set("search",this._search),this._activeTab==="logs"&&this._severity&&e.set("severity",this._severity),this.pipe&&e.set("pipe",this.pipe);const t=e.toString()?`?${e}`:"";try{const s=this._activeTab==="logs"?"logs":"spans",a=await fetch(`${this.apiBase}/${s}${t}`);if(a.ok){const i=await a.json();this._activeTab==="logs"?this._logs=i:this._spans=i}}catch{}this._loading=!1}_onSearch(e){this._search=e.target.value,clearTimeout(this._searchTimer),this._searchTimer=setTimeout(()=>this._fetch(),300)}_switchTab(e){this._activeTab=e,this._expanded=null,this._fetch()}_toggleExpand(e){this._expanded=this._expanded===e?null:e}render(){const e=this._activeTab==="logs"?this._logs:this._spans;return n`
      <div class="tabs">
        <button class="tab ${this._activeTab==="logs"?"active":""}" @click=${()=>this._switchTab("logs")}>
          Logs <span class="count">(${this._logs.length})</span>
        </button>
        <button class="tab ${this._activeTab==="spans"?"active":""}" @click=${()=>this._switchTab("spans")}>
          Spans <span class="count">(${this._spans.length})</span>
        </button>
      </div>
      <div class="toolbar">
        <input class="search" type="text" placeholder="Search..." .value=${this._search} @input=${this._onSearch} />
        ${this._activeTab==="logs"?n`<select .value=${this._severity} @change=${t=>{this._severity=t.target.value,this._fetch()}}>
              <option value="">All severities</option>
              <option value="DEBUG">DEBUG</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
            </select>`:""}
        <button @click=${()=>this._fetch()}>Refresh</button>
        ${this._live?n`<span class="live-label"><span class="live-dot"></span>Live</span>`:""}
      </div>
      <div class="list">
        ${this._loading?n`<p class="loading">Loading...</p>`:e.length===0?n`<p class="empty">No ${this._activeTab} found</p>`:e.map((t,s)=>this._activeTab==="logs"?this._renderLog(t,s):this._renderSpan(t,s))}
      </div>
    `}_renderLog(e,t){const s=this._expanded===t;return n`
      <div class="row" @click=${()=>this._toggleExpand(t)}>
        <div class="row-header">
          <span class="timestamp">${this._formatTime(e.timestamp)}</span>
          <span class="severity ${e.severity||""}">${e.severity||"-"}</span>
          <span class="body">${e.body||""}</span>
        </div>
        ${s?n`
          <div class="detail">
            <div style="white-space:pre-wrap; word-break:break-word; margin-bottom:0.5rem">${e.body||""}</div>
            ${this._detailRow("Service",e.service_name)}
            ${this._detailRow("Trace ID",e.trace_id)}
            ${this._detailRow("Span ID",e.span_id)}
            ${this._renderAttributes(e.attributes)}
          </div>
        `:""}
      </div>
    `}_renderSpan(e,t){const s=this._expanded===t;return n`
      <div class="row" @click=${()=>this._toggleExpand(t)}>
        <div class="row-header">
          <span class="timestamp">${this._formatTime(e.start_time)}</span>
          <span class="status ${e.status_code||""}">${e.status_code||"-"}</span>
          <span class="span-name">${e.name}</span>
          <span class="duration">${e.duration_ms!=null?`${Math.round(e.duration_ms)}ms`:""}</span>
        </div>
        ${s?n`
          <div class="detail">
            ${this._detailRow("Service",e.service_name)}
            ${this._detailRow("Kind",e.kind)}
            ${this._detailRow("Trace ID",e.trace_id)}
            ${this._detailRow("Span ID",e.span_id)}
            ${this._detailRow("Parent",e.parent_span_id)}
            ${this._detailRow("Status",e.status_code)}
            ${e.duration_ms!=null?this._detailRow("Duration",`${e.duration_ms.toFixed(2)}ms`):""}
            ${this._renderAttributes(e.attributes)}
          </div>
        `:""}
      </div>
    `}_detailRow(e,t){return t?n`<div class="detail-row"><span class="detail-key">${e}</span><span class="detail-value">${t}</span></div>`:""}_renderAttributes(e){if(!e)return"";let t=e;if(typeof e=="string")try{t=JSON.parse(e)}catch{return this._detailRow("Attributes",e)}if(typeof t!="object"||t===null)return this._detailRow("Attributes",String(e));const s=Object.entries(t);return s.length===0?"":n`
      <div class="detail-row">
        <span class="detail-key">Attributes</span>
        <div class="attr-list">
          ${s.map(([a,i])=>n`
            <div class="attr-item">
              <span class="attr-key">${a}</span>
              <span class="attr-val">${typeof i=="string"?i:JSON.stringify(i)}</span>
            </div>
          `)}
        </div>
      </div>
    `}_formatTime(e){if(!e)return"-";const t=new Date(String(e).endsWith("Z")?e:e+"Z");if(isNaN(t))return String(e).replace("T"," ").slice(0,23);const s=(a,i=2)=>String(a).padStart(i,"0");return`${t.getFullYear()}-${s(t.getMonth()+1)}-${s(t.getDate())} ${s(t.getHours())}:${s(t.getMinutes())}:${s(t.getSeconds())}.${s(t.getMilliseconds(),3)}`}}d(K,"properties",{apiBase:{type:String,attribute:"api-base"},pipe:{type:String},_activeTab:{state:!0},_logs:{state:!0},_spans:{state:!0},_loading:{state:!0},_search:{state:!0},_severity:{state:!0},_expanded:{state:!0},_live:{state:!0}}),d(K,"styles",[x,C,m`
      :host {
        display: flex;
        flex-direction: column;
        height: 100%;
        overflow: hidden;
      }
      .toolbar {
        display: flex;
        gap: 0.5rem;
        align-items: center;
        padding-bottom: 0.8rem;
        flex-shrink: 0;
      }
      .tabs {
        display: flex;
        gap: 0;
        border-bottom: 2px solid var(--shenas-border, #e0e0e0);
        margin-bottom: 0.8rem;
        flex-shrink: 0;
      }
      .tab {
        padding: 0.4rem 1rem;
        cursor: pointer;
        font-size: 0.85rem;
        color: var(--shenas-text-secondary, #666);
        border-bottom: 2px solid transparent;
        margin-bottom: -2px;
        background: none;
        border-top: none;
        border-left: none;
        border-right: none;
      }
      .tab.active {
        color: var(--shenas-text, #222);
        border-bottom-color: var(--shenas-primary, #0066cc);
        font-weight: 500;
      }
      .search {
        flex: 1;
        padding: 0.3rem 0.6rem;
        border: 1px solid var(--shenas-border-input, #ddd);
        border-radius: 4px;
        font-size: 0.85rem;
        background: var(--shenas-bg, #fff);
        color: var(--shenas-text, #222);
      }
      select {
        padding: 0.3rem 0.5rem;
        border: 1px solid var(--shenas-border-input, #ddd);
        border-radius: 4px;
        font-size: 0.85rem;
        background: var(--shenas-bg, #fff);
        color: var(--shenas-text, #222);
      }
      .list {
        flex: 1;
        overflow-y: auto;
        min-height: 0;
      }
      .row {
        padding: 0.4rem 0;
        border-bottom: 1px solid var(--shenas-border-light, #f0f0f0);
        font-size: 0.8rem;
        cursor: pointer;
      }
      .row:hover {
        background: var(--shenas-bg-hover, #f5f5f5);
      }
      .row-header {
        display: flex;
        gap: 0.5rem;
        align-items: baseline;
      }
      .timestamp {
        color: var(--shenas-text-muted, #888);
        font-family: monospace;
        font-size: 0.75rem;
        min-width: 140px;
      }
      .severity {
        font-size: 0.7rem;
        font-weight: 600;
        padding: 1px 4px;
        border-radius: 3px;
        min-width: 40px;
        text-align: center;
      }
      .severity.INFO { color: var(--shenas-primary, #0066cc); background: var(--shenas-bg-selected, #f0f4ff); }
      .severity.WARNING { color: #f57c00; background: #fff3e0; }
      .severity.ERROR { color: var(--shenas-error, #c62828); background: var(--shenas-error-bg, #fce4ec); }
      .severity.DEBUG { color: var(--shenas-text-muted, #888); background: var(--shenas-bg-secondary, #fafafa); }
      .body {
        color: var(--shenas-text, #222);
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .span-name {
        color: var(--shenas-text, #222);
        font-weight: 500;
        flex: 1;
      }
      .duration {
        color: var(--shenas-text-muted, #888);
        font-family: monospace;
        font-size: 0.75rem;
      }
      .status {
        font-size: 0.7rem;
        padding: 1px 4px;
        border-radius: 3px;
      }
      .status.OK { color: var(--shenas-success, #2e7d32); background: var(--shenas-success-bg, #e8f5e9); }
      .status.ERROR { color: var(--shenas-error, #c62828); background: var(--shenas-error-bg, #fce4ec); }
      .detail {
        padding: 0.5rem 0 0.5rem 1rem;
        font-size: 0.75rem;
        color: var(--shenas-text-secondary, #666);
      }
      .detail-row {
        display: flex;
        gap: 0.5rem;
        padding: 0.15rem 0;
      }
      .detail-key {
        color: var(--shenas-text-muted, #888);
        min-width: 100px;
      }
      .detail-value {
        font-family: monospace;
        word-break: break-all;
      }
      .attr-list {
        display: flex;
        flex-direction: column;
        gap: 2px;
      }
      .attr-item {
        display: flex;
        gap: 0.5rem;
      }
      .attr-key {
        color: var(--shenas-primary, #0066cc);
        min-width: 160px;
        flex-shrink: 0;
      }
      .attr-val {
        font-family: monospace;
        word-break: break-all;
        white-space: pre-wrap;
      }
      .count {
        color: var(--shenas-text-faint, #aaa);
        font-size: 0.8rem;
      }
      .live-dot {
        display: inline-block;
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: var(--shenas-success, #2e7d32);
        margin-right: 4px;
        animation: pulse 2s infinite;
      }
      @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.3; }
      }
      .live-label {
        font-size: 0.7rem;
        color: var(--shenas-success, #2e7d32);
      }
    `]);customElements.define("shenas-logs",K);class U extends g{constructor(){super();d(this,"_router",new te(this,[{path:"/",render:()=>this._renderDynamicHome()},{path:"/settings",render:()=>this._renderSettings("data-flow")},{path:"/settings/:kind",render:({kind:t})=>this._renderSettings(t)},{path:"/settings/:kind/:name",render:({kind:t,name:s})=>this._renderPluginDetail(t,s)},{path:"/settings/:kind/:name/config",render:({kind:t,name:s})=>this._renderPluginDetail(t,s,"config")},{path:"/settings/:kind/:name/auth",render:({kind:t,name:s})=>this._renderPluginDetail(t,s,"auth")},{path:"/settings/:kind/:name/data",render:({kind:t,name:s})=>this._renderPluginDetail(t,s,"data")},{path:"/settings/:kind/:name/logs",render:({kind:t,name:s})=>this._renderPluginDetail(t,s,"logs")},{path:"/logs",render:()=>n`<shenas-logs api-base="${this.apiBase}"></shenas-logs>`},{path:"/:tab",render:({tab:t})=>this._renderDynamicTab(t)}]));d(this,"_hotkeys",{});d(this,"_pluginDisplayNames",{});d(this,"_nextTabId",1);d(this,"_saveWorkspaceTimer",null);this.apiBase="/api",this._components=[],this._loading=!0,this._loadedScripts=new Set,this._elementCache=new Map,this._leftWidth=160,this._rightWidth=220,this._dbStatus=null,this._inspectTable=null,this._inspectRows=null,this._paletteOpen=!1,this._paletteCommands=[],this._navPaletteOpen=!1,this._navCommands=[],this._registeredCommands=new Map,this._tabs=[],this._activeTabId=null}connectedCallback(){super.connectedCallback(),this._fetchData(),this.addEventListener("plugin-state-changed",()=>this._refreshComponents()),this.addEventListener("inspect-table",t=>this._inspect(t.detail.schema,t.detail.table)),this.addEventListener("page-title",t=>{this._activeTabId!=null&&(this._tabs=this._tabs.map(s=>s.id===this._activeTabId?{...s,label:t.detail.title}:s))}),this.addEventListener("navigate",t=>this._navigateTo(t.detail.path,t.detail.label)),this.addEventListener("register-command",t=>{const{componentId:s,commands:a}=t.detail;!a||a.length===0?this._registeredCommands.delete(s):this._registeredCommands.set(s,a)}),this._loadHotkeys(),this._keyHandler=t=>{for(const[s,a]of Object.entries(this._hotkeys))if(a&&ne(t,a))for(const i of this._registeredCommands.values()){const o=i.find(r=>r.id===s);if(o&&o.action){t.preventDefault(),o.action();return}}},document.addEventListener("keydown",this._keyHandler),this.addEventListener("hotkeys-changed",()=>this._loadHotkeys())}disconnectedCallback(){super.disconnectedCallback(),document.removeEventListener("keydown",this._keyHandler)}async _loadHotkeys(){this._hotkeys=await h(this.apiBase,"/hotkeys")||{}}_togglePalette(){if(this._paletteOpen){this._paletteOpen=!1;return}this._navPaletteOpen=!1,this._buildCommands(),this._paletteOpen=!0}async _toggleNavPalette(){if(this._navPaletteOpen){this._navPaletteOpen=!1;return}this._paletteOpen=!1,await this._buildNavCommands(),this._navPaletteOpen=!0}async _buildNavCommands(){const t=[];for(const a of this._components)t.push({id:`nav:${a.name}`,category:"Page",label:a.display_name||a.name,path:`/${a.name}`});t.push({id:"nav:dataflow",category:"Settings",label:"Data Flow",path:"/settings/data-flow"});for(const a of y)t.push({id:`nav:settings:${a.id}`,category:"Settings",label:a.label,path:`/settings/${a.id}`});let s=[];try{s=(await Promise.all(y.map(async i=>(await this._fetch(`/plugins/${i.id}`)||[]).map(r=>({...r,kind:i.id,kindLabel:i.label}))))).flat()}catch{}for(const a of s)t.push({id:`nav:${a.kind}:${a.name}`,category:a.kindLabel,label:a.display_name||a.name,path:`/settings/${a.kind}/${a.name}`});this._navCommands=t}async _registerGlobalCommands(){const t=[],s={};try{for(const i of y){const o=await this._fetch(`/plugins/${i.id}`)||[];for(const r of o){const p=r.display_name||r.name;s[`${i.id}:${r.name}`]=p;const f=r.enabled!==!1;t.push({id:`toggle:${i.id}:${r.name}`,category:i.label,label:`Toggle ${p}`,action:async()=>{const w=f?"disable":"enable";await h(this.apiBase,`/plugins/${i.id}/${r.name}/${w}`,{method:"POST"}),await this._registerGlobalCommands()}}),i.id==="pipe"&&f&&t.push({id:`sync:${r.name}`,category:"Pipe",label:`Sync ${p}`,action:()=>fetch(`${this.apiBase}/sync/${r.name}`,{method:"POST"})})}}t.push({id:"sync:all",category:"Pipe",label:"Sync All Pipes",action:()=>fetch(`${this.apiBase}/sync`,{method:"POST"})}),t.push({id:"seed:transforms",category:"Transform",label:"Seed Default Transforms",action:()=>h(this.apiBase,"/transforms/seed",{method:"POST"})});for(const i of y){if(i.id!=="pipe")continue;const o=await this._fetch(`/plugins/${i.id}`)||[];for(const r of o)r.enabled!==!1&&t.push({id:`transform:pipe:${r.name}`,category:"Transform",label:`Run Transforms: ${r.display_name||r.name}`,action:()=>h(this.apiBase,`/transforms/run/pipe/${r.name}`,{method:"POST"})})}const a=await this._fetch("/plugins/schema")||[];for(const i of a){const r=(await this._fetch("/db/schema-plugins")||{})[i.name]||[];for(const p of r)t.push({id:`transform:schema:${p}`,category:"Transform",label:`Run Transforms -> ${i.display_name||i.name}: ${p}`,action:()=>h(this.apiBase,`/transforms/run/schema/${p}`,{method:"POST"})})}}catch{}this._pluginDisplayNames=s,t.push({id:"command-palette",category:"System",label:"Command Palette",action:()=>this._togglePalette()},{id:"navigation-palette",category:"System",label:"Navigation Palette",action:()=>this._toggleNavPalette()},{id:"close-tab",category:"System",label:"Close Tab",action:()=>{this._activeTabId!=null&&this._closeTab(this._activeTabId)}},{id:"new-tab",category:"System",label:"New Tab",action:()=>this._addTab()}),this._registeredCommands.set("global",t)}_buildCommands(){const t=[];for(const s of this._registeredCommands.values())t.push(...s);this._paletteCommands=t}_executePaletteCommand(t){const s=t.detail;s.path?this._openTab(s.path,s.label):s.action&&s.action(),this._paletteOpen=!1,this._navPaletteOpen=!1}_navigateTo(t,s){if(this._tabs.length===0||!this._activeTabId){this._openTab(t,s);return}const a=s||this._labelForPath(t);this._tabs=this._tabs.map(i=>i.id===this._activeTabId?{...i,path:t,label:a}:i),window.history.pushState({},"",t),this._router.goto(t),this._saveWorkspace()}_openTab(t,s){const a=this._nextTabId++;this._tabs=[...this._tabs,{id:a,path:t,label:s||this._labelForPath(t)}],this._activeTabId=a,window.history.pushState({},"",t),this._router.goto(t),this._saveWorkspace()}async _addTab(){await this._buildNavCommands(),this._navPaletteOpen=!0}_closeTab(t){const s=this._tabs.findIndex(i=>i.id===t);if(s===-1)return;const a=this._tabs.filter(i=>i.id!==t);if(this._tabs=a,this._activeTabId===t)if(a.length>0){const i=a[Math.min(s,a.length-1)];this._activeTabId=i.id,this._router.goto(i.path)}else this._activeTabId=null,window.history.pushState({},"","/");this._saveWorkspace()}_switchTab(t){const s=this._tabs.find(a=>a.id===t);s&&(this._activeTabId=t,window.history.pushState({},"",s.path),this._router.goto(s.path),this._saveWorkspace())}_saveWorkspace(){clearTimeout(this._saveWorkspaceTimer),this._saveWorkspaceTimer=setTimeout(()=>{const t={tabs:this._tabs,activeTabId:this._activeTabId,nextTabId:this._nextTabId};h(this.apiBase,"/workspace",{method:"PUT",json:t}).catch(()=>{})},300)}async _loadWorkspace(){try{const t=await h(this.apiBase,"/workspace");if(!t)return;if(t.tabs&&t.tabs.length>0){this._tabs=t.tabs,this._activeTabId=t.activeTabId||t.tabs[0].id,this._nextTabId=t.nextTabId||Math.max(...t.tabs.map(i=>i.id))+1;const s=window.location.pathname;if(s&&s!=="/"&&!this._tabs.some(i=>i.path===s)){this._openTab(s);return}const a=this._tabs.find(i=>i.id===this._activeTabId);a&&this._router.goto(a.path)}else{const s=window.location.pathname;s&&s!=="/"&&this._openTab(s)}}catch{const t=window.location.pathname;t&&t!=="/"&&this._openTab(t)}}_labelForPath(t){const s=t.replace(/^\/+/,"");if(!s||s==="settings"||s==="settings/data-flow")return"Data Flow";const a=s.split("/");if(a[0]==="settings"){if(a.length===2){const o=y.find(r=>r.id===a[1]);return o?o.label:a[1]}if(a.length>=3){const o=`${a[1]}:${a[2]}`;return this._pluginDisplayNames[o]||a[2]}}const i=this._components.find(o=>o.name===a[0]);return i?i.display_name||i.name:a[0]}async _refreshComponents(){this._components=await this._fetch("/components")||[]}async _fetchData(){this._loading=!0;try{const[t,s]=await Promise.all([this._fetch("/components"),this._fetch("/db/status")]);this._components=t||[],this._dbStatus=s}catch(t){console.error("Failed to fetch data:",t)}await this._registerGlobalCommands(),this._loading=!1,await this._loadWorkspace()}async _fetch(t){return h(this.apiBase,t)}_activeTab(){return(window.location.pathname.replace(/^\/+/,"")||"").split("/")[0]||(this._components.length>0?this._components[0].name:"settings")}_startDrag(t){return s=>{s.preventDefault();const a=s.clientX,i=t==="left"?this._leftWidth:this._rightWidth,o=s.target;o.classList.add("dragging");const r=f=>{const w=t==="left"?f.clientX-a:a-f.clientX,_=Math.max(80,Math.min(400,i+w));t==="left"?this._leftWidth=_:this._rightWidth=_},p=()=>{o.classList.remove("dragging"),window.removeEventListener("mousemove",r),window.removeEventListener("mouseup",p)};window.addEventListener("mousemove",r),window.addEventListener("mouseup",p)}}render(){var s;if(this._loading)return n`<shenas-page loading></shenas-page>`;const t=this._activeTab();return n`
      <div class="layout">
        <div class="panel-left" style="width: ${this._leftWidth}px">
          <div class="header">
            <img src="/static/images/shenas.png" alt="shenas" />
            <h1>shenas</h1>
          </div>
          <nav class="nav">
            ${this._components.map(a=>this._navItem(a.name,a.display_name||a.name,t))}
            ${this._navItem("logs","Logs",t)}
            ${this._navItem("settings","Settings",t)}
          </nav>
        </div>
        <div class="divider" @mousedown=${this._startDrag("left")}></div>
        <div class="panel-middle">
          ${this._tabs.length>0?n`
              <div class="tab-bar">
                ${this._tabs.map(a=>n`
                  <div class="tab-item ${a.id===this._activeTabId?"active":""}"
                    @click=${()=>this._switchTab(a.id)}>
                    <span>${a.label}</span>
                    <button class="tab-close" @click=${i=>{i.stopPropagation(),this._closeTab(a.id)}}>x</button>
                  </div>
                `)}
                <button class="tab-add" title="New tab" @click=${this._addTab}>+</button>
              </div>
              <div class="tab-content">
                <div class="tab-content-inner">
                  ${this._router.outlet()}
                </div>
              </div>`:n`
              <div class="empty-state">
                <img src="/static/images/shenas.png" alt="shenas" />
                <p>Open a page from the sidebar</p>
              </div>`}
        </div>
        <div class="divider" @mousedown=${this._startDrag("right")}></div>
        <div class="panel-right" style="width: ${this._rightWidth}px">
          ${this._inspectTable?this._renderInspect():this._renderDbStats()}
        </div>
        <div class="bottom-nav">
          <nav>
            ${this._components.map(a=>n`
              <a class="nav-item" href="/${a.name}" @click=${i=>{i.preventDefault(),this._navigateTo(`/${a.name}`)}}
                aria-selected=${(t==null?void 0:t.path)===`/${a.name}`}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/></svg>
                <span>${a.display_name||a.name}</span>
              </a>
            `)}
            <a class="nav-item" href="/logs" @click=${a=>{a.preventDefault(),this._navigateTo("/logs")}}
              aria-selected=${(t==null?void 0:t.path)==="/logs"}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
              <span>Logs</span>
            </a>
            <a class="nav-item" href="/settings" @click=${a=>{a.preventDefault(),this._navigateTo("/settings")}}
              aria-selected=${(s=t==null?void 0:t.path)==null?void 0:s.startsWith("/settings")}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/></svg>
              <span>Settings</span>
            </a>
          </nav>
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
    `}_navItem(t,s,a){return n`
      <a class="nav-item" href="/${t}" aria-selected=${a===t}
        @click=${i=>{i.preventDefault(),i.ctrlKey||i.metaKey?this._openTab(`/${t}`,s):this._navigateTo(`/${t}`,s)}}>
        ${s}
      </a>
    `}_renderDynamicHome(){return this._components.length>0?this._renderDynamicTab(this._components[0].name):this._renderSettings("pipe")}_renderDynamicTab(t){const s=this._components.find(a=>a.name===t);if(!s)return n`<p class="empty">Unknown page: ${t}</p>`;if(!this._loadedScripts.has(s.js)){this._loadedScripts=new Set([...this._loadedScripts,s.js]);const a=document.createElement("script");a.type="module",a.src=s.js,document.head.appendChild(a)}return n`<div class="component-host">
      ${this._getOrCreateElement(s)}
    </div>`}_renderPluginDetail(t,s,a="details"){return n`<shenas-plugin-detail
      api-base="${this.apiBase}"
      kind="${t}"
      name="${s}"
      active-tab="${a}"
    ></shenas-plugin-detail>`}_getAllActions(){const t=new Set,s=[];for(const a of this._registeredCommands.values())for(const i of a)!t.has(i.id)&&i.action&&(t.add(i.id),s.push({id:i.id,label:i.label,category:i.category}));return s.sort((a,i)=>a.category==="System"&&i.category!=="System"?-1:a.category!=="System"&&i.category==="System"?1:0),s}_renderSettings(t){return n`<shenas-settings
      api-base="${this.apiBase}"
      active-kind="${t||"data-flow"}"
      .allActions=${this._getAllActions()}
      .onNavigate=${s=>{this._navigateTo(`/settings/${s}`)}}
    ></shenas-settings>`}async _inspect(t,s){if(!/^[a-zA-Z_]\w*$/.test(t)||!/^[a-zA-Z_]\w*$/.test(s))return;const a=`${t}.${s}`;if(this._inspectTable===a){this._inspectTable=null,this._inspectRows=null;return}this._inspectTable=a,this._inspectRows=null;try{this._inspectRows=await h(this.apiBase,`/db/preview/${t}/${s}?limit=50`)||[]}catch{this._inspectRows=[]}}_renderDbStats(){const t=this._dbStatus;return t?n`
      <div class="db-section">
        <div class="db-meta">
          ${t.size_mb!=null?n`<code>${t.size_mb} MB</code>`:n`<span>Not created</span>`}
        </div>
        ${(t.schemas||[]).map(s=>n`
            <h4>${s.name}</h4>
            ${s.tables.map(a=>n`
                <div class="db-table-row">
                  <span class="db-table-name">${a.name}</span>
                  <span class="db-table-count">${a.rows}</span>
                </div>
                ${a.earliest?n`<span class="db-date-range">${a.earliest} - ${a.latest}</span>`:""}
              `)}
          `)}
      </div>
    `:n`<p class="empty">No database</p>`}_renderInspect(){return n`
      <div class="inspect-header">
        <h4>${this._inspectTable}</h4>
        <button class="inspect-close" title="Close" @click=${()=>{this._inspectTable=null,this._inspectRows=null}}>x</button>
      </div>
      ${this._inspectRows?this._inspectRows.length===0?n`<p class="empty" style="font-size:0.75rem">No rows</p>`:n`
            <div style="overflow-x: auto;">
              <table class="inspect-table">
                <thead>
                  <tr>${Object.keys(this._inspectRows[0]).map(t=>n`<th>${t}</th>`)}</tr>
                </thead>
                <tbody>
                  ${this._inspectRows.map(t=>n`<tr>${Object.keys(t).map(s=>n`<td title="${t[s]??""}">${t[s]??""}</td>`)}</tr>`)}
                </tbody>
              </table>
            </div>
          `:n`<p class="loading" style="font-size:0.75rem">Loading...</p>`}
    `}_getOrCreateElement(t){if(!this._elementCache.has(t.name)){const s=document.createElement(t.tag);s.setAttribute("api-base",this.apiBase),this._elementCache.set(t.name,s)}return this._elementCache.get(t.name)}}d(U,"properties",{apiBase:{type:String,attribute:"api-base"},_components:{state:!0},_loading:{state:!0},_loadedScripts:{state:!0},_leftWidth:{state:!0},_rightWidth:{state:!0},_dbStatus:{state:!0},_inspectTable:{state:!0},_inspectRows:{state:!0},_paletteOpen:{state:!0},_paletteCommands:{state:!0},_navPaletteOpen:{state:!0},_navCommands:{state:!0},_tabs:{state:!0},_activeTabId:{state:!0}}),d(U,"styles",[H,C,m`
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
        min-height: 0;
        position: relative;
      }
      .tab-content-inner {
        position: absolute;
        inset: 0;
        padding: 1.5rem 2rem;
        overflow-y: auto;
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
      /* Bottom nav for mobile */
      .bottom-nav {
        display: none;
        border-top: 1px solid var(--shenas-border, #e0e0e0);
        background: var(--shenas-bg, #fff);
        padding: 0.3rem 0;
      }
      .bottom-nav nav {
        display: flex;
        justify-content: space-around;
      }
      .bottom-nav .nav-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 2px;
        font-size: 0.6rem;
        padding: 0.3rem 0.8rem;
        border-radius: 6px;
        color: var(--shenas-text-muted, #888);
        text-decoration: none;
      }
      .bottom-nav .nav-item[aria-selected="true"] {
        color: var(--shenas-accent, #0066cc);
      }
      .bottom-nav .nav-item svg {
        flex-shrink: 0;
      }
      /* Responsive: narrow screens */
      @media (max-width: 768px) {
        .layout {
          flex-direction: column;
        }
        .panel-left {
          display: none;
        }
        .panel-right {
          display: none;
        }
        .divider {
          display: none;
        }
        .panel-middle {
          flex: 1;
        }
        .tab-bar {
          display: none;
        }
        .tab-content-inner {
          padding: 1rem;
        }
        .bottom-nav {
          display: block;
        }
        .header {
          display: none;
        }
      }
    `]);customElements.define("shenas-app",U);class M extends g{constructor(){super(),this.apiBase="/api",this.activeKind="data-flow",this.onNavigate=null,this._plugins={},this._loading=!0,this._actionMessage=null,this._installing=!1,this._menuOpen=!1}connectedCallback(){super.connectedCallback(),this._fetchAll()}async _fetchAll(){this._loading=!0;const e={};await Promise.all(y.map(async({id:t})=>{e[t]=await h(this.apiBase,`/plugins/${t}`)||[]})),this._plugins=e,this._loading=!1}async _togglePlugin(e,t,s){const a=s?"disable":"enable",{data:i}=await $(this.apiBase,`/plugins/${e}/${t}/${a}`,{method:"POST"});i!=null&&i.ok||(this._actionMessage={type:"error",text:(i==null?void 0:i.message)||`${a} failed`}),e==="theme"&&await this._applyActiveTheme(),await this._fetchAll()}async _applyActiveTheme(){const e=await h(this.apiBase,"/theme");if(!e)return;const{css:t}=e;let s=document.querySelector("link[data-shenas-theme]");t?(s||(s=document.createElement("link"),s.rel="stylesheet",s.setAttribute("data-shenas-theme",""),document.head.appendChild(s)),s.href=t):s&&s.remove()}async _install(e){var o,r;const t=this.shadowRoot.querySelector(`#install-${e}`),s=(o=t==null?void 0:t.value)==null?void 0:o.trim();if(!s)return;this._actionMessage=null;const{data:a}=await $(this.apiBase,`/plugins/${e}`,{method:"POST",json:{names:[s],skip_verify:!0}}),i=(r=a==null?void 0:a.results)==null?void 0:r[0];i!=null&&i.ok?(this._actionMessage={type:"success",text:i.message},this._installing=!1,await this._fetchAll()):this._actionMessage={type:"error",text:(i==null?void 0:i.message)||"Install failed"}}_switchKind(e){this.activeKind=e,this._menuOpen=!1,this.onNavigate&&this.onNavigate(e)}_displayName(){if(this.activeKind==="data-flow")return"Data Flow";if(this.activeKind==="hotkeys")return"Hotkeys";const e=y.find(t=>t.id===this.activeKind);return e?e.label:this.activeKind}render(){return n`
      <shenas-page ?loading=${this._loading} loading-text="Loading plugins..." display-name="${this._displayName()}">
        ${z(this._actionMessage)}
        <div class="layout">
        <button class="burger" @click=${()=>{this._menuOpen=!0}}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
          ${this._displayName()}
        </button>
        <div class="menu-overlay ${this._menuOpen?"open":""}" @click=${()=>{this._menuOpen=!1}}></div>
        ${this._menuOpen?n`
          <div class="menu-panel">
            <button class="menu-close" @click=${()=>{this._menuOpen=!1}}>x</button>
            <a href="/settings/data-flow" aria-selected=${this.activeKind==="data-flow"}
              @click=${e=>{e.preventDefault(),this._switchKind("data-flow")}}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>
              Data Flow
            </a>
            <a href="/settings/hotkeys" aria-selected=${this.activeKind==="hotkeys"}
              @click=${e=>{e.preventDefault(),this._switchKind("hotkeys")}}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="4" width="20" height="16" rx="2"/><line x1="6" y1="8" x2="6" y2="8"/><line x1="10" y1="8" x2="10" y2="8"/><line x1="14" y1="8" x2="14" y2="8"/><line x1="18" y1="8" x2="18" y2="8"/><line x1="6" y1="12" x2="18" y2="12"/><line x1="8" y1="16" x2="16" y2="16"/></svg>
              Hotkeys
            </a>
            <div class="sidebar-section">Plugins</div>
            ${y.map(({id:e,label:t})=>n`
              <a href="/settings/${e}" aria-selected=${this.activeKind===e}
                @click=${s=>{s.preventDefault(),this._switchKind(e)}}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.5 2H3.5C2.67 2 2 2.67 2 3.5v17C2 21.33 2.67 22 3.5 22h17c.83 0 1.5-.67 1.5-1.5v-17C22 2.67 21.33 2 20.5 2zM8 19H5v-3h3v3zm0-5H5v-3h3v3zm0-5H5V6h3v3z"/></svg>
                ${t} (${(this._plugins[e]||[]).length})
              </a>
            `)}
          </div>
        `:""}
        <nav class="sidebar">
          <ul>
            <li>
              <a href="/settings/data-flow" aria-selected=${this.activeKind==="data-flow"}
                @click=${e=>{e.preventDefault(),this._switchKind("data-flow")}}>
                Data Flow
              </a>
            </li>
            <li>
              <a href="/settings/hotkeys" aria-selected=${this.activeKind==="hotkeys"}
                @click=${e=>{e.preventDefault(),this._switchKind("hotkeys")}}>
                Hotkeys
              </a>
            </li>
          </ul>
          <div class="sidebar-section">Plugins</div>
          <ul>
            ${y.map(({id:e,label:t})=>n`
                <li>
                  <a
                    href="/settings/${e}"
                    aria-selected=${this.activeKind===e}
                    @click=${s=>{s.preventDefault(),this._switchKind(e)}}
                  >
                    ${t}
                    <span style="color:var(--shenas-text-faint, #aaa); font-weight:normal">
                      (${(this._plugins[e]||[]).length})
                    </span>
                  </a>
                </li>
              `)}
          </ul>
        </nav>
        <div class="content">
          ${this.activeKind==="data-flow"?n`<shenas-pipeline-overview api-base="${this.apiBase}"></shenas-pipeline-overview>`:this.activeKind==="hotkeys"?n`<shenas-hotkeys api-base="${this.apiBase}" .actions=${this.allActions||[]}></shenas-hotkeys>`:this._renderKind(this.activeKind)}
        </div>
      </div>
      </shenas-page>
    `}_formatFreq(e){return e>=1440&&e%1440===0?`${e/1440}d`:e>=60&&e%60===0?`${e/60}h`:e>=1?`${e}m`:`${e*60}s`}_renderKind(e){var a;const t=this._plugins[e]||[],s=((a=y.find(i=>i.id===e))==null?void 0:a.label)||e;return n`
      <h3>${s}</h3>
      <shenas-data-list
        .columns=${[{label:"Name",render:i=>n`<a href="/settings/${e}/${i.name}">${i.display_name||i.name}</a>`},{key:"version",label:"Version",class:"mono"},...e==="pipe"?[{label:"Sync Freq.",class:"mono",render:i=>i.sync_frequency?this._formatFreq(i.sync_frequency):""},{label:"Last Synced",class:"mono",render:i=>i.synced_at?i.synced_at.slice(0,16).replace("T"," "):"never"}]:[],{label:"Status",render:i=>e==="pipe"&&i.has_auth===!1?n`<span style="color:var(--shenas-error,#c62828);font-size:0.8rem">Needs Auth</span>`:n`<status-toggle ?enabled=${i.enabled!==!1} toggleable @toggle=${()=>this._togglePlugin(e,i.name,i.enabled!==!1)}></status-toggle>`}]}
        .rows=${t}
        .rowClass=${i=>i.enabled===!1?"disabled-row":""}
        ?show-add=${!this._installing}
        @add=${()=>{this._installing=!0}}
        empty-text="No ${s.toLowerCase()} installed"
      ></shenas-data-list>
      ${this._installing?n`<shenas-form-panel
            title="Install new plugin"
            submit-label="Install"
            @submit=${()=>this._install(e)}
            @cancel=${()=>{this._installing=!1}}
          >
            <div class="field">
              <input
                id="install-${e}"
                type="text"
                placeholder="Plugin name"
                @keydown=${i=>i.key==="Enter"&&this._install(e)}
              />
            </div>
          </shenas-form-panel>`:""}
    `}}d(M,"properties",{apiBase:{type:String,attribute:"api-base"},activeKind:{type:String,attribute:"active-kind"},onNavigate:{type:Function},allActions:{type:Array},_plugins:{state:!0},_loading:{state:!0},_actionMessage:{state:!0},_installing:{state:!0},_menuOpen:{state:!0}}),d(M,"styles",[x,B,H,E,m`
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
      .sidebar-section {
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--shenas-text-faint, #aaa);
        padding: 0.8rem 0.8rem 0.3rem;
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
      /* Burger menu button (hidden on desktop) */
      .burger {
        display: none;
        background: none;
        border: 1px solid var(--shenas-border, #e0e0e0);
        border-radius: 6px;
        padding: 0.4rem 0.6rem;
        cursor: pointer;
        color: var(--shenas-text-secondary, #666);
        margin-bottom: 0.5rem;
        align-items: center;
        gap: 0.4rem;
        font-size: 0.85rem;
      }
      .burger svg { flex-shrink: 0; }
      /* Overlay menu (mobile) */
      .menu-overlay {
        display: none;
        position: fixed;
        inset: 0;
        background: rgba(0,0,0,0.3);
        z-index: 100;
      }
      .menu-overlay.open { display: block; }
      .menu-panel {
        position: fixed;
        top: 0;
        left: 0;
        bottom: 0;
        width: 220px;
        background: var(--shenas-bg, #fff);
        z-index: 101;
        padding: 1rem;
        overflow-y: auto;
        box-shadow: 2px 0 8px rgba(0,0,0,0.15);
      }
      .menu-panel .menu-close {
        background: none;
        border: none;
        cursor: pointer;
        font-size: 1.2rem;
        color: var(--shenas-text-muted, #888);
        float: right;
      }
      .menu-panel a {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.6rem 0.5rem;
        font-size: 0.9rem;
        color: var(--shenas-text-secondary, #666);
        text-decoration: none;
        border-radius: 4px;
      }
      .menu-panel a:hover {
        background: var(--shenas-bg-hover, #f5f5f5);
      }
      .menu-panel a[aria-selected="true"] {
        background: var(--shenas-bg-selected, #f0f4ff);
        color: var(--shenas-text, #222);
        font-weight: 600;
      }
      .menu-panel a svg { flex-shrink: 0; }
      .menu-panel .sidebar-section {
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--shenas-text-faint, #aaa);
        padding: 0.8rem 0.5rem 0.3rem;
      }
      @media (max-width: 768px) {
        .sidebar { display: none; }
        .burger { display: flex; }
        .layout {
          gap: 0;
          flex-direction: column;
        }
        .content {
          flex: 1;
          min-height: 0;
          overflow-y: auto;
        }
      }
    `]);customElements.define("shenas-settings",M);class j extends g{constructor(){super(),this.apiBase="/api",this.kind="",this.name="",this.activeTab="details",this._info=null,this._loading=!0,this._message=null,this._tables=[],this._syncing=!1,this._schemaTransforms=[],this._selectedTable=null,this._previewRows=null,this._previewLoading=!1}willUpdate(e){(e.has("kind")||e.has("name"))&&this._fetchInfo()}async _fetchInfo(){if(!this.kind||!this.name)return;this._loading=!0,this._message=null,this._info=await h(this.apiBase,`/plugins/${this.kind}/${this.name}/info`);const e=this.kind==="pipe"||this.kind==="schema",[t,s,a]=await Promise.all([e?h(this.apiBase,"/db/status"):null,this.kind==="schema"?h(this.apiBase,"/db/schema-plugins"):null,this.kind==="schema"?h(this.apiBase,"/transforms"):null]),i=s?s[this.name]||[]:[];if(t){if(this.kind==="pipe"){const o=(t.schemas||[]).find(r=>r.name===this.name);this._tables=o?o.tables.filter(r=>!r.name.startsWith("_dlt_")):[]}else if(this.kind==="schema"){const o=(t.schemas||[]).find(r=>r.name==="metrics");this._tables=o?o.tables.filter(r=>i.includes(r.name)):[]}}a&&(this._schemaTransforms=a.filter(o=>i.includes(o.target_duckdb_table))),this._loading=!1,this._registerCommands()}_registerCommands(){if(!this._info)return;const e=this._info.display_name||this.name;X(this,`plugin-detail:${this.kind}:${this.name}`,[{id:`remove:${this.kind}:${this.name}`,category:"Plugin",label:`Remove ${e}`,action:()=>this._remove()}])}async _toggle(){var s;const e=((s=this._info)==null?void 0:s.enabled)!==!1?"disable":"enable",{data:t}=await $(this.apiBase,`/plugins/${this.kind}/${this.name}/${e}`,{method:"POST"});this._message={type:t!=null&&t.ok?"success":"error",text:(t==null?void 0:t.message)||`${e} failed`},await this._fetchInfo(),this.dispatchEvent(new CustomEvent("plugin-state-changed",{bubbles:!0,composed:!0}))}async _sync(){this._syncing=!0,this._message=null;try{const e=await fetch(`${this.apiBase}/sync/${this.name}`,{method:"POST"});if(!e.ok){const p=await e.json().catch(()=>({}));this._message={type:"error",text:p.detail||`Sync failed (${e.status})`},this._syncing=!1;return}const t=e.body.getReader(),s=new TextDecoder;let a="",i="",o=!1;for(;;){const{done:p,value:f}=await t.read();if(p)break;const w=s.decode(f,{stream:!0});for(const _ of w.split(`
`))_.startsWith("event: ")&&(a=_.slice(7).trim()),_.startsWith("data: ")&&(i=_.slice(6));a==="error"&&(o=!0)}let r="Sync complete";try{r=JSON.parse(i).message||r}catch{}this._message={type:o?"error":"success",text:r},o||await this._fetchInfo()}catch(e){this._message={type:"error",text:`Sync failed: ${e.message}`}}this._syncing=!1}async _remove(){const{data:e}=await $(this.apiBase,`/plugins/${this.kind}/${this.name}`,{method:"DELETE"});e!=null&&e.ok?(window.history.pushState({},"",`/settings/${this.kind}`),window.dispatchEvent(new PopStateEvent("popstate"))):this._message={type:"error",text:e.message||"Remove failed"}}_switchTab(e){this.activeTab=e;const t=`/settings/${this.kind}/${this.name}`,s=e==="details"?t:`${t}/${e}`;window.history.pushState({},"",s)}async _fetchPreview(e){if(this._selectedTable=e,!e){this._previewRows=null;return}this._previewLoading=!0,this._previewRows=await h(this.apiBase,`/db/preview/${this.name}/${e}?limit=100`),this._previewLoading=!1}_renderData(){var t;const e=this._tables||[];if(e.length===0)return n`<p style="color:var(--shenas-text-muted,#888)">No tables synced yet.</p>`;if(!this._selectedTable&&((t=this._info)!=null&&t.primary_table)){const s=this._info.primary_table;e.some(a=>a.name===s)&&this._fetchPreview(s)}return n`
      <div class="data-toolbar">
        <select @change=${s=>this._fetchPreview(s.target.value)}>
          <option value="">Select a table</option>
          ${e.map(s=>n`<option value=${s.name} ?selected=${this._selectedTable===s.name}>${s.name}${s.rows?` (${s.rows})`:""}</option>`)}
        </select>
        ${this._previewLoading?n`<span style="color:var(--shenas-text-muted,#888)">Loading...</span>`:""}
      </div>
      ${this._previewRows&&this._previewRows.length>0?n`
        <table class="data-table">
          <thead><tr>${Object.keys(this._previewRows[0]).map(s=>n`<th>${s}</th>`)}</tr></thead>
          <tbody>${this._previewRows.map(s=>n`
            <tr>${Object.values(s).map(a=>n`<td title="${a??""}">${a??""}</td>`)}</tr>
          `)}</tbody>
        </table>
      `:this._selectedTable&&!this._previewLoading?n`<p style="color:var(--shenas-text-muted,#888)">Table is empty.</p>`:""}
    `}render(){var e,t;return n`
      <shenas-page ?loading=${this._loading} ?empty=${!this._info} empty-text="Plugin not found."
        display-name="${((e=this._info)==null?void 0:e.display_name)||((t=this._info)==null?void 0:t.name)||this.name}">
        ${this._info?this._renderContent():""}
      </shenas-page>
    `}_renderContent(){const e=this._info,t=e.enabled!==!1,s=`/settings/${this.kind}/${this.name}`;return n`
      <a class="back" href="/settings/${this.kind}">&larr; Back to ${this.kind}s</a>

      <div class="title-row">
        <h2>${e.display_name||e.name} <span class="kind-badge">${e.kind}</span>${e.version?n` <span class="version">${e.version}</span>`:""}</h2>
        <div class="title-actions">
          ${this.kind==="pipe"&&t?n`<button @click=${this._sync} ?disabled=${this._syncing}>${this._syncing?"Syncing...":"Sync"}</button>`:""}
          <button class="danger" @click=${this._remove}>Remove</button>
        </div>
      </div>

      ${z(this._message)}

      <div class="tabs">
        <a class="tab" href="${s}" aria-selected=${this.activeTab==="details"}
          @click=${a=>{a.preventDefault(),this._switchTab("details")}}>Details</a>
        <a class="tab" href="${s}/config" aria-selected=${this.activeTab==="config"}
          @click=${a=>{a.preventDefault(),this._switchTab("config")}}>Config</a>
        ${this.kind==="pipe"?n`
          <a class="tab" href="${s}/auth" aria-selected=${this.activeTab==="auth"}
            @click=${a=>{a.preventDefault(),this._switchTab("auth")}}>Auth</a>
        `:""}
        <a class="tab" href="${s}/data" aria-selected=${this.activeTab==="data"}
          @click=${a=>{a.preventDefault(),this._switchTab("data")}}>Data</a>
        <a class="tab" href="${s}/logs" aria-selected=${this.activeTab==="logs"}
          @click=${a=>{a.preventDefault(),this._switchTab("logs")}}>Logs</a>
      </div>

      ${this.activeTab==="config"?n`<shenas-config api-base="${this.apiBase}" kind="${this.kind}" name="${this.name}"></shenas-config>`:this.activeTab==="auth"?n`<shenas-auth api-base="${this.apiBase}" pipe-name="${this.name}"></shenas-auth>`:this.activeTab==="data"?this._renderData():this.activeTab==="logs"?n`<shenas-logs api-base="${this.apiBase}" pipe="${this.name}"></shenas-logs>`:this._renderDetails(e,t)}
    `}_renderDetails(e,t){return n`
      ${e.description?n`<div class="description">${e.description}</div>`:""}

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

      ${this.kind==="pipe"||this.kind==="schema"?n`
          <h4 class="section-title">Resources</h4>
          <shenas-data-list
            .columns=${[{key:"name",label:"Table",class:"mono"},{key:"rows",label:"Rows",class:"muted"},{label:"Range",class:"muted",render:s=>s.earliest?`${s.earliest} - ${s.latest}`:""}]}
            .rows=${this._tables}
            empty-text="No tables synced yet"
          ></shenas-data-list>`:""}

      ${this.kind==="pipe"?n`
          <h4 class="section-title">Transforms</h4>
          <shenas-transforms api-base="${this.apiBase}" source="${this.name}"></shenas-transforms>`:""}

      ${this.kind==="schema"&&this._schemaTransforms.length>0?n`
          <h4 class="section-title">Transforms</h4>
          <shenas-data-list
            .columns=${[{key:"id",label:"ID",class:"muted"},{label:"Source",class:"mono",render:s=>`${s.source_duckdb_schema}.${s.source_duckdb_table}`},{label:"Target",class:"mono",render:s=>`${s.target_duckdb_schema}.${s.target_duckdb_table}`},{label:"Description",render:s=>s.description||""},{label:"Status",render:s=>n`<status-toggle ?enabled=${s.enabled}></status-toggle>`}]}
            .rows=${this._schemaTransforms}
            .rowClass=${s=>s.enabled?"":"disabled-row"}
            empty-text="No transforms"
          ></shenas-data-list>`:""}

    `}_stateRow(e,t){return t?n`
      <div class="state-row">
        <span class="state-label">${e}</span>
        <span class="state-value">${t.slice(0,19)}</span>
      </div>
    `:""}}d(j,"properties",{apiBase:{type:String,attribute:"api-base"},kind:{type:String},name:{type:String},activeTab:{type:String,attribute:"active-tab"},_info:{state:!0},_loading:{state:!0},_message:{state:!0},_tables:{state:!0},_syncing:{state:!0},_schemaTransforms:{state:!0},_selectedTable:{state:!0},_previewRows:{state:!0},_previewLoading:{state:!0}}),d(j,"styles",[x,H,E,se,m`
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
      .version {
        color: var(--shenas-text-muted, #999);
        font-size: 0.7rem;
        font-weight: 400;
        vertical-align: middle;
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
      .data-toolbar {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin: 1rem 0;
      }
      .data-toolbar select {
        padding: 0.4rem 0.6rem;
        font-size: 0.9rem;
        border: 1px solid var(--shenas-border, #ccc);
        border-radius: 4px;
      }
      .data-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.8rem;
        margin-top: 0.5rem;
        overflow-x: auto;
        display: block;
      }
      .data-table th, .data-table td {
        padding: 0.35rem 0.6rem;
        border: 1px solid var(--shenas-border-light, #e8e8e8);
        text-align: left;
        white-space: nowrap;
        max-width: 300px;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .data-table th {
        background: var(--shenas-bg-secondary, #f5f5f5);
        font-weight: 600;
        position: sticky;
        top: 0;
      }
    `]);customElements.define("shenas-plugin-detail",j);const J="background:none;border:none;cursor:pointer;color:var(--shenas-text-faint, #aaa);font-size:0.7rem;padding:0 2px";class W extends g{constructor(){super(),this.apiBase="/api",this.source="",this._transforms=[],this._loading=!0,this._editing=null,this._editSql="",this._message=null,this._previewRows=null,this._creating=!1,this._newForm=this._emptyForm(),this._dbTables={},this._schemaTables={}}_emptyForm(){return{source_duckdb_table:"",target_duckdb_table:"",description:"",sql:""}}connectedCallback(){super.connectedCallback(),this._fetchAll()}async _fetchAll(){this._loading=!0;const e=this.source?`?source=${this.source}`:"";this._transforms=await h(this.apiBase,`/transforms${e}`)||[],this._loading=!1,this._registerCommands()}_registerCommands(){const e=[];for(const t of this._transforms){const s=t.description||`${t.source_duckdb_table} -> ${t.target_duckdb_table}`;e.push({id:`transform:toggle:${t.id}`,category:"Transform",label:`${t.enabled?"Disable":"Enable"} #${t.id}`,description:s,action:()=>this._toggle(t)}),t.is_default||e.push({id:`transform:delete:${t.id}`,category:"Transform",label:`Delete #${t.id}`,description:s,action:()=>this._delete(t)})}X(this,`transforms:${this.source}`,e)}_inspectTable(e,t){this.dispatchEvent(new CustomEvent("inspect-table",{bubbles:!0,composed:!0,detail:{schema:e,table:t}}))}async _toggle(e){const t=e.enabled?"disable":"enable";await h(this.apiBase,`/transforms/${e.id}/${t}`,{method:"POST"}),await this._fetchAll()}async _delete(e){const{ok:t,data:s}=await $(this.apiBase,`/transforms/${e.id}`,{method:"DELETE"});t&&(s!=null&&s.ok)?(this._message={type:"success",text:s.message},await this._fetchAll()):this._message={type:"error",text:(s==null?void 0:s.detail)||(s==null?void 0:s.message)||"Delete failed"}}_startEdit(e){this._editing=e.id,this._editSql=e.sql,this._previewRows=null}_cancelEdit(){this._editing=null,this._editSql="",this._previewRows=null}async _saveEdit(){const{ok:e,data:t}=await $(this.apiBase,`/transforms/${this._editing}`,{method:"PUT",json:{sql:this._editSql}});e?(this._message={type:"success",text:"Transform updated"},this._editing=null,await this._fetchAll()):this._message={type:"error",text:(t==null?void 0:t.detail)||"Update failed"}}async _startCreate(){this._creating=!0,this._newForm=this._emptyForm(),this._editing=null,this._previewRows=null;const[e,t]=await Promise.all([h(this.apiBase,"/db/tables"),h(this.apiBase,"/db/schema-tables")]);this._dbTables=e||{},this._schemaTables=t||{}}_cancelCreate(){this._creating=!1,this._newForm=this._emptyForm()}_updateNewForm(e,t){this._newForm={...this._newForm,[e]:t}}async _saveCreate(){const e=this._newForm;if(!e.source_duckdb_table||!e.target_duckdb_table||!e.sql){this._message={type:"error",text:"Fill in all required fields"};return}const{ok:t,data:s}=await $(this.apiBase,"/transforms",{method:"POST",json:{source_duckdb_schema:this.source,source_duckdb_table:e.source_duckdb_table,target_duckdb_schema:"metrics",target_duckdb_table:e.target_duckdb_table,source_plugin:this.source,description:e.description,sql:e.sql}});t?(this._message={type:"success",text:"Transform created"},this._creating=!1,this._newForm=this._emptyForm(),await this._fetchAll()):this._message={type:"error",text:(s==null?void 0:s.detail)||"Create failed"}}async _preview(){const{ok:e,data:t}=await $(this.apiBase,`/transforms/${this._editing}/test?limit=5`,{method:"POST"});e?this._previewRows=t:this._message={type:"error",text:(t==null?void 0:t.detail)||"Preview failed"}}render(){return n`
      <shenas-page ?loading=${this._loading} loading-text="Loading transforms...">
      ${z(this._message)}
      ${this._editing?this._renderEditor():""}
      ${this._creating?this._renderCreateForm():""}
      <shenas-data-list
        ?show-add=${!this._creating&&!this._editing}
        @add=${this._startCreate}
        .columns=${[{key:"id",label:"ID",class:"muted"},{label:"Source",class:"mono",render:e=>n`${e.source_duckdb_schema}.${e.source_duckdb_table} <button style=${J} title="Inspect table" @click=${()=>this._inspectTable(e.source_duckdb_schema,e.source_duckdb_table)}>&#9655;</button>`},{label:"Target",class:"mono",render:e=>n`${e.target_duckdb_schema}.${e.target_duckdb_table} <button style=${J} title="Inspect table" @click=${()=>this._inspectTable(e.target_duckdb_schema,e.target_duckdb_table)}>&#9655;</button>`},{label:"Description",render:e=>n`${e.description||""}${e.is_default?n`<span style="font-size:0.75rem;color:var(--shenas-text-muted, #888);background:var(--shenas-border-light, #f0f0f0);padding:1px 5px;border-radius:3px;margin-left:4px">default</span>`:""}`},{label:"Status",render:e=>n`<status-toggle ?enabled=${e.enabled} toggleable @toggle=${()=>this._toggle(e)}></status-toggle>`}]}
        .rows=${this._transforms}
        .rowClass=${e=>e.enabled?"":"disabled-row"}
        .actions=${e=>n`
          ${e.is_default?n`<button @click=${()=>this._startEdit(e)}>View</button>`:n`<button @click=${()=>this._startEdit(e)}>Edit</button>`}
          ${e.is_default?"":n`<button class="danger" @click=${()=>this._delete(e)}>Delete</button>`}
        `}
        empty-text="No transforms"
      ></shenas-data-list>
      </shenas-page>
    `}_renderCreateForm(){const e=this._newForm,t=this.source,s=this._dbTables[t]||[],a=Object.values(this._schemaTables||{}).flat();return n`
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
              ${s.map(i=>n`<option value=${i} ?selected=${e.source_duckdb_table===i}>${i}</option>`)}
            </select>
          </label>
          <label>
            Schema table
            <select
              .value=${e.target_duckdb_table}
              @change=${i=>this._updateNewForm("target_duckdb_table",i.target.value)}
            >
              <option value="">-- select --</option>
              ${a.map(i=>n`<option value=${i} ?selected=${e.target_duckdb_table===i}>${i}</option>`)}
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
    `}_renderEditor(){const e=this._transforms.find(s=>s.id===this._editing);if(!e)return"";const t=e.is_default;return n`
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
          ${t?"":n`<button @click=${this._saveEdit}>Save</button>`}
          <button @click=${this._preview}>Preview</button>
          <button @click=${this._cancelEdit}>${t?"Close":"Cancel"}</button>
        </div>
        ${this._previewRows?this._renderPreview():""}
      </div>
    `}_renderPreview(){if(!this._previewRows||this._previewRows.length===0)return n`<p class="loading">No preview rows</p>`;const e=Object.keys(this._previewRows[0]);return n`
      <div class="preview-table">
        <table>
          <thead>
            <tr>
              ${e.map(t=>n`<th>${t}</th>`)}
            </tr>
          </thead>
          <tbody>
            ${this._previewRows.map(t=>n`
                <tr>
                  ${e.map(s=>n`<td>${t[s]}</td>`)}
                </tr>
              `)}
          </tbody>
        </table>
      </div>
    `}}d(W,"properties",{apiBase:{type:String,attribute:"api-base"},source:{type:String},_transforms:{state:!0},_loading:{state:!0},_editing:{state:!0},_editSql:{state:!0},_message:{state:!0},_previewRows:{state:!0},_creating:{state:!0},_newForm:{state:!0},_dbTables:{state:!0},_schemaTables:{state:!0}}),d(W,"styles",[Z,x,B,E,m`
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
        display: flex;
        flex-direction: column;
        gap: 0.2rem;
      }
      .form-grid input,
      .form-grid select {
        font-family: monospace;
      }
      .form-full {
        grid-column: 1 / -1;
      }
    `]);customElements.define("shenas-transforms",W);
