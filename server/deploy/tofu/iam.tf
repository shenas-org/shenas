# Service account for GitHub Actions deployments
resource "google_service_account" "github_deploy" {
  account_id   = "github-deploy"
  display_name = "GitHub Actions deploy"
}

# IAM roles for the deploy service account
resource "google_project_iam_member" "deploy_roles" {
  for_each = toset([
    "roles/artifactregistry.writer",
    "roles/container.developer",
    "roles/iam.serviceAccountUser",
    "roles/cloudbuild.builds.builder",
    "roles/logging.viewer",
    "roles/storage.objectViewer",
  ])

  project = var.project
  role    = each.value
  member  = "serviceAccount:${google_service_account.github_deploy.email}"
}

# Workload Identity Federation pool
resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github-wif-pool"
  display_name              = "GitHub Actions"

  depends_on = [google_project_service.apis["iam.googleapis.com"]]
}

# OIDC provider for GitHub Actions
resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  display_name                       = "GitHub"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
  }

  attribute_condition = "assertion.repository=='${var.github_repo}'"
}

# Allow the GitHub repo to impersonate the service account
resource "google_service_account_iam_member" "wif_binding" {
  service_account_id = google_service_account.github_deploy.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repo}"
}
