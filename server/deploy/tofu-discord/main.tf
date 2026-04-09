terraform {
  required_version = ">= 1.8"
  required_providers {
    discord = {
      source  = "Lucky3028/discord"
      version = "~> 2.0"
    }
  }
}

provider "discord" {
  token = var.discord_bot_token
}
