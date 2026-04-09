# -----------------------------------------------------------------------------
# Channel categories
# -----------------------------------------------------------------------------

resource "discord_category_channel" "welcome" {
  server_id = var.discord_server_id
  name      = "Welcome"
  position  = 0
}

resource "discord_category_channel" "community" {
  server_id = var.discord_server_id
  name      = "Community"
  position  = 1
}

resource "discord_category_channel" "plugins" {
  server_id = var.discord_server_id
  name      = "Plugins"
  position  = 3
}

resource "discord_category_channel" "support" {
  server_id = var.discord_server_id
  name      = "Support"
  position  = 4
}

