// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::env;
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::Mutex;
use std::thread;
use std::time::Duration;

use tauri::Manager;

struct ServerProcess(Mutex<Option<Child>>);
struct DaemonProcess(Mutex<Option<Child>>);

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
    // Fallback: assume we're somewhere inside the repo
    env::current_dir().unwrap()
}

fn start_server() -> Child {
    let root = workspace_root();
    eprintln!("Starting shenas server from: {}", root.display());
    Command::new("uv")
        .args(["run", "--no-sync", "shenas", "--no-tls"])
        .current_dir(&root)
        .spawn()
        .expect("Failed to start shenas server. Is uv and shenas-app installed?")
}

fn start_sync_daemon() -> Child {
    let root = workspace_root();
    eprintln!("Starting sync daemon from: {}", root.display());
    Command::new("uv")
        .args(["run", "--no-sync", "shenas-scheduler"])
        .current_dir(&root)
        .spawn()
        .expect("Failed to start sync daemon")
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

    let server_state = if already_running {
        eprintln!("Server already running, skipping sidecar spawn");
        ServerProcess(Mutex::new(None))
    } else {
        let server = start_server();
        let state = ServerProcess(Mutex::new(Some(server)));

        if !wait_for_server("http://localhost:7280/api/health", Duration::from_secs(30)) {
            eprintln!("Server failed to start within 30 seconds");
            if let Some(mut child) = state.0.lock().unwrap().take() {
                let _ = child.kill();
            }
            std::process::exit(1);
        }
        state
    };

    // Start the sync daemon sidecar (only if we also started the server)
    let daemon_state = if already_running {
        DaemonProcess(Mutex::new(None))
    } else {
        DaemonProcess(Mutex::new(Some(start_sync_daemon())))
    };

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(server_state)
        .manage(daemon_state)
        .setup(|app| {
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
                let mut guard = server.0.lock().unwrap();
                if let Some(ref mut child) = *guard {
                    let _: Result<(), std::io::Error> = child.kill();
                }
                drop(guard);

                // Kill sync daemon if we spawned it
                let daemon = window.state::<DaemonProcess>();
                let mut guard = daemon.0.lock().unwrap();
                if let Some(ref mut child) = *guard {
                    let _: Result<(), std::io::Error> = child.kill();
                }
                drop(guard);
            }
        })
        .run(tauri::generate_context!())
        .expect("Error while running tauri application");
}
