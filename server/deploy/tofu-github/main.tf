terraform {
  required_version = ">= 1.8"
  required_providers {
    github = {
      source  = "integrations/github"
      version = "~> 6.0"
    }
  }
}

# Public OSS org
provider "github" {
  alias = "shenas_org"
  owner = "shenas-org"
  token = var.github_token
}

# Private monorepo org
provider "github" {
  alias = "shenas_net"
  owner = "shenas-net"
  token = var.github_token
}
