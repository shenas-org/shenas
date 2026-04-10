# -----------------------------------------------------------------------------
# Channel permission overrides
# -----------------------------------------------------------------------------

# Announcements: only Admins and Moderators can post
resource "discord_channel_permission" "announcements_everyone_deny" {
  channel_id   = discord_text_channel.announcements.id
  type         = "role"
  overwrite_id = var.discord_server_id # @everyone role ID == server ID
  deny         = 2048                  # SEND_MESSAGES
}

resource "discord_channel_permission" "announcements_admin_allow" {
  channel_id   = discord_text_channel.announcements.id
  type         = "role"
  overwrite_id = discord_role.admin.id
  allow        = 2048 # SEND_MESSAGES
}

resource "discord_channel_permission" "announcements_mod_allow" {
  channel_id   = discord_text_channel.announcements.id
  type         = "role"
  overwrite_id = discord_role.moderator.id
  allow        = 2048 # SEND_MESSAGES
}

# Rules: read-only for everyone except Admins
resource "discord_channel_permission" "rules_everyone_deny" {
  channel_id   = discord_text_channel.rules.id
  type         = "role"
  overwrite_id = var.discord_server_id
  deny         = 2048 # SEND_MESSAGES
}

resource "discord_channel_permission" "rules_admin_allow" {
  channel_id   = discord_text_channel.rules.id
  type         = "role"
  overwrite_id = discord_role.admin.id
  allow        = 2048 # SEND_MESSAGES
}

