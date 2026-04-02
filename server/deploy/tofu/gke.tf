# GKE Autopilot cluster
resource "google_container_cluster" "shenas" {
  name     = var.cluster_name
  location = var.region

  enable_autopilot = true

  # Autopilot manages node pools automatically
  deletion_protection = false

  depends_on = [google_project_service.apis["container.googleapis.com"]]
}

# Static IP for the ingress load balancer
resource "google_compute_global_address" "ingress_ip" {
  name = "shenas-ip"
}

# Artifact Registry for Docker images
resource "google_artifact_registry_repository" "shenas" {
  location      = var.region
  repository_id = "shenas"
  format        = "DOCKER"
  description   = "Shenas container images"

  depends_on = [google_project_service.apis["artifactregistry.googleapis.com"]]
}
