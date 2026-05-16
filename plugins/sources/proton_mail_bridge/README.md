# Proton Mail Bridge (`shenas-source-proton-mail-bridge`)

Proton Mail Bridge IMAP connector for Shenas.

## Basis

This plugin is part of Shenas's source-plugin cohort. It ships under the [Shenas inclusion policy for source plugins](https://shenas.org/policy/sources) because Proton Mail Bridge runs as a local IMAP gateway under the user's own Proton account; the plugin connects to that locally-running bridge over IMAP, so access uses the user's own credentials and stays on-device. Terms reference: [Proton Mail Bridge](https://proton.me/mail/bridge). Scope: this plugin reads message envelopes from a locally-running Proton Mail Bridge using the user's bridge credentials; no data is sent off-device by the plugin.
