// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Child, Command};
use std::sync::Mutex;
use std::thread;
use std::time::Duration;

use tauri::Manager;

struct ServerProcess(Mutex<Option<Child>>);

fn start_server() -> Child {
    Command::new("shenas")
        .args(["serve", "--no-tls"])
        .spawn()
        .expect("Failed to start shenas server. Is shenas-app installed?")
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

    // Wait for the server to be ready
    if !wait_for_server("http://localhost:7280/api/health", Duration::from_secs(30)) {
        eprintln!("Server failed to start within 30 seconds");
        if let Some(mut child) = server_state.0.lock().unwrap().take() {
            let _ = child.kill();
        }
        std::process::exit(1);
    }

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(server_state)
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
