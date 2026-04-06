var p=Object.defineProperty;var u=(l,t,s)=>t in l?p(l,t,{enumerable:!0,configurable:!0,writable:!0,value:s}):l[t]=s;var d=(l,t,s)=>u(l,typeof t!="symbol"?t+"":t,s);import{tableFromIPC as f}from"apache-arrow";import{LitElement as _,css as g,html as a}from"lit";class h extends _{constructor(){super(),this.apiBase="/api",this.pageSize=25,this._tables=[],this._selectedTable="",this._columns=[],this._data=[],this._sortCol=null,this._sortDesc=!1,this._filters={},this._page=0,this._colWidths={},this._loading=!1,this._error=null}connectedCallback(){super.connectedCallback(),this._fetchTables()}async _fetchTables(){try{const t=await fetch(`${this.apiBase}/tables`);this._tables=await t.json(),this._tables.length>0&&(this._selectedTable=`${this._tables[0].schema}.${this._tables[0].table}`,this._fetchData())}catch(t){this._error=t.message}}async _fetchData(){this._loading=!0,this._error=null;try{const t=`SELECT * FROM ${this._selectedTable}`,s=await fetch(`${this.apiBase}/query?sql=${encodeURIComponent(t)}`);if(!s.ok)throw new Error(await s.text());const e=await s.arrayBuffer(),i=f(e);this._columns=i.schema.fields.map(r=>r.name);const n=[];for(let r=0;r<i.numRows;r++){const o={};for(const c of this._columns)o[c]=i.getChild(c).get(r);n.push(o)}this._data=n,this._page=0,this._filters={},this._sortCol=null}catch(t){this._error=t.message}this._loading=!1}get _filteredData(){return this._data.filter(t=>Object.entries(this._filters).every(([s,e])=>{if(!e)return!0;const i=t[s];return i!=null&&String(i).toLowerCase().includes(e.toLowerCase())}))}get _sortedData(){const t=[...this._filteredData];if(!this._sortCol)return t;const s=this._sortCol,e=this._sortDesc;return t.sort((i,n)=>{const r=i[s],o=n[s];return r==null&&o==null?0:r==null?1:o==null?-1:r<o?e?1:-1:r>o?e?-1:1:0})}get _pagedData(){const t=this._page*this.pageSize;return this._sortedData.slice(t,t+this.pageSize)}get _pageCount(){return Math.max(1,Math.ceil(this._sortedData.length/this.pageSize))}_onTableChange(t){this._selectedTable=t.target.value,this._fetchData()}_onSort(t){this._sortCol===t?this._sortDesc=!this._sortDesc:(this._sortCol=t,this._sortDesc=!1)}_onFilter(t,s){this._filters={...this._filters,[t]:s},this._page=0}_formatCell(t){return t==null?"":t instanceof Date?t.toISOString().slice(0,10):typeof t=="bigint"?t.toString():String(t)}_onResizeStart(t,s){t.preventDefault(),t.stopPropagation();const e=t.clientX,i=this._colWidths[s]||150,n=o=>{this._colWidths={...this._colWidths,[s]:Math.max(50,i+o.clientX-e)}},r=()=>{document.removeEventListener("mousemove",n),document.removeEventListener("mouseup",r)};document.addEventListener("mousemove",n),document.addEventListener("mouseup",r)}render(){if(this._error)return a`<div class="error">${this._error}</div>`;const t=a`
      <div class="controls">
        <h1>data table</h1>
        <select @change=${this._onTableChange}>
          ${this._tables.map(e=>a`
              <option value="${e.schema}.${e.table}" ?selected=${`${e.schema}.${e.table}`===this._selectedTable}>
                ${e.schema}.${e.table}
              </option>
            `)}
        </select>
      </div>
    `;if(this._loading)return a`${t}<div class="loading">Loading...</div>`;if(this._data.length===0)return a`${t}<div class="loading">No data</div>`;const s=this._pagedData;return a`
      ${t}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              ${this._columns.map(e=>a`
                  <th style="width:${this._colWidths[e]||150}px" @click=${()=>this._onSort(e)}>
                    ${e}
                    ${this._sortCol===e?a`<span class="sort-indicator">${this._sortDesc?"v":"^"}</span>`:""}
                    <div class="resize-handle" @mousedown=${i=>this._onResizeStart(i,e)}></div>
                  </th>
                `)}
            </tr>
            <tr class="filter-row">
              ${this._columns.map(e=>a`
                  <th>
                    <input
                      type="text"
                      placeholder="Filter..."
                      .value=${this._filters[e]||""}
                      @input=${i=>this._onFilter(e,i.target.value)}
                    />
                  </th>
                `)}
            </tr>
          </thead>
          <tbody>
            ${s.map(e=>a`
                <tr>
                  ${this._columns.map(i=>a`<td style="width:${this._colWidths[i]||150}px">${this._formatCell(e[i])}</td>`)}
                </tr>
              `)}
          </tbody>
        </table>
      </div>
      <div class="pagination">
        <button ?disabled=${this._page===0} @click=${()=>this._page--}>Previous</button>
        <span class="page-info">
          Page ${this._page+1} of ${this._pageCount}
          (${this._sortedData.length} rows)
        </span>
        <button ?disabled=${this._page>=this._pageCount-1} @click=${()=>this._page++}>Next</button>
      </div>
    `}}d(h,"properties",{apiBase:{type:String,attribute:"api-base"},pageSize:{type:Number,attribute:"page-size"},_tables:{state:!0},_selectedTable:{state:!0},_columns:{state:!0},_data:{state:!0},_sortCol:{state:!0},_sortDesc:{state:!0},_filters:{state:!0},_page:{state:!0},_colWidths:{state:!0},_loading:{state:!0},_error:{state:!0}}),d(h,"styles",g`
    :host {
      display: flex;
      flex-direction: column;
      font-family: system-ui, -apple-system, sans-serif;
      height: 100%;
      overflow: hidden;
    }
    h1 { font-size: 20px; font-weight: 600; color: #222; margin: 0 0 12px 0; }
    .controls { display: flex; gap: 12px; align-items: center; margin-bottom: 12px; flex-wrap: wrap; flex-shrink: 0; }
    select, input { padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 13px; }
    select { min-width: 200px; }
    .table-wrap { overflow: auto; flex: 1; border: 1px solid #e0e0e0; border-radius: 6px; background: #fff; }
    table { border-collapse: collapse; width: 100%; font-size: 13px; table-layout: fixed; }
    th {
      position: relative;
      background: #f5f5f5;
      border-bottom: 2px solid #ddd;
      padding: 8px 12px;
      text-align: left;
      font-weight: 600;
      color: #333;
      white-space: nowrap;
      overflow: hidden;
      cursor: pointer;
      user-select: none;
    }
    th:hover { background: #eee; }
    .sort-indicator { margin-left: 4px; color: #999; }
    .resize-handle {
      position: absolute;
      right: 0; top: 0; bottom: 0;
      width: 4px;
      cursor: col-resize;
    }
    .resize-handle:hover { background: #4a90d9; }
    .filter-row th { padding: 4px 8px; background: #fafafa; border-bottom: 1px solid #eee; cursor: default; }
    .filter-row input { width: 100%; box-sizing: border-box; padding: 4px 6px; font-size: 12px; }
    td { padding: 6px 12px; border-bottom: 1px solid #f0f0f0; color: #444; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    tr:hover td { background: #f8f8ff; }
    .pagination { display: flex; gap: 8px; align-items: center; margin-top: 8px; font-size: 13px; color: #666; flex-shrink: 0; }
    .pagination button { padding: 4px 12px; border: 1px solid #ccc; border-radius: 4px; background: #fff; cursor: pointer; }
    .pagination button:disabled { opacity: 0.4; cursor: default; }
    .pagination button:not(:disabled):hover { background: #f0f0f0; }
    .loading { color: #888; padding: 24px; text-align: center; }
    .error { color: #c00; background: #fee; padding: 12px; border-radius: 6px; }
    .page-info { flex: 1; text-align: center; }
  `);customElements.define("shenas-data-table",h);
