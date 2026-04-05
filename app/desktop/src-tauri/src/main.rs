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

fn is_server_running() -> bool {
    let client = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(2))
        .build()
        .unwrap();
    client
        .get(format!("{DESKTOP_URL}/api/health"))
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

            let window = WebviewWindowBuilder::new(
                app,
                "main",
                WebviewUrl::External(DESKTOP_URL.parse().unwrap()),
            )
            .title("shenas")
            .inner_size(1200.0, 800.0)
            .resizable(true)
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
