variable "project" {
  description = "GCP project ID"
  default     = "shenas-491609"
}

variable "region" {
  description = "GCP region"
  default     = "us-east4"
}

variable "github_repo" {
  description = "GitHub repository (owner/name)"
  default     = "shenas-net/shenas"
}

variable "domain" {
  description = "Primary domain"
  default     = "shenas.net"
}

variable "cluster_name" {
  description = "GKE cluster name"
  default     = "shenas"
}

variable "db_password" {
  description = "Cloud SQL password for the shenas user"
  sensitive   = true
}

variable "arc_app_id" {
  description = "GitHub App ID for ARC runner registration"
  type        = string
}

variable "arc_app_installation_id" {
  description = "GitHub App installation ID for ARC"
  type        = string
}

variable "arc_app_private_key" {
  description = "GitHub App private key (PEM) for ARC"
  type        = string
  sensitive   = true
}