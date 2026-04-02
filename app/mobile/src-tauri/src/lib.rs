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

/// Extract UI assets from Tauri's bundled resources to the writable data dir.
/// On Android, bundled assets live inside the APK and can't be served by axum.
/// We use Tauri's resource resolver to copy them out on first launch.
fn extract_ui_to_data_dir(app: &tauri::App) -> PathBuf {
    let data_dir = app.path().app_data_dir().unwrap_or_else(|_| PathBuf::from("/tmp/shenas"));
    let ui_dir = data_dir.join("mobile-dist");

    // Check if already extracted (skip on subsequent launches)
    if ui_dir.join("index.html").exists() {
        eprintln!("UI already extracted at {:?}", ui_dir);
        return ui_dir;
    }

    eprintln!("Extracting UI to {:?}", ui_dir);
    std::fs::create_dir_all(&ui_dir).ok();

    // Use Tauri's resource resolver to read bundled files
    let resource_path = app.path().resource_dir().unwrap_or_default();
    let src = resource_path.join("mobile-dist");
    if src.exists() {
        // Desktop: resources are on the filesystem
        copy_dir_recursive(&src, &ui_dir);
    } else {
        eprintln!("WARNING: no mobile-dist in resources, UI will not load");
    }

    ui_dir
}

fn copy_dir_recursive(src: &std::path::Path, dst: &std::path::Path) {
    std::fs::create_dir_all(dst).ok();
    if let Ok(entries) = std::fs::read_dir(src) {
        for entry in entries.flatten() {
            let dest = dst.join(entry.file_name());
            if entry.file_type().map(|t| t.is_dir()).unwrap_or(false) {
                copy_dir_recursive(&entry.path(), &dest);
            } else {
                std::fs::copy(entry.path(), dest).ok();
            }
        }
    }
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

            let ui_dir = extract_ui_to_data_dir(app);
            start_api_server(database, ui_dir);

            // Navigate WebView to axum -- serves both UI and API on same origin
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
