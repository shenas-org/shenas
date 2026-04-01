// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::Mutex;
use std::thread;
use std::time::Duration;

use tauri::Manager;
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::CommandChild;

struct ServerProcess(Mutex<Option<CommandChild>>);
struct DaemonProcess(Mutex<Option<CommandChild>>);

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

fn is_server_running() -> bool {
    let client = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(2))
        .build()
        .unwrap();
    client
        .get("http://localhost:7280/api/health")
        .send()
        .map(|r| r.status().is_success())
        .unwrap_or(false)
}

fn main() {
    // If the server is already running (e.g. via autostart service),
    // skip spawning sidecar processes.
    let already_running = is_server_running();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(move |app| {
            let server_state = if already_running {
                eprintln!("Server already running, skipping sidecar spawn");
                ServerProcess(Mutex::new(None))
            } else {
                eprintln!("Starting shenas server sidecar");
                let (_rx, child) = app
                    .shell()
                    .sidecar("shenas")
                    .expect("Failed to create shenas sidecar")
                    .args(["--no-tls"])
                    .spawn()
                    .expect("Failed to start shenas server sidecar");

                let state = ServerProcess(Mutex::new(Some(child)));

                if !wait_for_server(
                    "http://localhost:7280/api/health",
                    Duration::from_secs(30),
                ) {
                    eprintln!("Server failed to start within 30 seconds");
                    if let Some(child) = state.0.lock().unwrap().take() {
                        let _ = child.kill();
                    }
                    std::process::exit(1);
                }
                state
            };

            let daemon_state = if already_running {
                DaemonProcess(Mutex::new(None))
            } else {
                eprintln!("Starting shenas-scheduler sidecar");
                let (_rx, child) = app
                    .shell()
                    .sidecar("shenas-scheduler")
                    .expect("Failed to create shenas-scheduler sidecar")
                    .spawn()
                    .expect("Failed to start shenas-scheduler sidecar");
                DaemonProcess(Mutex::new(Some(child)))
            };

            app.manage(server_state);
            app.manage(daemon_state);

            let window = app.get_webview_window("main").unwrap();
            window
                .navigate("http://localhost:7280".parse().unwrap())
                .unwrap();
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                // Kill server if we spawned it
                let server = window.state::<ServerProcess>();
                if let Some(child) = server.0.lock().unwrap().take() {
                    let _ = child.kill();
                }

                // Kill sync daemon if we spawned it
                let daemon = window.state::<DaemonProcess>();
                if let Some(child) = daemon.0.lock().unwrap().take() {
                    let _ = child.kill();
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("Error while running tauri application");
}
