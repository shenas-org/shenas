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
  default     = "afuncke/shenas"
}

variable "domain" {
  description = "Primary domain"
  default     = "shenas.net"
}

variable "cluster_name" {
  description = "GKE cluster name"
  default     = "shenas"
}
