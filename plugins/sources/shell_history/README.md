# Shell history (`shenas-source-shell-history`)

Shell command history (bash/zsh/fish) connector for Shenas.

## Basis

This plugin is part of Shenas's source-plugin cohort. It ships under the [Shenas inclusion policy for source plugins](https://shenas.org/policy/sources) because shell history files are local files written by the user's own shell; there is no service ToS to apply to reading those files. Terms reference: local POSIX shell history files (typically `~/.bash_history`, `~/.zsh_history`, `~/.local/share/fish/fish_history`) — see the POSIX [`sh`](https://pubs.opengroup.org/onlinepubs/9699919799/utilities/sh.html) specification and the bash/zsh/fish manuals for per-shell behaviour. Scope: this plugin reads the user's local shell history files; no data is sent off-device by the plugin.
