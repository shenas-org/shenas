//! REST API endpoints + UI file serving.
//!
//! Serves the same API contract as the Python FastAPI server, plus the
//! built Lit UI from a filesystem directory passed at startup.

use std::path::PathBuf;
use std::sync::Arc;

use axum::{
    extract::{Query, State},
    http::StatusCode,
    response::Json,
    routing::get,
    Router,
};
use serde::Deserialize;
use tower_http::services::{ServeDir, ServeFile};

use crate::db::Database;

pub type AppState = Arc<Database>;

#[derive(Deserialize)]
pub struct QueryParams {
    sql: String,
    #[allow(dead_code)]
    #[serde(default)]
    format: Option<String>,
}

pub fn router(db: Arc<Database>, ui_dir: PathBuf) -> Router {
    eprintln!("Serving UI from {:?} (exists: {})", ui_dir, ui_dir.exists());

    let index_html = ui_dir.join("index.html");
    let serve_ui = ServeDir::new(&ui_dir)
        .append_index_html_on_directories(true)
        .fallback(ServeFile::new(index_html));

    Router::new()
        .route("/api/health", get(health))
        .route("/api/tables", get(tables))
        .route("/api/query", get(query))
        .route("/api/transforms", get(list_transforms))
        .route("/api/transforms/run", axum::routing::post(run_transforms))
        .route("/api/hotkeys", get(stub_empty_array))
        .route("/api/workspace", get(stub_empty_object).put(stub_ok))
        .route("/api/plugins/pipe", get(stub_empty_array))
        .route("/api/plugins/schema", get(stub_empty_array))
        .route("/api/plugins/component", get(stub_empty_array))
        .route("/api/plugins/ui", get(stub_empty_array))
        .route("/api/plugins/theme", get(stub_empty_array))
        .route("/api/db/status", get(db_status))
        .route("/api/dependencies", get(stub_empty_object))
        .route("/api/stream/logs", get(stub_empty_sse))
        .route("/api/stream/spans", get(stub_empty_sse))
        .route("/api/sync/schedule", get(stub_empty_array))
        .with_state(db)
        .fallback_service(serve_ui)
}

// ---- Stubs ----

async fn stub_empty_array() -> Json<serde_json::Value> {
    Json(serde_json::json!([]))
}

async fn stub_empty_object() -> Json<serde_json::Value> {
    Json(serde_json::json!({}))
}

async fn stub_ok() -> Json<serde_json::Value> {
    Json(serde_json::json!({"ok": true}))
}

async fn stub_empty_sse() -> &'static str {
    ""
}

async fn db_status(State(db): State<AppState>) -> Json<serde_json::Value> {
    let tables = db.list_tables().unwrap_or_default();
    Json(serde_json::json!({
        "path": "mobile (embedded)",
        "size_mb": 0,
        "tables": tables.len(),
        "schemas": {},
    }))
}

// ---- Core endpoints ----

async fn health() -> Json<serde_json::Value> {
    Json(serde_json::json!({"status": "ok", "platform": "mobile"}))
}

async fn tables(State(db): State<AppState>) -> Result<Json<serde_json::Value>, StatusCode> {
    match db.list_tables() {
        Ok(rows) => Ok(Json(serde_json::json!(rows))),
        Err(e) => {
            eprintln!("Error listing tables: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

async fn query(
    State(db): State<AppState>,
    Query(params): Query<QueryParams>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    match db.query_json(&params.sql) {
        Ok(rows) => Ok(Json(serde_json::json!(rows))),
        Err(e) => {
            eprintln!("Query error: {}", e);
            Err(StatusCode::BAD_REQUEST)
        }
    }
}

async fn list_transforms(
    State(db): State<AppState>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    match db.query_json(
        "SELECT id, source_schema, source_table, target_schema, target_table, sql, is_default, enabled
         FROM shenas_system.transforms ORDER BY id",
    ) {
        Ok(rows) => Ok(Json(serde_json::json!(rows))),
        Err(e) => {
            eprintln!("Error listing transforms: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

async fn run_transforms(
    State(db): State<AppState>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    match db.run_transforms() {
        Ok(results) => Ok(Json(serde_json::json!({"results": results}))),
        Err(e) => {
            eprintln!("Transform error: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}
