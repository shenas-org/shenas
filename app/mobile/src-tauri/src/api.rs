//! REST API endpoints -- same contract as the Python FastAPI server.
//!
//! The Lit UI calls these endpoints identically whether the backend
//! is Python (desktop) or Rust (mobile).

use std::sync::Arc;

use axum::{
    extract::{Query, State},
    http::StatusCode,
    response::{Html, Json},
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
    Router::new()
        .route("/", get(index))
        .route("/api/health", get(health))
        .route("/api/tables", get(tables))
        .route("/api/query", get(query))
        .route("/api/transforms", get(list_transforms))
        .route("/api/transforms/run", axum::routing::post(run_transforms))
        .with_state(db)
}

async fn index(State(db): State<AppState>) -> Html<String> {
    let tables = db.list_tables().unwrap_or_default();
    let table_count = tables.len();
    Html(format!(
        r#"<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>shenas</title>
    <style>
        body {{ font-family: system-ui, sans-serif; margin: 1rem; background: #f5f5f5; color: #333; }}
        h1 {{ font-size: 1.5rem; font-weight: 400; }}
        .status {{ background: #fff; padding: 1rem; border-radius: 8px; margin: 1rem 0; }}
        .ok {{ color: #2d7d46; }}
        pre {{ background: #e8e8e8; padding: 0.5rem; border-radius: 4px; overflow-x: auto; font-size: 0.85rem; }}
    </style>
</head>
<body>
    <h1>shenas mobile</h1>
    <div class="status">
        <p class="ok">Server running</p>
        <p>Platform: Android (Rust + DuckDB + axum)</p>
        <p>Tables: {table_count}</p>
    </div>
    <h2>API</h2>
    <pre>GET /api/health
GET /api/tables
GET /api/query?sql=SELECT 1
GET /api/transforms
POST /api/transforms/run</pre>
</body>
</html>"#
    ))
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
