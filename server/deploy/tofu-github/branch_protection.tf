# Branch protection for the public OSS repo.
resource "github_branch_protection" "oss_main" {
  provider      = github.shenas_org
  repository_id = github_repository.oss.node_id
  pattern       = "main"

  required_pull_request_reviews {
    required_approving_review_count = 0
    dismiss_stale_reviews           = true
  }

  allows_force_pushes = false
  allows_deletions    = false
}
