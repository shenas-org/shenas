# Cloud DNS zone for shenas.net
resource "google_dns_managed_zone" "shenas_net" {
  name     = "shenas-net"
  dns_name = "${var.domain}."

  depends_on = [google_project_service.apis["dns.googleapis.com"]]
}

# repo.shenas.net -> GKE ingress IP
resource "google_dns_record_set" "repo" {
  name         = "repo.${var.domain}."
  managed_zone = google_dns_managed_zone.shenas_net.name
  type         = "A"
  ttl          = 300
  rrdatas      = [google_compute_global_address.ingress_ip.address]
}

# fl.shenas.net -> GKE ingress IP
resource "google_dns_record_set" "fl" {
  name         = "fl.${var.domain}."
  managed_zone = google_dns_managed_zone.shenas_net.name
  type         = "A"
  ttl          = 300
  rrdatas      = [google_compute_global_address.ingress_ip.address]
}
