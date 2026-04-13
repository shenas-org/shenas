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

# ---------------------------------------------------------------------------
# GCS bucket for shenas.net static site (Astro SPA)
# ---------------------------------------------------------------------------

resource "google_storage_bucket" "shenas_net" {
  name          = "shenas-net-site"
  location      = var.region
  storage_class = "STANDARD"

  uniform_bucket_level_access = true

  website {
    main_page_suffix = "index.html"
    not_found_page   = "index.html" # SPA fallback
  }

  depends_on = [google_project_service.apis["storage.googleapis.com"]]
}

# Public read access (static website)
resource "google_storage_bucket_iam_member" "shenas_net_public" {
  bucket = google_storage_bucket.shenas_net.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}

# Allow deploy SA to upload
resource "google_storage_bucket_iam_member" "shenas_net_deploy" {
  bucket = google_storage_bucket.shenas_net.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.github_deploy.email}"
}

# ---------------------------------------------------------------------------
# GCS bucket for shenas.org static site (Astro)
# ---------------------------------------------------------------------------

resource "google_storage_bucket" "shenas_org" {
  name          = "shenas-org-site"
  location      = var.region
  storage_class = "STANDARD"

  uniform_bucket_level_access = true

  website {
    main_page_suffix = "index.html"
    not_found_page   = "index.html"
  }

  depends_on = [google_project_service.apis["storage.googleapis.com"]]
}

resource "google_storage_bucket_iam_member" "shenas_org_public" {
  bucket = google_storage_bucket.shenas_org.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}

resource "google_storage_bucket_iam_member" "shenas_org_deploy" {
  bucket = google_storage_bucket.shenas_org.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.github_deploy.email}"
}
