var X=Object.defineProperty;var Y=(_,i,e)=>i in _?X(_,i,{enumerable:!0,configurable:!0,writable:!0,value:e}):_[i]=e;var h=(_,i,e)=>Y(_,typeof i!="symbol"?i+"":i,e);import{utilityStyles as O,gql as b,buttonStyles as P,formStyles as I,messageStyles as C,gqlFull as m,renderMessage as N,formatHotkey as Z,sortActions as B,arrowQuery as D,linkStyles as W,matchesHotkey as Q,PLUGIN_KINDS as E,tabStyles as ee,registerCommands as G,tableStyles as te}from"shenas-frontends";import{LitElement as x,css as T,html as n}from"lit";import H,{dagre as se}from"cytoscape";import{Router as ae}from"@lit-labs/router";let J=!1;class z extends x{constructor(){super();h(this,"_cy",null);h(this,"_elements",null);h(this,"_resizeObserver",null);this.apiBase="/api",this.allPlugins={},this.schemaPlugins={},this._loading=!0,this._empty=!1}connectedCallback(){super.connectedCallback(),this._fetchData()}disconnectedCallback(){super.disconnectedCallback(),this._cy&&(this._cy.destroy(),this._cy=null),this._resizeObserver&&(this._resizeObserver.disconnect(),this._resizeObserver=null)}async _fetchData(){this._loading=!0;try{const e=await b(this.apiBase,`{
        transforms { id sourceDuckdbSchema sourceDuckdbTable targetDuckdbSchema targetDuckdbTable sourcePlugin enabled }
        dependencies
      }`),t=this.allPlugins||{};this._buildElements(t.source||[],t.dataset||[],(e==null?void 0:e.transforms)||[],this.schemaPlugins||{},t.dashboard||[],(e==null?void 0:e.dependencies)||{},t.model||[])}catch(e){console.error("Failed to fetch overview data:",e)}this._loading=!1}_buildElements(e,t,s,a,r,o,d=[]){const c=[],p=new Set,f={};for(const[l,u]of Object.entries(a))for(const $ of u)f[$]=l;for(const l of e){const u=`pipe:${l.name}`;p.add(u),c.push({data:{id:u,label:l.displayName||l.name,kind:"source",enabled:l.enabled!==!1?"yes":"no"}})}for(const l of t){const u=`schema:${l.name}`;p.add(u),c.push({data:{id:u,label:l.displayName||l.name,kind:"dataset",enabled:l.enabled!==!1?"yes":"no"}})}for(const l of r){const u=`component:${l.name}`;p.add(u),c.push({data:{id:u,label:l.displayName||l.name,kind:"dashboard",enabled:l.enabled!==!1?"yes":"no"}})}for(const l of d){const u=`model:${l.name}`;p.add(u),c.push({data:{id:u,label:l.displayName||l.name,kind:"model",enabled:l.enabled!==!1?"yes":"no"}})}for(const l of s){const u=`pipe:${l.sourcePlugin}`,$=f[l.targetDuckdbTable],k=$?`schema:${$}`:null;if(!k||!p.has(u)||!p.has(k))continue;const w=l.description||`${l.sourceDuckdbTable} -> ${l.targetDuckdbTable}`,S=w.length>30?w.slice(0,28)+"...":w;c.push({data:{id:`transform:${l.id}`,source:u,target:k,label:S,enabled:l.enabled?"yes":"no",sourcePlugin:l.sourcePlugin,edgeType:"transform"}})}const y=new Set;for(const l of c)l.data.edgeType==="transform"&&y.add(`${l.data.source}:${l.data.target}`);const g=new Set;for(const[l,u]of Object.entries(o))for(const $ of u){const k=l.split(":")[0];let w,S;if(k==="dashboard"||k==="model"?(w=$,S=l):(w=l,S=$),!p.has(w)||!p.has(S)||k==="source"&&y.has(`${w}:${S}`))continue;const R=`dep:${w}:${S}`;g.has(R)||(g.add(R),c.push({data:{id:R,source:w,target:S,edgeType:"dependency"}}))}this._elements=c,this._empty=c.filter(l=>l.data.source).length===0}_initCytoscape(){const e=this.renderRoot.querySelector("#cy");!e||!this._elements||(J||(H.use(se),J=!0),this._cy&&this._cy.destroy(),this._cy=H({container:e,elements:this._elements,style:[{selector:"node",style:{label:"data(label)","text-valign":"center","text-halign":"center","font-size":12,color:"#fff","text-wrap":"wrap","text-max-width":100,width:120,height:40,shape:"round-rectangle"}},{selector:'node[kind="source"]',style:{"background-color":"#4a90d9",cursor:"pointer"}},{selector:'node[kind="dataset"]',style:{"background-color":"#66bb6a",cursor:"pointer"}},{selector:'node[kind="dashboard"]',style:{"background-color":"#ffa726",cursor:"pointer"}},{selector:'node[kind="model"]',style:{"background-color":"#ab47bc",cursor:"pointer"}},{selector:'node[enabled="no"]',style:{opacity:.4,"border-width":2,"border-color":"#999","border-style":"dashed"}},{selector:"edge",style:{"curve-style":"bezier","target-arrow-shape":"triangle","target-arrow-color":"#999","line-color":"#999",cursor:"pointer",width:2,label:"data(label)","font-size":9,color:"#888","text-rotation":"autorotate","text-margin-y":-8}},{selector:'edge[enabled="yes"]',style:{"line-style":"solid"}},{selector:'edge[enabled="no"]',style:{"line-style":"dashed","line-color":"#ccc","target-arrow-color":"#ccc",opacity:.5}},{selector:'edge[edgeType="dependency"]',style:{"line-style":"dotted","line-color":"#bbb","target-arrow-color":"#bbb",width:1.5,label:""}}],layout:{name:"dagre",rankDir:"LR",nodeSep:60,rankSep:150,padding:30},userZoomingEnabled:!0,userPanningEnabled:!0,boxSelectionEnabled:!1}),this._cy.on("tap","node",t=>{const s=t.target.data(),a=s.id.substring(s.id.indexOf(":")+1);let r;if(s.kind==="source")r=`/settings/source/${a}`;else if(s.kind==="dataset")r=`/settings/dataset/${a}`;else if(s.kind==="dashboard")r=`/settings/dashboard/${a}`;else if(s.kind==="model")r=`/settings/model/${a}`;else return;this.dispatchEvent(new CustomEvent("navigate",{bubbles:!0,composed:!0,detail:{path:r}}))}),this._cy.on("tap","edge",t=>{const s=t.target.data("sourcePlugin");s&&this.dispatchEvent(new CustomEvent("navigate",{bubbles:!0,composed:!0,detail:{path:`/settings/source/${s}`}}))}),this._resizeObserver&&this._resizeObserver.disconnect(),this._resizeObserver=new ResizeObserver(()=>{this._cy&&(this._cy.resize(),this._cy.fit(void 0,30))}),this._resizeObserver.observe(e))}firstUpdated(){!this._loading&&this._elements&&this._initCytoscape()}updated(e){e.has("_loading")&&!this._loading&&this._elements&&requestAnimationFrame(()=>this._initCytoscape())}render(){return n`
      <shenas-page ?loading=${this._loading} loading-text="Loading overview...">
        <div id="cy"></div>
        <div class="legend">
          <span class="legend-item"><span class="legend-dot pipe"></span> Pipe</span>
          <span class="legend-item"><span class="legend-dot schema"></span> Schema</span>
          <span class="legend-item"><span class="legend-dot component"></span> Component</span>
          <span class="legend-item"><span class="legend-dot model"></span> Model</span>
          <span class="legend-item"><span class="legend-line enabled"></span> Transform</span>
          <span class="legend-item"><span class="legend-line disabled"></span> Disabled</span>
          <span class="legend-item"><span class="legend-line" style="border-top:2px dotted var(--shenas-text-faint, #aaa);height:0;background:none"></span> Dependency</span>
        </div>
        ${this._empty?n`<p class="empty">No connections found. Add transforms in pipe settings.</p>`:""}
      </shenas-page>
    `}}h(z,"properties",{apiBase:{type:String,attribute:"api-base"},allPlugins:{type:Object},schemaPlugins:{type:Object},_loading:{state:!0},_empty:{state:!0}}),h(z,"styles",[O,T`
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
        flex-wrap: wrap;
        gap: 0.8rem;
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
      .legend-dot.model { background: var(--shenas-node-model, #ab47bc); }
      .legend-line {
        width: 20px;
        height: 2px;
      }
      .legend-line.enabled { background: var(--shenas-text-muted, #888); }
      .legend-line.disabled { background: var(--shenas-text-faint, #aaa); border-top: 2px dashed var(--shenas-text-faint, #aaa); height: 0; }
    `]);customElements.define("shenas-pipeline-overview",z);class L extends x{constructor(){super(),this.apiBase="/api",this.pipeName="",this._fields=[],this._instructions="",this._loading=!0,this._message=null,this._needsMfa=!1,this._oauthUrl=null,this._submitting=!1,this._stored=[]}willUpdate(i){i.has("pipeName")&&this._fetchFields()}async _fetchFields(){if(!this.pipeName)return;this._loading=!0,this._needsMfa=!1,this._oauthUrl=null;const i=await b(this.apiBase,"query($pipe: String!) { authFields(pipe: $pipe) { fields { name prompt hide } instructions stored } }",{pipe:this.pipeName});if(i!=null&&i.authFields){const e=i.authFields;this._fields=e.fields||[],this._instructions=e.instructions||"",this._stored=e.stored||[]}this._loading=!1}async _submit(){var s,a;this._submitting=!0,this._message=null;const i={};if(this._needsMfa){const r=this.renderRoot.querySelector("#mfa-code");i.mfa_code=((s=r==null?void 0:r.value)==null?void 0:s.trim())||""}else if(this._oauthUrl)i.auth_complete="true";else for(const r of this._fields){const o=this.renderRoot.querySelector(`#field-${r.name}`),d=(a=o==null?void 0:o.value)==null?void 0:a.trim();d&&(i[r.name]=d)}const{data:e}=await m(this.apiBase,"mutation($pipe: String!, $creds: JSON!) { authenticate(pipe: $pipe, credentials: $creds) { ok message error needsMfa oauthUrl } }",{pipe:this.pipeName,creds:i});this._submitting=!1;const t=e==null?void 0:e.authenticate;t!=null&&t.ok?(this._message={type:"success",text:t.message},this._needsMfa=!1,this._oauthUrl=null,this._fetchFields()):t!=null&&t.needsMfa?(this._needsMfa=!0,this._message={type:"success",text:"MFA code required"}):t!=null&&t.oauthUrl?(this._oauthUrl=t.oauthUrl,this._message={type:"success",text:t.message}):(this._message={type:"error",text:(t==null?void 0:t.error)||"Authentication failed"},this._needsMfa=!1,this._oauthUrl=null)}render(){const i=this._fields.length===0&&!this._instructions;return n`
      <shenas-page ?loading=${this._loading} ?empty=${i}
        loading-text="Loading auth..." empty-text="No authentication required for this plugin.">
        ${N(this._message)}
        ${this._stored.length>0?n`<div class="stored-creds">
              ${this._stored.map(e=>n`<div class="stored-item">&#10003; ${e} configured</div>`)}
            </div>`:""}
        ${this._instructions?n`<div class="instructions">${this._instructions}</div>`:""}
        ${this._oauthUrl?this._renderOAuth():this._needsMfa?this._renderMfa():this._renderFields()}
      </shenas-page>
    `}_renderFields(){return n`
      ${this._fields.map(i=>n`
        <div class="field">
          <label for="field-${i.name}">${i.prompt}</label>
          <input id="field-${i.name}"
            type="${i.hide?"password":"text"}"
            @keydown=${e=>{e.key==="Enter"&&this._submit()}}
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
          @keydown=${i=>{i.key==="Enter"&&this._submit()}}
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
    `}}h(L,"properties",{apiBase:{type:String,attribute:"api-base"},pipeName:{type:String,attribute:"pipe-name"},_fields:{state:!0},_instructions:{state:!0},_loading:{state:!0},_message:{state:!0},_needsMfa:{state:!0},_oauthUrl:{state:!0},_submitting:{state:!0},_stored:{state:!0}}),h(L,"styles",[P,I,C,T`
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
    `]);customElements.define("shenas-auth",L);const v=class v extends x{constructor(){super(),this.apiBase="/api",this.kind="",this.name="",this._config=null,this._loading=!0,this._message=null,this._editing=null,this._editValue="",this._freqNum="",this._freqUnit="hours"}willUpdate(i){(i.has("kind")||i.has("name"))&&this._fetchConfig()}async _fetchConfig(){if(!this.kind||!this.name)return;this._loading=!0;const i=await b(this.apiBase,"query($kind: String!) { plugins(kind: $kind) { name hasConfig configEntries { key label value description } } }",{kind:this.kind}),t=((i==null?void 0:i.plugins)||[]).find(s=>s.name===this.name&&s.hasConfig);this._config=t?{kind:this.kind,name:t.name,entries:t.configEntries}:null,this._loading=!1}_startEdit(i,e){if(this._editing=i,this._editValue=e||"",v._DURATION_FIELDS.has(i)&&e){const t=parseFloat(e);t>=1440&&t%1440===0?(this._freqNum=String(t/1440),this._freqUnit="days"):t>=60&&t%60===0?(this._freqNum=String(t/60),this._freqUnit="hours"):t>=1?(this._freqNum=String(t),this._freqUnit="minutes"):(this._freqNum=String(t*60),this._freqUnit="seconds")}else v._DURATION_FIELDS.has(i)&&(this._freqNum="",this._freqUnit="hours")}_cancelEdit(){this._editing=null,this._editValue=""}_freqToMinutes(){const i=parseFloat(this._freqNum);return isNaN(i)||i<=0?null:String(Math.round(i*v._UNIT_MULTIPLIERS[this._freqUnit]))}_formatFreq(i){const e=parseFloat(i);return isNaN(e)?i:e>=1440&&e%1440===0?`${e/1440} day${e/1440!==1?"s":""}`:e>=60&&e%60===0?`${e/60} hour${e/60!==1?"s":""}`:e>=1?`${e} minute${e!==1?"s":""}`:`${e*60} second${e*60!==1?"s":""}`}async _saveEdit(i){const e=v._DURATION_FIELDS.has(i)?this._freqToMinutes():this._editValue;if(v._DURATION_FIELDS.has(i)&&e===null){this._message={type:"error",text:"Enter a positive number"};return}const{ok:t,data:s}=await m(this.apiBase,"mutation($kind: String!, $name: String!, $key: String!, $value: String!) { setConfig(kind: $kind, name: $name, key: $key, value: $value) { ok } }",{kind:this.kind,name:this.name,key:i,value:e});t?(this._message={type:"success",text:`Updated ${i}`},this._editing=null,await this._fetchConfig()):this._message={type:"error",text:(s==null?void 0:s.detail)||"Update failed"}}render(){var e;const i=!this._config||this._config.entries.length===0;return n`
      <shenas-page ?loading=${this._loading} ?empty=${i}
        loading-text="Loading config..." empty-text="No configuration settings for this plugin.">
        ${N(this._message)}
        ${(e=this._config)==null?void 0:e.entries.map(t=>this._renderEntry(t))}
      </shenas-page>
    `}_renderFreqEdit(i){return n`
      <div class="edit-row">
        <input class="config-input" type="number" min="0" step="any" style="width: 80px"
          .value=${this._freqNum}
          @input=${e=>{this._freqNum=e.target.value}}
          @keydown=${e=>{e.key==="Enter"&&this._saveEdit(i.key),e.key==="Escape"&&this._cancelEdit()}}
        />
        <select @change=${e=>{this._freqUnit=e.target.value}}>
          ${Object.keys(v._UNIT_MULTIPLIERS).map(e=>n`
            <option value=${e} ?selected=${this._freqUnit===e}>${e}</option>
          `)}
        </select>
        <button @click=${()=>this._saveEdit(i.key)}>Save</button>
        <button @click=${this._cancelEdit}>Cancel</button>
      </div>`}_renderEntry(i){const e=this._editing===i.key,t=v._DURATION_FIELDS.has(i.key),s=t&&i.value?this._formatFreq(i.value):i.value;return n`
      <div class="config-row">
        <div class="config-key">${i.label||i.key}</div>
        ${e?t?this._renderFreqEdit(i):n`
            <div class="edit-row">
              <input class="config-input"
                .value=${this._editValue}
                @input=${a=>{this._editValue=a.target.value}}
                @keydown=${a=>{a.key==="Enter"&&this._saveEdit(i.key),a.key==="Escape"&&this._cancelEdit()}}
              />
              <button @click=${()=>this._saveEdit(i.key)}>Save</button>
              <button @click=${this._cancelEdit}>Cancel</button>
            </div>`:n`
            <div class="config-detail">
              <div class="config-value ${s?"":"empty"}"
                @click=${()=>this._startEdit(i.key,i.value)}
                style="cursor: pointer"
                title="Click to edit"
              >${s||"not set"}</div>
              ${i.description?n`<div class="config-desc">${i.description}</div>`:""}
            </div>`}
      </div>
    `}};h(v,"properties",{apiBase:{type:String,attribute:"api-base"},kind:{type:String},name:{type:String},_config:{state:!0},_loading:{state:!0},_message:{state:!0},_editing:{state:!0},_editValue:{state:!0},_freqNum:{state:!0},_freqUnit:{state:!0}}),h(v,"styles",[P,I,C,T`
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
    `]),h(v,"_UNIT_MULTIPLIERS",{seconds:1/60,minutes:1,hours:60,days:1440}),h(v,"_DURATION_FIELDS",new Set(["sync_frequency","lookback_period"]));let A=v;customElements.define("shenas-config",A);class F extends x{constructor(){super();h(this,"_boundKeydown",null);this.apiBase="/api",this.actions=[],this._bindings={},this._recording=null,this._recordedKey="",this._conflict=null,this._loading=!0,this._filter=""}connectedCallback(){super.connectedCallback(),this._loadBindings(),this._boundKeydown=e=>this._onKeydown(e),document.addEventListener("keydown",this._boundKeydown,!0)}disconnectedCallback(){super.disconnectedCallback(),this._boundKeydown&&document.removeEventListener("keydown",this._boundKeydown,!0)}async _loadBindings(){this._loading=!0;const e=await b(this.apiBase,"{ hotkeys }");this._bindings=(e==null?void 0:e.hotkeys)||{},this._loading=!1}async _saveBinding(e,t){t?await m(this.apiBase,"mutation($id: String!, $b: String!) { setHotkey(actionId: $id, binding: $b) { ok } }",{id:e,b:t}):await m(this.apiBase,"mutation($id: String!) { deleteHotkey(actionId: $id) { ok } }",{id:e}),this.dispatchEvent(new CustomEvent("hotkeys-changed",{bubbles:!0,composed:!0}))}_startRecording(e){this._recording=e,this._recordedKey="",this._conflict=null}_stopRecording(){this._recording=null,this._recordedKey="",this._conflict=null}_onKeydown(e){if(!this._recording)return;if(e.preventDefault(),e.stopPropagation(),e.key==="Escape"){this._stopRecording();return}if(["Control","Shift","Alt","Meta"].includes(e.key))return;const t=Z(e);this._recordedKey=t;const s=Object.entries(this._bindings).find(([a,r])=>r===t&&a!==this._recording);this._conflict=s?s[0]:null}async _applyRecording(){!this._recordedKey||!this._recording||(this._conflict&&(this._bindings={...this._bindings,[this._conflict]:""},await this._saveBinding(this._conflict,"")),this._bindings={...this._bindings,[this._recording]:this._recordedKey},await this._saveBinding(this._recording,this._recordedKey),this._stopRecording())}async _clearBinding(e){this._bindings={...this._bindings,[e]:""},await this._saveBinding(e,"")}async _resetDefaults(){await m(this.apiBase,"mutation { resetHotkeys { ok } }"),await this._loadBindings(),this.dispatchEvent(new CustomEvent("hotkeys-changed",{bubbles:!0,composed:!0}))}_getActionLabel(e){const t=this.actions.find(s=>s.id===e);return t?t.label:e}_getActionCategory(e){const t=this.actions.find(s=>s.id===e);return t?t.category:""}render(){if(this._loading)return n`<p class="loading">Loading hotkeys...</p>`;const e=this._filter.toLowerCase(),t=B(this.actions.filter(s=>!e||s.label.toLowerCase().includes(e)||s.category.toLowerCase().includes(e)),this._bindings);return n`
      <div class="toolbar">
        <button @click=${this._resetDefaults}>Reset to Defaults</button>
        <input class="filter-input" type="text" placeholder="Filter actions..."
          .value=${this._filter} @input=${s=>{this._filter=s.target.value}} />
      </div>
      ${t.map(s=>this._renderRow(s.id,s.label,s.category))}
    `}_renderRow(e,t,s){const a=this._bindings[e]||"",r=this._recording===e,o=this._conflict?this._getActionLabel(this._conflict):"";return n`
      <div class="hotkey-row">
        <span class="hotkey-category">${s}</span>
        <span class="hotkey-label">${t}</span>
        <span class="hotkey-binding">
          ${r?n`
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
    `}}h(F,"properties",{apiBase:{type:String,attribute:"api-base"},actions:{type:Array},_bindings:{state:!0},_recording:{state:!0},_recordedKey:{state:!0},_conflict:{state:!0},_loading:{state:!0},_filter:{state:!0}}),h(F,"styles",[P,C,O,T`
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
    `]);customElements.define("shenas-hotkeys",F);class q extends x{constructor(){super();h(this,"_logSource",null);h(this,"_spanSource",null);h(this,"_searchTimer");this.apiBase="/api",this.pipe="",this._activeTab="logs",this._logs=[],this._spans=[],this._loading=!0,this._search="",this._severity="",this._expanded=null,this._live=!1}connectedCallback(){super.connectedCallback(),this.dispatchEvent(new CustomEvent("page-title",{bubbles:!0,composed:!0,detail:{title:"Logs"}})),this._fetchBoth(),this._connectStreams()}disconnectedCallback(){super.disconnectedCallback(),this._disconnectStreams(),clearTimeout(this._searchTimer)}_connectStreams(){const e=this.apiBase.startsWith("http")?this.apiBase:`${location.origin}${this.apiBase}`;this._logSource=new EventSource(`${e}/stream/logs`),this._logSource.onmessage=t=>{try{const s=JSON.parse(t.data);this._logs=[s,...this._logs].slice(0,500)}catch{}},this._logSource.onopen=()=>{this._live=!0},this._logSource.onerror=()=>{this._live=!1},this._spanSource=new EventSource(`${e}/stream/spans`),this._spanSource.onmessage=t=>{try{const s=JSON.parse(t.data);this._spans=[s,...this._spans].slice(0,500)}catch{}}}_disconnectStreams(){this._logSource&&(this._logSource.close(),this._logSource=null),this._spanSource&&(this._spanSource.close(),this._spanSource=null),this._live=!1}_logsSql(e=""){const t=[];return this._severity&&t.push(`severity = '${this._severity}'`),this._search&&t.push(`body LIKE '%${this._search}%'`),this.pipe&&t.push(`(body LIKE '%${this.pipe}%' OR attributes LIKE '%${this.pipe}%')`),e&&t.push(e),`SELECT timestamp, trace_id, span_id, severity, body, attributes, service_name FROM telemetry.logs${t.length?` WHERE ${t.join(" AND ")}`:""} ORDER BY timestamp DESC LIMIT 100`}_spansSql(){const e=[];return this._search&&e.push(`name LIKE '%${this._search}%'`),this.pipe&&e.push(`(name LIKE '%${this.pipe}%' OR attributes LIKE '%${this.pipe}%')`),`SELECT trace_id, span_id, parent_span_id, name, kind, service_name, status_code, start_time, end_time, duration_ms, attributes FROM telemetry.spans${e.length?` WHERE ${e.join(" AND ")}`:""} ORDER BY start_time DESC LIMIT 100`}async _fetchBoth(){this._loading=!0;try{const[e,t]=await Promise.all([D(this.apiBase,this._logsSql()),D(this.apiBase,this._spansSql())]);e&&(this._logs=e),t&&(this._spans=t)}catch{}this._loading=!1}async _fetch(){this._loading=!0,this._expanded=null;try{this._activeTab==="logs"?this._logs=await D(this.apiBase,this._logsSql())||[]:this._spans=await D(this.apiBase,this._spansSql())||[]}catch{}this._loading=!1}_onSearch(e){this._search=e.target.value,clearTimeout(this._searchTimer),this._searchTimer=setTimeout(()=>this._fetch(),300)}_switchTab(e){this._activeTab=e,this._expanded=null,this._fetch()}_toggleExpand(e){this._expanded=this._expanded===e?null:e}render(){const e=this._activeTab==="logs"?this._logs:this._spans;return n`
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
          ${s.map(([a,r])=>n`
            <div class="attr-item">
              <span class="attr-key">${a}</span>
              <span class="attr-val">${typeof r=="string"?r:JSON.stringify(r)}</span>
            </div>
          `)}
        </div>
      </div>
    `}_formatTime(e){if(!e)return"-";const t=typeof e=="number"?new Date(e):new Date(String(e).endsWith("Z")?e:e+"Z");if(isNaN(t.getTime()))return String(e);const s=(a,r=2)=>String(a).padStart(r,"0");return`${t.getFullYear()}-${s(t.getMonth()+1)}-${s(t.getDate())} ${s(t.getHours())}:${s(t.getMinutes())}:${s(t.getSeconds())}`}}h(q,"properties",{apiBase:{type:String,attribute:"api-base"},pipe:{type:String},_activeTab:{state:!0},_logs:{state:!0},_spans:{state:!0},_loading:{state:!0},_search:{state:!0},_severity:{state:!0},_expanded:{state:!0},_live:{state:!0}}),h(q,"styles",[P,O,T`
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
    `]);customElements.define("shenas-logs",q);class j extends x{constructor(){super();h(this,"_elementCache",new Map);h(this,"_registeredCommands",new Map);h(this,"_keyHandler",null);h(this,"_schemaPlugins",{});h(this,"_deviceName","");h(this,"_hotkeys",{});h(this,"_pluginDisplayNames",{});h(this,"_nextTabId",1);h(this,"_saveWorkspaceTimer",null);h(this,"_router",new ae(this,[{path:"/",render:()=>this._renderDynamicHome()},{path:"/settings",render:()=>this._renderSettings("flow")},{path:"/settings/:kind",render:e=>this._renderSettings((e==null?void 0:e.kind)??"")},{path:"/settings/:kind/:name",render:e=>this._renderPluginDetail((e==null?void 0:e.kind)??"",(e==null?void 0:e.name)??"")},{path:"/settings/:kind/:name/config",render:e=>this._renderPluginDetail((e==null?void 0:e.kind)??"",(e==null?void 0:e.name)??"","config")},{path:"/settings/:kind/:name/auth",render:e=>this._renderPluginDetail((e==null?void 0:e.kind)??"",(e==null?void 0:e.name)??"","auth")},{path:"/settings/:kind/:name/data",render:e=>this._renderPluginDetail((e==null?void 0:e.kind)??"",(e==null?void 0:e.name)??"","data")},{path:"/settings/:kind/:name/logs",render:e=>this._renderPluginDetail((e==null?void 0:e.kind)??"",(e==null?void 0:e.name)??"","logs")},{path:"/logs",render:()=>n`<shenas-logs api-base="${this.apiBase}"></shenas-logs>`},{path:"/:tab",render:e=>this._renderDynamicTab((e==null?void 0:e.tab)??"")}]));this.apiBase="/api",this._dashboards=[],this._loading=!0,this._loadedScripts=new Set,this._leftWidth=160,this._rightWidth=220,this._dbStatus=null,this._inspectTable=null,this._inspectRows=null,this._paletteOpen=!1,this._paletteCommands=[],this._navPaletteOpen=!1,this._navCommands=[],this._tabs=[],this._activeTabId=null,this._allPlugins={},this._rightOpen=!0,this._mobileDrawerOpen=!1}connectedCallback(){super.connectedCallback(),this._fetchData(),this.addEventListener("plugin-state-changed",()=>this._refreshDashboards()),this.addEventListener("job-start",(s=>{var a;return(a=this._getJobPanel())==null?void 0:a.addJob(s.detail.id,s.detail.label)})),this.addEventListener("job-log",(s=>{var a;return(a=this._getJobPanel())==null?void 0:a.appendLine(s.detail.id,s.detail.text)})),this.addEventListener("job-finish",(s=>{var a;return(a=this._getJobPanel())==null?void 0:a.finishJob(s.detail.id,s.detail.ok,s.detail.message)})),this.addEventListener("inspect-table",(s=>this._inspect(s.detail.schema,s.detail.table))),this.addEventListener("page-title",(s=>{this._activeTabId!=null&&(this._tabs=this._tabs.map(a=>a.id===this._activeTabId?{...a,label:s.detail.title}:a))})),this.addEventListener("navigate",(s=>this._navigateTo(s.detail.path,s.detail.label))),this.addEventListener("register-command",(s=>{const{componentId:a,commands:r}=s.detail;!r||r.length===0?this._registeredCommands.delete(a):this._registeredCommands.set(a,r)})),this._keyHandler=s=>{for(const[a,r]of Object.entries(this._hotkeys))if(r&&Q(s,r))for(const o of this._registeredCommands.values()){const d=o.find(c=>c.id===a);if(d&&d.action){s.preventDefault(),d.action();return}}},document.addEventListener("keydown",this._keyHandler),this.addEventListener("hotkeys-changed",()=>this._loadHotkeys()),this.addEventListener("plugins-changed",(s=>{s.detail?this._allPlugins=s.detail:this._allPlugins={}}));let e=0,t=0;this.addEventListener("touchstart",(s=>{e=s.touches[0].clientX,t=s.touches[0].clientY}),{passive:!0}),this.addEventListener("touchend",(s=>{const a=s.changedTouches[0].clientX-e,r=s.changedTouches[0].clientY-t;Math.abs(r)>Math.abs(a)||(a<-50&&e>window.innerWidth-40&&(this._mobileDrawerOpen=!0),a>50&&this._mobileDrawerOpen&&(this._mobileDrawerOpen=!1))}),{passive:!0})}disconnectedCallback(){super.disconnectedCallback(),this._keyHandler&&document.removeEventListener("keydown",this._keyHandler)}async _loadHotkeys(){const e=await b(this.apiBase,"{ hotkeys }");this._hotkeys=(e==null?void 0:e.hotkeys)||{}}_togglePalette(){if(this._paletteOpen){this._paletteOpen=!1;return}this._navPaletteOpen=!1,this._buildCommands(),this._paletteOpen=!0}async _toggleNavPalette(){if(this._navPaletteOpen){this._navPaletteOpen=!1;return}this._paletteOpen=!1,await this._buildNavCommands(),this._navPaletteOpen=!0}async _buildNavCommands(){const e=[];for(const s of this._dashboards)e.push({id:`nav:${s.name}`,category:"Page",label:s.display_name||s.name,path:`/${s.name}`});e.push({id:"nav:dataflow",category:"Settings",label:"Flow",path:"/settings/flow"});for(const s of E)e.push({id:`nav:settings:${s.id}`,category:"Settings",label:s.label,path:`/settings/${s.id}`});const t=E.flatMap(s=>(this._allPlugins[s.id]||[]).map(a=>({...a,kind:s.id,kindLabel:s.label})));for(const s of t)e.push({id:`nav:${s.kind}:${s.name}`,category:s.kindLabel,label:s.displayName||s.name,path:`/settings/${s.kind}/${s.name}`});this._navCommands=e}async _registerGlobalCommands(){const e=[],t={};try{const s=this._schemaPlugins||{};for(const a of E){const r=this._allPlugins[a.id]||[];for(const o of r){const d=o.displayName||o.name;t[`${a.id}:${o.name}`]=d;const c=o.enabled!==!1;e.push({id:`toggle:${a.id}:${o.name}`,category:a.label,label:`Toggle ${d}`,action:async()=>{const p=c?"mutation($k: String!, $n: String!) { disablePlugin(kind: $k, name: $n) { ok } }":"mutation($k: String!, $n: String!) { enablePlugin(kind: $k, name: $n) { ok } }";if(await m(this.apiBase,p,{k:a.id,n:o.name}),a.id==="ui"&&!c){window.location.replace(window.location.pathname+"?_switch="+Date.now());return}await this._fetchData()}}),a.id==="ui"&&e.push({id:`switch-ui:${o.name}`,category:"Switch UI",label:`${d}${c?" (active)":""}`,action:async()=>{c||(await m(this.apiBase,"mutation($k: String!, $n: String!) { enablePlugin(kind: $k, name: $n) { ok } }",{k:"ui",n:o.name}),window.location.replace(window.location.pathname+"?_switch="+Date.now()))}}),a.id==="source"&&c&&(e.push({id:`sync:${o.name}`,category:"Pipe",label:`Sync ${d}`,action:()=>{fetch(`${this.apiBase}/sync/${o.name}`,{method:"POST"})}}),e.push({id:`transform:pipe:${o.name}`,category:"Transform",label:`Run Transforms: ${d}`,action:()=>{m(this.apiBase,"mutation($pipe: String!) { runPipeTransforms(pipe: $pipe) }",{pipe:o.name})}}))}}e.push({id:"sync:all",category:"Pipe",label:"Sync All Pipes",action:()=>{fetch(`${this.apiBase}/sync`,{method:"POST"})}}),e.push({id:"seed:transforms",category:"Transform",label:"Seed Default Transforms",action:()=>{m(this.apiBase,"mutation { seedTransforms }")}});for(const a of this._allPlugins.schema||[]){const r=s[a.name]||[];for(const o of r)e.push({id:`transform:schema:${o}`,category:"Transform",label:`Run Transforms -> ${a.displayName||a.name}: ${o}`,action:()=>{m(this.apiBase,"mutation($schema: String!) { runSchemaTransforms(schema: $schema) }",{schema:o})}})}}catch{}this._pluginDisplayNames=t,e.push({id:"command-palette",category:"System",label:"Command Palette",action:()=>this._togglePalette()},{id:"navigation-palette",category:"System",label:"Navigation Palette",action:()=>this._toggleNavPalette()},{id:"close-tab",category:"System",label:"Close Tab",action:()=>{this._activeTabId!=null&&this._closeTab(this._activeTabId)}},{id:"new-tab",category:"System",label:"New Tab",action:()=>this._addTab()}),this._registeredCommands.set("global",e)}_buildCommands(){const e=[];for(const t of this._registeredCommands.values())e.push(...t);this._paletteCommands=B(e,this._hotkeys)}_executePaletteCommand(e){const t=e.detail;t.path?this._openTab(t.path,t.label):t.action&&t.action(),this._paletteOpen=!1,this._navPaletteOpen=!1}_navigateTo(e,t){if(this._tabs.length===0||!this._activeTabId){this._openTab(e,t);return}const s=t||this._labelForPath(e);this._tabs=this._tabs.map(a=>a.id===this._activeTabId?{...a,path:e,label:s}:a),window.history.pushState({},"",e),this._router.goto(e),this._saveWorkspace()}_openTab(e,t){const s=this._nextTabId++;this._tabs=[...this._tabs,{id:s,path:e,label:t||this._labelForPath(e)}],this._activeTabId=s,window.history.pushState({},"",e),this._router.goto(e),this._saveWorkspace()}async _addTab(){await this._buildNavCommands(),this._navPaletteOpen=!0}_closeTab(e){const t=this._tabs.findIndex(a=>a.id===e);if(t===-1)return;const s=this._tabs.filter(a=>a.id!==e);if(this._tabs=s,this._activeTabId===e)if(s.length>0){const a=s[Math.min(t,s.length-1)];this._activeTabId=a.id,this._router.goto(a.path)}else this._activeTabId=null,window.history.pushState({},"","/");this._saveWorkspace()}_switchTab(e){const t=this._tabs.find(s=>s.id===e);t&&(this._activeTabId=e,window.history.pushState({},"",t.path),this._router.goto(t.path),this._saveWorkspace())}_saveWorkspace(){this._saveWorkspaceTimer&&clearTimeout(this._saveWorkspaceTimer),this._saveWorkspaceTimer=setTimeout(()=>{const e={tabs:this._tabs,activeTabId:this._activeTabId,nextTabId:this._nextTabId,rightPanelOpen:this._rightOpen};m(this.apiBase,"mutation($data: JSON!) { saveWorkspace(data: $data) { ok } }",{data:e}).catch(()=>{})},300)}async _loadWorkspace(){try{const e=await b(this.apiBase,"{ workspace }"),t=e==null?void 0:e.workspace;if(!t)return;if(t.tabs&&t.tabs.length>0){this._tabs=t.tabs,this._activeTabId=t.activeTabId||t.tabs[0].id,this._nextTabId=t.nextTabId||Math.max(...t.tabs.map(r=>r.id))+1;const s=window.location.pathname;if(s&&s!=="/"&&!this._tabs.some(r=>r.path===s)){this._openTab(s);return}const a=this._tabs.find(r=>r.id===this._activeTabId);a&&this._router.goto(a.path)}else{const s=window.location.pathname;s&&s!=="/"&&this._openTab(s)}}catch{const e=window.location.pathname;e&&e!=="/"&&this._openTab(e)}}_labelForPath(e){const t=e.replace(/^\/+/,"");if(!t||t==="settings"||t==="settings/flow")return"Flow";const s=t.split("/");if(s[0]==="settings"){if(s.length===2){const r=E.find(o=>o.id===s[1]);return r?r.label:s[1]}if(s.length>=3){const r=`${s[1]}:${s[2]}`;return this._pluginDisplayNames[r]||s[2]}}const a=this._dashboards.find(r=>r.name===s[0]);return a?a.display_name||a.name:s[0]}async _refreshDashboards(){const e=await b(this.apiBase,"{ dashboards }");this._dashboards=(e==null?void 0:e.dashboards)||[]}async _refreshPlugins(){const e=await b(this.apiBase,`{
      sources: plugins(kind: "source") { name displayName enabled syncedAt hasAuth isAuthenticated }
      datasets: plugins(kind: "dataset") { name displayName enabled }
      dashboardPlugins: plugins(kind: "dashboard") { name displayName enabled }
      frontends: plugins(kind: "frontend") { name displayName enabled }
      themes: plugins(kind: "theme") { name displayName enabled }
      models: plugins(kind: "model") { name displayName enabled }
    }`);e&&(this._allPlugins={source:e.sources||[],dataset:e.datasets||[],dashboard:e.dashboardPlugins||[],frontend:e.frontends||[],theme:e.themes||[],model:e.models||[]})}async _fetchData(){this._loading=!0;try{const e=await b(this.apiBase,`{
        dashboards
        hotkeys
        workspace
        dbStatus { keySource dbPath sizeMb schemas { name tables { name rows cols earliest latest } } }
        sources: plugins(kind: "source") { name displayName enabled syncedAt hasAuth isAuthenticated }
        datasets: plugins(kind: "dataset") { name displayName enabled }
        dashboardPlugins: plugins(kind: "dashboard") { name displayName enabled }
        frontends: plugins(kind: "frontend") { name displayName enabled }
        themes: plugins(kind: "theme") { name displayName enabled }
        models: plugins(kind: "model") { name displayName enabled }
        theme { css }
        deviceName
        schemaPlugins
      }`);this._dashboards=(e==null?void 0:e.dashboards)||[],this._dbStatus=e==null?void 0:e.dbStatus,this._deviceName=(e==null?void 0:e.deviceName)||"",this._hotkeys=(e==null?void 0:e.hotkeys)||{},this._allPlugins={source:(e==null?void 0:e.sources)||[],dataset:(e==null?void 0:e.datasets)||[],dashboard:(e==null?void 0:e.dashboardPlugins)||[],frontend:(e==null?void 0:e.frontends)||[],theme:(e==null?void 0:e.themes)||[],model:(e==null?void 0:e.models)||[]},this._schemaPlugins=(e==null?void 0:e.schemaPlugins)||{};const t=e==null?void 0:e.theme;if(t!=null&&t.css&&!document.querySelector("link[data-shenas-theme]")){const a=document.createElement("link");a.rel="stylesheet",a.setAttribute("data-shenas-theme",""),a.href=t.css,document.head.appendChild(a)}const s=e==null?void 0:e.workspace;if((s==null?void 0:s.rightPanelOpen)!==void 0&&(this._rightOpen=s.rightPanelOpen),s!=null&&s.tabs&&s.tabs.length>0){this._tabs=s.tabs,this._activeTabId=s.activeTabId||s.tabs[0].id,this._nextTabId=s.nextTabId||Math.max(...s.tabs.map(r=>r.id))+1;const a=window.location.pathname;if(a&&a!=="/"&&!this._tabs.some(r=>r.path===a))this._openTab(a);else{const r=this._tabs.find(o=>o.id===this._activeTabId);r&&this._router.goto(r.path)}}else{const a=window.location.pathname;a&&a!=="/"&&this._openTab(a)}}catch(e){console.error("Failed to fetch data:",e)}this._loading=!1,this._registerGlobalCommands(),fetch(`${this.apiBase}/auth/me`).then(e=>e.json()).then(e=>{this._remoteUser=e.user||null}).catch(()=>{this._remoteUser=null})}_activeTab(){var t,s;const e=this._tabs.find(a=>a.id===this._activeTabId);return((s=(t=e==null?void 0:e.path)==null?void 0:t.replace(/^\/+/,""))==null?void 0:s.split("/")[0])||(this._dashboards.length>0?this._dashboards[0].name:"settings")}_activePath(){const e=this._tabs.find(t=>t.id===this._activeTabId);return(e==null?void 0:e.path)||window.location.pathname}_startDrag(e){return t=>{t.preventDefault();const s=t.clientX,a=e==="left"?this._leftWidth:this._rightWidth,r=t.target;r.classList.add("dragging");const o=c=>{const p=e==="left"?c.clientX-s:s-c.clientX,f=Math.max(80,Math.min(400,a+p));e==="left"?this._leftWidth=f:this._rightWidth=f},d=()=>{r.classList.remove("dragging"),window.removeEventListener("mousemove",o),window.removeEventListener("mouseup",d)};window.addEventListener("mousemove",o),window.addEventListener("mouseup",d)}}render(){if(this._loading)return n`<div style="display:flex;align-items:center;justify-content:center;height:100vh;color:var(--shenas-text-muted,#888);background:var(--shenas-bg,#f5f1eb)">Loading...</div>`;const e=this._activeTab(),t=this._activePath();return t.startsWith("/settings")&&this._settingsOpen===void 0&&(this._settingsOpen=!0),n`
      <div class="layout">
        <div class="panel-left" style="width: ${this._leftWidth}px">
          <div class="header">
            <img src="/static/images/shenas.svg" alt="shenas" />
          </div>
          <nav class="nav">
            ${this._dashboards.map(s=>this._navItem(s.name,s.display_name||s.name,e))}
            ${this._navItem("logs","Logs",e)}
            <a class="nav-link settings-toggle" @click=${()=>{this._settingsOpen=!this._settingsOpen}}>
              Settings
              <span class="chevron ${this._settingsOpen?"open":""}">&rsaquo;</span>
            </a>
            ${this._settingsOpen?n`
              <div class="settings-sub">
                ${this._settingsNavItem("flow","Flow",t)}
                ${this._settingsNavItem("hotkeys","Hotkeys",t)}
                <span class="sub-heading">Plugins</span>
                ${E.map(({id:s,label:a})=>n`
                  ${this._settingsNavItem(s,`${a} (${(this._allPlugins[s]||[]).length})`,t)}
                `)}
              </div>
            `:""}
          </nav>
          <div class="sidebar-footer">
            <a class="auth-link" href="/api/auth/login" @click=${s=>{s.preventDefault(),window.location.href="/api/auth/login"}}>
              ${this._remoteUser?this._remoteUser.name||this._remoteUser.email:"Sign in"}
            </a>
            ${this._deviceName?n`<span class="device-name"><span class="device-dot ${this._remoteUser?"connected":""}"></span>${this._deviceName}</span>`:""}
          </div>
        </div>
        <div class="divider" @mousedown=${this._startDrag("left")}></div>
        <div class="panel-middle">
          ${this._tabs.length>0?n`
              <div class="tab-bar">
                ${this._tabs.map(s=>n`
                  <div class="tab-item ${s.id===this._activeTabId?"active":""}"
                    @click=${()=>this._switchTab(s.id)}>
                    <span>${s.label}</span>
                    <button class="tab-close" @click=${a=>{a.stopPropagation(),this._closeTab(s.id)}}>x</button>
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
          <shenas-job-panel></shenas-job-panel>
        </div>
        <button class="right-toggle" @click=${()=>{this._rightOpen=!this._rightOpen,this._saveWorkspace()}} title="${this._rightOpen?"Collapse":"Expand"} panel">${this._rightOpen?"›":"‹"}</button>
        <div class="divider" @mousedown=${this._startDrag("right")}></div>
        <div class="drawer-overlay ${this._mobileDrawerOpen?"visible":""}" @click=${()=>{this._mobileDrawerOpen=!1}}></div>
        <div class="panel-right ${this._rightOpen?"":"collapsed"} ${this._mobileDrawerOpen?"mobile-open":""}" style="width: ${this._rightWidth}px">
          ${this._inspectTable?this._renderInspect():this._renderDbStats()}
        </div>
        <div class="bottom-nav">
          <nav>
            ${this._dashboards.map(s=>n`
              <a class="nav-item" href="/${s.name}" @click=${a=>{a.preventDefault(),this._navigateTo(`/${s.name}`)}}
                aria-selected=${e===s.name}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/></svg>
                <span>${s.display_name||s.name}</span>
              </a>
            `)}
            <a class="nav-item" href="/logs" @click=${s=>{s.preventDefault(),this._navigateTo("/logs")}}
              aria-selected=${e==="logs"}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
              <span>Logs</span>
            </a>
            <a class="nav-item" href="/settings" aria-selected=${t.startsWith("/settings")}
              @click=${s=>{s.preventDefault(),this._navigateTo("/settings")}}>
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
    `}_navItem(e,t,s){return n`
      <a class="nav-item" href="/${e}" aria-selected=${s===e}
        @click=${a=>{a.preventDefault(),a.ctrlKey||a.metaKey?this._openTab(`/${e}`,t):this._navigateTo(`/${e}`,t)}}>
        ${t}
      </a>
    `}_settingsNavItem(e,t,s){const a=`/settings/${e}`,r=s===a||s.startsWith(a+"/");return n`
      <a class="nav-sub-item" href="${a}" aria-selected=${r}
        @click=${o=>{o.preventDefault(),o.ctrlKey||o.metaKey?this._openTab(a,t):this._navigateTo(a,t)}}>
        ${t}
      </a>
    `}_renderDynamicHome(){return this._dashboards.length>0?this._renderDynamicTab(this._dashboards[0].name):this._renderSettings("source")}_renderDynamicTab(e){const t=this._dashboards.find(s=>s.name===e);if(!t)return n`<p class="empty">Unknown page: ${e}</p>`;if(!this._loadedScripts.has(t.js)){this._loadedScripts=new Set([...this._loadedScripts,t.js]);const s=document.createElement("script");s.type="module",s.src=t.js,document.head.appendChild(s)}return n`<div class="component-host">
      ${this._getOrCreateElement(t)}
    </div>`}_renderPluginDetail(e,t,s="details"){const a=(this._allPlugins[e]||[]).find(r=>r.name===t);return n`<shenas-plugin-detail
      api-base="${this.apiBase}"
      kind="${e}"
      name="${t}"
      active-tab="${s}"
      .dbStatus=${this._dbStatus}
      .schemaPlugins=${this._schemaPlugins}
      .initialInfo=${a||null}
    ></shenas-plugin-detail>`}_getAllActions(){const e=new Set,t=[];for(const s of this._registeredCommands.values())for(const a of s)!e.has(a.id)&&a.action&&(e.add(a.id),t.push({id:a.id,label:a.label,category:a.category}));return B(t,this._hotkeys)}_getJobPanel(){var e;return(e=this.shadowRoot)==null?void 0:e.querySelector("shenas-job-panel")}_renderSettings(e){return n`<shenas-settings
      api-base="${this.apiBase}"
      active-kind="${e||"flow"}"
      .allActions=${this._getAllActions()}
      .allPlugins=${this._allPlugins}
      .schemaPlugins=${this._schemaPlugins}
      .onNavigate=${t=>{this._navigateTo(`/settings/${t}`)}}
      .onPluginsChanged=${t=>{this._allPlugins=t}}
    ></shenas-settings>`}async _inspect(e,t){if(!/^[a-zA-Z_]\w*$/.test(e)||!/^[a-zA-Z_]\w*$/.test(t))return;const s=`${e}.${t}`;if(this._inspectTable===s){this._inspectTable=null,this._inspectRows=null;return}this._inspectTable=s,this._inspectRows=null;try{this._inspectRows=await D(this.apiBase,`SELECT * FROM "${e}"."${t}" ORDER BY 1 DESC LIMIT 50`)||[]}catch{this._inspectRows=[]}}_renderDbStats(){const e=this._dbStatus;return e?n`
      <div class="db-section">
        <div class="db-meta">
          ${e.size_mb!=null?n`<code>${e.size_mb} MB</code>`:n`<span>Not created</span>`}
        </div>
        ${(e.schemas||[]).map(t=>n`
            <h4>${t.name}</h4>
            ${t.tables.map(s=>n`
                <div class="db-table-row">
                  <span class="db-table-name">${s.name}</span>
                  <span class="db-table-count">${s.rows}</span>
                </div>
                ${s.earliest?n`<span class="db-date-range">${s.earliest} - ${s.latest}</span>`:""}
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
                  <tr>${Object.keys(this._inspectRows[0]).map(e=>n`<th>${e}</th>`)}</tr>
                </thead>
                <tbody>
                  ${this._inspectRows.map(e=>n`<tr>${Object.keys(e).map(t=>n`<td title="${e[t]??""}">${e[t]??""}</td>`)}</tr>`)}
                </tbody>
              </table>
            </div>
          `:n`<p class="loading" style="font-size:0.75rem">Loading...</p>`}
    `}_getOrCreateElement(e){if(!this._elementCache.has(e.name)){const t=document.createElement(e.tag);t.setAttribute("api-base",this.apiBase),this._elementCache.set(e.name,t)}return this._elementCache.get(e.name)}}h(j,"properties",{apiBase:{type:String,attribute:"api-base"},_dashboards:{state:!0},_loading:{state:!0},_loadedScripts:{state:!0},_leftWidth:{state:!0},_rightWidth:{state:!0},_dbStatus:{state:!0},_inspectTable:{state:!0},_inspectRows:{state:!0},_paletteOpen:{state:!0},_paletteCommands:{state:!0},_navPaletteOpen:{state:!0},_settingsOpen:{state:!0},_remoteUser:{state:!0},_navCommands:{state:!0},_tabs:{state:!0},_activeTabId:{state:!0},_allPlugins:{state:!0},_rightOpen:{state:!0},_mobileDrawerOpen:{state:!0}}),h(j,"styles",[W,O,T`
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
        display: flex;
        flex-direction: column;
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
      .sidebar-footer {
        margin-top: auto;
        padding: 0.8rem;
        border-top: 1px solid var(--shenas-border, #e0e0e0);
      }
      .auth-link {
        display: block;
        padding: 0.5rem 0.8rem;
        font-size: 0.85rem;
        color: var(--shenas-text-secondary, #666);
        text-decoration: none;
        border-radius: 4px;
      }
      .auth-link:hover {
        background: var(--shenas-bg-hover, #f5f5f5);
        color: var(--shenas-text, #222);
      }
      .device-name {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.2rem 0.8rem;
        font-size: 0.7rem;
        color: var(--shenas-text-faint, #aaa);
      }
      .device-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: var(--shenas-text-faint, #ccc);
        flex-shrink: 0;
      }
      .device-dot.connected {
        background: var(--shenas-success, #2e7d32);
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
      .right-toggle {
        width: 14px;
        flex-shrink: 0;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        background: transparent;
        border: none;
        color: var(--shenas-text-faint, #aaa);
        font-size: 0.7rem;
        padding: 0;
      }
      .right-toggle:hover {
        background: var(--shenas-bg-hover, #f5f5f5);
        color: var(--shenas-text-secondary, #666);
      }
      .panel-right.collapsed {
        display: none;
      }
      .drawer-overlay {
        display: none;
        position: fixed;
        inset: 0;
        background: rgba(0,0,0,0.3);
        z-index: 200;
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
          position: fixed;
          top: 0;
          right: 0;
          bottom: 0;
          width: 260px;
          z-index: 201;
          background: var(--shenas-bg, #fff);
          box-shadow: -2px 0 8px rgba(0,0,0,0.15);
          transform: translateX(100%);
          transition: transform 0.2s ease;
        }
        .panel-right.mobile-open {
          display: block;
          transform: translateX(0);
        }
        .drawer-overlay.visible {
          display: block;
        }
        .divider {
          display: none;
        }
        .right-toggle {
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
    `]);customElements.define("shenas-app",j);class M extends x{constructor(){super(),this.apiBase="/api",this.activeKind="flow",this.onNavigate=null,this.onPluginsChanged=null,this.allActions=[],this.allPlugins={},this.schemaPlugins={},this._plugins={},this._loading=!0,this._actionMessage=null,this._installing=!1,this._availablePlugins=null,this._selectedPlugin="",this._menuOpen=!1}connectedCallback(){super.connectedCallback(),this.allPlugins&&Object.keys(this.allPlugins).length>0?(this._plugins=this.allPlugins,this._loading=!1):this._fetchAll()}async _fetchAll(i){this._loading=!0;const e=await b(this.apiBase,`{
      sources: plugins(kind: "source") { name displayName package version enabled description syncedAt hasAuth isAuthenticated }
      datasets: plugins(kind: "dataset") { name displayName package version enabled description }
      dashboardPlugins: plugins(kind: "dashboard") { name displayName package version enabled description }
      frontends: plugins(kind: "frontend") { name displayName package version enabled description }
      themes: plugins(kind: "theme") { name displayName package version enabled description }
      models: plugins(kind: "model") { name displayName package version enabled description }
    }`),t={source:(e==null?void 0:e.sources)||[],dataset:(e==null?void 0:e.datasets)||[],dashboard:(e==null?void 0:e.dashboardPlugins)||[],frontend:(e==null?void 0:e.frontends)||[],theme:(e==null?void 0:e.themes)||[],model:(e==null?void 0:e.models)||[]};this._plugins=t,this._loading=!1,this.onPluginsChanged&&this.onPluginsChanged(t)}async _togglePlugin(i,e,t){const s=t?"disable":"enable",a=s==="enable"?"mutation($k: String!, $n: String!) { enablePlugin(kind: $k, name: $n) { ok message } }":"mutation($k: String!, $n: String!) { disablePlugin(kind: $k, name: $n) { ok message } }",{data:r}=await m(this.apiBase,a,{k:i,n:e}),o=s==="enable"?r==null?void 0:r.enablePlugin:r==null?void 0:r.disablePlugin;if(o!=null&&o.ok||(this._actionMessage={type:"error",text:(o==null?void 0:o.message)||`${s} failed`}),i==="theme"&&await this._applyActiveTheme(),i==="ui"){window.location.replace(window.location.pathname+"?_switch="+Date.now());return}this.dispatchEvent(new CustomEvent("plugin-state-changed",{bubbles:!0,composed:!0})),await this._fetchAll({force:!0})}async _applyActiveTheme(){const i=await b(this.apiBase,"{ theme { css } }");if(!(i!=null&&i.theme))return;const{css:e}=i.theme;let t=document.querySelector("link[data-shenas-theme]");e?(t||(t=document.createElement("link"),t.rel="stylesheet",t.setAttribute("data-shenas-theme",""),document.head.appendChild(t)),t.href=e):t&&t.remove()}async _startInstall(i){this._installing=!0,this._selectedPlugin="",this._availablePlugins=null;const e=await b(this.apiBase,"query($kind: String!) { availablePlugins(kind: $kind) }",{kind:i}),t=(e==null?void 0:e.availablePlugins)||[],s=new Set((this._plugins[i]||[]).map(a=>a.name));this._availablePlugins=t.filter(a=>!s.has(a))}async _install(i){const e=this._selectedPlugin;if(!e)return;this._actionMessage=null,this._installing=!1;const t=this._displayPluginName(e),s=`install-${i}-${e}-${Date.now()}`;this.dispatchEvent(new CustomEvent("job-start",{bubbles:!0,composed:!0,detail:{id:s,label:`Adding ${t}`}}));const a=await this._streamJob(s,`${this.apiBase}/plugins/${i}/install-stream`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({names:[e],skip_verify:!0})});a!=null&&a.ok?(this._actionMessage={type:"success",text:a.message},await this._fetchAll()):this._actionMessage={type:"error",text:(a==null?void 0:a.message)||"Add failed"}}async _streamJob(i,e,t){try{const a=(await fetch(e,t)).body.getReader(),r=new TextDecoder;let o="",d=null;for(;;){const{done:c,value:p}=await a.read();if(c)break;o+=r.decode(p,{stream:!0});const f=o.split(`
`);o=f.pop();for(const y of f)if(y.startsWith("data: "))try{const g=JSON.parse(y.slice(6));g.event==="log"?this.dispatchEvent(new CustomEvent("job-log",{bubbles:!0,composed:!0,detail:{id:i,text:g.text}})):g.event==="done"&&(d={ok:g.ok,message:g.message},this.dispatchEvent(new CustomEvent("job-finish",{bubbles:!0,composed:!0,detail:{id:i,ok:g.ok,message:g.message}})))}catch{}}return d}catch(s){const a=s;return this.dispatchEvent(new CustomEvent("job-finish",{bubbles:!0,composed:!0,detail:{id:i,ok:!1,message:a.message}})),{ok:!1,message:a.message}}}_displayPluginName(i){return i.split("-").map(e=>e.charAt(0).toUpperCase()+e.slice(1)).join(" ")}_switchKind(i){this.activeKind=i,this._menuOpen=!1,this.onNavigate&&this.onNavigate(i)}_displayName(){if(this.activeKind==="flow")return"Flow";if(this.activeKind==="hotkeys")return"Hotkeys";const i=E.find(e=>e.id===this.activeKind);return i?i.label:this.activeKind}render(){return n`
      <button class="burger" @click=${()=>{this._menuOpen=!this._menuOpen}}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
        ${this._displayName()}
      </button>
      ${this._menuOpen?n`
        <div class="menu-overlay" @click=${()=>{this._menuOpen=!1}}></div>
        <div class="menu-panel">
          <a href="/settings/flow" aria-selected=${this.activeKind==="flow"} @click=${i=>{i.preventDefault(),this._switchKind("flow")}}>Flow</a>
          <a href="/settings/hotkeys" aria-selected=${this.activeKind==="hotkeys"} @click=${i=>{i.preventDefault(),this._switchKind("hotkeys")}}>Hotkeys</a>
          <span class="sidebar-section">Plugins</span>
          ${E.map(({id:i,label:e})=>n`
            <a href="/settings/${i}" aria-selected=${this.activeKind===i} @click=${t=>{t.preventDefault(),this._switchKind(i)}}>${e}</a>
          `)}
        </div>
      `:""}
      <shenas-page ?loading=${this._loading} loading-text="Loading plugins..." display-name="${this._displayName()}">
        ${N(this._actionMessage)}
        ${this.activeKind==="flow"?n`<shenas-pipeline-overview api-base="${this.apiBase}" .allPlugins=${this.allPlugins} .schemaPlugins=${this.schemaPlugins}></shenas-pipeline-overview>`:this.activeKind==="hotkeys"?n`<shenas-hotkeys api-base="${this.apiBase}" .actions=${this.allActions||[]}></shenas-hotkeys>`:this._renderKind(this.activeKind)}
      </shenas-page>
    `}_formatFreq(i){return i>=1440&&i%1440===0?`${i/1440}d`:i>=60&&i%60===0?`${i/60}h`:i>=1?`${i}m`:`${i*60}s`}_renderKind(i){var s;const e=this._plugins[i]||[],t=((s=E.find(a=>a.id===i))==null?void 0:s.label)||i;return n`
      <h3>${t}</h3>
      <shenas-data-list
        .columns=${[{label:"Name",render:a=>n`<a href="/settings/${i}/${a.name}">${a.displayName||a.name}</a>`},...i==="source"?[{label:"Last Synced",class:"mono",render:a=>a.syncedAt?a.syncedAt.slice(0,16).replace("T"," "):"never"}]:[],{label:"Status",render:a=>a.hasAuth&&a.isAuthenticated===!1?n`<span style="color:var(--shenas-error,#c62828);font-size:0.8rem">Needs Auth</span>`:n`<status-toggle ?enabled=${a.enabled!==!1} toggleable @toggle=${()=>this._togglePlugin(i,a.name,a.enabled!==!1)}></status-toggle>`}]}
        .rows=${e}
        .rowClass=${a=>a.enabled===!1?"disabled-row":""}
        ?show-add=${!this._installing}
        @add=${()=>this._startInstall(i)}
        empty-text="No ${t.toLowerCase()} added"
      ></shenas-data-list>
      ${this._installing?n`<shenas-form-panel
            title="Add ${t.slice(0,-1)}"
            submit-label="Add"
            @submit=${()=>this._install(i)}
            @cancel=${()=>{this._installing=!1}}
          >
            <div class="field">
              ${this._availablePlugins===null?n`<span style="color:var(--shenas-text-muted)">Loading available plugins...</span>`:this._availablePlugins.length===0?n`<span style="color:var(--shenas-text-muted)">No new ${t.toLowerCase()} available</span>`:n`<select
                      @change=${a=>{this._selectedPlugin=a.target.value}}
                      style="width:100%;padding:0.5rem;border:1px solid var(--shenas-border-input,#ddd);border-radius:6px;font-size:0.9rem"
                    >
                      <option value="">Select a ${t.slice(0,-1).toLowerCase()}...</option>
                      ${this._availablePlugins.map(a=>n`<option value=${a}>${this._displayPluginName(a)}</option>`)}
                    </select>`}
            </div>
          </shenas-form-panel>`:""}
    `}}h(M,"properties",{apiBase:{type:String,attribute:"api-base"},activeKind:{type:String,attribute:"active-kind"},onNavigate:{type:Function},onPluginsChanged:{type:Function},allActions:{type:Array},allPlugins:{type:Object},schemaPlugins:{type:Object},_plugins:{state:!0},_loading:{state:!0},_actionMessage:{state:!0},_installing:{state:!0},_availablePlugins:{state:!0},_selectedPlugin:{state:!0},_menuOpen:{state:!0}}),h(M,"styles",[P,I,W,C,T`
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
    `]);customElements.define("shenas-settings",M);class U extends x{constructor(){super();h(this,"_loadingTimer",null);this.apiBase="/api",this.kind="",this.name="",this.activeTab="details",this.dbStatus=null,this.schemaPlugins={},this.initialInfo=null,this._info=null,this._loading=!0,this._showLoading=!1,this._message=null,this._tables=[],this._syncing=!1,this._transforming=!1,this._schemaTransforms=[],this._selectedTable=null,this._previewRows=null,this._previewLoading=!1}willUpdate(e){(e.has("kind")||e.has("name"))&&(this.initialInfo&&!this._info&&(this._info=this.initialInfo,this._loading=!1,this._showLoading=!1),this._fetchInfo()),e.has("_loading")&&(this._loadingTimer&&clearTimeout(this._loadingTimer),this._loading?this._loadingTimer=setTimeout(()=>{this._showLoading=!0},200):this._showLoading=!1)}async _fetchInfo(){if(!this.kind||!this.name)return;this._loading=!0,this._message=null;const t=["pluginInfo(kind: $kind, name: $name)",this.kind==="dataset"?"transforms { id sourceDuckdbSchema sourceDuckdbTable targetDuckdbSchema targetDuckdbTable sourcePlugin description enabled }":""].filter(Boolean).join(" "),s=await b(this.apiBase,`query($kind: String!, $name: String!) { ${t} }`,{kind:this.kind,name:this.name});this._info=s==null?void 0:s.pluginInfo;const a=this.dbStatus,r=this.schemaPlugins,o=s==null?void 0:s.transforms,d=r?r[this.name]||[]:[];if(a){if(this.kind==="source"){const c=(a.schemas||[]).find(p=>p.name===this.name);this._tables=c?c.tables.filter(p=>!p.name.startsWith("_dlt_")):[]}else if(this.kind==="dataset"){const c=(a.schemas||[]).find(p=>p.name==="metrics");this._tables=c?c.tables.filter(p=>d.includes(p.name)):[]}}o&&(this._schemaTransforms=o.filter(c=>d.includes(c.targetDuckdbTable))),this._loading=!1,this._registerCommands()}_registerCommands(){if(!this._info)return;const e=this._info.display_name||this.name,t=[{id:`remove:${this.kind}:${this.name}`,category:"Plugin",label:`Remove ${e}`,action:()=>this._remove()}];this.kind==="dataset"&&t.unshift({id:`flush:${this.kind}:${this.name}`,category:"Plugin",label:`Flush ${e}`,action:()=>this._flush()},{id:`transform:${this.kind}:${this.name}`,category:"Plugin",label:`Transform ${e}`,action:()=>this._runTransforms()}),G(this,`plugin-detail:${this.kind}:${this.name}`,t)}async _toggle(){var r,o;const e=((r=this._info)==null?void 0:r.enabled)!==!1?"disable":"enable",t=e==="enable"?"mutation($k: String!, $n: String!) { enablePlugin(kind: $k, name: $n) { ok message } }":"mutation($k: String!, $n: String!) { disablePlugin(kind: $k, name: $n) { ok message } }",{data:s}=await m(this.apiBase,t,{k:this.kind,n:this.name}),a=e==="enable"?s==null?void 0:s.enablePlugin:s==null?void 0:s.disablePlugin;if(this._message={type:a!=null&&a.ok?"success":"error",text:(a==null?void 0:a.message)||`${e} failed`},await this._fetchInfo(),this.kind==="theme"){const d=await b(this.apiBase,"{ theme { css } }"),c=(o=d==null?void 0:d.theme)==null?void 0:o.css;let p=document.querySelector("link[data-shenas-theme]");c?(p||(p=document.createElement("link"),p.rel="stylesheet",p.setAttribute("data-shenas-theme",""),document.head.appendChild(p)),p.href=c):p&&p.remove()}if(this.kind==="ui"&&e==="enable"){window.location.replace(window.location.pathname+"?_switch="+Date.now());return}this.dispatchEvent(new CustomEvent("plugin-state-changed",{bubbles:!0,composed:!0}))}async _sync(){var s;this._syncing=!0,this._message=null;const e=((s=this._info)==null?void 0:s.display_name)||this.name,t=`sync-${this.name}-${Date.now()}`;this.dispatchEvent(new CustomEvent("job-start",{bubbles:!0,composed:!0,detail:{id:t,label:`Syncing ${e}`}}));try{const a=await fetch(`${this.apiBase}/sync/${this.name}`,{method:"POST"});if(!a.ok){const g=(await a.json().catch(()=>({}))).detail||`Sync failed (${a.status})`;this._message={type:"error",text:g},this.dispatchEvent(new CustomEvent("job-finish",{bubbles:!0,composed:!0,detail:{id:t,ok:!1,message:g}})),this._syncing=!1;return}const r=a.body.getReader(),o=new TextDecoder;let d="",c="",p=!1;for(;;){const{done:y,value:g}=await r.read();if(y)break;const l=o.decode(g,{stream:!0});for(const u of l.split(`
`))if(u.startsWith("event: ")&&(d=u.slice(7).trim()),u.startsWith("data: ")){c=u.slice(6);try{const $=JSON.parse(c),k=$.message||$.source||c;this.dispatchEvent(new CustomEvent("job-log",{bubbles:!0,composed:!0,detail:{id:t,text:k}}))}catch{}}d==="error"&&(p=!0)}let f="Sync complete";try{f=JSON.parse(c).message||f}catch{}this._message={type:p?"error":"success",text:f},this.dispatchEvent(new CustomEvent("job-finish",{bubbles:!0,composed:!0,detail:{id:t,ok:!p,message:f}})),p||await this._fetchInfo()}catch(a){const r=a;this._message={type:"error",text:`Sync failed: ${r.message}`},this.dispatchEvent(new CustomEvent("job-finish",{bubbles:!0,composed:!0,detail:{id:t,ok:!1,message:r.message}}))}this._syncing=!1}async _runTransforms(){this._transforming=!0,this._message=null;try{const{data:e}=await m(this.apiBase,"mutation($s: String!) { runSchemaTransforms(schema: $s) }",{s:this.name}),t=e==null?void 0:e.runSchemaTransforms;(t==null?void 0:t.count)!=null?(this._message={type:"success",text:`Ran ${t.count} transform(s)`},await this._fetchInfo()):this._message={type:"error",text:"Transform failed"}}catch(e){this._message={type:"error",text:`Transform failed: ${e.message}`}}this._transforming=!1}async _flush(){this._message=null;try{const{data:e}=await m(this.apiBase,"mutation($s: String!) { flushSchema(schemaPlugin: $s) }",{s:this.name}),t=e==null?void 0:e.flushSchema;(t==null?void 0:t.rows_deleted)!=null?(this._message={type:"success",text:`Flushed ${t.rows_deleted} rows`},await this._fetchInfo()):this._message={type:"error",text:"Flush failed"}}catch(e){this._message={type:"error",text:`Flush failed: ${e.message}`}}}async _remove(){var s;const e=((s=this._info)==null?void 0:s.display_name)||this.name.replace("-"," ").replace(/\b\w/g,a=>a.toUpperCase()),t=`remove-${this.kind}-${this.name}-${Date.now()}`;this.dispatchEvent(new CustomEvent("job-start",{bubbles:!0,composed:!0,detail:{id:t,label:`Removing ${e}`}}));try{const r=(await fetch(`${this.apiBase}/plugins/${this.kind}/${this.name}/remove-stream`,{method:"POST"})).body.getReader(),o=new TextDecoder;let d="",c=!1;for(;;){const{done:p,value:f}=await r.read();if(p)break;d+=o.decode(f,{stream:!0});const y=d.split(`
`);d=y.pop();for(const g of y)if(g.startsWith("data: "))try{const l=JSON.parse(g.slice(6));l.event==="log"?this.dispatchEvent(new CustomEvent("job-log",{bubbles:!0,composed:!0,detail:{id:t,text:l.text}})):l.event==="done"&&(c=l.ok,this.dispatchEvent(new CustomEvent("job-finish",{bubbles:!0,composed:!0,detail:{id:t,ok:l.ok,message:l.message}})))}catch{}}c?(this.dispatchEvent(new CustomEvent("plugins-changed",{bubbles:!0,composed:!0,detail:null})),window.history.pushState({},"",`/settings/${this.kind}`),window.dispatchEvent(new PopStateEvent("popstate"))):this._message={type:"error",text:"Remove failed"}}catch(a){const r=a;this.dispatchEvent(new CustomEvent("job-finish",{bubbles:!0,composed:!0,detail:{id:t,ok:!1,message:r.message}})),this._message={type:"error",text:r.message}}}_switchTab(e){this.activeTab=e;const t=`/settings/${this.kind}/${this.name}`,s=e==="details"?t:`${t}/${e}`;window.history.pushState({},"",s)}async _fetchPreview(e){if(this._selectedTable=e,!e){this._previewRows=null;return}this._previewLoading=!0,this._previewRows=null;try{const t=this.kind==="dataset"?"metrics":this.name;this._previewRows=await D(this.apiBase,`SELECT * FROM "${t}"."${e}" ORDER BY 1 DESC LIMIT 100`)}catch(t){console.error("Preview query failed:",t),this._previewRows=null}this._previewLoading=!1}_renderPreviewTable(){const e=Object.keys(this._previewRows[0]).filter(t=>!t.startsWith("_dlt"));return n`
      <table class="data-table">
        <thead><tr>${e.map(t=>n`<th>${t}</th>`)}</tr></thead>
        <tbody>${this._previewRows.map(t=>n`
          <tr>${e.map(s=>n`<td title="${t[s]??""}">${t[s]??""}</td>`)}</tr>
        `)}</tbody>
      </table>`}_renderData(){var t,s;const e=this._tables||[];if(e.length===0)return n`<p style="color:var(--shenas-text-muted,#888)">No tables synced yet.</p>`;if(!this._selectedTable){const a=(t=this._info)==null?void 0:t.primary_table,r=a&&e.some(o=>o.name===a)?a:(s=e[0])==null?void 0:s.name;if(r)return requestAnimationFrame(()=>this._fetchPreview(r)),n`<p style="color:var(--shenas-text-muted,#888)">Loading...</p>`}return n`
      <div class="data-toolbar">
        <select @change=${a=>this._fetchPreview(a.target.value)}>
          <option value="">Select a table</option>
          ${e.map(a=>n`<option value=${a.name} ?selected=${this._selectedTable===a.name}>${a.name}${a.rows?` (${a.rows})`:""}</option>`)}
        </select>
        ${this._previewLoading?n`<span style="color:var(--shenas-text-muted,#888)">Loading...</span>`:""}
      </div>
      ${this._previewRows&&this._previewRows.length>0?this._renderPreviewTable():this._selectedTable&&!this._previewLoading?n`<p style="color:var(--shenas-text-muted,#888)">Table is empty.</p>`:""}
    `}render(){var e,t;return n`
      <shenas-page ?loading=${this._showLoading} ?empty=${!this._loading&&!this._info} empty-text="Plugin not found."
        display-name="${((e=this._info)==null?void 0:e.display_name)||((t=this._info)==null?void 0:t.name)||this.name}">
        ${this._info?this._renderContent():""}
      </shenas-page>
    `}_renderContent(){var a,r,o;const e=this._info,t=e.enabled!==!1,s=`/settings/${this.kind}/${this.name}`;return n`
      <a class="back" href="/settings/${this.kind}" @click=${d=>{d.preventDefault(),window.history.pushState({},"",`/settings/${this.kind}`),window.dispatchEvent(new PopStateEvent("popstate"))}}>&larr; Back to ${this.kind}s</a>

      <div class="title-row">
        <h2>${e.display_name||e.name} <span class="kind-badge">${e.kind}</span>${e.version?n` <span class="version">${e.version}</span>`:""}</h2>
        <div class="title-actions">
          ${this.kind==="source"&&t?n`<button @click=${this._sync} ?disabled=${this._syncing}>${this._syncing?"Syncing...":"Sync"}</button>`:""}
          ${this.kind==="dataset"?n`<button @click=${this._runTransforms} ?disabled=${this._transforming}>${this._transforming?"Transforming...":"Transform"}</button>`:""}
          ${this.kind==="dataset"?n`<button class="danger" @click=${this._flush}>Flush</button>`:""}
          <button class="danger" @click=${this._remove}>Remove</button>
        </div>
      </div>

      ${N(this._message)}

      <div class="tabs">
        <a class="tab" href="${s}" aria-selected=${this.activeTab==="details"}
          @click=${d=>{d.preventDefault(),this._switchTab("details")}}>Details</a>
        ${(a=this._info)!=null&&a.has_config?n`
          <a class="tab" href="${s}/config" aria-selected=${this.activeTab==="config"}
            @click=${d=>{d.preventDefault(),this._switchTab("config")}}>Config</a>
        `:""}
        ${(r=this._info)!=null&&r.has_auth?n`
          <a class="tab" href="${s}/auth" aria-selected=${this.activeTab==="auth"}
            @click=${d=>{d.preventDefault(),this._switchTab("auth")}}>Auth</a>
        `:""}
        ${((o=this._info)==null?void 0:o.has_data)!==!1?n`
          <a class="tab" href="${s}/data" aria-selected=${this.activeTab==="data"}
            @click=${d=>{d.preventDefault(),this._switchTab("data")}}>Data</a>
        `:""}
        <a class="tab" href="${s}/logs" aria-selected=${this.activeTab==="logs"}
          @click=${d=>{d.preventDefault(),this._switchTab("logs")}}>Logs</a>
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

      ${this.kind==="source"||this.kind==="dataset"?n`
          <h4 class="section-title">Resources</h4>
          <shenas-data-list
            .columns=${[{key:"name",label:"Table",class:"mono"},{key:"rows",label:"Rows",class:"muted"},{label:"Range",class:"muted",render:s=>s.earliest?`${s.earliest} - ${s.latest}`:""}]}
            .rows=${this._tables}
            empty-text="No tables synced yet"
          ></shenas-data-list>`:""}

      ${this.kind==="source"?n`
          <h4 class="section-title">Transforms</h4>
          <shenas-transforms api-base="${this.apiBase}" source="${this.name}"></shenas-transforms>`:""}

      ${this.kind==="dataset"&&this._schemaTransforms.length>0?n`
          <h4 class="section-title">Transforms</h4>
          <shenas-data-list
            .columns=${[{key:"id",label:"ID",class:"muted"},{label:"Source",class:"mono",render:s=>`${s.sourceDuckdbSchema}.${s.sourceDuckdbTable}`},{label:"Target",class:"mono",render:s=>`${s.targetDuckdbSchema}.${s.targetDuckdbTable}`},{label:"Description",render:s=>s.description||""},{label:"Status",render:s=>n`<status-toggle ?enabled=${s.enabled}></status-toggle>`}]}
            .rows=${this._schemaTransforms}
            .rowClass=${s=>s.enabled?"":"disabled-row"}
            empty-text="No transforms"
          ></shenas-data-list>`:""}

    `}_stateRow(e,t){return t?n`
      <div class="state-row">
        <span class="state-label">${e}</span>
        <span class="state-value">${t.slice(0,19)}</span>
      </div>
    `:""}}h(U,"properties",{apiBase:{type:String,attribute:"api-base"},kind:{type:String},name:{type:String},activeTab:{type:String,attribute:"active-tab"},dbStatus:{type:Object},schemaPlugins:{type:Object},initialInfo:{type:Object},_info:{state:!0},_loading:{state:!0},_showLoading:{state:!0},_message:{state:!0},_tables:{state:!0},_syncing:{state:!0},_transforming:{state:!0},_schemaTransforms:{state:!0},_selectedTable:{state:!0},_previewRows:{state:!0},_previewLoading:{state:!0}}),h(U,"styles",[P,W,C,ee,T`
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
    `]);customElements.define("shenas-plugin-detail",U);const V="background:none;border:none;cursor:pointer;color:var(--shenas-text-faint, #aaa);font-size:0.7rem;padding:0 2px";class K extends x{constructor(){super(),this.apiBase="/api",this.source="",this._transforms=[],this._loading=!0,this._editing=null,this._editSql="",this._message=null,this._previewRows=null,this._creating=!1,this._newForm=this._emptyForm(),this._dbTables={},this._schemaTables={}}_emptyForm(){return{source_duckdb_table:"",target_duckdb_table:"",description:"",sql:""}}connectedCallback(){super.connectedCallback(),this._fetchAll()}async _fetchAll(){this._loading=!0;const i=await b(this.apiBase,"query($source: String) { transforms(source: $source) { id sourceDuckdbSchema sourceDuckdbTable targetDuckdbSchema targetDuckdbTable sourcePlugin description sql isDefault enabled } }",{source:this.source||null});this._transforms=(i==null?void 0:i.transforms)||[],this._loading=!1,this._registerCommands()}_registerCommands(){const i=[];for(const e of this._transforms){const t=e.description||`${e.sourceDuckdbTable} -> ${e.targetDuckdbTable}`;i.push({id:`transform:toggle:${e.id}`,category:"Transform",label:`${e.enabled?"Disable":"Enable"} #${e.id}`,description:t,action:()=>this._toggle(e)}),e.isDefault||i.push({id:`transform:delete:${e.id}`,category:"Transform",label:`Delete #${e.id}`,description:t,action:()=>this._delete(e)})}G(this,`transforms:${this.source}`,i)}_inspectTable(i,e){this.dispatchEvent(new CustomEvent("inspect-table",{bubbles:!0,composed:!0,detail:{schema:i,table:e}}))}async _toggle(i){const e=i.enabled?"mutation($id: Int!) { disableTransform(transformId: $id) { id enabled } }":"mutation($id: Int!) { enableTransform(transformId: $id) { id enabled } }";await m(this.apiBase,e,{id:i.id}),await this._fetchAll()}async _delete(i){var s;const{ok:e,data:t}=await m(this.apiBase,"mutation($id: Int!) { deleteTransform(transformId: $id) { ok message } }",{id:i.id});e&&((s=t==null?void 0:t.deleteTransform)!=null&&s.ok)?(this._message={type:"success",text:`Deleted transform #${i.id}`},await this._fetchAll()):this._message={type:"error",text:"Delete failed"}}_startEdit(i){this._editing=i.id,this._editSql=i.sql,this._previewRows=null}_cancelEdit(){this._editing=null,this._editSql="",this._previewRows=null}async _saveEdit(){const{ok:i}=await m(this.apiBase,"mutation($id: Int!, $sql: String!) { updateTransform(transformId: $id, sql: $sql) { id } }",{id:this._editing,sql:this._editSql});i?(this._message={type:"success",text:"Transform updated"},this._editing=null,await this._fetchAll()):this._message={type:"error",text:"Update failed"}}async _startCreate(){this._creating=!0,this._newForm=this._emptyForm(),this._editing=null,this._previewRows=null;const i=await b(this.apiBase,"{ dbTables schemaTables }");this._dbTables=(i==null?void 0:i.dbTables)||{},this._schemaTables=(i==null?void 0:i.schemaTables)||{}}_cancelCreate(){this._creating=!1,this._newForm=this._emptyForm()}_updateNewForm(i,e){this._newForm={...this._newForm,[i]:e}}async _saveCreate(){const i=this._newForm;if(!i.source_duckdb_table||!i.target_duckdb_table||!i.sql){this._message={type:"error",text:"Fill in all required fields"};return}const{ok:e,data:t}=await m(this.apiBase,"mutation($input: TransformCreateInput!) { createTransform(transformInput: $input) { id } }",{input:{sourceDuckdbSchema:this.source,sourceDuckdbTable:i.source_duckdb_table,targetDuckdbSchema:"metrics",targetDuckdbTable:i.target_duckdb_table,sourcePlugin:this.source,description:i.description,sql:i.sql}});e?(this._message={type:"success",text:"Transform created"},this._creating=!1,this._newForm=this._emptyForm(),await this._fetchAll()):this._message={type:"error",text:(t==null?void 0:t.detail)||"Create failed"}}async _preview(){const{ok:i,data:e}=await m(this.apiBase,"mutation($id: Int!) { testTransform(transformId: $id, limit: 5) }",{id:this._editing});i?this._previewRows=e==null?void 0:e.testTransform:this._message={type:"error",text:(e==null?void 0:e.detail)||"Preview failed"}}render(){return this._loading?n``:n`
      <div>
      ${N(this._message)}
      ${this._editing?this._renderEditor():""}
      ${this._creating?this._renderCreateForm():""}
      <shenas-data-list
        ?show-add=${!this._creating&&!this._editing}
        @add=${this._startCreate}
        .columns=${[{key:"id",label:"ID",class:"muted"},{label:"Source",class:"mono",render:i=>n`${i.sourceDuckdbSchema}.${i.sourceDuckdbTable} <button style=${V} title="Inspect table" @click=${()=>this._inspectTable(i.sourceDuckdbSchema,i.sourceDuckdbTable)}>&#9655;</button>`},{label:"Target",class:"mono",render:i=>n`${i.targetDuckdbSchema}.${i.targetDuckdbTable} <button style=${V} title="Inspect table" @click=${()=>this._inspectTable(i.targetDuckdbSchema,i.targetDuckdbTable)}>&#9655;</button>`},{label:"Description",render:i=>n`${i.description||""}${i.isDefault?n`<span style="font-size:0.75rem;color:var(--shenas-text-muted, #888);background:var(--shenas-border-light, #f0f0f0);padding:1px 5px;border-radius:3px;margin-left:4px">default</span>`:""}`},{label:"Status",render:i=>n`<status-toggle ?enabled=${i.enabled} toggleable @toggle=${()=>this._toggle(i)}></status-toggle>`}]}
        .rows=${this._transforms}
        .rowClass=${i=>i.enabled?"":"disabled-row"}
        .actions=${i=>n`
          ${i.isDefault?n`<button @click=${()=>this._startEdit(i)}>View</button>`:n`<button @click=${()=>this._startEdit(i)}>Edit</button>`}
          ${i.isDefault?"":n`<button class="danger" @click=${()=>this._delete(i)}>Delete</button>`}
        `}
        empty-text="No transforms"
      ></shenas-data-list>
      </div>
    `}_renderCreateForm(){const i=this._newForm,e=this.source,t=this._dbTables[e]||[],s=Object.values(this._schemaTables||{}).flat();return n`
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
              .value=${i.source_duckdb_table}
              @change=${a=>this._updateNewForm("source_duckdb_table",a.target.value)}
            >
              <option value="">-- select --</option>
              ${t.map(a=>n`<option value=${a} ?selected=${i.source_duckdb_table===a}>${a}</option>`)}
            </select>
          </label>
          <label>
            Schema table
            <select
              .value=${i.target_duckdb_table}
              @change=${a=>this._updateNewForm("target_duckdb_table",a.target.value)}
            >
              <option value="">-- select --</option>
              ${s.map(a=>n`<option value=${a} ?selected=${i.target_duckdb_table===a}>${a}</option>`)}
            </select>
          </label>
          <label class="form-full">
            Description
            <input
              .value=${i.description}
              @input=${a=>this._updateNewForm("description",a.target.value)}
            />
          </label>
        </div>
        <textarea
          .value=${i.sql}
          @input=${a=>this._updateNewForm("sql",a.target.value)}
          placeholder="SELECT ... FROM ${e}.${i.source_duckdb_table||"table_name"}"
        ></textarea>
      </shenas-form-panel>
    `}_renderEditor(){const i=this._transforms.find(t=>t.id===this._editing);if(!i)return"";const e=i.isDefault;return n`
      <div class="edit-panel">
        <h3>
          ${e?"View":"Edit"}: ${i.sourceDuckdbSchema}.${i.sourceDuckdbTable} ->
          ${i.targetDuckdbSchema}.${i.targetDuckdbTable}
        </h3>
        <textarea
          .value=${this._editSql}
          @input=${t=>this._editSql=t.target.value}
          ?readonly=${e}
          class="${e?"readonly":""}"
        ></textarea>
        <div class="edit-actions">
          ${e?"":n`<button @click=${this._saveEdit}>Save</button>`}
          <button @click=${this._preview}>Preview</button>
          <button @click=${this._cancelEdit}>${e?"Close":"Cancel"}</button>
        </div>
        ${this._previewRows?this._renderPreview():""}
      </div>
    `}_renderPreview(){if(!this._previewRows||this._previewRows.length===0)return n`<p class="loading">No preview rows</p>`;const i=Object.keys(this._previewRows[0]);return n`
      <div class="preview-table">
        <table>
          <thead>
            <tr>
              ${i.map(e=>n`<th>${e}</th>`)}
            </tr>
          </thead>
          <tbody>
            ${this._previewRows.map(e=>n`
                <tr>
                  ${i.map(t=>n`<td>${e[t]}</td>`)}
                </tr>
              `)}
          </tbody>
        </table>
      </div>
    `}}h(K,"properties",{apiBase:{type:String,attribute:"api-base"},source:{type:String},_transforms:{state:!0},_loading:{state:!0},_editing:{state:!0},_editSql:{state:!0},_message:{state:!0},_previewRows:{state:!0},_creating:{state:!0},_newForm:{state:!0},_dbTables:{state:!0},_schemaTables:{state:!0}}),h(K,"styles",[te,P,I,C,T`
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
    `]);customElements.define("shenas-transforms",K);
