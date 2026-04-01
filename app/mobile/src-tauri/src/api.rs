//! REST API endpoints -- same contract as the Python FastAPI server.
//!
//! The Lit UI calls these endpoints identically whether the backend
//! is Python (desktop) or Rust (mobile).

use std::sync::Arc;

use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
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
    #[serde(default)]
    format: Option<String>,
}

pub fn router(db: Arc<Database>) -> Router {
    Router::new()
        .route("/api/health", get(health))
        .route("/api/tables", get(tables))
        .route("/api/query", get(query))
        .route("/api/transforms", get(list_transforms))
        .route("/api/transforms/run", axum::routing::post(run_transforms))
        .with_state(db)
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
