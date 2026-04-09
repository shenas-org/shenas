output "server_id" {
  description = "Discord server ID"
  value       = var.discord_server_id
}

output "channel_ids" {
  description = "Map of channel names to IDs"
  value = {
    rules            = discord_text_channel.rules.id
    introductions    = discord_text_channel.introductions.id
    announcements    = discord_text_channel.announcements.id
    general          = discord_text_channel.general.id
    show_and_tell    = discord_text_channel.show_and_tell.id
    feature_requests = discord_text_channel.feature_requests.id
    off_topic        = discord_text_channel.off_topic.id
    sources          = discord_text_channel.sources.id
    datasets         = discord_text_channel.datasets.id
    dashboards       = discord_text_channel.dashboards.id
    plugin_ideas     = discord_text_channel.plugin_ideas.id
    help             = discord_text_channel.help.id
    bug_reports      = discord_text_channel.bug_reports.id
  }
}

output "role_ids" {
  description = "Map of role names to IDs"
  value = {
    admin            = discord_role.admin.id
    moderator        = discord_role.moderator.id
    contributor      = discord_role.contributor.id
    plugin_developer = discord_role.plugin_developer.id
    member           = discord_role.member.id
  }
}
