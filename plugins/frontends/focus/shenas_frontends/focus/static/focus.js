var f=Object.defineProperty;var y=(i,n,e)=>n in i?f(i,n,{enumerable:!0,configurable:!0,writable:!0,value:e}):i[n]=e;var l=(i,n,e)=>y(i,typeof n!="symbol"?n+"":n,e);import"shenas-frontends";import{LitElement as v,css as b,html as c}from"lit";class d extends v{constructor(){super();l(this,"_elementCache",new Map);l(this,"_keyHandler",null);this.apiBase="/api",this._dashboards=[],this._activeIndex=0,this._loading=!0,this._loadedScripts=new Set,this._hotkeys={},this._paletteOpen=!1,this._paletteCommands=[],this._uis=[]}connectedCallback(){super.connectedCallback(),this._fetchData(),this._keyHandler=e=>this._onKeydown(e),document.addEventListener("keydown",this._keyHandler)}disconnectedCallback(){super.disconnectedCallback(),this._keyHandler&&document.removeEventListener("keydown",this._keyHandler)}async _fetchData(){this._loading=!0;try{const s=(await(await fetch(`${this.apiBase}/graphql`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({query:'{ dashboards hotkeys theme { css } uis: plugins(kind: "frontend") { name displayName enabled } }'})})).json()).data;this._dashboards=(s==null?void 0:s.dashboards)||[],this._hotkeys=(s==null?void 0:s.hotkeys)||{},this._uis=(s==null?void 0:s.uis)||[];const a=s==null?void 0:s.theme;if(a!=null&&a.css&&!document.querySelector("link[data-shenas-theme]")){const o=document.createElement("link");o.rel="stylesheet",o.setAttribute("data-shenas-theme",""),o.href=a.css,document.head.appendChild(o)}}catch(e){console.error("Failed to fetch data:",e)}this._loading=!1,this._buildCommands()}_buildCommands(){const e=this._dashboards.map((t,s)=>({id:`nav:${t.name}`,category:"Navigate",label:t.display_name||t.name,action:()=>{this._activeIndex=s}}));for(const t of this._uis){const s=t.displayName||t.name;e.push({id:`ui:${t.name}`,category:"Switch UI",label:`${s}${t.enabled?" (active)":""}`,action:()=>this._switchUI(t.name)})}e.push({id:"command-palette",category:"System",label:"Command Palette",action:()=>{this._paletteOpen=!0}}),this._paletteCommands=e}async _switchUI(e){await fetch(`${this.apiBase}/graphql`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({query:"mutation($k: String!, $n: String!) { enablePlugin(kind: $k, name: $n) { ok } }",variables:{k:"ui",n:e}})}),window.location.replace(window.location.pathname+"?_switch="+Date.now())}_onKeydown(e){if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="p"){e.preventDefault(),this._paletteOpen=!this._paletteOpen;return}if(e.ctrlKey||e.metaKey){const t=parseInt(e.key);if(t>=1&&t<=this._dashboards.length){e.preventDefault(),this._activeIndex=t-1;return}}for(const[t,s]of Object.entries(this._hotkeys)){if(!s)continue;const a=s.split("+").map(r=>r.trim().toLowerCase()),o=a.includes("ctrl")||a.includes("cmd"),m=a.includes("shift"),p=a.includes("alt"),u=a.filter(r=>!["ctrl","cmd","shift","alt"].includes(r))[0]||"";if((e.ctrlKey||e.metaKey)===o&&e.shiftKey===m&&e.altKey===p&&e.key.toLowerCase()===u){e.preventDefault();const r=t.match(/^nav:(.+)$/);if(r){const h=this._dashboards.findIndex(_=>_.name===r[1]);h>=0&&(this._activeIndex=h)}return}}}_getOrCreateElement(e){if(!this._elementCache.has(e.name)){const t=document.createElement(e.tag);t.setAttribute("api-base",this.apiBase),this._elementCache.set(e.name,t)}return this._elementCache.get(e.name)}_switchTo(e){this._activeIndex=e}render(){if(this._loading)return c`<div class="loading">Loading...</div>`;if(this._dashboards.length===0)return c`<div class="empty">
        <p>No dashboards installed.</p>
      </div>`;const e=this._dashboards[this._activeIndex];if(e&&!this._loadedScripts.has(e.js)){this._loadedScripts=new Set([...this._loadedScripts,e.js]);const t=document.createElement("script");t.type="module",t.src=e.js,document.head.appendChild(t)}return c`
      <div class="content">
        ${e?c`<div class="component-host">${this._getOrCreateElement(e)}</div>`:""}
      </div>
      <shenas-job-panel></shenas-job-panel>
      <nav class="bottom-nav">
        ${this._dashboards.map((t,s)=>c`
          <button class="nav-item" aria-selected=${s===this._activeIndex}
            @click=${()=>this._switchTo(s)}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/>
            </svg>
            <span>${t.display_name||t.name}</span>
            ${s<9?c`<span class="hotkey-hint">Ctrl+${s+1}</span>`:""}
          </button>
        `)}
      </nav>
      <shenas-command-palette
        ?open=${this._paletteOpen}
        .commands=${this._paletteCommands}
        @execute=${t=>{const s=t.detail;s.action&&s.action(),this._paletteOpen=!1}}
        @close=${()=>{this._paletteOpen=!1}}
      ></shenas-command-palette>
    `}}l(d,"properties",{apiBase:{type:String,attribute:"api-base"},_dashboards:{state:!0},_activeIndex:{state:!0},_loading:{state:!0},_loadedScripts:{state:!0},_hotkeys:{state:!0},_paletteOpen:{state:!0},_paletteCommands:{state:!0},_uis:{state:!0}}),l(d,"styles",b`
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
  `);customElements.define("shenas-focus",d);
