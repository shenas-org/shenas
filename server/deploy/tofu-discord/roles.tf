# -----------------------------------------------------------------------------
# Roles (ordered by hierarchy, highest first)
# -----------------------------------------------------------------------------

resource "discord_role" "admin" {
  server_id   = var.discord_server_id
  name        = "Admin"
  permissions = 8 # ADMINISTRATOR
  color       = 15158332
  hoist       = true
  mentionable = false
  position    = 5
}

# Moderator permissions:
#   BAN_MEMBERS=4 + KICK_MEMBERS=2 + MANAGE_MESSAGES=8192 +
#   MANAGE_THREADS=268435456 + MANAGE_CHANNELS=16384 + MANAGE_ROLES=65536 +
#   MUTE_MEMBERS=4194304 + DEAFEN_MEMBERS=8388608 + MOVE_MEMBERS=16777216
resource "discord_role" "moderator" {
  server_id   = var.discord_server_id
  name        = "Moderator"
  permissions = 4 + 2 + 8192 + 268435456 + 16384 + 65536 + 4194304 + 8388608 + 16777216
  color       = 3447003
  hoist       = true
  mentionable = true
  position    = 4
}

# Contributor permissions:
#   SEND_MESSAGES=2048 + ADD_REACTIONS=64 + VIEW_CHANNEL=1024 +
#   USE_EXTERNAL_EMOJIS=67108864 + READ_MESSAGE_HISTORY=262144 +
#   CREATE_PUBLIC_THREADS=34359738368 + SEND_MESSAGES_IN_THREADS=4294967296 +
#   EMBED_LINKS=256 + ATTACH_FILES=32768
resource "discord_role" "contributor" {
  server_id   = var.discord_server_id
  name        = "Contributor"
  permissions = 2048 + 64 + 1024 + 67108864 + 262144 + 34359738368 + 4294967296 + 256 + 32768
  color       = 3066993
  hoist       = true
  mentionable = true
  position    = 3
}

# Plugin Developer: same permissions as Contributor
resource "discord_role" "plugin_developer" {
  server_id   = var.discord_server_id
  name        = "Plugin Developer"
  permissions = 2048 + 64 + 1024 + 67108864 + 262144 + 34359738368 + 4294967296 + 256 + 32768
  color       = 10181046
  hoist       = true
  mentionable = true
  position    = 2
}

# Member: basic send + read permissions
resource "discord_role" "member" {
  server_id   = var.discord_server_id
  name        = "Member"
  permissions = 2048 + 64 + 1024 + 262144 + 34359738368 + 4294967296 + 256 + 32768
  color       = 9807270
  hoist       = false
  mentionable = false
  position    = 1
}
