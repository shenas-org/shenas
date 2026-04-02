fn main() {
    // Debug: print the manifest dir so we can verify rust-embed paths
    let manifest_dir = std::env::var("CARGO_MANIFEST_DIR").unwrap_or_default();
    let ui_dist = std::path::Path::new(&manifest_dir).join("../ui-dist");
    println!("cargo:warning=CARGO_MANIFEST_DIR={}", manifest_dir);
    println!("cargo:warning=ui-dist resolved to: {}", ui_dist.display());
    println!("cargo:warning=ui-dist exists: {}", ui_dist.exists());
    if ui_dist.exists() {
        for entry in std::fs::read_dir(&ui_dist).unwrap() {
            let entry = entry.unwrap();
            println!("cargo:warning=  ui-dist/{}", entry.file_name().to_string_lossy());
        }
    }
    tauri_build::build();
}
