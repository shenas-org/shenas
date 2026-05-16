# IMAP (`shenas-source-imap`)

Generic IMAP envelope-metadata connector for Shenas.

## Basis

This plugin is part of Shenas's source-plugin cohort. It ships under the [Shenas inclusion policy for source plugins](https://shenas.org/policy/sources) because IMAP is an open IETF-standardised protocol designed for third-party mail clients, accessed under the user's own mailbox credentials. Terms reference: [RFC 9051 — IMAP4rev2](https://datatracker.ietf.org/doc/html/rfc9051). Scope: this plugin reads message envelopes from an IMAP mailbox using credentials the user has supplied; no data is sent off-device by the plugin.

> Note: individual IMAP providers may layer additional terms on top of the protocol (for example, Microsoft 365 requires OAuth for IMAP access). The plugin's own basis under the inclusion policy is the open protocol; per-provider variance is a deployment concern.
