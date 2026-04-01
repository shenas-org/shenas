mod api;
mod db;

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
            eprintln!("setup: getting data dir");

            let data_dir = app.path().app_data_dir().unwrap_or_else(|_| {
                eprintln!("setup: app_data_dir failed, using /tmp");
                std::path::PathBuf::from("/tmp/shenas")
            });

            eprintln!("setup: data_dir = {:?}", data_dir);
            std::fs::create_dir_all(&data_dir).ok();

            let db_path = data_dir.join("shenas.duckdb");
            eprintln!("setup: opening DuckDB at {:?}", db_path);

            let database = match db::Database::open(&db_path) {
                Ok(db) => {
                    eprintln!("setup: DuckDB opened OK");
                    Arc::new(db)
                }
                Err(e) => {
                    eprintln!("setup: DuckDB file open failed: {:?}, using in-memory", e);
                    Arc::new(db::Database::open_memory().expect("In-memory DB also failed"))
                }
            };

            eprintln!("setup: starting API server");
            start_api_server(database);

            // Don't block -- navigate immediately, the page will retry
            eprintln!("setup: navigating WebView");
            let window = app.get_webview_window("main").unwrap();
            window
                .navigate(
                    format!("http://127.0.0.1:{}", API_PORT)
                        .parse()
                        .unwrap(),
                )
                .unwrap();

            eprintln!("setup: done");
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("Error while running tauri application");
}
