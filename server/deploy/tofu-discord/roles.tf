# -----------------------------------------------------------------------------
# Roles (ordered by hierarchy, highest first)
# -----------------------------------------------------------------------------

resource "discord_role" "admin" {
  server_id   = var.discord_server_id
  name        = "Admin"
  permissions = 8 # ADMINISTRATOR
  color       = "0xe74c3c"
  hoist       = true
  mentionable = false
  position    = 5
}

resource "discord_role" "moderator" {
  server_id = var.discord_server_id
  name      = "Moderator"
  permissions = sum([
    0x4,        # BAN_MEMBERS
    0x2,        # KICK_MEMBERS
    0x2000,     # MANAGE_MESSAGES
    0x10000000, # MANAGE_THREADS
    0x4000,     # MANAGE_CHANNELS
    0x10000,    # MANAGE_ROLES
    0x400000,   # MUTE_MEMBERS
    0x800000,   # DEAFEN_MEMBERS
    0x1000000,  # MOVE_MEMBERS
  ])
  color       = "0x3498db"
  hoist       = true
  mentionable = true
  position    = 4
}

resource "discord_role" "contributor" {
  server_id = var.discord_server_id
  name      = "Contributor"
  permissions = sum([
    0x800,      # SEND_MESSAGES
    0x40,       # ADD_REACTIONS
    0x400,      # VIEW_CHANNEL
    0x4000000,  # USE_EXTERNAL_EMOJIS
    0x40000,    # READ_MESSAGE_HISTORY
    0x800000000, # CREATE_PUBLIC_THREADS
    0x1000000000, # SEND_MESSAGES_IN_THREADS
    0x100,      # EMBED_LINKS
    0x8000,     # ATTACH_FILES
  ])
  color       = "0x2ecc71"
  hoist       = true
  mentionable = true
  position    = 3
}

resource "discord_role" "plugin_developer" {
  server_id = var.discord_server_id
  name      = "Plugin Developer"
  permissions = sum([
    0x800,      # SEND_MESSAGES
    0x40,       # ADD_REACTIONS
    0x400,      # VIEW_CHANNEL
    0x4000000,  # USE_EXTERNAL_EMOJIS
    0x40000,    # READ_MESSAGE_HISTORY
    0x800000000, # CREATE_PUBLIC_THREADS
    0x1000000000, # SEND_MESSAGES_IN_THREADS
    0x100,      # EMBED_LINKS
    0x8000,     # ATTACH_FILES
  ])
  color       = "0x9b59b6"
  hoist       = true
  mentionable = true
  position    = 2
}

resource "discord_role" "member" {
  server_id = var.discord_server_id
  name      = "Member"
  permissions = sum([
    0x800,      # SEND_MESSAGES
    0x40,       # ADD_REACTIONS
    0x400,      # VIEW_CHANNEL
    0x40000,    # READ_MESSAGE_HISTORY
    0x800000000, # CREATE_PUBLIC_THREADS
    0x1000000000, # SEND_MESSAGES_IN_THREADS
    0x100,      # EMBED_LINKS
    0x8000,     # ATTACH_FILES
  ])
  color       = "0x95a5a6"
  hoist       = false
  mentionable = false
  position    = 1
}
