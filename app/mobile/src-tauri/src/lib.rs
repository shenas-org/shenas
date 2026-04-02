mod api;
mod db;

use std::path::PathBuf;
use std::sync::Arc;

use tauri::Manager;

const API_PORT: u16 = 7280;

fn start_api_server(database: Arc<db::Database>, ui_dir: PathBuf) {
    std::thread::spawn(move || {
        let rt = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .expect("Failed to create Tokio runtime");

        rt.block_on(async {
            let app = api::router(database, ui_dir);
            let listener = tokio::net::TcpListener::bind(format!("127.0.0.1:{}", API_PORT))
                .await
                .expect("Failed to bind API server");
            eprintln!("API server listening on http://127.0.0.1:{}", API_PORT);
            axum::serve(listener, app).await.unwrap();
        });
    });
}

/// Copy bundled UI files from Tauri's resource dir to the app data dir.
/// On Android, resource files are inside the APK and can't be served directly
/// by axum's ServeDir. We extract them to the writable data dir.
fn extract_ui_assets(app: &tauri::App) -> PathBuf {
    let resource_dir = app.path().resource_dir().expect("No resource dir");
    let data_dir = app.path().app_data_dir().unwrap_or_else(|_| PathBuf::from("/tmp/shenas"));
    let ui_dir = data_dir.join("ui");

    eprintln!("extract_ui: resource_dir={:?}", resource_dir);
    eprintln!("extract_ui: ui_dir={:?}", ui_dir);

    // For now, use the resource dir directly if it contains our files
    // (works on desktop; on Android we'll need extraction)
    let resource_ui = resource_dir.join("ui-dist");
    if resource_ui.join("index.html").exists() {
        eprintln!("extract_ui: found ui-dist in resource dir");
        return resource_ui;
    }

    // Fallback: check if ui-dist is next to the binary (desktop dev)
    let exe_dir = std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|p| p.to_path_buf()))
        .unwrap_or_default();
    let dev_ui = exe_dir.join("../../../ui-dist");
    if dev_ui.join("index.html").exists() {
        eprintln!("extract_ui: found ui-dist relative to exe");
        return dev_ui;
    }

    // Last resort: check working directory
    let cwd_ui = PathBuf::from("ui-dist");
    if cwd_ui.join("index.html").exists() {
        eprintln!("extract_ui: found ui-dist in cwd");
        return cwd_ui;
    }

    eprintln!("extract_ui: WARNING no ui-dist found anywhere");
    ui_dir
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

            let ui_dir = extract_ui_assets(app);
            eprintln!("setup: starting API server with ui_dir={:?}", ui_dir);
            start_api_server(database, ui_dir);

            // Navigate immediately -- ServeDir handles the rest
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
