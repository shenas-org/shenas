var g=Object.defineProperty;var m=(i,t,e)=>t in i?g(i,t,{enumerable:!0,configurable:!0,writable:!0,value:e}):i[t]=e;var o=(i,t,e)=>m(i,typeof t!="symbol"?t+"":t,e);import{LitElement as p,unsafeCSS as b,css as f,html as l}from"lit";import{tableFromIPC as _}from"apache-arrow";import x from"uplot";async function d(i,t){const e=await fetch(`${i}/query?sql=${encodeURIComponent(t)}`);if(!e.ok){const s=await e.text();throw new Error(s)}const r=await e.arrayBuffer();return await _(r)}function y(i){const t={};for(const e of i.schema.fields){const r=i.getChild(e.name);t[e.name]=r.toArray()}return t}function v(i){return Float64Array.from(i,t=>{if(t==null)return null;const e=Number(t);return Number.isNaN(e)?null:e>1e9?e/1e3:e*86400})}const k='.uplot,.uplot *,.uplot *:before,.uplot *:after{box-sizing:border-box}.uplot{font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica Neue,Arial,Noto Sans,sans-serif,"Apple Color Emoji","Segoe UI Emoji",Segoe UI Symbol,"Noto Color Emoji";line-height:1.5;width:min-content}.u-title{text-align:center;font-size:18px;font-weight:700}.u-wrap{position:relative;-webkit-user-select:none;user-select:none}.u-over,.u-under{position:absolute}.u-under{overflow:hidden}.uplot canvas{display:block;position:relative;width:100%;height:100%}.u-axis{position:absolute}.u-legend{font-size:14px;margin:auto;text-align:center}.u-inline{display:block}.u-inline *{display:inline-block}.u-inline tr{margin-right:16px}.u-legend th{font-weight:600}.u-legend th>*{vertical-align:middle;display:inline-block}.u-legend .u-marker{width:1em;height:1em;margin-right:4px;background-clip:padding-box!important}.u-inline.u-live th:after{content:":";vertical-align:middle}.u-inline:not(.u-live) .u-value{display:none}.u-series>*{padding:4px}.u-series th{cursor:pointer}.u-legend .u-off>*{opacity:.3}.u-select{background:#00000012;position:absolute;pointer-events:none}.u-cursor-x,.u-cursor-y{position:absolute;left:0;top:0;pointer-events:none;will-change:transform}.u-hz .u-cursor-x,.u-vt .u-cursor-y{height:100%;border-right:1px dashed #607D8B}.u-hz .u-cursor-y,.u-vt .u-cursor-x{width:100%;border-bottom:1px dashed #607D8B}.u-cursor-pt{position:absolute;top:0;left:0;border-radius:50%;border:0 solid;pointer-events:none;will-change:transform;background-clip:padding-box!important}.u-axis.u-off,.u-select.u-off,.u-cursor-x.u-off,.u-cursor-y.u-off,.u-cursor-pt.u-off{display:none}';class c extends p{constructor(){super(),this.title="",this.data=null,this.series=[],this.axes=[],this._chart=null,this._ro=null}updated(t){(t.has("data")||t.has("series"))&&this._renderChart()}disconnectedCallback(){super.disconnectedCallback(),this._chart&&this._chart.destroy(),this._ro&&this._ro.disconnect()}_renderChart(){if(!this.data||this.data.length<2||this.data[0].length===0)return;this._chart&&(this._chart.destroy(),this._chart=null);const t=this.renderRoot.querySelector(".chart-wrap");if(!t)return;const r={width:t.clientWidth||600,height:200,cursor:{show:!0,drag:{x:!0,y:!1}},scales:{x:{time:!0}},axes:[{stroke:"#888",grid:{stroke:"#eee"},values:(s,n)=>n.map(h=>{const a=new Date(h*1e3);return`${a.getMonth()+1}/${a.getDate()}`})},...this.axes.length?this.axes:[{stroke:"#888",grid:{stroke:"#f4f4f4"}}]],series:[{},...this.series.map(s=>({label:s.label,stroke:s.color||"#4a90d9",width:2,points:{show:!1},...s}))]};this._chart=new x(r,this.data,t),this._ro||(this._ro=new ResizeObserver(()=>{if(this._chart){const s=t.clientWidth;s>0&&this._chart.setSize({width:s,height:200})}}),this._ro.observe(t))}render(){const t=this.data&&this.data.length>=2&&this.data[0].length>0;return l`
      <h3>${this.title}</h3>
      <div class="chart-wrap"></div>
      ${t?"":l`<div class="no-data">No data</div>`}
    `}}o(c,"properties",{title:{type:String},data:{type:Array},series:{type:Array},axes:{type:Array}}),o(c,"styles",[b(k),f`
      :host {
        display: block;
        background: #fff;
        border: 1px solid #e0e0e0;
        border-radius: 6px;
        padding: 16px;
        margin-bottom: 16px;
      }
      h3 {
        margin: 0 0 12px 0;
        font-size: 14px;
        font-weight: 600;
        color: #333;
      }
      .chart-wrap {
        width: 100%;
        overflow: hidden;
      }
      .no-data {
        color: #999;
        font-size: 13px;
        padding: 24px 0;
        text-align: center;
      }
    `]);customElements.define("chart-panel",c);class u extends p{constructor(){super(),this.apiBase="/api",this._loading=!0,this._error=null,this._hrv=null,this._sleep=null,this._vitals=null,this._body=null}connectedCallback(){super.connectedCallback(),this._fetchAll()}async _fetchAll(){this._loading=!0,this._error=null;try{const[t,e,r,s]=await Promise.all([d(this.apiBase,"SELECT date, rmssd FROM metrics.daily_hrv ORDER BY date"),d(this.apiBase,"SELECT date, total_hours, deep_min, rem_min, light_min, score FROM metrics.daily_sleep ORDER BY date"),d(this.apiBase,"SELECT date, resting_hr, steps, active_kcal FROM metrics.daily_vitals ORDER BY date"),d(this.apiBase,"SELECT date, weight_kg FROM metrics.daily_body WHERE weight_kg IS NOT NULL ORDER BY date")]);this._hrv=this._prepTimeSeries(t,["rmssd"]),this._sleep=this._prepTimeSeries(e,["total_hours","deep_min","rem_min","light_min"]),this._vitals=this._prepTimeSeries(r,["resting_hr","steps","active_kcal"]),this._body=this._prepTimeSeries(s,["weight_kg"])}catch(t){this._error=t.message}this._loading=!1}_prepTimeSeries(t,e){const r=y(t);if(!r.date||r.date.length===0)return null;const n=[v(r.date)];for(const h of e)r[h]&&n.push(Float64Array.from(r[h],a=>a==null?null:Number(a)));return n}render(){return this._loading?l`<div class="loading">Loading...</div>`:this._error?l`<div class="error">${this._error}</div>`:l`
      <div class="grid">
        <chart-panel
          title="HRV (RMSSD)"
          .data=${this._hrv}
          .series=${[{label:"rmssd",color:"#6b5ce7"}]}
          .axes=${[{stroke:"#888",grid:{stroke:"#f4f4f4"},label:"ms"}]}
        ></chart-panel>

        <chart-panel
          title="Sleep"
          .data=${this._sleep}
          .series=${[{label:"total hrs",color:"#4a90d9"},{label:"deep min",color:"#2d5f8a"},{label:"rem min",color:"#7bb3e0"},{label:"light min",color:"#b8d4ed"}]}
          .axes=${[{stroke:"#888",grid:{stroke:"#f4f4f4"}}]}
        ></chart-panel>

        <chart-panel
          title="Resting Heart Rate"
          .data=${this._vitals?[this._vitals[0],this._vitals[1]]:null}
          .series=${[{label:"bpm",color:"#e74c3c"}]}
          .axes=${[{stroke:"#888",grid:{stroke:"#f4f4f4"},label:"bpm"}]}
        ></chart-panel>

        <chart-panel
          title="Steps"
          .data=${this._vitals?[this._vitals[0],this._vitals[2]]:null}
          .series=${[{label:"steps",color:"#27ae60",fill:"rgba(39,174,96,0.1)"}]}
          .axes=${[{stroke:"#888",grid:{stroke:"#f4f4f4"}}]}
        ></chart-panel>

        <chart-panel
          title="Active Calories"
          .data=${this._vitals?[this._vitals[0],this._vitals[3]]:null}
          .series=${[{label:"kcal",color:"#e67e22",fill:"rgba(230,126,34,0.1)"}]}
          .axes=${[{stroke:"#888",grid:{stroke:"#f4f4f4"}}]}
        ></chart-panel>

        <chart-panel
          title="Weight"
          .data=${this._body}
          .series=${[{label:"kg",color:"#8e44ad"}]}
          .axes=${[{stroke:"#888",grid:{stroke:"#f4f4f4"},label:"kg"}]}
        ></chart-panel>
      </div>
    `}}o(u,"properties",{apiBase:{type:String,attribute:"api-base"},_loading:{state:!0},_error:{state:!0},_hrv:{state:!0},_sleep:{state:!0},_vitals:{state:!0},_body:{state:!0}}),o(u,"styles",f`
    :host {
      display: block;
      font-family: system-ui, -apple-system, sans-serif;
      max-width: 960px;
      margin: 0 auto;
      padding: 24px 16px;
      background: #f8f8f8;
      min-height: 100vh;
    }
    h1 {
      font-size: 20px;
      font-weight: 600;
      color: #222;
      margin: 0 0 4px 0;
    }
    .subtitle {
      font-size: 13px;
      color: #888;
      margin-bottom: 24px;
    }
    .grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: 0;
    }
    .error {
      color: #c00;
      background: #fee;
      padding: 12px;
      border-radius: 6px;
      font-size: 13px;
    }
    .loading {
      color: #888;
      font-size: 13px;
      padding: 24px;
      text-align: center;
    }
  `);customElements.define("shenas-dashboard",u);
