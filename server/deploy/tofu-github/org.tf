# Org creation is manual (GitHub web UI). These manage settings post-creation.

resource "github_organization_settings" "shenas_org" {
  provider      = github.shenas_org
  billing_email = var.billing_email
  blog          = "https://shenas.net"
  description   = "Personal analytics platform"
}

resource "github_organization_settings" "shenas_net" {
  provider      = github.shenas_net
  billing_email = var.billing_email
  description   = "shenas platform (private)"
}
