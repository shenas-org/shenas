//! REST API endpoints + embedded UI serving.
//!
//! Serves the same API contract as the Python FastAPI server, plus the
//! built Lit UI from the embedded ui-dist/ directory.

use std::sync::Arc;

use axum::{
    extract::{Query, State},
    http::{header, StatusCode, Uri},
    response::{Html, IntoResponse, Json, Response},
    routing::get,
    Router,
};
use rust_embed::Embed;
use serde::Deserialize;

use crate::db::Database;

pub type AppState = Arc<Database>;

/// Embed the built UI files at compile time.
/// Run `bash build-ui.sh` before `cargo build` to populate ui-dist/.
#[derive(Embed)]
#[folder = "../ui-dist/"]
struct UiAssets;

#[derive(Deserialize)]
pub struct QueryParams {
    sql: String,
    #[allow(dead_code)]
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
        // Fallback: serve embedded UI files
        .fallback(get(serve_ui))
}

/// Serve embedded UI files. Falls back to index.html for SPA routing.
async fn serve_ui(uri: Uri) -> Response {
    let path = uri.path().trim_start_matches('/');

    // Try exact file match
    if let Some(file) = UiAssets::get(path) {
        let mime = mime_guess::from_path(path).first_or_text_plain();
        return (
            StatusCode::OK,
            [(header::CONTENT_TYPE, mime.as_ref())],
            file.data,
        )
            .into_response();
    }

    // SPA fallback: serve index.html for non-API, non-file paths
    if let Some(file) = UiAssets::get("index.html") {
        return (
            StatusCode::OK,
            [(header::CONTENT_TYPE, "text/html")],
            file.data,
        )
            .into_response();
    }

    (StatusCode::NOT_FOUND, "Not found").into_response()
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
