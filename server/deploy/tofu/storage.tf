# GCS bucket for package wheels (repo-server)
resource "google_storage_bucket" "packages" {
  name          = "shenas-packages"
  location      = var.region
  storage_class = "STANDARD"

  uniform_bucket_level_access = true

  depends_on = [google_project_service.apis["storage.googleapis.com"]]
}

# Allow the GKE service account to read/write packages
resource "google_storage_bucket_iam_member" "packages_rw" {
  bucket = google_storage_bucket.packages.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.github_deploy.email}"
}
