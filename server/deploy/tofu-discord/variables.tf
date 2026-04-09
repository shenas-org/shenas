variable "discord_bot_token" {
  description = "Discord bot token (from Developer Portal)"
  type        = string
  sensitive   = true
}

variable "discord_server_id" {
  description = "Existing Discord server (guild) ID to manage"
  type        = string
}
