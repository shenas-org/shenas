# GCS bucket for package wheels (repo-server)
resource "google_storage_bucket" "packages" {
  name          = "shenas-packages"
  location      = var.region
  storage_class = "STANDARD"

  uniform_bucket_level_access = true

  depends_on = [google_project_service.apis["storage.googleapis.com"]]
}

# Allow the deploy service account to upload packages
resource "google_storage_bucket_iam_member" "packages_deploy" {
  bucket = google_storage_bucket.packages.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.github_deploy.email}"
}

# Allow the default compute SA (GKE pods) to read packages
resource "google_storage_bucket_iam_member" "packages_gke" {
  bucket = google_storage_bucket.packages.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:232211553387-compute@developer.gserviceaccount.com"
}
