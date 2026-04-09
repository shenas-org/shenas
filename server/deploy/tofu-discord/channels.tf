# -----------------------------------------------------------------------------
# Welcome channels
# -----------------------------------------------------------------------------

resource "discord_text_channel" "rules" {
  server_id = var.discord_server_id
  name      = "rules"
  category  = discord_category_channel.welcome.id
  topic     = "Community guidelines and code of conduct"
  position  = 0
}

resource "discord_text_channel" "introductions" {
  server_id = var.discord_server_id
  name      = "introductions"
  category  = discord_category_channel.welcome.id
  topic     = "Introduce yourself to the community"
  position  = 1
}

resource "discord_text_channel" "announcements" {
  server_id = var.discord_server_id
  name      = "announcements"
  category  = discord_category_channel.welcome.id
  topic     = "Releases, updates, and important news"
  position  = 2
}

# -----------------------------------------------------------------------------
# Community channels
# -----------------------------------------------------------------------------

resource "discord_text_channel" "general" {
  server_id = var.discord_server_id
  name      = "general"
  category  = discord_category_channel.community.id
  topic     = "General discussion about shenas and self-tracking"
  position  = 0
}

resource "discord_text_channel" "show_and_tell" {
  server_id = var.discord_server_id
  name      = "show-and-tell"
  category  = discord_category_channel.community.id
  topic     = "Share your dashboards, setups, and insights"
  position  = 1
}

resource "discord_text_channel" "feature_requests" {
  server_id = var.discord_server_id
  name      = "feature-requests"
  category  = discord_category_channel.community.id
  topic     = "Suggest new features and improvements"
  position  = 2
}

resource "discord_text_channel" "off_topic" {
  server_id = var.discord_server_id
  name      = "off-topic"
  category  = discord_category_channel.community.id
  topic     = "Non-shenas chat"
  position  = 3
}

# -----------------------------------------------------------------------------
# Development channels
# -----------------------------------------------------------------------------

resource "discord_text_channel" "dev_general" {
  server_id = var.discord_server_id
  name      = "dev-general"
  category  = discord_category_channel.development.id
  topic     = "General development discussion"
  position  = 0
}

resource "discord_text_channel" "architecture" {
  server_id = var.discord_server_id
  name      = "architecture"
  category  = discord_category_channel.development.id
  topic     = "Architecture decisions, RFCs, and design discussions"
  position  = 1
}

resource "discord_text_channel" "pull_requests" {
  server_id = var.discord_server_id
  name      = "pull-requests"
  category  = discord_category_channel.development.id
  topic     = "PR notifications and code review discussion"
  position  = 2
}

resource "discord_text_channel" "ci_cd" {
  server_id = var.discord_server_id
  name      = "ci-cd"
  category  = discord_category_channel.development.id
  topic     = "Build and deployment notifications"
  position  = 3
}

# -----------------------------------------------------------------------------
# Plugin channels
# -----------------------------------------------------------------------------

resource "discord_text_channel" "sources" {
  server_id = var.discord_server_id
  name      = "sources"
  category  = discord_category_channel.plugins.id
  topic     = "Discussion about source plugins (Garmin, Strava, Spotify, etc.)"
  position  = 0
}

resource "discord_text_channel" "datasets" {
  server_id = var.discord_server_id
  name      = "datasets"
  category  = discord_category_channel.plugins.id
  topic     = "Discussion about dataset plugins (fitness, finance, events, etc.)"
  position  = 1
}

resource "discord_text_channel" "dashboards" {
  server_id = var.discord_server_id
  name      = "dashboards"
  category  = discord_category_channel.plugins.id
  topic     = "Dashboard and frontend plugin development"
  position  = 2
}

resource "discord_text_channel" "plugin_ideas" {
  server_id = var.discord_server_id
  name      = "plugin-ideas"
  category  = discord_category_channel.plugins.id
  topic     = "Propose and discuss new plugin ideas"
  position  = 3
}

# -----------------------------------------------------------------------------
# Support channels
# -----------------------------------------------------------------------------

resource "discord_text_channel" "help" {
  server_id = var.discord_server_id
  name      = "help"
  category  = discord_category_channel.support.id
  topic     = "Ask questions and get help with shenas"
  position  = 0
}

resource "discord_text_channel" "bug_reports" {
  server_id = var.discord_server_id
  name      = "bug-reports"
  category  = discord_category_channel.support.id
  topic     = "Report bugs (for confirmed issues, open a GitHub issue)"
  position  = 1
}

resource "discord_text_channel" "self_hosting" {
  server_id = var.discord_server_id
  name      = "self-hosting"
  category  = discord_category_channel.support.id
  topic     = "Help with self-hosting, Docker, and deployment"
  position  = 2
}

# -----------------------------------------------------------------------------
# Voice channels
# -----------------------------------------------------------------------------

resource "discord_voice_channel" "general_voice" {
  server_id = var.discord_server_id
  name      = "General"
  category  = discord_category_channel.voice.id
  position  = 0
}

resource "discord_voice_channel" "pair_programming" {
  server_id = var.discord_server_id
  name      = "Pair Programming"
  category  = discord_category_channel.voice.id
  position  = 1
}
