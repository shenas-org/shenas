//! REST API endpoints.
//!
//! Same contract as the Python FastAPI server. The Lit UI is served by
//! Tauri's built-in asset protocol, not by axum.

use std::sync::Arc;

use axum::{
    extract::{Query, State},
    http::{HeaderValue, Method, StatusCode},
    response::Json,
    routing::get,
    Router,
};
use serde::Deserialize;

use crate::db::Database;

pub type AppState = Arc<Database>;

#[derive(Deserialize)]
pub struct QueryParams {
    sql: String,
    #[allow(dead_code)]
    #[serde(default)]
    format: Option<String>,
}

pub fn router(db: Arc<Database>) -> Router {
    let cors = tower_http::cors::CorsLayer::new()
        .allow_origin("http://tauri.localhost".parse::<HeaderValue>().unwrap())
        .allow_methods([Method::GET, Method::POST, Method::PUT, Method::DELETE])
        .allow_headers(tower_http::cors::Any);

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
        .route("/api/components", get(stub_empty_array))
        .with_state(db)
        .layer(cors)
}

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

async fn db_status(State(db): State<AppState>) -> Result<Json<serde_json::Value>, StatusCode> {
    match db.status() {
        Ok(status) => Ok(Json(status)),
        Err(e) => {
            eprintln!("DB status error: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

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
