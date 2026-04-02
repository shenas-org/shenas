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
            let listener = tokio::net::TcpListener::bind(format!("127.0.0.1:{}", API_PORT))
                .await
                .expect("Failed to bind API server");
            eprintln!("API server listening on http://127.0.0.1:{}", API_PORT);
            axum::serve(listener, app).await.unwrap();
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
