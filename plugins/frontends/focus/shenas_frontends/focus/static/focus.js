var f=Object.defineProperty;var _=(n,e,t)=>e in n?f(n,e,{enumerable:!0,configurable:!0,writable:!0,value:t}):n[e]=t;var c=(n,e,t)=>_(n,typeof e!="symbol"?e+"":e,t);import"shenas-frontends";import{LitElement as y,css as v,html as r}from"lit";class l extends y{constructor(){super(),this.apiBase="/api",this._dashboards=[],this._activeIndex=0,this._loading=!0,this._loadedScripts=new Set,this._hotkeys={},this._elementCache=new Map,this._paletteOpen=!1,this._paletteCommands=[],this._uis=[]}connectedCallback(){super.connectedCallback(),this._fetchData(),this._keyHandler=e=>this._onKeydown(e),document.addEventListener("keydown",this._keyHandler)}disconnectedCallback(){super.disconnectedCallback(),document.removeEventListener("keydown",this._keyHandler)}async _fetchData(){var e;this._loading=!0;try{const s=(await(await fetch(`${this.apiBase}/graphql`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({query:'{ dashboards hotkeys theme { css } uis: plugins(kind: "frontend") { name displayName enabled } }'})})).json()).data;if(this._dashboards=(s==null?void 0:s.dashboards)||[],this._hotkeys=(s==null?void 0:s.hotkeys)||{},this._uis=(s==null?void 0:s.uis)||[],(e=s==null?void 0:s.theme)!=null&&e.css&&!document.querySelector("link[data-shenas-theme]")){const i=document.createElement("link");i.rel="stylesheet",i.setAttribute("data-shenas-theme",""),i.href=s.theme.css,document.head.appendChild(i)}}catch(t){console.error("Failed to fetch data:",t)}this._loading=!1,this._buildCommands()}_buildCommands(){const e=this._dashboards.map((t,a)=>({id:`nav:${t.name}`,category:"Navigate",label:t.display_name||t.name,action:()=>{this._activeIndex=a}}));for(const t of this._uis){const a=t.displayName||t.name;e.push({id:`ui:${t.name}`,category:"Switch UI",label:`${a}${t.enabled?" (active)":""}`,action:()=>this._switchUI(t.name)})}e.push({id:"command-palette",category:"System",label:"Command Palette",action:()=>{this._paletteOpen=!0}}),this._paletteCommands=e}async _switchUI(e){await fetch(`${this.apiBase}/graphql`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({query:"mutation($k: String!, $n: String!) { enablePlugin(kind: $k, name: $n) { ok } }",variables:{k:"ui",n:e}})}),window.location.replace(window.location.pathname+"?_switch="+Date.now())}_onKeydown(e){if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="p"){e.preventDefault(),this._paletteOpen=!this._paletteOpen;return}if(e.ctrlKey||e.metaKey){const t=parseInt(e.key);if(t>=1&&t<=this._dashboards.length){e.preventDefault(),this._activeIndex=t-1;return}}for(const[t,a]of Object.entries(this._hotkeys)){if(!a)continue;const s=a.split("+").map(o=>o.trim().toLowerCase()),i=s.includes("ctrl")||s.includes("cmd"),h=s.includes("shift"),m=s.includes("alt"),p=s.filter(o=>!["ctrl","cmd","shift","alt"].includes(o))[0]||"";if((e.ctrlKey||e.metaKey)===i&&e.shiftKey===h&&e.altKey===m&&e.key.toLowerCase()===p){e.preventDefault();const o=t.match(/^nav:(.+)$/);if(o){const d=this._dashboards.findIndex(u=>u.name===o[1]);d>=0&&(this._activeIndex=d)}return}}}_getOrCreateElement(e){if(!this._elementCache.has(e.name)){const t=document.createElement(e.tag);t.setAttribute("api-base",this.apiBase),this._elementCache.set(e.name,t)}return this._elementCache.get(e.name)}_switchTo(e){this._activeIndex=e}render(){if(this._loading)return r`<div class="loading">Loading...</div>`;if(this._dashboards.length===0)return r`<div class="empty">
        <p>No dashboards installed.</p>
      </div>`;const e=this._dashboards[this._activeIndex];if(e&&!this._loadedScripts.has(e.js)){this._loadedScripts=new Set([...this._loadedScripts,e.js]);const t=document.createElement("script");t.type="module",t.src=e.js,document.head.appendChild(t)}return r`
      <div class="content">
        ${e?r`<div class="component-host">${this._getOrCreateElement(e)}</div>`:""}
      </div>
      <shenas-job-panel></shenas-job-panel>
      <nav class="bottom-nav">
        ${this._dashboards.map((t,a)=>r`
          <button class="nav-item" aria-selected=${a===this._activeIndex}
            @click=${()=>this._switchTo(a)}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/>
            </svg>
            <span>${t.display_name||t.name}</span>
            ${a<9?r`<span class="hotkey-hint">Ctrl+${a+1}</span>`:""}
          </button>
        `)}
      </nav>
      <shenas-command-palette
        ?open=${this._paletteOpen}
        .commands=${this._paletteCommands}
        @execute=${t=>{const a=t.detail;a.action&&a.action(),this._paletteOpen=!1}}
        @close=${()=>{this._paletteOpen=!1}}
      ></shenas-command-palette>
    `}}c(l,"properties",{apiBase:{type:String,attribute:"api-base"},_dashboards:{state:!0},_activeIndex:{state:!0},_loading:{state:!0},_loadedScripts:{state:!0},_hotkeys:{state:!0},_paletteOpen:{state:!0},_paletteCommands:{state:!0},_uis:{state:!0}}),c(l,"styles",v`
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
  `);customElements.define("shenas-focus",l);
