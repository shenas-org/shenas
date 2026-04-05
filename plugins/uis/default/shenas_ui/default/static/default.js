var ee=Object.defineProperty;var te=(l,e,t)=>e in l?ee(l,e,{enumerable:!0,configurable:!0,writable:!0,value:t}):l[e]=t;var c=(l,e,t)=>te(l,typeof e!="symbol"?e+"":e,t);import{LitElement as _,css as g,html as n}from"lit";import G,{dagre as se}from"cytoscape";import{Router as ae}from"@lit-labs/router";class N extends _{constructor(){super(),this.open=!1,this.commands=[],this._query="",this._filtered=[],this._selectedIndex=0}updated(e){e.has("open")&&this.open&&(this._query="",this._selectedIndex=0,this._filter(),requestAnimationFrame(()=>{const t=this.renderRoot.querySelector("input");t&&t.focus()})),e.has("commands")&&this._filter()}_filter(){const e=this._query.toLowerCase();e?this._filtered=this.commands.filter(t=>t.label.toLowerCase().includes(e)||t.category.toLowerCase().includes(e)||(t.description||"").toLowerCase().includes(e)):this._filtered=this.commands,this._selectedIndex>=this._filtered.length&&(this._selectedIndex=Math.max(0,this._filtered.length-1))}_onInput(e){this._query=e.target.value,this._selectedIndex=0,this._filter()}_onKeydown(e){if(e.key==="ArrowDown")e.preventDefault(),this._filtered.length>0&&(this._selectedIndex=Math.min(this._selectedIndex+1,this._filtered.length-1)),this._scrollToSelected();else if(e.key==="ArrowUp")e.preventDefault(),this._selectedIndex=Math.max(this._selectedIndex-1,0),this._scrollToSelected();else if(e.key==="Enter"){e.preventDefault();const t=this._filtered[this._selectedIndex];t&&this._execute(t)}else e.key==="Escape"&&this._close()}_scrollToSelected(){requestAnimationFrame(()=>{const e=this.renderRoot.querySelector(".item.selected");e&&e.scrollIntoView({block:"nearest"})})}_execute(e){this.dispatchEvent(new CustomEvent("execute",{detail:e,bubbles:!0,composed:!0}))}_close(){this.dispatchEvent(new CustomEvent("close",{bubbles:!0,composed:!0}))}render(){return this.open?n`
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
    `:n``}}c(N,"properties",{open:{type:Boolean,reflect:!0},commands:{type:Array},_query:{state:!0},_filtered:{state:!0},_selectedIndex:{state:!0}}),c(N,"styles",g`
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
  `);customElements.define("shenas-command-palette",N);const X=g`
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
`,x=g`
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
`,ie=g`
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
`,C=g`
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
`,P=g`
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
`,I=g`
  .loading {
    color: var(--shenas-text-muted, #888);
    font-style: italic;
  }
  .empty {
    color: var(--shenas-text-muted, #888);
    padding: 0.5rem 0;
  }
`,R=g`
  a {
    color: var(--shenas-primary, #0066cc);
    text-decoration: none;
  }
  a:hover {
    text-decoration: underline;
  }
`;class B extends _{constructor(){super(),this.loading=!1,this.empty=!1,this.loadingText="Loading...",this.emptyText="No data",this.displayName=""}updated(e){e.has("displayName")&&this.displayName&&this.dispatchEvent(new CustomEvent("page-title",{bubbles:!0,composed:!0,detail:{title:this.displayName}}))}render(){return this.loading?n`<p class="loading">${this.loadingText}</p>`:this.empty?n`<p class="empty">${this.emptyText}</p>`:n`<slot></slot>`}}c(B,"properties",{loading:{type:Boolean,reflect:!0},empty:{type:Boolean,reflect:!0},loadingText:{type:String,attribute:"loading-text"},emptyText:{type:String,attribute:"empty-text"},displayName:{type:String,attribute:"display-name"}}),c(B,"styles",[I,g`
      :host([loading]), :host([empty]) {
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 100vh;
      }
      .loading, .empty {
        color: var(--shenas-text-muted, #888);
      }
    `]);customElements.define("shenas-page",B);class O extends _{constructor(){super(),this.enabled=!1,this.toggleable=!1}updated(){this.title=this.enabled?"Enabled":"Disabled"}render(){return n`<div class="track" @click=${this._onClick}><div class="knob"></div></div>`}_onClick(){this.toggleable&&this.dispatchEvent(new CustomEvent("toggle",{bubbles:!0,composed:!0}))}}c(O,"properties",{enabled:{type:Boolean,reflect:!0},toggleable:{type:Boolean,reflect:!0}}),c(O,"styles",g`
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
  `);customElements.define("status-toggle",O);class q extends _{constructor(){super(),this.columns=[],this.rows=[],this.rowClass=null,this.actions=null,this.emptyText="No items",this.showAdd=!1}_onAdd(){this.dispatchEvent(new CustomEvent("add",{bubbles:!0,composed:!0}))}render(){const e=typeof this.actions=="function",t=this.showAdd?n`<div class="add-row"><button class="add-btn" title="Add" @click=${this._onAdd}>+</button></div>`:"";return!this.rows||this.rows.length===0?n`<p class="empty">${this.emptyText}</p>${t}`:n`
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
    `}}c(q,"properties",{columns:{type:Array},rows:{type:Array},rowClass:{type:Object},actions:{type:Object},emptyText:{type:String,attribute:"empty-text"},showAdd:{type:Boolean,attribute:"show-add"}}),c(q,"styles",[X,x,R,I,g`
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
    `]);customElements.define("shenas-data-list",q);class L extends _{constructor(){super(),this.title="",this.submitLabel="Save"}render(){return n`
      ${this.title?n`<h3>${this.title}</h3>`:""}
      <slot></slot>
      <div class="actions">
        <button @click=${this._onSubmit}>${this.submitLabel}</button>
        <button @click=${this._onCancel}>Cancel</button>
      </div>
    `}_onSubmit(){this.dispatchEvent(new CustomEvent("submit",{bubbles:!0,composed:!0}))}_onCancel(){this.dispatchEvent(new CustomEvent("cancel",{bubbles:!0,composed:!0}))}}c(L,"properties",{title:{type:String},submitLabel:{type:String,attribute:"submit-label"}}),c(L,"styles",[x,g`
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
    `]);customElements.define("shenas-form-panel",L);const ne="modulepreload",re=function(l){return"/"+l},J={},oe=function(e,t,s){let a=Promise.resolve();if(t&&t.length>0){let r=function(h){return Promise.all(h.map(m=>Promise.resolve(m).then(f=>({status:"fulfilled",value:f}),f=>({status:"rejected",reason:f}))))};document.getElementsByTagName("link");const o=document.querySelector("meta[property=csp-nonce]"),p=(o==null?void 0:o.nonce)||(o==null?void 0:o.getAttribute("nonce"));a=r(t.map(h=>{if(h=re(h),h in J)return;J[h]=!0;const m=h.endsWith(".css"),f=m?'[rel="stylesheet"]':"";if(document.querySelector(`link[href="${h}"]${f}`))return;const d=document.createElement("link");if(d.rel=m?"stylesheet":ne,m||(d.as="script"),d.crossOrigin="",d.href=h,p&&d.setAttribute("nonce",p),document.head.appendChild(d),m)return new Promise((b,k)=>{d.addEventListener("load",b),d.addEventListener("error",()=>k(new Error(`Unable to preload CSS for ${h}`)))})}))}function i(r){const o=new Event("vite:preloadError",{cancelable:!0});if(o.payload=r,window.dispatchEvent(o),!o.defaultPrevented)throw r}return a.then(r=>{for(const o of r||[])o.status==="rejected"&&i(o.reason);return e().catch(i)})};async function y(l,e,t={}){const s=await fetch(`${l}/graphql`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({query:e,variables:t})});if(!s.ok)return null;const a=await s.json();return a.errors?(console.warn("GraphQL errors:",a.errors),null):a.data}async function u(l,e,t={}){const s=await fetch(`${l}/graphql`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({query:e,variables:t})});if(!s.ok)return{ok:!1,data:null,errors:[{message:`HTTP ${s.status}`}]};const a=await s.json();return{ok:!a.errors,data:a.data,errors:a.errors||[]}}async function E(l,e){const{tableFromIPC:t}=await oe(async()=>{const{tableFromIPC:r}=await import("/vendor/apache-arrow.js");return{tableFromIPC:r}},[]),s=await fetch(`${l}/query?sql=${encodeURIComponent(e)}`);if(!s.ok)return null;const a=await s.arrayBuffer();return t(new Uint8Array(a)).toArray().map(r=>r.toJSON())}function D(l){return l?n`<div class="message ${l.type}">${l.text}</div>`:""}function Q(l,e,t){l.dispatchEvent(new CustomEvent("register-command",{bubbles:!0,composed:!0,detail:{componentId:e,commands:t}}))}let Y=!1;class A extends _{constructor(){super(),this.apiBase="/api",this._loading=!0,this._empty=!1,this._cy=null,this._elements=null,this._resizeObserver=null}connectedCallback(){super.connectedCallback(),this._fetchData()}disconnectedCallback(){super.disconnectedCallback(),this._cy&&(this._cy.destroy(),this._cy=null),this._resizeObserver&&(this._resizeObserver.disconnect(),this._resizeObserver=null)}async _fetchData(){this._loading=!0;try{const e=await y(this.apiBase,`{
        transforms { id sourceDuckdbSchema sourceDuckdbTable targetDuckdbSchema targetDuckdbTable sourcePlugin enabled }
        dependencies
      }`),t=this.allPlugins||{};this._buildElements(t.pipe||[],t.schema||[],(e==null?void 0:e.transforms)||[],this.schemaPlugins||{},t.component||[],(e==null?void 0:e.dependencies)||{})}catch(e){console.error("Failed to fetch overview data:",e)}this._loading=!1}_buildElements(e,t,s,a,i,r){const o=[],p=new Set,h={};for(const[d,b]of Object.entries(a))for(const k of b)h[k]=d;for(const d of e){const b=`pipe:${d.name}`;p.add(b),o.push({data:{id:b,label:d.display_name||d.name,kind:"pipe",enabled:d.enabled!==!1?"yes":"no"}})}for(const d of t){const b=`schema:${d.name}`;p.add(b),o.push({data:{id:b,label:d.display_name||d.name,kind:"schema",enabled:d.enabled!==!1?"yes":"no"}})}for(const d of i){const b=`component:${d.name}`;p.add(b),o.push({data:{id:b,label:d.display_name||d.name,kind:"component",enabled:d.enabled!==!1?"yes":"no"}})}for(const d of s){const b=`pipe:${d.source_plugin}`,k=h[d.target_duckdb_table],T=k?`schema:${k}`:null;if(!T||!p.has(b)||!p.has(T))continue;const $=d.description||`${d.source_duckdb_table} -> ${d.target_duckdb_table}`,w=$.length>30?$.slice(0,28)+"...":$;o.push({data:{id:`transform:${d.id}`,source:b,target:T,label:w,enabled:d.enabled?"yes":"no",sourcePlugin:d.source_plugin,edgeType:"transform"}})}const m=new Set;for(const d of o)d.data.edgeType==="transform"&&m.add(`${d.data.source}:${d.data.target}`);const f=new Set;for(const[d,b]of Object.entries(r))for(const k of b){const T=d.split(":")[0];let $,w;if(T==="component"?($=k,w=d):($=d,w=k),!p.has($)||!p.has(w)||T==="pipe"&&m.has(`${$}:${w}`))continue;const z=`dep:${$}:${w}`;f.has(z)||(f.add(z),o.push({data:{id:z,source:$,target:w,edgeType:"dependency"}}))}this._elements=o,this._empty=o.filter(d=>d.data.source).length===0}_initCytoscape(){const e=this.renderRoot.querySelector("#cy");!e||!this._elements||(Y||(G.use(se),Y=!0),this._cy&&this._cy.destroy(),this._cy=G({container:e,elements:this._elements,style:[{selector:"node",style:{label:"data(label)","text-valign":"center","text-halign":"center","font-size":12,color:"#fff","text-wrap":"wrap","text-max-width":100,width:120,height:40,shape:"round-rectangle"}},{selector:'node[kind="pipe"]',style:{"background-color":"#4a90d9",cursor:"pointer"}},{selector:'node[kind="schema"]',style:{"background-color":"#66bb6a",cursor:"pointer"}},{selector:'node[kind="component"]',style:{"background-color":"#ffa726",cursor:"pointer"}},{selector:'node[enabled="no"]',style:{opacity:.4,"border-width":2,"border-color":"#999","border-style":"dashed"}},{selector:"edge",style:{"curve-style":"bezier","target-arrow-shape":"triangle","target-arrow-color":"#999","line-color":"#999",cursor:"pointer",width:2,label:"data(label)","font-size":9,color:"#888","text-rotation":"autorotate","text-margin-y":-8}},{selector:'edge[enabled="yes"]',style:{"line-style":"solid"}},{selector:'edge[enabled="no"]',style:{"line-style":"dashed","line-color":"#ccc","target-arrow-color":"#ccc",opacity:.5}},{selector:'edge[edgeType="dependency"]',style:{"line-style":"dotted","line-color":"#bbb","target-arrow-color":"#bbb",width:1.5,label:""}}],layout:{name:"dagre",rankDir:"LR",nodeSep:60,rankSep:150,padding:30},userZoomingEnabled:!0,userPanningEnabled:!0,boxSelectionEnabled:!1}),this._cy.on("tap","node",t=>{const s=t.target.data(),a=s.id.substring(s.id.indexOf(":")+1);let i;if(s.kind==="pipe")i=`/settings/pipe/${a}`;else if(s.kind==="schema")i=`/settings/schema/${a}`;else if(s.kind==="component")i=`/settings/component/${a}`;else return;this.dispatchEvent(new CustomEvent("navigate",{bubbles:!0,composed:!0,detail:{path:i}}))}),this._cy.on("tap","edge",t=>{const s=t.target.data("sourcePlugin");s&&this.dispatchEvent(new CustomEvent("navigate",{bubbles:!0,composed:!0,detail:{path:`/settings/pipe/${s}`}}))}),this._resizeObserver&&this._resizeObserver.disconnect(),this._resizeObserver=new ResizeObserver(()=>{this._cy&&(this._cy.resize(),this._cy.fit(void 0,30))}),this._resizeObserver.observe(e))}firstUpdated(){!this._loading&&this._elements&&this._initCytoscape()}updated(e){e.has("_loading")&&!this._loading&&this._elements&&requestAnimationFrame(()=>this._initCytoscape())}render(){return n`
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
    `}}c(A,"properties",{apiBase:{type:String,attribute:"api-base"},allPlugins:{type:Object},schemaPlugins:{type:Object},_loading:{state:!0},_empty:{state:!0}}),c(A,"styles",[I,g`
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
    `]);customElements.define("shenas-pipeline-overview",A);class F extends _{constructor(){super(),this.apiBase="/api",this.pipeName="",this._fields=[],this._instructions="",this._loading=!0,this._message=null,this._needsMfa=!1,this._oauthUrl=null,this._submitting=!1,this._stored=[]}willUpdate(e){e.has("pipeName")&&this._fetchFields()}async _fetchFields(){if(!this.pipeName)return;this._loading=!0,this._needsMfa=!1,this._oauthUrl=null;const e=await y(this.apiBase,"query($pipe: String!) { authFields(pipe: $pipe) { fields { name prompt hide } instructions stored } }",{pipe:this.pipeName});e!=null&&e.authFields&&(this._fields=e.authFields.fields||[],this._instructions=e.authFields.instructions||"",this._stored=e.authFields.stored||[]),this._loading=!1}async _submit(){var a,i;this._submitting=!0,this._message=null;const e={};if(this._needsMfa){const r=this.renderRoot.querySelector("#mfa-code");e.mfa_code=((a=r==null?void 0:r.value)==null?void 0:a.trim())||""}else if(this._oauthUrl)e.auth_complete="true";else for(const r of this._fields){const o=this.renderRoot.querySelector(`#field-${r.name}`),p=(i=o==null?void 0:o.value)==null?void 0:i.trim();p&&(e[r.name]=p)}const{data:t}=await u(this.apiBase,"mutation($pipe: String!, $creds: JSON!) { authenticate(pipe: $pipe, credentials: $creds) { ok message error needsMfa oauthUrl } }",{pipe:this.pipeName,creds:e});this._submitting=!1;const s=t==null?void 0:t.authenticate;s!=null&&s.ok?(this._message={type:"success",text:s.message},this._needsMfa=!1,this._oauthUrl=null,this._fetchFields()):s!=null&&s.needsMfa?(this._needsMfa=!0,this._message={type:"success",text:"MFA code required"}):s!=null&&s.oauthUrl?(this._oauthUrl=s.oauthUrl,this._message={type:"success",text:s.message}):(this._message={type:"error",text:(s==null?void 0:s.error)||"Authentication failed"},this._needsMfa=!1,this._oauthUrl=null)}render(){const e=this._fields.length===0&&!this._instructions;return n`
      <shenas-page ?loading=${this._loading} ?empty=${e}
        loading-text="Loading auth..." empty-text="No authentication required for this plugin.">
        ${D(this._message)}
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
    `}}c(F,"properties",{apiBase:{type:String,attribute:"api-base"},pipeName:{type:String,attribute:"pipe-name"},_fields:{state:!0},_instructions:{state:!0},_loading:{state:!0},_message:{state:!0},_needsMfa:{state:!0},_oauthUrl:{state:!0},_submitting:{state:!0},_stored:{state:!0}}),c(F,"styles",[x,P,C,g`
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
    `]);customElements.define("shenas-auth",F);const v=class v extends _{constructor(){super(),this.apiBase="/api",this.kind="",this.name="",this._config=null,this._loading=!0,this._message=null,this._editing=null,this._editValue="",this._freqNum="",this._freqUnit="hours"}willUpdate(e){(e.has("kind")||e.has("name"))&&this._fetchConfig()}async _fetchConfig(){if(!this.kind||!this.name)return;this._loading=!0;const e=await y(this.apiBase,"query($kind: String, $name: String) { config(kind: $kind, name: $name) { kind name entries { key label value description } } }",{kind:this.kind,name:this.name}),t=(e==null?void 0:e.config)||[];this._config=t.length>0?t[0]:null,this._loading=!1}_startEdit(e,t){if(this._editing=e,this._editValue=t||"",v._DURATION_FIELDS.has(e)&&t){const s=parseFloat(t);s>=1440&&s%1440===0?(this._freqNum=String(s/1440),this._freqUnit="days"):s>=60&&s%60===0?(this._freqNum=String(s/60),this._freqUnit="hours"):s>=1?(this._freqNum=String(s),this._freqUnit="minutes"):(this._freqNum=String(s*60),this._freqUnit="seconds")}else v._DURATION_FIELDS.has(e)&&(this._freqNum="",this._freqUnit="hours")}_cancelEdit(){this._editing=null,this._editValue=""}_freqToMinutes(){const e=parseFloat(this._freqNum);return isNaN(e)||e<=0?null:String(Math.round(e*v._UNIT_MULTIPLIERS[this._freqUnit]))}_formatFreq(e){const t=parseFloat(e);return isNaN(t)?e:t>=1440&&t%1440===0?`${t/1440} day${t/1440!==1?"s":""}`:t>=60&&t%60===0?`${t/60} hour${t/60!==1?"s":""}`:t>=1?`${t} minute${t!==1?"s":""}`:`${t*60} second${t*60!==1?"s":""}`}async _saveEdit(e){const t=v._DURATION_FIELDS.has(e)?this._freqToMinutes():this._editValue;if(v._DURATION_FIELDS.has(e)&&t===null){this._message={type:"error",text:"Enter a positive number"};return}const{ok:s,data:a}=await u(this.apiBase,"mutation($kind: String!, $name: String!, $key: String!, $value: String!) { setConfig(kind: $kind, name: $name, key: $key, value: $value) { ok } }",{kind:this.kind,name:this.name,key:e,value:t});s?(this._message={type:"success",text:`Updated ${e}`},this._editing=null,await this._fetchConfig()):this._message={type:"error",text:(a==null?void 0:a.detail)||"Update failed"}}render(){var t;const e=!this._config||this._config.entries.length===0;return n`
      <shenas-page ?loading=${this._loading} ?empty=${e}
        loading-text="Loading config..." empty-text="No configuration settings for this plugin.">
        ${D(this._message)}
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
          ${Object.keys(v._UNIT_MULTIPLIERS).map(t=>n`
            <option value=${t} ?selected=${this._freqUnit===t}>${t}</option>
          `)}
        </select>
        <button @click=${()=>this._saveEdit(e.key)}>Save</button>
        <button @click=${this._cancelEdit}>Cancel</button>
      </div>`}_renderEntry(e){const t=this._editing===e.key,s=v._DURATION_FIELDS.has(e.key),a=s&&e.value?this._formatFreq(e.value):e.value;return n`
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
    `}};c(v,"properties",{apiBase:{type:String,attribute:"api-base"},kind:{type:String},name:{type:String},_config:{state:!0},_loading:{state:!0},_message:{state:!0},_editing:{state:!0},_editValue:{state:!0},_freqNum:{state:!0},_freqUnit:{state:!0}}),c(v,"styles",[x,P,C,g`
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
    `]),c(v,"_UNIT_MULTIPLIERS",{seconds:1/60,minutes:1,hours:60,days:1440}),c(v,"_DURATION_FIELDS",new Set(["sync_frequency","lookback_period"]));let M=v;customElements.define("shenas-config",M);function le(l){if(!l)return null;const e=l.split("+").map(t=>t.trim().toLowerCase());return{ctrl:e.includes("ctrl")||e.includes("cmd"),shift:e.includes("shift"),alt:e.includes("alt"),key:e.filter(t=>!["ctrl","cmd","shift","alt"].includes(t))[0]||""}}function de(l){const e=[];(l.ctrlKey||l.metaKey)&&e.push("Ctrl"),l.shiftKey&&e.push("Shift"),l.altKey&&e.push("Alt");const t=l.key.length===1?l.key.toUpperCase():l.key;return["Control","Shift","Alt","Meta"].includes(l.key)||e.push(t),e.join("+")}function ce(l,e){const t=le(e);return!t||!t.key?!1:(l.ctrlKey||l.metaKey)===t.ctrl&&l.shiftKey===t.shift&&l.altKey===t.alt&&l.key.toLowerCase()===t.key}const S=[{id:"pipe",label:"Pipes"},{id:"schema",label:"Schemas"},{id:"component",label:"Components"},{id:"ui",label:"UI"},{id:"theme",label:"Themes"}];class U extends _{constructor(){super(),this.apiBase="/api",this.actions=[],this._bindings={},this._recording=null,this._recordedKey="",this._conflict=null,this._loading=!0,this._filter=""}connectedCallback(){super.connectedCallback(),this._loadBindings(),this._boundKeydown=e=>this._onKeydown(e),document.addEventListener("keydown",this._boundKeydown,!0)}disconnectedCallback(){super.disconnectedCallback(),document.removeEventListener("keydown",this._boundKeydown,!0)}async _loadBindings(){this._loading=!0;const e=await y(this.apiBase,"{ hotkeys }");this._bindings=(e==null?void 0:e.hotkeys)||{},this._loading=!1}async _saveBinding(e,t){t?await u(this.apiBase,"mutation($id: String!, $b: String!) { setHotkey(actionId: $id, binding: $b) { ok } }",{id:e,b:t}):await u(this.apiBase,"mutation($id: String!) { deleteHotkey(actionId: $id) { ok } }",{id:e}),this.dispatchEvent(new CustomEvent("hotkeys-changed",{bubbles:!0,composed:!0}))}_startRecording(e){this._recording=e,this._recordedKey="",this._conflict=null}_stopRecording(){this._recording=null,this._recordedKey="",this._conflict=null}_onKeydown(e){if(!this._recording)return;if(e.preventDefault(),e.stopPropagation(),e.key==="Escape"){this._stopRecording();return}if(["Control","Shift","Alt","Meta"].includes(e.key))return;const t=de(e);this._recordedKey=t;const s=Object.entries(this._bindings).find(([a,i])=>i===t&&a!==this._recording);this._conflict=s?s[0]:null}async _applyRecording(){!this._recordedKey||!this._recording||(this._conflict&&(this._bindings={...this._bindings,[this._conflict]:""},await this._saveBinding(this._conflict,"")),this._bindings={...this._bindings,[this._recording]:this._recordedKey},await this._saveBinding(this._recording,this._recordedKey),this._stopRecording())}async _clearBinding(e){this._bindings={...this._bindings,[e]:""},await this._saveBinding(e,"")}async _resetDefaults(){await u(this.apiBase,"mutation { resetHotkeys { ok } }"),await this._loadBindings(),this.dispatchEvent(new CustomEvent("hotkeys-changed",{bubbles:!0,composed:!0}))}_getActionLabel(e){const t=this.actions.find(s=>s.id===e);return t?t.label:e}_getActionCategory(e){const t=this.actions.find(s=>s.id===e);return t?t.category:""}render(){if(this._loading)return n`<p class="loading">Loading hotkeys...</p>`;const e=this._filter.toLowerCase(),t=this.actions.filter(s=>!e||s.label.toLowerCase().includes(e)||s.category.toLowerCase().includes(e));return n`
      <div class="toolbar">
        <button @click=${this._resetDefaults}>Reset to Defaults</button>
        <input class="filter-input" type="text" placeholder="Filter actions..."
          .value=${this._filter} @input=${s=>{this._filter=s.target.value}} />
      </div>
      ${t.map(s=>this._renderRow(s.id,s.label,s.category))}
    `}_renderRow(e,t,s){const a=this._bindings[e]||"",i=this._recording===e,r=this._conflict?this._getActionLabel(this._conflict):"";return n`
      <div class="hotkey-row">
        <span class="hotkey-category">${s}</span>
        <span class="hotkey-label">${t}</span>
        <span class="hotkey-binding">
          ${i?n`
              <span class="recording">${this._recordedKey||"Press a key..."}</span>
              ${this._conflict?n`<span class="conflict">Conflicts with ${r}</span>`:""}
              <button @click=${this._applyRecording} ?disabled=${!this._recordedKey}>Save</button>
              <button @click=${this._stopRecording}>Cancel</button>
            `:n`
              ${a?n`<span class="kbd">${a}</span>`:n`<span class="unbound">-</span>`}
              <button class="edit-btn" @click=${()=>this._startRecording(e)}>Edit</button>
              ${a?n`<button class="edit-btn" @click=${()=>this._clearBinding(e)}>Clear</button>`:""}
            `}
        </span>
      </div>
    `}}c(U,"properties",{apiBase:{type:String,attribute:"api-base"},actions:{type:Array},_bindings:{state:!0},_recording:{state:!0},_recordedKey:{state:!0},_conflict:{state:!0},_loading:{state:!0},_filter:{state:!0}}),c(U,"styles",[x,C,I,g`
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
    `]);customElements.define("shenas-hotkeys",U);class K extends _{constructor(){super(),this.apiBase="/api",this._activeTab="logs",this._logs=[],this._spans=[],this._loading=!0,this._search="",this._severity="",this._expanded=null,this._live=!1,this._logSource=null,this._spanSource=null}connectedCallback(){super.connectedCallback(),this.dispatchEvent(new CustomEvent("page-title",{bubbles:!0,composed:!0,detail:{title:"Logs"}})),this._fetchBoth(),this._connectStreams()}disconnectedCallback(){super.disconnectedCallback(),this._disconnectStreams(),clearTimeout(this._searchTimer)}_connectStreams(){const e=this.apiBase.startsWith("http")?this.apiBase:`${location.origin}${this.apiBase}`;this._logSource=new EventSource(`${e}/stream/logs`),this._logSource.onmessage=t=>{try{const s=JSON.parse(t.data);this._logs=[s,...this._logs].slice(0,500)}catch{}},this._logSource.onopen=()=>{this._live=!0},this._logSource.onerror=()=>{this._live=!1},this._spanSource=new EventSource(`${e}/stream/spans`),this._spanSource.onmessage=t=>{try{const s=JSON.parse(t.data);this._spans=[s,...this._spans].slice(0,500)}catch{}}}_disconnectStreams(){this._logSource&&(this._logSource.close(),this._logSource=null),this._spanSource&&(this._spanSource.close(),this._spanSource=null),this._live=!1}_logsSql(e=""){const t=[];return this._severity&&t.push(`severity = '${this._severity}'`),this._search&&t.push(`body LIKE '%${this._search}%'`),this.pipe&&t.push(`(body LIKE '%${this.pipe}%' OR attributes LIKE '%${this.pipe}%')`),e&&t.push(e),`SELECT timestamp, trace_id, span_id, severity, body, attributes, service_name FROM telemetry.logs${t.length?` WHERE ${t.join(" AND ")}`:""} ORDER BY timestamp DESC LIMIT 100`}_spansSql(){const e=[];return this._search&&e.push(`name LIKE '%${this._search}%'`),this.pipe&&e.push(`(name LIKE '%${this.pipe}%' OR attributes LIKE '%${this.pipe}%')`),`SELECT trace_id, span_id, parent_span_id, name, kind, service_name, status_code, start_time, end_time, duration_ms, attributes FROM telemetry.spans${e.length?` WHERE ${e.join(" AND ")}`:""} ORDER BY start_time DESC LIMIT 100`}async _fetchBoth(){this._loading=!0;try{const[e,t]=await Promise.all([E(this.apiBase,this._logsSql()),E(this.apiBase,this._spansSql())]);e&&(this._logs=e),t&&(this._spans=t)}catch{}this._loading=!1}async _fetch(){this._loading=!0,this._expanded=null;try{this._activeTab==="logs"?this._logs=await E(this.apiBase,this._logsSql())||[]:this._spans=await E(this.apiBase,this._spansSql())||[]}catch{}this._loading=!1}_onSearch(e){this._search=e.target.value,clearTimeout(this._searchTimer),this._searchTimer=setTimeout(()=>this._fetch(),300)}_switchTab(e){this._activeTab=e,this._expanded=null,this._fetch()}_toggleExpand(e){this._expanded=this._expanded===e?null:e}render(){const e=this._activeTab==="logs"?this._logs:this._spans;return n`
      <div class="tabs">
        <button class="tab ${this._activeTab==="logs"?"active":""}" @click=${()=>this._switchTab("logs")}>
          Logs
        </button>
        <button class="tab ${this._activeTab==="spans"?"active":""}" @click=${()=>this._switchTab("spans")}>
          Spans
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
    `}_formatTime(e){if(!e)return"-";const t=typeof e=="number"?new Date(e):new Date(String(e).endsWith("Z")?e:e+"Z");if(isNaN(t))return String(e);const s=(a,i=2)=>String(a).padStart(i,"0");return`${t.getFullYear()}-${s(t.getMonth()+1)}-${s(t.getDate())} ${s(t.getHours())}:${s(t.getMinutes())}:${s(t.getSeconds())}`}}c(K,"properties",{apiBase:{type:String,attribute:"api-base"},pipe:{type:String},_activeTab:{state:!0},_logs:{state:!0},_spans:{state:!0},_loading:{state:!0},_search:{state:!0},_severity:{state:!0},_expanded:{state:!0},_live:{state:!0}}),c(K,"styles",[x,I,g`
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
    `]);customElements.define("shenas-logs",K);class j extends _{constructor(){super();c(this,"_router",new ae(this,[{path:"/",render:()=>this._renderDynamicHome()},{path:"/settings",render:()=>this._renderSettings("data-flow")},{path:"/settings/:kind",render:({kind:t})=>this._renderSettings(t)},{path:"/settings/:kind/:name",render:({kind:t,name:s})=>this._renderPluginDetail(t,s)},{path:"/settings/:kind/:name/config",render:({kind:t,name:s})=>this._renderPluginDetail(t,s,"config")},{path:"/settings/:kind/:name/auth",render:({kind:t,name:s})=>this._renderPluginDetail(t,s,"auth")},{path:"/settings/:kind/:name/data",render:({kind:t,name:s})=>this._renderPluginDetail(t,s,"data")},{path:"/settings/:kind/:name/logs",render:({kind:t,name:s})=>this._renderPluginDetail(t,s,"logs")},{path:"/logs",render:()=>n`<shenas-logs api-base="${this.apiBase}"></shenas-logs>`},{path:"/:tab",render:({tab:t})=>this._renderDynamicTab(t)}]));c(this,"_hotkeys",{});c(this,"_pluginDisplayNames",{});c(this,"_nextTabId",1);c(this,"_saveWorkspaceTimer",null);c(this,"_allPlugins",{});this.apiBase="/api",this._components=[],this._loading=!0,this._loadedScripts=new Set,this._elementCache=new Map,this._leftWidth=160,this._rightWidth=220,this._dbStatus=null,this._inspectTable=null,this._inspectRows=null,this._paletteOpen=!1,this._paletteCommands=[],this._navPaletteOpen=!1,this._navCommands=[],this._registeredCommands=new Map,this._tabs=[],this._activeTabId=null}connectedCallback(){super.connectedCallback(),this._fetchData(),this.addEventListener("plugin-state-changed",()=>this._refreshComponents()),this.addEventListener("inspect-table",t=>this._inspect(t.detail.schema,t.detail.table)),this.addEventListener("page-title",t=>{this._activeTabId!=null&&(this._tabs=this._tabs.map(s=>s.id===this._activeTabId?{...s,label:t.detail.title}:s))}),this.addEventListener("navigate",t=>this._navigateTo(t.detail.path,t.detail.label)),this.addEventListener("register-command",t=>{const{componentId:s,commands:a}=t.detail;!a||a.length===0?this._registeredCommands.delete(s):this._registeredCommands.set(s,a)}),this._keyHandler=t=>{for(const[s,a]of Object.entries(this._hotkeys))if(a&&ce(t,a))for(const i of this._registeredCommands.values()){const r=i.find(o=>o.id===s);if(r&&r.action){t.preventDefault(),r.action();return}}},document.addEventListener("keydown",this._keyHandler),this.addEventListener("hotkeys-changed",()=>this._loadHotkeys())}disconnectedCallback(){super.disconnectedCallback(),document.removeEventListener("keydown",this._keyHandler)}async _loadHotkeys(){const t=await y(this.apiBase,"{ hotkeys }");this._hotkeys=(t==null?void 0:t.hotkeys)||{}}_togglePalette(){if(this._paletteOpen){this._paletteOpen=!1;return}this._navPaletteOpen=!1,this._buildCommands(),this._paletteOpen=!0}async _toggleNavPalette(){if(this._navPaletteOpen){this._navPaletteOpen=!1;return}this._paletteOpen=!1,await this._buildNavCommands(),this._navPaletteOpen=!0}async _buildNavCommands(){const t=[];for(const a of this._components)t.push({id:`nav:${a.name}`,category:"Page",label:a.display_name||a.name,path:`/${a.name}`});t.push({id:"nav:dataflow",category:"Settings",label:"Data Flow",path:"/settings/data-flow"});for(const a of S)t.push({id:`nav:settings:${a.id}`,category:"Settings",label:a.label,path:`/settings/${a.id}`});const s=S.flatMap(a=>(this._allPlugins[a.id]||[]).map(i=>({...i,display_name:i.displayName,kind:a.id,kindLabel:a.label})));for(const a of s)t.push({id:`nav:${a.kind}:${a.name}`,category:a.kindLabel,label:a.display_name||a.name,path:`/settings/${a.kind}/${a.name}`});this._navCommands=t}async _registerGlobalCommands(){const t=[],s={};try{const a=this._schemaPlugins||{};for(const i of S){const r=this._allPlugins[i.id]||[];for(const o of r){const p=o.displayName||o.name;s[`${i.id}:${o.name}`]=p;const h=o.enabled!==!1;t.push({id:`toggle:${i.id}:${o.name}`,category:i.label,label:`Toggle ${p}`,action:async()=>{const m=h?"mutation($k: String!, $n: String!) { disablePlugin(kind: $k, name: $n) { ok } }":"mutation($k: String!, $n: String!) { enablePlugin(kind: $k, name: $n) { ok } }";await u(this.apiBase,m,{k:i.id,n:o.name}),await this._fetchData()}}),i.id==="pipe"&&h&&(t.push({id:`sync:${o.name}`,category:"Pipe",label:`Sync ${p}`,action:()=>fetch(`${this.apiBase}/sync/${o.name}`,{method:"POST"})}),t.push({id:`transform:pipe:${o.name}`,category:"Transform",label:`Run Transforms: ${p}`,action:()=>u(this.apiBase,"mutation($pipe: String!) { runPipeTransforms(pipe: $pipe) }",{pipe:o.name})}))}}t.push({id:"sync:all",category:"Pipe",label:"Sync All Pipes",action:()=>fetch(`${this.apiBase}/sync`,{method:"POST"})}),t.push({id:"seed:transforms",category:"Transform",label:"Seed Default Transforms",action:()=>u(this.apiBase,"mutation { seedTransforms }")});for(const i of this._allPlugins.schema||[]){const r=a[i.name]||[];for(const o of r)t.push({id:`transform:schema:${o}`,category:"Transform",label:`Run Transforms -> ${i.displayName||i.name}: ${o}`,action:()=>u(this.apiBase,"mutation($schema: String!) { runSchemaTransforms(schema: $schema) }",{schema:o})})}}catch{}this._pluginDisplayNames=s,t.push({id:"command-palette",category:"System",label:"Command Palette",action:()=>this._togglePalette()},{id:"navigation-palette",category:"System",label:"Navigation Palette",action:()=>this._toggleNavPalette()},{id:"close-tab",category:"System",label:"Close Tab",action:()=>{this._activeTabId!=null&&this._closeTab(this._activeTabId)}},{id:"new-tab",category:"System",label:"New Tab",action:()=>this._addTab()}),this._registeredCommands.set("global",t)}_buildCommands(){const t=[];for(const s of this._registeredCommands.values())t.push(...s);this._paletteCommands=t}_executePaletteCommand(t){const s=t.detail;s.path?this._openTab(s.path,s.label):s.action&&s.action(),this._paletteOpen=!1,this._navPaletteOpen=!1}_navigateTo(t,s){if(this._tabs.length===0||!this._activeTabId){this._openTab(t,s);return}const a=s||this._labelForPath(t);this._tabs=this._tabs.map(i=>i.id===this._activeTabId?{...i,path:t,label:a}:i),window.history.pushState({},"",t),this._router.goto(t),this._saveWorkspace()}_openTab(t,s){const a=this._nextTabId++;this._tabs=[...this._tabs,{id:a,path:t,label:s||this._labelForPath(t)}],this._activeTabId=a,window.history.pushState({},"",t),this._router.goto(t),this._saveWorkspace()}async _addTab(){await this._buildNavCommands(),this._navPaletteOpen=!0}_closeTab(t){const s=this._tabs.findIndex(i=>i.id===t);if(s===-1)return;const a=this._tabs.filter(i=>i.id!==t);if(this._tabs=a,this._activeTabId===t)if(a.length>0){const i=a[Math.min(s,a.length-1)];this._activeTabId=i.id,this._router.goto(i.path)}else this._activeTabId=null,window.history.pushState({},"","/");this._saveWorkspace()}_switchTab(t){const s=this._tabs.find(a=>a.id===t);s&&(this._activeTabId=t,window.history.pushState({},"",s.path),this._router.goto(s.path),this._saveWorkspace())}_saveWorkspace(){clearTimeout(this._saveWorkspaceTimer),this._saveWorkspaceTimer=setTimeout(()=>{const t={tabs:this._tabs,activeTabId:this._activeTabId,nextTabId:this._nextTabId};u(this.apiBase,"mutation($data: JSON!) { saveWorkspace(data: $data) { ok } }",{data:t}).catch(()=>{})},300)}async _loadWorkspace(){try{const t=await y(this.apiBase,"{ workspace }"),s=t==null?void 0:t.workspace;if(!s)return;if(s.tabs&&s.tabs.length>0){this._tabs=s.tabs,this._activeTabId=s.activeTabId||s.tabs[0].id,this._nextTabId=s.nextTabId||Math.max(...s.tabs.map(r=>r.id))+1;const a=window.location.pathname;if(a&&a!=="/"&&!this._tabs.some(r=>r.path===a)){this._openTab(a);return}const i=this._tabs.find(r=>r.id===this._activeTabId);i&&this._router.goto(i.path)}else{const a=window.location.pathname;a&&a!=="/"&&this._openTab(a)}}catch{const t=window.location.pathname;t&&t!=="/"&&this._openTab(t)}}_labelForPath(t){const s=t.replace(/^\/+/,"");if(!s||s==="settings"||s==="settings/data-flow")return"Data Flow";const a=s.split("/");if(a[0]==="settings"){if(a.length===2){const r=S.find(o=>o.id===a[1]);return r?r.label:a[1]}if(a.length>=3){const r=`${a[1]}:${a[2]}`;return this._pluginDisplayNames[r]||a[2]}}const i=this._components.find(r=>r.name===a[0]);return i?i.display_name||i.name:a[0]}async _refreshComponents(){const t=await y(this.apiBase,"{ components }");this._components=(t==null?void 0:t.components)||[]}async _fetchData(){var t;this._loading=!0;try{const s=await y(this.apiBase,`{
        components
        hotkeys
        workspace
        dbStatus { keySource dbPath sizeMb schemas { name tables { name rows cols earliest latest } } }
        pipes: plugins(kind: "pipe") { name displayName enabled }
        schemas: plugins(kind: "schema") { name displayName enabled }
        componentPlugins: plugins(kind: "component") { name displayName enabled }
        uis: plugins(kind: "ui") { name displayName enabled }
        themes: plugins(kind: "theme") { name displayName enabled }
        schemaPlugins
      }`);this._components=(s==null?void 0:s.components)||[],this._dbStatus=s==null?void 0:s.dbStatus,this._hotkeys=(s==null?void 0:s.hotkeys)||{},this._allPlugins={pipe:(s==null?void 0:s.pipes)||[],schema:(s==null?void 0:s.schemas)||[],component:(s==null?void 0:s.componentPlugins)||[],ui:(s==null?void 0:s.uis)||[],theme:(s==null?void 0:s.themes)||[]},this._schemaPlugins=(s==null?void 0:s.schemaPlugins)||{};const a=s==null?void 0:s.workspace;if(((t=a==null?void 0:a.tabs)==null?void 0:t.length)>0){this._tabs=a.tabs,this._activeTabId=a.activeTabId||a.tabs[0].id,this._nextTabId=a.nextTabId||Math.max(...a.tabs.map(r=>r.id))+1;const i=window.location.pathname;if(i&&i!=="/"&&!this._tabs.some(r=>r.path===i))this._openTab(i);else{const r=this._tabs.find(o=>o.id===this._activeTabId);r&&this._router.goto(r.path)}}else{const i=window.location.pathname;i&&i!=="/"&&this._openTab(i)}}catch(s){console.error("Failed to fetch data:",s)}await this._registerGlobalCommands(),this._loading=!1}_activeTab(){var s,a;const t=this._tabs.find(i=>i.id===this._activeTabId);return((a=(s=t==null?void 0:t.path)==null?void 0:s.replace(/^\/+/,""))==null?void 0:a.split("/")[0])||(this._components.length>0?this._components[0].name:"settings")}_activePath(){const t=this._tabs.find(s=>s.id===this._activeTabId);return(t==null?void 0:t.path)||window.location.pathname}_startDrag(t){return s=>{s.preventDefault();const a=s.clientX,i=t==="left"?this._leftWidth:this._rightWidth,r=s.target;r.classList.add("dragging");const o=h=>{const m=t==="left"?h.clientX-a:a-h.clientX,f=Math.max(80,Math.min(400,i+m));t==="left"?this._leftWidth=f:this._rightWidth=f},p=()=>{r.classList.remove("dragging"),window.removeEventListener("mousemove",o),window.removeEventListener("mouseup",p)};window.addEventListener("mousemove",o),window.addEventListener("mouseup",p)}}render(){var a;if(this._loading)return n`<shenas-page loading></shenas-page>`;const t=this._activeTab(),s=this._activePath();return s.startsWith("/settings")&&this._settingsOpen===void 0&&(this._settingsOpen=!0),n`
      <div class="layout">
        <div class="panel-left" style="width: ${this._leftWidth}px">
          <div class="header">
            <img src="/static/images/shenas.svg" alt="shenas" />
          </div>
          <nav class="nav">
            ${this._components.map(i=>this._navItem(i.name,i.display_name||i.name,t))}
            ${this._navItem("logs","Logs",t)}
            <a class="nav-link settings-toggle" @click=${()=>{this._settingsOpen=!this._settingsOpen}}>
              Settings
              <span class="chevron ${this._settingsOpen?"open":""}">&rsaquo;</span>
            </a>
            ${this._settingsOpen?n`
              <div class="settings-sub">
                ${this._settingsNavItem("data-flow","Data Flow",s)}
                ${this._settingsNavItem("hotkeys","Hotkeys",s)}
                <span class="sub-heading">Plugins</span>
                ${S.map(({id:i,label:r})=>n`
                  ${this._settingsNavItem(i,`${r} (${(this._allPlugins[i]||[]).length})`,s)}
                `)}
              </div>
            `:""}
          </nav>
        </div>
        <div class="divider" @mousedown=${this._startDrag("left")}></div>
        <div class="panel-middle">
          ${this._tabs.length>0?n`
              <div class="tab-bar">
                ${this._tabs.map(i=>n`
                  <div class="tab-item ${i.id===this._activeTabId?"active":""}"
                    @click=${()=>this._switchTab(i.id)}>
                    <span>${i.label}</span>
                    <button class="tab-close" @click=${r=>{r.stopPropagation(),this._closeTab(i.id)}}>x</button>
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
                <img src="/static/images/shenas.svg" alt="shenas" />
                <p>Open a page from the sidebar</p>
              </div>`}
        </div>
        <div class="divider" @mousedown=${this._startDrag("right")}></div>
        <div class="panel-right" style="width: ${this._rightWidth}px">
          ${this._inspectTable?this._renderInspect():this._renderDbStats()}
        </div>
        <div class="bottom-nav">
          <nav>
            ${this._components.map(i=>n`
              <a class="nav-item" href="/${i.name}" @click=${r=>{r.preventDefault(),this._navigateTo(`/${i.name}`)}}
                aria-selected=${(t==null?void 0:t.path)===`/${i.name}`}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/></svg>
                <span>${i.display_name||i.name}</span>
              </a>
            `)}
            <a class="nav-item" href="/logs" @click=${i=>{i.preventDefault(),this._navigateTo("/logs")}}
              aria-selected=${(t==null?void 0:t.path)==="/logs"}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
              <span>Logs</span>
            </a>
            <a class="nav-item" href="/settings" @click=${i=>{i.preventDefault(),this._navigateTo("/settings")}}
              aria-selected=${(a=t==null?void 0:t.path)==null?void 0:a.startsWith("/settings")}>
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
    `}_settingsNavItem(t,s,a){const i=`/settings/${t}`,r=a===i||a.startsWith(i+"/");return n`
      <a class="nav-sub-item" href="${i}" aria-selected=${r}
        @click=${o=>{o.preventDefault(),o.ctrlKey||o.metaKey?this._openTab(i,s):this._navigateTo(i,s)}}>
        ${s}
      </a>
    `}_renderDynamicHome(){return this._components.length>0?this._renderDynamicTab(this._components[0].name):this._renderSettings("pipe")}_renderDynamicTab(t){const s=this._components.find(a=>a.name===t);if(!s)return n`<p class="empty">Unknown page: ${t}</p>`;if(!this._loadedScripts.has(s.js)){this._loadedScripts=new Set([...this._loadedScripts,s.js]);const a=document.createElement("script");a.type="module",a.src=s.js,document.head.appendChild(a)}return n`<div class="component-host">
      ${this._getOrCreateElement(s)}
    </div>`}_renderPluginDetail(t,s,a="details"){return n`<shenas-plugin-detail
      api-base="${this.apiBase}"
      kind="${t}"
      name="${s}"
      active-tab="${a}"
      .dbStatus=${this._dbStatus}
      .schemaPlugins=${this._schemaPlugins}
    ></shenas-plugin-detail>`}_getAllActions(){const t=new Set,s=[];for(const a of this._registeredCommands.values())for(const i of a)!t.has(i.id)&&i.action&&(t.add(i.id),s.push({id:i.id,label:i.label,category:i.category}));return s.sort((a,i)=>a.category==="System"&&i.category!=="System"?-1:a.category!=="System"&&i.category==="System"?1:0),s}_renderSettings(t){return n`<shenas-settings
      api-base="${this.apiBase}"
      active-kind="${t||"data-flow"}"
      .allActions=${this._getAllActions()}
      .allPlugins=${this._allPlugins}
      .schemaPlugins=${this._schemaPlugins}
      .onNavigate=${s=>{this._navigateTo(`/settings/${s}`)}}
    ></shenas-settings>`}async _inspect(t,s){if(!/^[a-zA-Z_]\w*$/.test(t)||!/^[a-zA-Z_]\w*$/.test(s))return;const a=`${t}.${s}`;if(this._inspectTable===a){this._inspectTable=null,this._inspectRows=null;return}this._inspectTable=a,this._inspectRows=null;try{this._inspectRows=await E(this.apiBase,`SELECT * FROM "${t}"."${s}" ORDER BY 1 DESC LIMIT 50`)||[]}catch{this._inspectRows=[]}}_renderDbStats(){const t=this._dbStatus;return t?n`
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
    `}_getOrCreateElement(t){if(!this._elementCache.has(t.name)){const s=document.createElement(t.tag);s.setAttribute("api-base",this.apiBase),this._elementCache.set(t.name,s)}return this._elementCache.get(t.name)}}c(j,"properties",{apiBase:{type:String,attribute:"api-base"},_components:{state:!0},_loading:{state:!0},_loadedScripts:{state:!0},_leftWidth:{state:!0},_rightWidth:{state:!0},_dbStatus:{state:!0},_inspectTable:{state:!0},_inspectRows:{state:!0},_paletteOpen:{state:!0},_paletteCommands:{state:!0},_navPaletteOpen:{state:!0},_settingsOpen:{state:!0},_navCommands:{state:!0},_tabs:{state:!0},_activeTabId:{state:!0}}),c(j,"styles",[R,I,g`
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
        width: 120px;
        height: 120px;
        border-radius: 12px;
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
      .settings-toggle {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.5rem 0.8rem;
        font-size: 0.9rem;
        color: var(--shenas-text-secondary, #666);
        text-decoration: none;
        border-radius: 4px;
        cursor: pointer;
      }
      .settings-toggle:hover {
        background: var(--shenas-bg-hover, #f5f5f5);
        color: var(--shenas-text, #222);
      }
      .chevron {
        transition: transform 0.15s;
        font-size: 1.1rem;
      }
      .chevron.open {
        transform: rotate(90deg);
      }
      .settings-sub {
        padding-left: 0.5rem;
      }
      .nav-sub-item {
        display: block;
        padding: 0.35rem 0.8rem;
        font-size: 0.82rem;
        color: var(--shenas-text-secondary, #666);
        text-decoration: none;
        border-radius: 4px;
        cursor: pointer;
      }
      .nav-sub-item:hover {
        background: var(--shenas-bg-hover, #f5f5f5);
        color: var(--shenas-text, #222);
      }
      .nav-sub-item[aria-selected="true"] {
        background: var(--shenas-bg-selected, #f0f4ff);
        color: var(--shenas-text, #222);
        font-weight: 600;
      }
      .sub-heading {
        display: block;
        padding: 0.4rem 0.8rem 0.2rem;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--shenas-text-faint, #aaa);
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
    `]);customElements.define("shenas-app",j);class W extends _{constructor(){super(),this.apiBase="/api",this.activeKind="data-flow",this.onNavigate=null,this._plugins={},this._loading=!0,this._actionMessage=null,this._installing=!1,this._menuOpen=!1}connectedCallback(){super.connectedCallback(),this._fetchAll()}async _fetchAll(){if(this.allPlugins&&Object.keys(this.allPlugins).length>0){this._plugins=this.allPlugins,this._loading=!1;return}this._loading=!0;const e={};await Promise.all(S.map(async({id:t})=>{const s=await y(this.apiBase,"query($kind: String!) { plugins(kind: $kind) { name displayName package version enabled description } }",{kind:t});e[t]=(s==null?void 0:s.plugins)||[]})),this._plugins=e,this._loading=!1}async _togglePlugin(e,t,s){const a=s?"disable":"enable",i=a==="enable"?"mutation($k: String!, $n: String!) { enablePlugin(kind: $k, name: $n) { ok message } }":"mutation($k: String!, $n: String!) { disablePlugin(kind: $k, name: $n) { ok message } }",{data:r}=await u(this.apiBase,i,{k:e,n:t}),o=a==="enable"?r==null?void 0:r.enablePlugin:r==null?void 0:r.disablePlugin;o!=null&&o.ok||(this._actionMessage={type:"error",text:(o==null?void 0:o.message)||`${a} failed`}),e==="theme"&&await this._applyActiveTheme(),await this._fetchAll()}async _applyActiveTheme(){const e=await y(this.apiBase,"{ theme { css } }");if(!(e!=null&&e.theme))return;const{css:t}=e.theme;let s=document.querySelector("link[data-shenas-theme]");t?(s||(s=document.createElement("link"),s.rel="stylesheet",s.setAttribute("data-shenas-theme",""),document.head.appendChild(s)),s.href=t):s&&s.remove()}async _install(e){var r,o,p;const t=this.shadowRoot.querySelector(`#install-${e}`),s=(r=t==null?void 0:t.value)==null?void 0:r.trim();if(!s)return;this._actionMessage=null;const{data:a}=await u(this.apiBase,"mutation($kind: String!, $names: [String!]!) { installPlugins(kind: $kind, names: $names, skipVerify: true) { results { name ok message } } }",{kind:e,names:[s]}),i=(p=(o=a==null?void 0:a.installPlugins)==null?void 0:o.results)==null?void 0:p[0];i!=null&&i.ok?(this._actionMessage={type:"success",text:i.message},this._installing=!1,await this._fetchAll()):this._actionMessage={type:"error",text:(i==null?void 0:i.message)||"Install failed"}}_switchKind(e){this.activeKind=e,this._menuOpen=!1,this.onNavigate&&this.onNavigate(e)}_displayName(){if(this.activeKind==="data-flow")return"Data Flow";if(this.activeKind==="hotkeys")return"Hotkeys";const e=S.find(t=>t.id===this.activeKind);return e?e.label:this.activeKind}render(){return n`
      <shenas-page ?loading=${this._loading} loading-text="Loading plugins..." display-name="${this._displayName()}">
        ${D(this._actionMessage)}
        ${this.activeKind==="data-flow"?n`<shenas-pipeline-overview api-base="${this.apiBase}" .allPlugins=${this.allPlugins} .schemaPlugins=${this.schemaPlugins}></shenas-pipeline-overview>`:this.activeKind==="hotkeys"?n`<shenas-hotkeys api-base="${this.apiBase}" .actions=${this.allActions||[]}></shenas-hotkeys>`:this._renderKind(this.activeKind)}
      </shenas-page>
    `}_formatFreq(e){return e>=1440&&e%1440===0?`${e/1440}d`:e>=60&&e%60===0?`${e/60}h`:e>=1?`${e}m`:`${e*60}s`}_renderKind(e){var a;const t=this._plugins[e]||[],s=((a=S.find(i=>i.id===e))==null?void 0:a.label)||e;return n`
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
    `}}c(W,"properties",{apiBase:{type:String,attribute:"api-base"},activeKind:{type:String,attribute:"active-kind"},onNavigate:{type:Function},allActions:{type:Array},allPlugins:{type:Object},schemaPlugins:{type:Object},_plugins:{state:!0},_loading:{state:!0},_actionMessage:{state:!0},_installing:{state:!0},_menuOpen:{state:!0}}),c(W,"styles",[x,P,R,C,g`
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
    `]);customElements.define("shenas-settings",W);class H extends _{constructor(){super(),this.apiBase="/api",this.kind="",this.name="",this.activeTab="details",this._info=null,this._loading=!0,this._message=null,this._tables=[],this._syncing=!1,this._schemaTransforms=[],this._selectedTable=null,this._previewRows=null,this._previewLoading=!1}willUpdate(e){(e.has("kind")||e.has("name"))&&this._fetchInfo()}async _fetchInfo(){var p;if(!this.kind||!this.name)return;this._loading=!0,this._message=null;const t=["pluginInfo(kind: $kind, name: $name)",this.kind==="schema"?"transforms { id sourceDuckdbSchema sourceDuckdbTable targetDuckdbSchema targetDuckdbTable sourcePlugin description enabled }":""].filter(Boolean).join(" "),s=await y(this.apiBase,`query($kind: String!, $name: String!) { ${t} }`,{kind:this.kind,name:this.name});this._info=s==null?void 0:s.pluginInfo;const a=this.dbStatus,i=this.schemaPlugins,r=(p=s==null?void 0:s.transforms)==null?void 0:p.map(h=>({...h,source_duckdb_schema:h.sourceDuckdbSchema,source_duckdb_table:h.sourceDuckdbTable,target_duckdb_schema:h.targetDuckdbSchema,target_duckdb_table:h.targetDuckdbTable,source_plugin:h.sourcePlugin})),o=i?i[this.name]||[]:[];if(a){if(this.kind==="pipe"){const h=(a.schemas||[]).find(m=>m.name===this.name);this._tables=h?h.tables.filter(m=>!m.name.startsWith("_dlt_")):[]}else if(this.kind==="schema"){const h=(a.schemas||[]).find(m=>m.name==="metrics");this._tables=h?h.tables.filter(m=>o.includes(m.name)):[]}}r&&(this._schemaTransforms=r.filter(h=>o.includes(h.target_duckdb_table))),this._loading=!1,this._registerCommands()}_registerCommands(){if(!this._info)return;const e=this._info.display_name||this.name,t=[{id:`remove:${this.kind}:${this.name}`,category:"Plugin",label:`Remove ${e}`,action:()=>this._remove()}];this.kind==="schema"&&t.unshift({id:`flush:${this.kind}:${this.name}`,category:"Plugin",label:`Flush ${e}`,action:()=>this._flush()},{id:`transform:${this.kind}:${this.name}`,category:"Plugin",label:`Transform ${e}`,action:()=>this._runTransforms()}),Q(this,`plugin-detail:${this.kind}:${this.name}`,t)}async _toggle(){var i;const e=((i=this._info)==null?void 0:i.enabled)!==!1?"disable":"enable",t=e==="enable"?"mutation($k: String!, $n: String!) { enablePlugin(kind: $k, name: $n) { ok message } }":"mutation($k: String!, $n: String!) { disablePlugin(kind: $k, name: $n) { ok message } }",{data:s}=await u(this.apiBase,t,{k:this.kind,n:this.name}),a=e==="enable"?s==null?void 0:s.enablePlugin:s==null?void 0:s.disablePlugin;this._message={type:a!=null&&a.ok?"success":"error",text:(a==null?void 0:a.message)||`${e} failed`},await this._fetchInfo(),this.dispatchEvent(new CustomEvent("plugin-state-changed",{bubbles:!0,composed:!0}))}async _sync(){this._syncing=!0,this._message=null;try{const e=await fetch(`${this.apiBase}/sync/${this.name}`,{method:"POST"});if(!e.ok){const p=await e.json().catch(()=>({}));this._message={type:"error",text:p.detail||`Sync failed (${e.status})`},this._syncing=!1;return}const t=e.body.getReader(),s=new TextDecoder;let a="",i="",r=!1;for(;;){const{done:p,value:h}=await t.read();if(p)break;const m=s.decode(h,{stream:!0});for(const f of m.split(`
`))f.startsWith("event: ")&&(a=f.slice(7).trim()),f.startsWith("data: ")&&(i=f.slice(6));a==="error"&&(r=!0)}let o="Sync complete";try{o=JSON.parse(i).message||o}catch{}this._message={type:r?"error":"success",text:o},r||await this._fetchInfo()}catch(e){this._message={type:"error",text:`Sync failed: ${e.message}`}}this._syncing=!1}async _runTransforms(){this._transforming=!0,this._message=null;try{const{data:e}=await u(this.apiBase,"mutation($s: String!) { runSchemaTransforms(schema: $s) }",{s:this.name}),t=e==null?void 0:e.runSchemaTransforms;(t==null?void 0:t.count)!=null?(this._message={type:"success",text:`Ran ${t.count} transform(s)`},await this._fetchInfo()):this._message={type:"error",text:"Transform failed"}}catch(e){this._message={type:"error",text:`Transform failed: ${e.message}`}}this._transforming=!1}async _flush(){this._message=null;try{const{data:e}=await u(this.apiBase,"mutation($s: String!) { flushSchema(schemaPlugin: $s) }",{s:this.name}),t=e==null?void 0:e.flushSchema;(t==null?void 0:t.rows_deleted)!=null?(this._message={type:"success",text:`Flushed ${t.rows_deleted} rows`},await this._fetchInfo()):this._message={type:"error",text:"Flush failed"}}catch(e){this._message={type:"error",text:`Flush failed: ${e.message}`}}}async _remove(){var t,s;const{data:e}=await u(this.apiBase,"mutation($k: String!, $n: String!) { removePlugin(kind: $k, name: $n) { ok message } }",{k:this.kind,n:this.name});(t=e==null?void 0:e.removePlugin)!=null&&t.ok?(window.history.pushState({},"",`/settings/${this.kind}`),window.dispatchEvent(new PopStateEvent("popstate"))):this._message={type:"error",text:((s=e==null?void 0:e.removePlugin)==null?void 0:s.message)||"Remove failed"}}_switchTab(e){this.activeTab=e;const t=`/settings/${this.kind}/${this.name}`,s=e==="details"?t:`${t}/${e}`;window.history.pushState({},"",s)}async _fetchPreview(e){if(this._selectedTable=e,!e){this._previewRows=null;return}this._previewLoading=!0;const t=this.kind==="schema"?"metrics":this.name;this._previewRows=await E(this.apiBase,`SELECT * FROM "${t}"."${e}" ORDER BY 1 DESC LIMIT 100`),this._previewLoading=!1}_renderData(){var t,s;const e=this._tables||[];if(e.length===0)return n`<p style="color:var(--shenas-text-muted,#888)">No tables synced yet.</p>`;if(!this._selectedTable){const a=(t=this._info)==null?void 0:t.primary_table,i=a&&e.some(r=>r.name===a)?a:(s=e[0])==null?void 0:s.name;i&&this._fetchPreview(i)}return n`
      <div class="data-toolbar">
        <select @change=${a=>this._fetchPreview(a.target.value)}>
          <option value="">Select a table</option>
          ${e.map(a=>n`<option value=${a.name} ?selected=${this._selectedTable===a.name}>${a.name}${a.rows?` (${a.rows})`:""}</option>`)}
        </select>
        ${this._previewLoading?n`<span style="color:var(--shenas-text-muted,#888)">Loading...</span>`:""}
      </div>
      ${this._previewRows&&this._previewRows.length>0?n`
        <table class="data-table">
          <thead><tr>${Object.keys(this._previewRows[0]).map(a=>n`<th>${a}</th>`)}</tr></thead>
          <tbody>${this._previewRows.map(a=>n`
            <tr>${Object.values(a).map(i=>n`<td title="${i??""}">${i??""}</td>`)}</tr>
          `)}</tbody>
        </table>
      `:this._selectedTable&&!this._previewLoading?n`<p style="color:var(--shenas-text-muted,#888)">Table is empty.</p>`:""}
    `}render(){var e,t;return n`
      <shenas-page ?loading=${this._loading} ?empty=${!this._info} empty-text="Plugin not found."
        display-name="${((e=this._info)==null?void 0:e.display_name)||((t=this._info)==null?void 0:t.name)||this.name}">
        ${this._info?this._renderContent():""}
      </shenas-page>
    `}_renderContent(){var a;const e=this._info,t=e.enabled!==!1,s=`/settings/${this.kind}/${this.name}`;return n`
      <a class="back" href="/settings/${this.kind}">&larr; Back to ${this.kind}s</a>

      <div class="title-row">
        <h2>${e.display_name||e.name} <span class="kind-badge">${e.kind}</span>${e.version?n` <span class="version">${e.version}</span>`:""}</h2>
        <div class="title-actions">
          ${this.kind==="pipe"&&t?n`<button @click=${this._sync} ?disabled=${this._syncing}>${this._syncing?"Syncing...":"Sync"}</button>`:""}
          ${this.kind==="schema"?n`<button @click=${this._runTransforms} ?disabled=${this._transforming}>${this._transforming?"Transforming...":"Transform"}</button>`:""}
          ${this.kind==="schema"?n`<button class="danger" @click=${this._flush}>Flush</button>`:""}
          <button class="danger" @click=${this._remove}>Remove</button>
        </div>
      </div>

      ${D(this._message)}

      <div class="tabs">
        <a class="tab" href="${s}" aria-selected=${this.activeTab==="details"}
          @click=${i=>{i.preventDefault(),this._switchTab("details")}}>Details</a>
        ${(a=this._info)!=null&&a.has_config?n`
          <a class="tab" href="${s}/config" aria-selected=${this.activeTab==="config"}
            @click=${i=>{i.preventDefault(),this._switchTab("config")}}>Config</a>
        `:""}
        ${this.kind==="pipe"?n`
          <a class="tab" href="${s}/auth" aria-selected=${this.activeTab==="auth"}
            @click=${i=>{i.preventDefault(),this._switchTab("auth")}}>Auth</a>
        `:""}
        <a class="tab" href="${s}/data" aria-selected=${this.activeTab==="data"}
          @click=${i=>{i.preventDefault(),this._switchTab("data")}}>Data</a>
        <a class="tab" href="${s}/logs" aria-selected=${this.activeTab==="logs"}
          @click=${i=>{i.preventDefault(),this._switchTab("logs")}}>Logs</a>
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
    `:""}}c(H,"properties",{apiBase:{type:String,attribute:"api-base"},kind:{type:String},name:{type:String},activeTab:{type:String,attribute:"active-tab"},dbStatus:{type:Object},schemaPlugins:{type:Object},_info:{state:!0},_loading:{state:!0},_message:{state:!0},_tables:{state:!0},_syncing:{state:!0},_transforming:{state:!0},_schemaTransforms:{state:!0},_selectedTable:{state:!0},_previewRows:{state:!0},_previewLoading:{state:!0}}),c(H,"styles",[x,R,C,ie,g`
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
    `]);customElements.define("shenas-plugin-detail",H);const Z="background:none;border:none;cursor:pointer;color:var(--shenas-text-faint, #aaa);font-size:0.7rem;padding:0 2px";class V extends _{constructor(){super(),this.apiBase="/api",this.source="",this._transforms=[],this._loading=!0,this._editing=null,this._editSql="",this._message=null,this._previewRows=null,this._creating=!1,this._newForm=this._emptyForm(),this._dbTables={},this._schemaTables={}}_emptyForm(){return{source_duckdb_table:"",target_duckdb_table:"",description:"",sql:""}}connectedCallback(){super.connectedCallback(),this._fetchAll()}async _fetchAll(){this._loading=!0,this.source&&`${this.source}`;const e=await y(this.apiBase,"query($source: String) { transforms(source: $source) { id sourceDuckdbSchema sourceDuckdbTable targetDuckdbSchema targetDuckdbTable sourcePlugin description sql isDefault enabled } }",{source:this.source||null});this._transforms=((e==null?void 0:e.transforms)||[]).map(t=>({id:t.id,source_duckdb_schema:t.sourceDuckdbSchema,source_duckdb_table:t.sourceDuckdbTable,target_duckdb_schema:t.targetDuckdbSchema,target_duckdb_table:t.targetDuckdbTable,source_plugin:t.sourcePlugin,description:t.description,sql:t.sql,is_default:t.isDefault,enabled:t.enabled})),this._loading=!1,this._registerCommands()}_registerCommands(){const e=[];for(const t of this._transforms){const s=t.description||`${t.source_duckdb_table} -> ${t.target_duckdb_table}`;e.push({id:`transform:toggle:${t.id}`,category:"Transform",label:`${t.enabled?"Disable":"Enable"} #${t.id}`,description:s,action:()=>this._toggle(t)}),t.is_default||e.push({id:`transform:delete:${t.id}`,category:"Transform",label:`Delete #${t.id}`,description:s,action:()=>this._delete(t)})}Q(this,`transforms:${this.source}`,e)}_inspectTable(e,t){this.dispatchEvent(new CustomEvent("inspect-table",{bubbles:!0,composed:!0,detail:{schema:e,table:t}}))}async _toggle(e){const t=e.enabled?"mutation($id: Int!) { disableTransform(transformId: $id) { id enabled } }":"mutation($id: Int!) { enableTransform(transformId: $id) { id enabled } }";await u(this.apiBase,t,{id:e.id}),await this._fetchAll()}async _delete(e){var a;const{ok:t,data:s}=await u(this.apiBase,"mutation($id: Int!) { deleteTransform(transformId: $id) { ok message } }",{id:e.id});t&&((a=s==null?void 0:s.deleteTransform)!=null&&a.ok)?(this._message={type:"success",text:`Deleted transform #${e.id}`},await this._fetchAll()):this._message={type:"error",text:"Delete failed"}}_startEdit(e){this._editing=e.id,this._editSql=e.sql,this._previewRows=null}_cancelEdit(){this._editing=null,this._editSql="",this._previewRows=null}async _saveEdit(){const{ok:e}=await u(this.apiBase,"mutation($id: Int!, $sql: String!) { updateTransform(transformId: $id, sql: $sql) { id } }",{id:this._editing,sql:this._editSql});e?(this._message={type:"success",text:"Transform updated"},this._editing=null,await this._fetchAll()):this._message={type:"error",text:"Update failed"}}async _startCreate(){this._creating=!0,this._newForm=this._emptyForm(),this._editing=null,this._previewRows=null;const e=await y(this.apiBase,"{ dbTables schemaTables }");this._dbTables=(e==null?void 0:e.dbTables)||{},this._schemaTables=(e==null?void 0:e.schemaTables)||{}}_cancelCreate(){this._creating=!1,this._newForm=this._emptyForm()}_updateNewForm(e,t){this._newForm={...this._newForm,[e]:t}}async _saveCreate(){const e=this._newForm;if(!e.source_duckdb_table||!e.target_duckdb_table||!e.sql){this._message={type:"error",text:"Fill in all required fields"};return}const{ok:t,data:s}=await u(this.apiBase,"mutation($input: TransformCreateInput!) { createTransform(transformInput: $input) { id } }",{input:{sourceDuckdbSchema:this.source,sourceDuckdbTable:e.source_duckdb_table,targetDuckdbSchema:"metrics",targetDuckdbTable:e.target_duckdb_table,sourcePlugin:this.source,description:e.description,sql:e.sql}});t?(this._message={type:"success",text:"Transform created"},this._creating=!1,this._newForm=this._emptyForm(),await this._fetchAll()):this._message={type:"error",text:(s==null?void 0:s.detail)||"Create failed"}}async _preview(){const{ok:e,data:t}=await u(this.apiBase,"mutation($id: Int!) { testTransform(transformId: $id, limit: 5) }",{id:this._editing});e?this._previewRows=t==null?void 0:t.testTransform:this._message={type:"error",text:(t==null?void 0:t.detail)||"Preview failed"}}render(){return n`
      <shenas-page ?loading=${this._loading} loading-text="Loading transforms...">
      ${D(this._message)}
      ${this._editing?this._renderEditor():""}
      ${this._creating?this._renderCreateForm():""}
      <shenas-data-list
        ?show-add=${!this._creating&&!this._editing}
        @add=${this._startCreate}
        .columns=${[{key:"id",label:"ID",class:"muted"},{label:"Source",class:"mono",render:e=>n`${e.source_duckdb_schema}.${e.source_duckdb_table} <button style=${Z} title="Inspect table" @click=${()=>this._inspectTable(e.source_duckdb_schema,e.source_duckdb_table)}>&#9655;</button>`},{label:"Target",class:"mono",render:e=>n`${e.target_duckdb_schema}.${e.target_duckdb_table} <button style=${Z} title="Inspect table" @click=${()=>this._inspectTable(e.target_duckdb_schema,e.target_duckdb_table)}>&#9655;</button>`},{label:"Description",render:e=>n`${e.description||""}${e.is_default?n`<span style="font-size:0.75rem;color:var(--shenas-text-muted, #888);background:var(--shenas-border-light, #f0f0f0);padding:1px 5px;border-radius:3px;margin-left:4px">default</span>`:""}`},{label:"Status",render:e=>n`<status-toggle ?enabled=${e.enabled} toggleable @toggle=${()=>this._toggle(e)}></status-toggle>`}]}
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
    `}}c(V,"properties",{apiBase:{type:String,attribute:"api-base"},source:{type:String},_transforms:{state:!0},_loading:{state:!0},_editing:{state:!0},_editSql:{state:!0},_message:{state:!0},_previewRows:{state:!0},_creating:{state:!0},_newForm:{state:!0},_dbTables:{state:!0},_schemaTables:{state:!0}}),c(V,"styles",[X,x,P,C,g`
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
    `]);customElements.define("shenas-transforms",V);
