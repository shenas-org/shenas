mod api;
mod db;

use std::path::PathBuf;
use std::sync::Arc;

use tauri::Manager;

const API_PORT: u16 = 7280;

fn start_api_server(database: Arc<db::Database>) {
    std::thread::spawn(move || {
        let rt = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .expect("Failed to create Tokio runtime");

        rt.block_on(async {
            let app = api::router(database);
            // In dev mode the host's vite/shenas may already be reverse-forwarded
            // onto this port via `adb reverse tcp:7280`. If we can't bind, just
            // log and exit the API thread -- the WebView will use the host's API.
            match tokio::net::TcpListener::bind(format!("127.0.0.1:{}", API_PORT)).await {
                Ok(listener) => {
                    eprintln!("API server listening on http://127.0.0.1:{}", API_PORT);
                    axum::serve(listener, app).await.unwrap();
                }
                Err(e) => {
                    eprintln!("API server bind failed ({}); assuming reverse-forwarded host API", e);
                }
            }
        });
    });
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    eprintln!("shenas mobile starting");

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let data_dir = app.path().app_data_dir().unwrap_or_else(|_| {
                PathBuf::from("/tmp/shenas")
            });
            std::fs::create_dir_all(&data_dir).ok();

            let db_path = data_dir.join("shenas.duckdb");
            eprintln!("setup: opening DuckDB at {:?}", db_path);

            let database = match db::Database::open(&db_path) {
                Ok(db) => {
                    eprintln!("setup: DuckDB opened OK");
                    Arc::new(db)
                }
                Err(e) => {
                    eprintln!("setup: DuckDB open failed: {:?}, using in-memory", e);
                    Arc::new(db::Database::open_memory().expect("In-memory DB also failed"))
                }
            };

            // Start API server -- UI calls it via http://127.0.0.1:7280/api
            // Tauri serves the frontend via its built-in asset protocol
            start_api_server(database);
            eprintln!("setup: done");
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("Error while running tauri application");
}
