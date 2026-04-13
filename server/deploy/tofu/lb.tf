# Terraform-managed HTTPS Load Balancer
#
# Replaces the GKE-managed Ingress. Supports mixed backends:
# - GCS backend buckets for static sites (shenas.net, shenas.org)
# - GKE NEG backend services for APIs (shenas-net-api, fl-server)
#
# The K8s services create standalone NEGs via cloud.google.com/neg
# annotations. We reference them here by name.

# ---------------------------------------------------------------------------
# NEG backend services (K8s pods via standalone NEGs)
# ---------------------------------------------------------------------------

# NEGs are created by GKE when services have the annotation:
#   cloud.google.com/neg: '{"exposed_ports": {"80": {"name": "api-neg"}}}'
# We reference them as data sources.

locals {
  zones = ["${var.region}-a", "${var.region}-b", "${var.region}-c"]
}

data "google_compute_network_endpoint_group" "api" {
  for_each = toset(local.zones)
  name     = "api-neg"
  zone     = each.value
}

data "google_compute_network_endpoint_group" "fl_api" {
  for_each = toset(local.zones)
  name     = "fl-api-neg"
  zone     = each.value
}

data "google_compute_network_endpoint_group" "fl_grpc" {
  for_each = toset(local.zones)
  name     = "fl-grpc-neg"
  zone     = each.value
}

resource "google_compute_backend_service" "api" {
  name                  = "api-backend"
  protocol              = "HTTP"
  port_name             = "http"
  timeout_sec           = 30
  health_checks         = [google_compute_health_check.api.id]
  load_balancing_scheme = "EXTERNAL_MANAGED"

  dynamic "backend" {
    for_each = data.google_compute_network_endpoint_group.api
    content {
      group          = backend.value.id
      balancing_mode = "RATE"
      max_rate       = 1000
    }
  }
}

resource "google_compute_backend_service" "fl_api" {
  name                  = "fl-api-backend"
  protocol              = "HTTP"
  port_name             = "http"
  timeout_sec           = 30
  health_checks         = [google_compute_health_check.api.id]
  load_balancing_scheme = "EXTERNAL_MANAGED"

  dynamic "backend" {
    for_each = data.google_compute_network_endpoint_group.fl_api
    content {
      group          = backend.value.id
      balancing_mode = "RATE"
      max_rate       = 1000
    }
  }
}

resource "google_compute_backend_service" "fl_grpc" {
  name                  = "fl-grpc-backend"
  protocol              = "HTTP2"
  port_name             = "grpc"
  timeout_sec           = 30
  health_checks         = [google_compute_health_check.api.id]
  load_balancing_scheme = "EXTERNAL_MANAGED"

  dynamic "backend" {
    for_each = data.google_compute_network_endpoint_group.fl_grpc
    content {
      group          = backend.value.id
      balancing_mode = "RATE"
      max_rate       = 1000
    }
  }
}

resource "google_compute_health_check" "api" {
  name = "api-health-check"

  http_health_check {
    port         = 8000
    request_path = "/api/health"
  }
}

# ---------------------------------------------------------------------------
# URL Map (routing rules)
# ---------------------------------------------------------------------------

resource "google_compute_url_map" "main" {
  name            = "shenas-lb"
  default_service = google_compute_backend_bucket.shenas_net.id

  # shenas.net: /api/* -> API, /* -> GCS
  host_rule {
    hosts        = ["shenas.net", "www.shenas.net"]
    path_matcher = "shenas-net"
  }

  path_matcher {
    name            = "shenas-net"
    default_service = google_compute_backend_bucket.shenas_net.id

    path_rule {
      paths   = ["/api/*"]
      service = google_compute_backend_service.api.id
    }
  }

  # repo.shenas.net -> API
  host_rule {
    hosts        = ["repo.shenas.net"]
    path_matcher = "repo"
  }

  path_matcher {
    name            = "repo"
    default_service = google_compute_backend_service.api.id
  }

  # fl.shenas.net: /api/* -> FL API, /* -> FL gRPC
  host_rule {
    hosts        = ["fl.shenas.net"]
    path_matcher = "fl"
  }

  path_matcher {
    name            = "fl"
    default_service = google_compute_backend_service.fl_grpc.id

    path_rule {
      paths   = ["/api/*"]
      service = google_compute_backend_service.fl_api.id
    }
  }

  # shenas.org -> GCS
  host_rule {
    hosts        = ["shenas.org", "www.shenas.org"]
    path_matcher = "shenas-org"
  }

  path_matcher {
    name            = "shenas-org"
    default_service = google_compute_backend_bucket.shenas_org.id
  }
}

# HTTP -> HTTPS redirect
resource "google_compute_url_map" "http_redirect" {
  name = "shenas-http-redirect"

  default_url_redirect {
    https_redirect         = true
    strip_query            = false
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
  }
}

# ---------------------------------------------------------------------------
# SSL Certificate
# ---------------------------------------------------------------------------

resource "google_compute_managed_ssl_certificate" "main" {
  name = "shenas-cert-tf"

  managed {
    domains = [
      "shenas.net",
      "www.shenas.net",
      "repo.shenas.net",
      "fl.shenas.net",
      "shenas.org",
      "www.shenas.org",
    ]
  }
}

# ---------------------------------------------------------------------------
# HTTPS proxy + forwarding rule
# ---------------------------------------------------------------------------

resource "google_compute_target_https_proxy" "main" {
  name             = "shenas-https-proxy"
  url_map          = google_compute_url_map.main.id
  ssl_certificates = [google_compute_managed_ssl_certificate.main.id]
}

resource "google_compute_global_forwarding_rule" "https" {
  name                  = "shenas-https"
  ip_address            = google_compute_global_address.ingress_ip.address
  ip_protocol           = "TCP"
  port_range            = "443"
  target                = google_compute_target_https_proxy.main.id
  load_balancing_scheme = "EXTERNAL_MANAGED"
}

# HTTP proxy + forwarding rule (redirects to HTTPS)
resource "google_compute_target_http_proxy" "redirect" {
  name    = "shenas-http-redirect"
  url_map = google_compute_url_map.http_redirect.id
}

resource "google_compute_global_forwarding_rule" "http" {
  name                  = "shenas-http"
  ip_address            = google_compute_global_address.ingress_ip.address
  ip_protocol           = "TCP"
  port_range            = "80"
  target                = google_compute_target_http_proxy.redirect.id
  load_balancing_scheme = "EXTERNAL_MANAGED"
}
