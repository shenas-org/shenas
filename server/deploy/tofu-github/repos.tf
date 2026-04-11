# Public OSS repo under the shenas-org org.
# Copybara syncs from shenas-net/shenas with premium paths stripped.
resource "github_repository" "oss" {
  provider    = github.shenas_org
  name        = "shenas"
  description = "Local-first quantified-self platform -- sync, normalize, and visualize your health, finance, and lifestyle data"
  visibility  = "public"

  has_issues   = true
  has_wiki     = false
  has_projects = false

  allow_merge_commit = false
  allow_squash_merge = true
  allow_rebase_merge = true

  delete_branch_on_merge = true

  topics = [
    "quantified-self",
    "local-first",
    "duckdb",
    "data-pipeline",
    "federated-learning",
  ]
}

# Private monorepo under the shenas-net org.
# Transferred from afuncke/shenas.
# Terraform import: tofu import github_repository.private shenas
resource "github_repository" "private" {
  provider    = github.shenas_net
  name        = "shenas"
  description = "shenas platform monorepo (private)"
  visibility  = "private"

  has_issues   = true
  has_wiki     = false
  has_projects = false

  allow_merge_commit = false
  allow_squash_merge = true
  allow_rebase_merge = true

  delete_branch_on_merge = true
}
