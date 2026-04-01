// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod api;
mod db;

use std::path::PathBuf;
use std::sync::Arc;
use std::thread;

use tauri::Manager;

const API_PORT: u16 = 7280;

fn data_dir() -> PathBuf {
    // On mobile, use the app's data directory
    // On desktop (for testing), use ./data/
    dirs::data_dir()
        .map(|d| d.join("shenas"))
        .unwrap_or_else(|| PathBuf::from("data"))
}

fn start_api_server(database: Arc<db::Database>) {
    let rt = tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .build()
        .expect("Failed to create Tokio runtime");

    thread::spawn(move || {
        rt.block_on(async {
            let app = api::router(database);
            let listener = tokio::net::TcpListener::bind(format!("127.0.0.1:{}", API_PORT))
                .await
                .expect("Failed to bind API server");
            eprintln!("API server listening on http://127.0.0.1:{}", API_PORT);
            axum::serve(listener, app).await.unwrap();
        });
    });
}

fn main() {
    let db_path = data_dir().join("shenas.duckdb");
    std::fs::create_dir_all(db_path.parent().unwrap()).ok();

    let database = Arc::new(
        db::Database::open(&db_path).expect("Failed to open DuckDB"),
    );

    start_api_server(database.clone());

    // Wait for API server to be ready
    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(1))
        .build()
        .unwrap();
    for _ in 0..30 {
        if client
            .get(format!("http://127.0.0.1:{}/api/health", API_PORT))
            .send()
            .map(|r| r.status().is_success())
            .unwrap_or(false)
        {
            break;
        }
        thread::sleep(std::time::Duration::from_millis(100));
    }

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let window = app.get_webview_window("main").unwrap();
            window
                .navigate(
                    format!("http://127.0.0.1:{}", API_PORT)
                        .parse()
                        .unwrap(),
                )
                .unwrap();
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("Error while running tauri application");
}
