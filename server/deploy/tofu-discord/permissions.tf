# -----------------------------------------------------------------------------
# Channel permission overrides
# -----------------------------------------------------------------------------

# Announcements: only Admins and Moderators can post
resource "discord_channel_permission" "announcements_everyone_deny" {
  channel_id   = discord_text_channel.announcements.id
  type         = "role"
  overwrite_id = var.discord_server_id # @everyone role ID == server ID
  deny         = 0x800                 # SEND_MESSAGES
}

resource "discord_channel_permission" "announcements_admin_allow" {
  channel_id   = discord_text_channel.announcements.id
  type         = "role"
  overwrite_id = discord_role.admin.id
  allow        = 0x800 # SEND_MESSAGES
}

resource "discord_channel_permission" "announcements_mod_allow" {
  channel_id   = discord_text_channel.announcements.id
  type         = "role"
  overwrite_id = discord_role.moderator.id
  allow        = 0x800 # SEND_MESSAGES
}

# Rules: read-only for everyone except Admins
resource "discord_channel_permission" "rules_everyone_deny" {
  channel_id   = discord_text_channel.rules.id
  type         = "role"
  overwrite_id = var.discord_server_id
  deny         = 0x800 # SEND_MESSAGES
}

resource "discord_channel_permission" "rules_admin_allow" {
  channel_id   = discord_text_channel.rules.id
  type         = "role"
  overwrite_id = discord_role.admin.id
  allow        = 0x800 # SEND_MESSAGES
}

# CI/CD: read-only for members, writable by Admins and Contributors
resource "discord_channel_permission" "ci_cd_everyone_deny" {
  channel_id   = discord_text_channel.ci_cd.id
  type         = "role"
  overwrite_id = var.discord_server_id
  deny         = 0x800 # SEND_MESSAGES
}

resource "discord_channel_permission" "ci_cd_admin_allow" {
  channel_id   = discord_text_channel.ci_cd.id
  type         = "role"
  overwrite_id = discord_role.admin.id
  allow        = 0x800 # SEND_MESSAGES
}

resource "discord_channel_permission" "ci_cd_contributor_allow" {
  channel_id   = discord_text_channel.ci_cd.id
  type         = "role"
  overwrite_id = discord_role.contributor.id
  allow        = 0x800 # SEND_MESSAGES
}

# Pull Requests: read-only for members, writable by Contributors and Plugin Devs
resource "discord_channel_permission" "pr_everyone_deny" {
  channel_id   = discord_text_channel.pull_requests.id
  type         = "role"
  overwrite_id = var.discord_server_id
  deny         = 0x800 # SEND_MESSAGES
}

resource "discord_channel_permission" "pr_contributor_allow" {
  channel_id   = discord_text_channel.pull_requests.id
  type         = "role"
  overwrite_id = discord_role.contributor.id
  allow        = 0x800 # SEND_MESSAGES
}

resource "discord_channel_permission" "pr_plugin_dev_allow" {
  channel_id   = discord_text_channel.pull_requests.id
  type         = "role"
  overwrite_id = discord_role.plugin_developer.id
  allow        = 0x800 # SEND_MESSAGES
}
