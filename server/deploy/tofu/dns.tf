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

# shenas.net -> GKE ingress IP
resource "google_dns_record_set" "root" {
  name         = "${var.domain}."
  managed_zone = google_dns_managed_zone.shenas_net.name
  type         = "A"
  ttl          = 300
  rrdatas      = [google_compute_global_address.ingress_ip.address]
}

# www.shenas.net -> shenas.net (CNAME)
resource "google_dns_record_set" "www" {
  name         = "www.${var.domain}."
  managed_zone = google_dns_managed_zone.shenas_net.name
  type         = "CNAME"
  ttl          = 300
  rrdatas      = ["${var.domain}."]
}

# fl.shenas.net -> GKE ingress IP
resource "google_dns_record_set" "fl" {
  name         = "fl.${var.domain}."
  managed_zone = google_dns_managed_zone.shenas_net.name
  type         = "A"
  ttl          = 300
  rrdatas      = [google_compute_global_address.ingress_ip.address]
}

# --------------------------------------------------------------------------
# Cloud DNS zone for shenas.org
# --------------------------------------------------------------------------

resource "google_dns_managed_zone" "shenas_org" {
  name     = "shenas-org"
  dns_name = "shenas.org."

  depends_on = [google_project_service.apis["dns.googleapis.com"]]
}

# shenas.org -> GKE ingress IP
resource "google_dns_record_set" "org_root" {
  name         = "shenas.org."
  managed_zone = google_dns_managed_zone.shenas_org.name
  type         = "A"
  ttl          = 300
  rrdatas      = [google_compute_global_address.ingress_ip.address]
}

# www.shenas.org -> shenas.org (CNAME)
resource "google_dns_record_set" "org_www" {
  name         = "www.shenas.org."
  managed_zone = google_dns_managed_zone.shenas_org.name
  type         = "CNAME"
  ttl          = 300
  rrdatas      = ["shenas.org."]
}
