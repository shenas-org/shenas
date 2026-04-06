var y=Object.defineProperty;var b=(a,e,t)=>e in a?y(a,e,{enumerable:!0,configurable:!0,writable:!0,value:t}):a[e]=t;var o=(a,e,t)=>b(a,typeof e!="symbol"?e+"":e,t);import{LitElement as p,css as m,html as i}from"lit";class c extends p{constructor(){super(),this.apiBase="/api",this._components=[],this._activeIndex=0,this._loading=!0,this._loadedScripts=new Set,this._hotkeys={},this._elementCache=new Map,this._paletteOpen=!1,this._paletteCommands=[],this._uis=[]}connectedCallback(){super.connectedCallback(),this._fetchData(),this._keyHandler=e=>this._onKeydown(e),document.addEventListener("keydown",this._keyHandler)}disconnectedCallback(){super.disconnectedCallback(),document.removeEventListener("keydown",this._keyHandler)}async _fetchData(){var e;this._loading=!0;try{const n=(await(await fetch(`${this.apiBase}/graphql`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({query:'{ components hotkeys theme { css } uis: plugins(kind: "frontend") { name displayName enabled } }'})})).json()).data;if(this._components=(n==null?void 0:n.components)||[],this._hotkeys=(n==null?void 0:n.hotkeys)||{},this._uis=(n==null?void 0:n.uis)||[],(e=n==null?void 0:n.theme)!=null&&e.css&&!document.querySelector("link[data-shenas-theme]")){const r=document.createElement("link");r.rel="stylesheet",r.setAttribute("data-shenas-theme",""),r.href=n.theme.css,document.head.appendChild(r)}}catch(t){console.error("Failed to fetch data:",t)}this._loading=!1,this._buildCommands()}_buildCommands(){const e=this._components.map((t,s)=>({id:`nav:${t.name}`,category:"Navigate",label:t.display_name||t.name,action:()=>{this._activeIndex=s}}));for(const t of this._uis){const s=t.displayName||t.name;e.push({id:`ui:${t.name}`,category:"Switch UI",label:`${s}${t.enabled?" (active)":""}`,action:()=>this._switchUI(t.name)})}e.push({id:"command-palette",category:"System",label:"Command Palette",action:()=>{this._paletteOpen=!0}}),this._paletteCommands=e}async _switchUI(e){await fetch(`${this.apiBase}/graphql`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({query:"mutation($k: String!, $n: String!) { enablePlugin(kind: $k, name: $n) { ok } }",variables:{k:"ui",n:e}})}),window.location.replace(window.location.pathname+"?_switch="+Date.now())}_onKeydown(e){if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="p"){e.preventDefault(),this._paletteOpen=!this._paletteOpen;return}if(e.ctrlKey||e.metaKey){const t=parseInt(e.key);if(t>=1&&t<=this._components.length){e.preventDefault(),this._activeIndex=t-1;return}}for(const[t,s]of Object.entries(this._hotkeys)){if(!s)continue;const n=s.split("+").map(l=>l.trim().toLowerCase()),r=n.includes("ctrl")||n.includes("cmd"),f=n.includes("shift"),_=n.includes("alt"),v=n.filter(l=>!["ctrl","cmd","shift","alt"].includes(l))[0]||"";if((e.ctrlKey||e.metaKey)===r&&e.shiftKey===f&&e.altKey===_&&e.key.toLowerCase()===v){e.preventDefault();const l=t.match(/^nav:(.+)$/);if(l){const u=this._components.findIndex(g=>g.name===l[1]);u>=0&&(this._activeIndex=u)}return}}}_getOrCreateElement(e){if(!this._elementCache.has(e.name)){const t=document.createElement(e.tag);t.setAttribute("api-base",this.apiBase),this._elementCache.set(e.name,t)}return this._elementCache.get(e.name)}_switchTo(e){this._activeIndex=e}render(){if(this._loading)return i`<div class="loading">Loading...</div>`;if(this._components.length===0)return i`<div class="empty">
        <p>No components installed.</p>
      </div>`;const e=this._components[this._activeIndex];if(e&&!this._loadedScripts.has(e.js)){this._loadedScripts=new Set([...this._loadedScripts,e.js]);const t=document.createElement("script");t.type="module",t.src=e.js,document.head.appendChild(t)}return i`
      <div class="content">
        ${e?i`<div class="component-host">${this._getOrCreateElement(e)}</div>`:""}
      </div>
      <shenas-job-panel></shenas-job-panel>
      <nav class="bottom-nav">
        ${this._components.map((t,s)=>i`
          <button class="nav-item" aria-selected=${s===this._activeIndex}
            @click=${()=>this._switchTo(s)}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/>
            </svg>
            <span>${t.display_name||t.name}</span>
            ${s<9?i`<span class="hotkey-hint">Ctrl+${s+1}</span>`:""}
          </button>
        `)}
      </nav>
      <shenas-command-palette
        ?open=${this._paletteOpen}
        .commands=${this._paletteCommands}
        @execute=${t=>{const s=t.detail;s.action&&s.action(),this._paletteOpen=!1}}
        @close=${()=>{this._paletteOpen=!1}}
      ></shenas-command-palette>
    `}}o(c,"properties",{apiBase:{type:String,attribute:"api-base"},_components:{state:!0},_activeIndex:{state:!0},_loading:{state:!0},_loadedScripts:{state:!0},_hotkeys:{state:!0},_paletteOpen:{state:!0},_paletteCommands:{state:!0},_uis:{state:!0}}),o(c,"styles",m`
    :host {
      display: flex;
      flex-direction: column;
      height: 100vh;
      background: var(--shenas-bg, #f5f1eb);
      color: var(--shenas-text, #222);
    }
    .content {
      flex: 1;
      overflow: auto;
      position: relative;
    }
    .component-host {
      width: 100%;
      height: 100%;
    }
    .loading {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100%;
      color: var(--shenas-text-muted, #888);
    }
    .empty {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100%;
      color: var(--shenas-text-muted, #888);
      flex-direction: column;
      gap: 0.5rem;
    }
    .bottom-nav {
      display: flex;
      justify-content: space-around;
      border-top: 1px solid var(--shenas-border, #e0e0e0);
      background: var(--shenas-bg, #fff);
      padding: 0.4rem 0;
      flex-shrink: 0;
    }
    .nav-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 2px;
      font-size: 0.65rem;
      padding: 0.3rem 0.8rem;
      border-radius: 6px;
      color: var(--shenas-text-muted, #888);
      text-decoration: none;
      cursor: pointer;
      background: none;
      border: none;
      transition: color 0.15s;
    }
    .nav-item:hover {
      color: var(--shenas-text-secondary, #666);
    }
    .nav-item[aria-selected="true"] {
      color: var(--shenas-accent, #728F67);
      font-weight: 600;
    }
    .nav-item svg {
      flex-shrink: 0;
    }
    .hotkey-hint {
      font-size: 0.5rem;
      color: var(--shenas-text-faint, #ccc);
      font-family: monospace;
    }
  `);customElements.define("shenas-focus",c);class d extends p{constructor(){super(),this._jobs=[],this._collapsed=!1}get _hasJobs(){return this._jobs.length>0}get _activeCount(){return this._jobs.filter(e=>e.status==="running").length}addJob(e,t){this._jobs=[...this._jobs,{id:e,label:t,status:"running",lines:[]}],this._collapsed=!1,this._scrollToBottom()}appendLine(e,t){this._jobs=this._jobs.map(s=>s.id===e?{...s,lines:[...s.lines,t]}:s),this._scrollToBottom()}finishJob(e,t,s){this._jobs=this._jobs.map(n=>n.id===e?{...n,status:t?"done":"error",message:s}:n)}_scrollToBottom(){requestAnimationFrame(()=>{var t;const e=(t=this.shadowRoot)==null?void 0:t.querySelector(".log-area");e&&(e.scrollTop=e.scrollHeight)})}_dismiss(e){this._jobs=this._jobs.filter(t=>t.id!==e)}_dismissAll(){this._jobs=this._jobs.filter(e=>e.status==="running")}render(){if(!this._hasJobs)return"";const e=this._jobs.filter(t=>t.status!=="running").length;return i`
      <div class="panel">
        <div class="header" @click=${()=>{this._collapsed=!this._collapsed}}>
          <span>
            Jobs
            ${this._activeCount>0?i`<span class="badge">${this._activeCount}</span>`:""}
          </span>
          <span>
            ${e>0?i`<button class="dismiss" @click=${t=>{t.stopPropagation(),this._dismissAll()}}>Clear</button>`:""}
            <span class="chevron ${this._collapsed?"":"up"}">\u25BC</span>
          </span>
        </div>
        ${this._collapsed?"":i`
          <div class="log-area">
            ${this._jobs.map(t=>i`
              <div class="job-group">
                <div class="job-label">
                  <span class="status">
                    ${t.status==="running"?i`<span class="spinning">\u25E0</span>`:t.status==="done"?"✓":"✗"}
                  </span>
                  ${t.label}
                  ${t.status!=="running"?i`<button class="dismiss" @click=${()=>this._dismiss(t.id)}>\u2715</button>`:""}
                </div>
                ${t.lines.map(s=>i`
                  <div class="line ${t.status==="error"?"error":""}">${s}</div>
                `)}
                ${t.message?i`
                  <div class="line ${t.status==="done"?"success":"error"}">${t.message}</div>
                `:""}
              </div>
            `)}
          </div>
        `}
      </div>
    `}}o(d,"properties",{_jobs:{state:!0},_collapsed:{state:!0}}),o(d,"styles",m`
    :host {
      display: block;
    }
    :host([hidden]) {
      display: none;
    }
    .panel {
      border-top: 1px solid var(--shenas-border, #e0e0e0);
      background: var(--shenas-bg, #fff);
      display: flex;
      flex-direction: column;
      max-height: 200px;
    }
    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.3rem 0.8rem;
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--shenas-text-secondary, #666);
      cursor: pointer;
      user-select: none;
      flex-shrink: 0;
    }
    .header:hover {
      background: var(--shenas-bg-hover, #f5f5f5);
    }
    .badge {
      background: var(--shenas-accent, #728F67);
      color: #fff;
      border-radius: 8px;
      padding: 0 0.4rem;
      font-size: 0.65rem;
      margin-left: 0.4rem;
    }
    .chevron {
      transition: transform 0.15s;
      font-size: 0.7rem;
    }
    .chevron.up {
      transform: rotate(180deg);
    }
    .log-area {
      overflow-y: auto;
      flex: 1;
      padding: 0 0.8rem 0.4rem;
      font-family: monospace;
      font-size: 0.75rem;
      line-height: 1.5;
      color: var(--shenas-text, #222);
    }
    .job-group {
      margin-bottom: 0.4rem;
    }
    .job-label {
      font-weight: 600;
      color: var(--shenas-text-secondary, #666);
      display: flex;
      align-items: center;
      gap: 0.4rem;
      padding: 0.15rem 0;
    }
    .job-label .status {
      font-size: 0.7rem;
    }
    .spinning {
      display: inline-block;
      animation: spin 1s linear infinite;
    }
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
    .line {
      color: var(--shenas-text-muted, #999);
      padding-left: 1rem;
      white-space: pre-wrap;
      word-break: break-all;
    }
    .line.error {
      color: var(--shenas-error, #c62828);
    }
    .line.success {
      color: var(--shenas-success, #2e7d32);
    }
    .dismiss {
      background: none;
      border: none;
      color: var(--shenas-text-muted, #999);
      cursor: pointer;
      font-size: 0.7rem;
      padding: 0.1rem 0.3rem;
    }
    .dismiss:hover {
      color: var(--shenas-text, #222);
    }
  `);customElements.define("shenas-job-panel",d);class h extends p{constructor(){super(),this.open=!1,this.commands=[],this._query="",this._filtered=[],this._selectedIndex=0}willUpdate(e){e.has("open")&&this.open&&(this._query="",this._selectedIndex=0,this._filter()),e.has("commands")&&this._filter()}updated(e){e.has("open")&&this.open&&requestAnimationFrame(()=>{const t=this.renderRoot.querySelector("input");t&&t.focus()})}_filter(){const e=this._query.toLowerCase();e?this._filtered=this.commands.filter(t=>t.label.toLowerCase().includes(e)||t.category.toLowerCase().includes(e)||(t.description||"").toLowerCase().includes(e)):this._filtered=this.commands,this._selectedIndex>=this._filtered.length&&(this._selectedIndex=Math.max(0,this._filtered.length-1))}_onInput(e){this._query=e.target.value,this._selectedIndex=0,this._filter()}_onKeydown(e){if(e.key==="ArrowDown")e.preventDefault(),this._filtered.length>0&&(this._selectedIndex=Math.min(this._selectedIndex+1,this._filtered.length-1)),this._scrollToSelected();else if(e.key==="ArrowUp")e.preventDefault(),this._selectedIndex=Math.max(this._selectedIndex-1,0),this._scrollToSelected();else if(e.key==="Enter"){e.preventDefault();const t=this._filtered[this._selectedIndex];t&&this._execute(t)}else e.key==="Escape"&&this._close()}_scrollToSelected(){requestAnimationFrame(()=>{const e=this.renderRoot.querySelector(".item.selected");e&&e.scrollIntoView({block:"nearest"})})}_execute(e){this.dispatchEvent(new CustomEvent("execute",{detail:e,bubbles:!0,composed:!0}))}_close(){this.dispatchEvent(new CustomEvent("close",{bubbles:!0,composed:!0}))}render(){return this.open?i`
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
          ${this._filtered.length===0?i`<div class="empty">No matching commands</div>`:this._filtered.map((e,t)=>i`
                  <div
                    class="item ${t===this._selectedIndex?"selected":""}"
                    @click=${()=>this._execute(e)}
                    @mouseenter=${()=>{this._selectedIndex=t}}
                  >
                    <span class="item-category">${e.category}</span>
                    <span class="item-label">${e.label}</span>
                    ${e.description?i`<span class="item-desc">${e.description}</span>`:""}
                  </div>
                `)}
        </div>
      </div>
    `:i``}}o(h,"properties",{open:{type:Boolean,reflect:!0},commands:{type:Array},_query:{state:!0},_filtered:{state:!0},_selectedIndex:{state:!0}}),o(h,"styles",m`
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
  `);customElements.define("shenas-command-palette",h);
