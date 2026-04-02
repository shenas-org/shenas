output "nameservers" {
  description = "Set these as custom nameservers in GoDaddy"
  value       = google_dns_managed_zone.shenas_net.name_servers
}

output "static_ip" {
  description = "GKE ingress static IP"
  value       = google_compute_global_address.ingress_ip.address
}

output "wif_provider" {
  description = "Workload Identity Provider (set as GCP_WORKLOAD_IDENTITY_PROVIDER in GitHub)"
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "service_account" {
  description = "Deploy service account (set as GCP_SERVICE_ACCOUNT in GitHub)"
  value       = google_service_account.github_deploy.email
}

output "artifact_registry" {
  description = "Docker registry URL"
  value       = "${var.region}-docker.pkg.dev/${var.project}/${google_artifact_registry_repository.shenas.repository_id}"
}
