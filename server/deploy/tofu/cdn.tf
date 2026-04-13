# Backend buckets for static sites (GCS + Cloud CDN)

resource "google_compute_backend_bucket" "shenas_net" {
  name        = "shenas-net-cdn"
  bucket_name = google_storage_bucket.shenas_net.name
  enable_cdn  = true
}

resource "google_compute_backend_bucket" "shenas_org" {
  name        = "shenas-org-cdn"
  bucket_name = google_storage_bucket.shenas_org.name
  enable_cdn  = true
}
