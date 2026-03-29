var dt=Object.defineProperty;var pt=(r,t,e)=>t in r?dt(r,t,{enumerable:!0,configurable:!0,writable:!0,value:e}):r[t]=e;var z=(r,t,e)=>pt(r,typeof t!="symbol"?t+"":t,e);/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const T=globalThis,W=T.ShadowRoot&&(T.ShadyCSS===void 0||T.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,q=Symbol(),F=new WeakMap;let nt=class{constructor(t,e,s){if(this._$cssResult$=!0,s!==q)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o;const e=this.t;if(W&&t===void 0){const s=e!==void 0&&e.length===1;s&&(t=F.get(e)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),s&&F.set(e,t))}return t}toString(){return this.cssText}};const ut=r=>new nt(typeof r=="string"?r:r+"",void 0,q),$t=(r,...t)=>{const e=r.length===1?r[0]:t.reduce((s,i,o)=>s+(n=>{if(n._$cssResult$===!0)return n.cssText;if(typeof n=="number")return n;throw Error("Value passed to 'css' function must be a 'css' function result: "+n+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+r[o+1],r[0]);return new nt(e,r,q)},_t=(r,t)=>{if(W)r.adoptedStyleSheets=t.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(const e of t){const s=document.createElement("style"),i=T.litNonce;i!==void 0&&s.setAttribute("nonce",i),s.textContent=e.cssText,r.appendChild(s)}},J=W?r=>r:r=>r instanceof CSSStyleSheet?(t=>{let e="";for(const s of t.cssRules)e+=s.cssText;return ut(e)})(r):r;/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const{is:ft,defineProperty:mt,getOwnPropertyDescriptor:gt,getOwnPropertyNames:At,getOwnPropertySymbols:vt,getPrototypeOf:yt}=Object,m=globalThis,K=m.trustedTypes,bt=K?K.emptyScript:"",D=m.reactiveElementPolyfillSupport,x=(r,t)=>r,I={toAttribute(r,t){switch(t){case Boolean:r=r?bt:null;break;case Object:case Array:r=r==null?r:JSON.stringify(r)}return r},fromAttribute(r,t){let e=r;switch(t){case Boolean:e=r!==null;break;case Number:e=r===null?null:Number(r);break;case Object:case Array:try{e=JSON.parse(r)}catch{e=null}}return e}},ot=(r,t)=>!ft(r,t),G={attribute:!0,type:String,converter:I,reflect:!1,useDefault:!1,hasChanged:ot};Symbol.metadata??(Symbol.metadata=Symbol("metadata")),m.litPropertyMetadata??(m.litPropertyMetadata=new WeakMap);let b=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??(this.l=[])).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=G){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){const s=Symbol(),i=this.getPropertyDescriptor(t,s,e);i!==void 0&&mt(this.prototype,t,i)}}static getPropertyDescriptor(t,e,s){const{get:i,set:o}=gt(this.prototype,t)??{get(){return this[e]},set(n){this[e]=n}};return{get:i,set(n){const h=i==null?void 0:i.call(this);o==null||o.call(this,n),this.requestUpdate(t,h,s)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??G}static _$Ei(){if(this.hasOwnProperty(x("elementProperties")))return;const t=yt(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(x("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(x("properties"))){const e=this.properties,s=[...At(e),...vt(e)];for(const i of s)this.createProperty(i,e[i])}const t=this[Symbol.metadata];if(t!==null){const e=litPropertyMetadata.get(t);if(e!==void 0)for(const[s,i]of e)this.elementProperties.set(s,i)}this._$Eh=new Map;for(const[e,s]of this.elementProperties){const i=this._$Eu(e,s);i!==void 0&&this._$Eh.set(i,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){const e=[];if(Array.isArray(t)){const s=new Set(t.flat(1/0).reverse());for(const i of s)e.unshift(J(i))}else t!==void 0&&e.push(J(t));return e}static _$Eu(t,e){const s=e.attribute;return s===!1?void 0:typeof s=="string"?s:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){var t;this._$ES=new Promise(e=>this.enableUpdating=e),this._$AL=new Map,this._$E_(),this.requestUpdate(),(t=this.constructor.l)==null||t.forEach(e=>e(this))}addController(t){var e;(this._$EO??(this._$EO=new Set)).add(t),this.renderRoot!==void 0&&this.isConnected&&((e=t.hostConnected)==null||e.call(t))}removeController(t){var e;(e=this._$EO)==null||e.delete(t)}_$E_(){const t=new Map,e=this.constructor.elementProperties;for(const s of e.keys())this.hasOwnProperty(s)&&(t.set(s,this[s]),delete this[s]);t.size>0&&(this._$Ep=t)}createRenderRoot(){const t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return _t(t,this.constructor.elementStyles),t}connectedCallback(){var t;this.renderRoot??(this.renderRoot=this.createRenderRoot()),this.enableUpdating(!0),(t=this._$EO)==null||t.forEach(e=>{var s;return(s=e.hostConnected)==null?void 0:s.call(e)})}enableUpdating(t){}disconnectedCallback(){var t;(t=this._$EO)==null||t.forEach(e=>{var s;return(s=e.hostDisconnected)==null?void 0:s.call(e)})}attributeChangedCallback(t,e,s){this._$AK(t,s)}_$ET(t,e){var o;const s=this.constructor.elementProperties.get(t),i=this.constructor._$Eu(t,s);if(i!==void 0&&s.reflect===!0){const n=(((o=s.converter)==null?void 0:o.toAttribute)!==void 0?s.converter:I).toAttribute(e,s.type);this._$Em=t,n==null?this.removeAttribute(i):this.setAttribute(i,n),this._$Em=null}}_$AK(t,e){var o,n;const s=this.constructor,i=s._$Eh.get(t);if(i!==void 0&&this._$Em!==i){const h=s.getPropertyOptions(i),a=typeof h.converter=="function"?{fromAttribute:h.converter}:((o=h.converter)==null?void 0:o.fromAttribute)!==void 0?h.converter:I;this._$Em=i;const c=a.fromAttribute(e,h.type);this[i]=c??((n=this._$Ej)==null?void 0:n.get(i))??c,this._$Em=null}}requestUpdate(t,e,s,i=!1,o){var n;if(t!==void 0){const h=this.constructor;if(i===!1&&(o=this[t]),s??(s=h.getPropertyOptions(t)),!((s.hasChanged??ot)(o,e)||s.useDefault&&s.reflect&&o===((n=this._$Ej)==null?void 0:n.get(t))&&!this.hasAttribute(h._$Eu(t,s))))return;this.C(t,e,s)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,e,{useDefault:s,reflect:i,wrapped:o},n){s&&!(this._$Ej??(this._$Ej=new Map)).has(t)&&(this._$Ej.set(t,n??e??this[t]),o!==!0||n!==void 0)||(this._$AL.has(t)||(this.hasUpdated||s||(e=void 0),this._$AL.set(t,e)),i===!0&&this._$Em!==t&&(this._$Eq??(this._$Eq=new Set)).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}const t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){var s;if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??(this.renderRoot=this.createRenderRoot()),this._$Ep){for(const[o,n]of this._$Ep)this[o]=n;this._$Ep=void 0}const i=this.constructor.elementProperties;if(i.size>0)for(const[o,n]of i){const{wrapped:h}=n,a=this[o];h!==!0||this._$AL.has(o)||a===void 0||this.C(o,void 0,n,a)}}let t=!1;const e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),(s=this._$EO)==null||s.forEach(i=>{var o;return(o=i.hostUpdate)==null?void 0:o.call(i)}),this.update(e)):this._$EM()}catch(i){throw t=!1,this._$EM(),i}t&&this._$AE(e)}willUpdate(t){}_$AE(t){var e;(e=this._$EO)==null||e.forEach(s=>{var i;return(i=s.hostUpdated)==null?void 0:i.call(s)}),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&(this._$Eq=this._$Eq.forEach(e=>this._$ET(e,this[e]))),this._$EM()}updated(t){}firstUpdated(t){}};b.elementStyles=[],b.shadowRootOptions={mode:"open"},b[x("elementProperties")]=new Map,b[x("finalized")]=new Map,D==null||D({ReactiveElement:b}),(m.reactiveElementVersions??(m.reactiveElementVersions=[])).push("2.1.2");/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const C=globalThis,Q=r=>r,R=C.trustedTypes,X=R?R.createPolicy("lit-html",{createHTML:r=>r}):void 0,at="$lit$",f=`lit$${Math.random().toFixed(9).slice(2)}$`,ht="?"+f,Et=`<${ht}>`,y=document,U=()=>y.createComment(""),O=r=>r===null||typeof r!="object"&&typeof r!="function",Z=Array.isArray,St=r=>Z(r)||typeof(r==null?void 0:r[Symbol.iterator])=="function",L=`[ 	
\f\r]`,w=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,Y=/-->/g,tt=/>/g,g=RegExp(`>|${L}(?:([^\\s"'>=/]+)(${L}*=${L}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),et=/'/g,st=/"/g,lt=/^(?:script|style|textarea|title)$/i,wt=r=>(t,...e)=>({_$litType$:r,strings:t,values:e}),u=wt(1),E=Symbol.for("lit-noChange"),d=Symbol.for("lit-nothing"),it=new WeakMap,A=y.createTreeWalker(y,129);function ct(r,t){if(!Z(r)||!r.hasOwnProperty("raw"))throw Error("invalid template strings array");return X!==void 0?X.createHTML(t):t}const xt=(r,t)=>{const e=r.length-1,s=[];let i,o=t===2?"<svg>":t===3?"<math>":"",n=w;for(let h=0;h<e;h++){const a=r[h];let c,p,l=-1,$=0;for(;$<a.length&&(n.lastIndex=$,p=n.exec(a),p!==null);)$=n.lastIndex,n===w?p[1]==="!--"?n=Y:p[1]!==void 0?n=tt:p[2]!==void 0?(lt.test(p[2])&&(i=RegExp("</"+p[2],"g")),n=g):p[3]!==void 0&&(n=g):n===g?p[0]===">"?(n=i??w,l=-1):p[1]===void 0?l=-2:(l=n.lastIndex-p[2].length,c=p[1],n=p[3]===void 0?g:p[3]==='"'?st:et):n===st||n===et?n=g:n===Y||n===tt?n=w:(n=g,i=void 0);const _=n===g&&r[h+1].startsWith("/>")?" ":"";o+=n===w?a+Et:l>=0?(s.push(c),a.slice(0,l)+at+a.slice(l)+f+_):a+f+(l===-2?h:_)}return[ct(r,o+(r[e]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),s]};class H{constructor({strings:t,_$litType$:e},s){let i;this.parts=[];let o=0,n=0;const h=t.length-1,a=this.parts,[c,p]=xt(t,e);if(this.el=H.createElement(c,s),A.currentNode=this.el.content,e===2||e===3){const l=this.el.content.firstChild;l.replaceWith(...l.childNodes)}for(;(i=A.nextNode())!==null&&a.length<h;){if(i.nodeType===1){if(i.hasAttributes())for(const l of i.getAttributeNames())if(l.endsWith(at)){const $=p[n++],_=i.getAttribute(l).split(f),M=/([.?@])?(.*)/.exec($);a.push({type:1,index:o,name:M[2],strings:_,ctor:M[1]==="."?Pt:M[1]==="?"?Ut:M[1]==="@"?Ot:k}),i.removeAttribute(l)}else l.startsWith(f)&&(a.push({type:6,index:o}),i.removeAttribute(l));if(lt.test(i.tagName)){const l=i.textContent.split(f),$=l.length-1;if($>0){i.textContent=R?R.emptyScript:"";for(let _=0;_<$;_++)i.append(l[_],U()),A.nextNode(),a.push({type:2,index:++o});i.append(l[$],U())}}}else if(i.nodeType===8)if(i.data===ht)a.push({type:2,index:o});else{let l=-1;for(;(l=i.data.indexOf(f,l+1))!==-1;)a.push({type:7,index:o}),l+=f.length-1}o++}}static createElement(t,e){const s=y.createElement("template");return s.innerHTML=t,s}}function S(r,t,e=r,s){var n,h;if(t===E)return t;let i=s!==void 0?(n=e._$Co)==null?void 0:n[s]:e._$Cl;const o=O(t)?void 0:t._$litDirective$;return(i==null?void 0:i.constructor)!==o&&((h=i==null?void 0:i._$AO)==null||h.call(i,!1),o===void 0?i=void 0:(i=new o(r),i._$AT(r,e,s)),s!==void 0?(e._$Co??(e._$Co=[]))[s]=i:e._$Cl=i),i!==void 0&&(t=S(r,i._$AS(r,t.values),i,s)),t}class Ct{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){const{el:{content:e},parts:s}=this._$AD,i=((t==null?void 0:t.creationScope)??y).importNode(e,!0);A.currentNode=i;let o=A.nextNode(),n=0,h=0,a=s[0];for(;a!==void 0;){if(n===a.index){let c;a.type===2?c=new N(o,o.nextSibling,this,t):a.type===1?c=new a.ctor(o,a.name,a.strings,this,t):a.type===6&&(c=new Ht(o,this,t)),this._$AV.push(c),a=s[++h]}n!==(a==null?void 0:a.index)&&(o=A.nextNode(),n++)}return A.currentNode=y,i}p(t){let e=0;for(const s of this._$AV)s!==void 0&&(s.strings!==void 0?(s._$AI(t,s,e),e+=s.strings.length-2):s._$AI(t[e])),e++}}class N{get _$AU(){var t;return((t=this._$AM)==null?void 0:t._$AU)??this._$Cv}constructor(t,e,s,i){this.type=2,this._$AH=d,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=s,this.options=i,this._$Cv=(i==null?void 0:i.isConnected)??!0}get parentNode(){let t=this._$AA.parentNode;const e=this._$AM;return e!==void 0&&(t==null?void 0:t.nodeType)===11&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=S(this,t,e),O(t)?t===d||t==null||t===""?(this._$AH!==d&&this._$AR(),this._$AH=d):t!==this._$AH&&t!==E&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):St(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==d&&O(this._$AH)?this._$AA.nextSibling.data=t:this.T(y.createTextNode(t)),this._$AH=t}$(t){var o;const{values:e,_$litType$:s}=t,i=typeof s=="number"?this._$AC(t):(s.el===void 0&&(s.el=H.createElement(ct(s.h,s.h[0]),this.options)),s);if(((o=this._$AH)==null?void 0:o._$AD)===i)this._$AH.p(e);else{const n=new Ct(i,this),h=n.u(this.options);n.p(e),this.T(h),this._$AH=n}}_$AC(t){let e=it.get(t.strings);return e===void 0&&it.set(t.strings,e=new H(t)),e}k(t){Z(this._$AH)||(this._$AH=[],this._$AR());const e=this._$AH;let s,i=0;for(const o of t)i===e.length?e.push(s=new N(this.O(U()),this.O(U()),this,this.options)):s=e[i],s._$AI(o),i++;i<e.length&&(this._$AR(s&&s._$AB.nextSibling,i),e.length=i)}_$AR(t=this._$AA.nextSibling,e){var s;for((s=this._$AP)==null?void 0:s.call(this,!1,!0,e);t!==this._$AB;){const i=Q(t).nextSibling;Q(t).remove(),t=i}}setConnected(t){var e;this._$AM===void 0&&(this._$Cv=t,(e=this._$AP)==null||e.call(this,t))}}class k{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,s,i,o){this.type=1,this._$AH=d,this._$AN=void 0,this.element=t,this.name=e,this._$AM=i,this.options=o,s.length>2||s[0]!==""||s[1]!==""?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=d}_$AI(t,e=this,s,i){const o=this.strings;let n=!1;if(o===void 0)t=S(this,t,e,0),n=!O(t)||t!==this._$AH&&t!==E,n&&(this._$AH=t);else{const h=t;let a,c;for(t=o[0],a=0;a<o.length-1;a++)c=S(this,h[s+a],e,a),c===E&&(c=this._$AH[a]),n||(n=!O(c)||c!==this._$AH[a]),c===d?t=d:t!==d&&(t+=(c??"")+o[a+1]),this._$AH[a]=c}n&&!i&&this.j(t)}j(t){t===d?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}}class Pt extends k{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===d?void 0:t}}class Ut extends k{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==d)}}class Ot extends k{constructor(t,e,s,i,o){super(t,e,s,i,o),this.type=5}_$AI(t,e=this){if((t=S(this,t,e,0)??d)===E)return;const s=this._$AH,i=t===d&&s!==d||t.capture!==s.capture||t.once!==s.once||t.passive!==s.passive,o=t!==d&&(s===d||i);i&&this.element.removeEventListener(this.name,this,s),o&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){var e;typeof this._$AH=="function"?this._$AH.call(((e=this.options)==null?void 0:e.host)??this.element,t):this._$AH.handleEvent(t)}}class Ht{constructor(t,e,s){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=s}get _$AU(){return this._$AM._$AU}_$AI(t){S(this,t)}}const j=C.litHtmlPolyfillSupport;j==null||j(H,N),(C.litHtmlVersions??(C.litHtmlVersions=[])).push("3.3.2");const Nt=(r,t,e)=>{const s=(e==null?void 0:e.renderBefore)??t;let i=s._$litPart$;if(i===void 0){const o=(e==null?void 0:e.renderBefore)??null;s._$litPart$=i=new N(t.insertBefore(U(),o),o,void 0,e??{})}return i._$AI(r),i};/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const v=globalThis;class P extends b{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){var e;const t=super.createRenderRoot();return(e=this.renderOptions).renderBefore??(e.renderBefore=t.firstChild),t}update(t){const e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=Nt(e,this.renderRoot,this.renderOptions)}connectedCallback(){var t;super.connectedCallback(),(t=this._$Do)==null||t.setConnected(!0)}disconnectedCallback(){var t;super.disconnectedCallback(),(t=this._$Do)==null||t.setConnected(!1)}render(){return E}}var rt;P._$litElement$=!0,P.finalized=!0,(rt=v.litElementHydrateSupport)==null||rt.call(v,{LitElement:P});const B=v.litElementPolyfillSupport;B==null||B({LitElement:P});(v.litElementVersions??(v.litElementVersions=[])).push("4.2.2");class V extends P{constructor(){super(),this.apiBase="/api",this._pipes=[],this._dbStatus=null,this._components=[],this._loading=!0}connectedCallback(){super.connectedCallback(),this._fetchData()}async _fetchData(){this._loading=!0;try{const[t,e,s]=await Promise.all([this._fetch("/plugins/pipe"),this._fetch("/db/status"),this._fetch("/plugins/component")]);this._pipes=t||[],this._dbStatus=e,this._components=s||[]}catch(t){console.error("Failed to fetch data:",t)}this._loading=!1}async _fetch(t){const e=await fetch(`${this.apiBase}${t}`);return e.ok?e.json():null}render(){return this._loading?u`<p class="loading">Loading...</p>`:u`
      <div class="header">
        <img src="/static/images/shenas.png" alt="shenas" />
        <h1>shenas</h1>
      </div>

      ${this._renderDb()} ${this._renderPipes()} ${this._renderComponents()}
    `}_renderDb(){const t=this._dbStatus;return t?u`
      <div class="section">
        <h2>Database</h2>
        <div class="status">
          <p>Path: <code>${t.db_path}</code></p>
          ${t.size_mb!=null?u`<p>Size: ${t.size_mb} MB</p>`:u`<p>Not created yet</p>`}
          ${(t.schemas||[]).map(e=>u`
              <p>
                <strong>${e.name}</strong>: ${e.tables.length} tables,
                ${e.tables.reduce((s,i)=>s+i.rows,0)} rows
              </p>
            `)}
        </div>
      </div>
    `:u``}_renderPipes(){return u`
      <div class="section">
        <h2>Pipes</h2>
        ${this._pipes.length===0?u`<p class="status">No pipes installed</p>`:u`
              <div class="cards">
                ${this._pipes.map(t=>u`
                    <div class="card">
                      <h3>${t.name}</h3>
                      <div class="meta">${t.version}</div>
                      <div class="commands">
                        ${(t.commands||[]).join(", ")}
                      </div>
                    </div>
                  `)}
              </div>
            `}
      </div>
    `}_renderComponents(){return u`
      <div class="section">
        <h2>Components</h2>
        ${this._components.length===0?u`<p class="status">No components installed</p>`:u`
              <div class="cards">
                ${this._components.map(t=>u`
                    <div class="card">
                      <h3>
                        <a href="/components/${t.name}/${t.html||"index.html"}">${t.name}</a>
                      </h3>
                      <div class="meta">${t.version}</div>
                      ${t.description?u`<div class="commands">${t.description}</div>`:""}
                    </div>
                  `)}
              </div>
            `}
      </div>
    `}}z(V,"properties",{apiBase:{type:String,attribute:"api-base"},_pipes:{state:!0},_dbStatus:{state:!0},_components:{state:!0},_loading:{state:!0}}),z(V,"styles",$t`
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
    .card .commands {
      margin-top: 0.5rem;
      font-size: 0.85rem;
      color: #555;
    }
    .section {
      margin: 2rem 0;
    }
    .section h2 {
      font-size: 1.1rem;
      border-bottom: 1px solid #e0e0e0;
      padding-bottom: 0.5rem;
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
  `);customElements.define("shenas-app",V);
