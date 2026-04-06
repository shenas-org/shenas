// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::Mutex;
use std::thread;
use std::time::Duration;

use tauri::Manager;
use tauri::WebviewUrl;
use tauri::WebviewWindowBuilder;
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

// Desktop sidecars use different ports than dev (7280) to avoid conflicts
const DESKTOP_PORT: u16 = 7281;
const DESKTOP_URL: &str = "http://localhost:7281";

fn find_running_server() -> Option<String> {
    let client = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(2))
        .danger_accept_invalid_certs(true)
        .build()
        .unwrap();

    // 1. Vite dev server (highest priority during development)
    if client
        .get("http://127.0.0.1:5173/api/health")
        .send()
        .map(|r| r.status().is_success())
        .unwrap_or(false)
    {
        return Some("http://127.0.0.1:5173".to_string());
    }

    // 2. Dev server (make dev)
    if client
        .get("http://127.0.0.1:7280/api/health")
        .send()
        .map(|r| r.status().is_success())
        .unwrap_or(false)
    {
        return Some("http://127.0.0.1:7280".to_string());
    }

    // 3. Sidecar server
    if client
        .get("http://127.0.0.1:7281/api/health")
        .send()
        .map(|r| r.status().is_success())
        .unwrap_or(false)
    {
        return Some("http://127.0.0.1:7281".to_string());
    }

    None
}

fn main() {
    // If a server is already running (Vite, dev, or sidecar),
    // skip spawning sidecar processes and use the detected URL.
    let detected_url = find_running_server();
    let already_running = detected_url.is_some();

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
                    .args(["--no-tls", "--port", &DESKTOP_PORT.to_string()])
                    .spawn()
                    .expect("Failed to start shenas server sidecar");

                let state = ServerProcess(Mutex::new(Some(child)));

                if !wait_for_server(
                    &format!("{DESKTOP_URL}/api/health"),
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
                    .args(["--server-url", DESKTOP_URL])
                    .spawn()
                    .expect("Failed to start shenas-scheduler sidecar");
                DaemonProcess(Mutex::new(Some(child)))
            };

            app.manage(server_state);
            app.manage(daemon_state);

            let server_url = detected_url
                .clone()
                .unwrap_or_else(|| DESKTOP_URL.to_string());
            let window = WebviewWindowBuilder::new(
                app,
                "main",
                WebviewUrl::External(server_url.parse().unwrap()),
            )
            .title("shenas")
            .inner_size(1200.0, 800.0)
            .resizable(true)
            .decorations(false)
            .initialization_script(
                // Prevent WebKitGTK from consuming browser shortcuts (Ctrl+P, Ctrl+W, etc.)
                // so they reach the app's hotkey handler instead.
                r#"document.addEventListener('keydown', function(e) {
                    if ((e.ctrlKey || e.metaKey) && ['p','o','w','t','l','g','u','f','h'].includes(e.key.toLowerCase())) {
                        e.preventDefault();
                    }
                }, true);"#,
            )
            .build()?;

            window.show().unwrap();
            Ok(())
        })
        .on_window_event(|window, event| {
            match event {
                tauri::WindowEvent::CloseRequested { .. } | tauri::WindowEvent::Destroyed => {
                    // Kill server if we spawned it
                    if let Some(child) = window.state::<ServerProcess>().0.lock().unwrap().take() {
                        let _ = child.kill();
                    }
                    // Kill sync daemon if we spawned it
                    if let Some(child) = window.state::<DaemonProcess>().0.lock().unwrap().take() {
                        let _ = child.kill();
                    }
                }
                _ => {}
            }
        })
        .run(tauri::generate_context!())
        .expect("Error while running tauri application");
}
