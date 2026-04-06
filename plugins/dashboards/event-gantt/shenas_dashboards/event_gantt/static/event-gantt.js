var f=Object.defineProperty;var _=(r,t,a)=>t in r?f(r,t,{enumerable:!0,configurable:!0,writable:!0,value:a}):r[t]=a;var l=(r,t,a)=>_(r,typeof t!="symbol"?t+"":t,a);import{LitElement as y,css as b,html as i,nothing as c}from"lit";import{tableFromIPC as x}from"apache-arrow";async function w(r,t){const a=await fetch(`${r}/query?sql=${encodeURIComponent(t)}`);if(!a.ok){const e=await a.text();throw new Error(e)}const s=await a.arrayBuffer();return x(s)}function $(r){const t=r.schema.fields.map(s=>s.name),a=[];for(let s=0;s<r.numRows;s++){const e={};for(const o of t)e[o]=r.getChild(o).get(s);a.push(e)}return a}const h={meeting:"#6c5ce7",workout:"#00b894",running:"#00b894",music:"#e17055",meal:"#fdcb6e",focus:"#0984e3",default:"#636e72"};function m(r){if(!r)return h.default;const t=r.toLowerCase();return h[t]||h.default}function g(r){return r.toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"})}function E(r){return r.toLocaleDateString([],{weekday:"short",month:"short",day:"numeric"})}function p(r){return`${r.getFullYear()}-${String(r.getMonth()+1).padStart(2,"0")}-${String(r.getDate()).padStart(2,"0")}`}class u extends y{constructor(){super(),this.apiBase="/api",this.days=7,this._events=[],this._loading=!1,this._error=null,this._hoveredEvent=null,this._tooltipX=0,this._tooltipY=0}connectedCallback(){super.connectedCallback(),this._fetchEvents()}async _fetchEvents(){this._loading=!0,this._error=null;try{const t=await w(this.apiBase,`SELECT source, source_id, start_at, end_at, duration_min, title, category
         FROM metrics.events
         WHERE start_at >= current_date - INTERVAL '${this.days}' DAY
         ORDER BY start_at`);this._events=$(t)}catch(t){this._error=t.message}this._loading=!1}_setDays(t){this.days=t,this._fetchEvents()}_groupByDay(){const t=new Map;for(const a of this._events){const s=new Date(Number(a.start_at)/1e3),e=p(s);t.has(e)||t.set(e,{date:s,events:[]}),t.get(e).events.push({...a,_start:s})}return[...t.values()].sort((a,s)=>a.date-s.date)}_onBarEnter(t,a){this._hoveredEvent=t,this._tooltipX=a.clientX+12,this._tooltipY=a.clientY-10}_onBarMove(t){this._tooltipX=t.clientX+12,this._tooltipY=t.clientY-10}_onBarLeave(){this._hoveredEvent=null}render(){if(this._loading)return i`<div class="loading">Loading events...</div>`;if(this._error)return i`<div class="error">${this._error}</div>`;if(this._events.length===0)return i`<div class="empty">No events in the last ${this.days} days.</div>`;const t=this._groupByDay(),a=p(new Date),s=[...new Set(this._events.map(e=>e.category).filter(Boolean))];return i`
      <div class="header">
        <h2>Events Timeline</h2>
        <div class="controls">
          ${[7,14,30].map(e=>i`<button aria-pressed=${this.days===e} @click=${()=>this._setDays(e)}>${e}d</button>`)}
        </div>
      </div>

      <div class="container">
        <div class="gantt">
          <div class="hour-labels">
            ${Array.from({length:24},(e,o)=>i`<div class="hour-label">${o===0?"12a":o<12?`${o}a`:o===12?"12p":`${o-12}p`}</div>`)}
          </div>

          ${t.map(({date:e,events:o})=>{const d=p(e)===a;return i`
              <div class="day-row">
                <div class="day-label ${d?"today":""}">${E(e)}</div>
                <div class="timeline">
                  <div class="hour-grid">
                    ${Array.from({length:24},()=>i`<div class="hour-line"></div>`)}
                  </div>
                  ${o.map(n=>this._renderBar(n))}
                </div>
              </div>
            `})}
        </div>
      </div>

      <div class="legend">
        ${s.map(e=>i`
            <div class="legend-item">
              <div class="legend-dot" style="background: ${m(e)}"></div>
              ${e}
            </div>
          `)}
      </div>

      ${this._hoveredEvent?i`
            <div class="tooltip" style="left: ${this._tooltipX}px; top: ${this._tooltipY}px">
              <div class="tooltip-title">${this._hoveredEvent.title||"Untitled"}</div>
              <div class="tooltip-meta">
                <span>${g(this._hoveredEvent._start)}${this._hoveredEvent._end?` - ${g(this._hoveredEvent._end)}`:""}</span>
                <span>${this._hoveredEvent.category||"uncategorized"} / ${this._hoveredEvent.source}</span>
                ${this._hoveredEvent.duration_min?i`<span>${Math.round(this._hoveredEvent.duration_min)} min</span>`:c}
              </div>
            </div>
          `:c}
    `}_renderBar(t){const s=(t._start.getHours()+t._start.getMinutes()/60)/24*100;let e=(t.duration_min||30)/60;if(t.end_at){const n=new Date(Number(t.end_at)/1e3);e=(n-t._start)/36e5,t._end=n}const o=Math.max(e/24*100,.3),v=m(t.category),d=o>4;return i`
      <div
        class="event-bar"
        style="left: ${s}%; width: ${o}%; background: ${v}"
        @mouseenter=${n=>this._onBarEnter(t,n)}
        @mousemove=${n=>this._onBarMove(n)}
        @mouseleave=${()=>this._onBarLeave()}
      >
        ${d?i`<span class="bar-label">${t.title||""}</span>`:c}
      </div>
    `}}l(u,"properties",{apiBase:{type:String,attribute:"api-base"},days:{type:Number},_events:{state:!0},_loading:{state:!0},_error:{state:!0},_hoveredEvent:{state:!0},_tooltipX:{state:!0},_tooltipY:{state:!0}}),l(u,"styles",b`
    :host {
      display: block;
      font-family: var(--shenas-font, system-ui, sans-serif);
      color: var(--shenas-text, #e8e8ef);
    }

    .container {
      overflow-x: auto;
    }

    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 1rem;
    }

    h2 {
      margin: 0;
      font-size: 1.2rem;
      font-weight: 600;
    }

    .controls {
      display: flex;
      gap: 0.5rem;
    }

    .controls button {
      background: var(--shenas-surface, #22222f);
      border: 1px solid var(--shenas-border, #2a2a3a);
      color: var(--shenas-text, #e8e8ef);
      padding: 0.3rem 0.75rem;
      border-radius: 6px;
      cursor: pointer;
      font-size: 0.8rem;
    }

    .controls button[aria-pressed="true"] {
      background: var(--shenas-accent, #6c5ce7);
      border-color: var(--shenas-accent, #6c5ce7);
      color: white;
    }

    .loading, .error, .empty {
      padding: 2rem;
      text-align: center;
      color: var(--shenas-text-muted, #8888a0);
    }

    .error {
      color: #e74c3c;
    }

    .gantt {
      min-width: 100%;
    }

    .day-row {
      display: flex;
      align-items: stretch;
      border-bottom: 1px solid var(--shenas-border, #2a2a3a);
      min-height: 36px;
    }

    .day-label {
      width: 120px;
      min-width: 120px;
      padding: 0.4rem 0.75rem;
      font-size: 0.8rem;
      font-weight: 500;
      color: var(--shenas-text-muted, #8888a0);
      display: flex;
      align-items: center;
      border-right: 1px solid var(--shenas-border, #2a2a3a);
    }

    .day-label.today {
      color: var(--shenas-accent, #6c5ce7);
      font-weight: 600;
    }

    .timeline {
      flex: 1;
      position: relative;
      min-height: 32px;
      padding: 2px 0;
    }

    .hour-grid {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      display: flex;
    }

    .hour-line {
      flex: 1;
      border-right: 1px solid var(--shenas-border, #2a2a3a);
      opacity: 0.3;
    }

    .hour-line:last-child {
      border-right: none;
    }

    .event-bar {
      position: absolute;
      top: 3px;
      height: calc(100% - 6px);
      min-width: 3px;
      border-radius: 3px;
      cursor: pointer;
      opacity: 0.85;
      transition: opacity 0.15s;
      display: flex;
      align-items: center;
      padding: 0 4px;
      overflow: hidden;
    }

    .event-bar:hover {
      opacity: 1;
      z-index: 10;
    }

    .event-bar .bar-label {
      font-size: 0.65rem;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      color: white;
      text-shadow: 0 1px 2px rgba(0,0,0,0.4);
    }

    .hour-labels {
      display: flex;
      padding-left: 120px;
      border-bottom: 1px solid var(--shenas-border, #2a2a3a);
      margin-bottom: 2px;
    }

    .hour-label {
      flex: 1;
      font-size: 0.65rem;
      color: var(--shenas-text-muted, #8888a0);
      text-align: center;
      padding: 0.2rem 0;
    }

    .legend {
      display: flex;
      gap: 1rem;
      margin-top: 0.75rem;
      flex-wrap: wrap;
    }

    .legend-item {
      display: flex;
      align-items: center;
      gap: 0.35rem;
      font-size: 0.75rem;
      color: var(--shenas-text-muted, #8888a0);
    }

    .legend-dot {
      width: 10px;
      height: 10px;
      border-radius: 2px;
    }

    .tooltip {
      position: fixed;
      background: var(--shenas-bg-card, #1a1a25);
      border: 1px solid var(--shenas-border, #2a2a3a);
      border-radius: 8px;
      padding: 0.6rem 0.8rem;
      font-size: 0.8rem;
      z-index: 1000;
      pointer-events: none;
      max-width: 300px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.3);
    }

    .tooltip-title {
      font-weight: 600;
      margin-bottom: 0.3rem;
    }

    .tooltip-meta {
      color: var(--shenas-text-muted, #8888a0);
      font-size: 0.75rem;
    }

    .tooltip-meta span {
      display: block;
    }
  `);customElements.define("shenas-event-gantt",u);
