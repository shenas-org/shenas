// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::env;
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::Mutex;
use std::thread;
use std::time::Duration;

use tauri::Manager;

const DESKTOP_PORT: u16 = 7281;

struct ServerProcess(Mutex<Option<Child>>);

fn workspace_root() -> PathBuf {
    // SHENAS_ROOT env var, or walk up from current dir to find pyproject.toml
    if let Ok(root) = env::var("SHENAS_ROOT") {
        return PathBuf::from(root);
    }
    let mut dir = env::current_dir().unwrap();
    loop {
        if dir.join("pyproject.toml").exists() && dir.join("uv.lock").exists() {
            return dir;
        }
        if !dir.pop() {
            break;
        }
    }
    env::current_dir().unwrap()
}

fn start_server() -> Child {
    let root = workspace_root();
    let port = DESKTOP_PORT.to_string();
    eprintln!("Starting shenas server on port {} from: {}", port, root.display());
    Command::new("uv")
        .args(["run", "--no-sync", "shenas", "serve", "--no-tls", "--port", &port])
        .current_dir(&root)
        .spawn()
        .expect("Failed to start shenas server. Is uv and shenas-app installed?")
}

fn wait_for_server(url: &str, timeout: Duration) -> bool {
    let start = std::time::Instant::now();
    let client = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(1))
        .build()
        .unwrap();

    while start.elapsed() < timeout {
        if let Ok(resp) = client.get(url).send() {
            if resp.status().is_success() {
                return true;
            }
        }
        thread::sleep(Duration::from_millis(200));
    }
    false
}

fn main() {
    let server = start_server();
    let server_state = ServerProcess(Mutex::new(Some(server)));

    let url = format!("http://localhost:{}", DESKTOP_PORT);
    let health_url = format!("{}/api/health", url);

    if !wait_for_server(&health_url, Duration::from_secs(30)) {
        eprintln!("Server failed to start within 30 seconds");
        if let Some(mut child) = server_state.0.lock().unwrap().take() {
            let _ = child.kill();
        }
        std::process::exit(1);
    }

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(server_state)
        .setup(move |app| {
            let window = app.get_webview_window("main").unwrap();
            window
                .navigate(url.parse().unwrap())
                .unwrap();
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                let state = window.state::<ServerProcess>();
                let mut guard = state.0.lock().unwrap();
                if let Some(ref mut child) = *guard {
                    let _: Result<(), std::io::Error> = child.kill();
                }
                drop(guard);
            }
        })
        .run(tauri::generate_context!())
        .expect("Error while running tauri application");
}
