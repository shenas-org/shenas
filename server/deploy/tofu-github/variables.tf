variable "github_token" {
  description = "GitHub personal access token with admin:org and repo scopes"
  type        = string
  sensitive   = true
}

variable "org_name" {
  description = "GitHub organization name"
  type        = string
  default     = "shenas"
}

variable "billing_email" {
  description = "Organization billing email"
  type        = string
  default     = ""
}
