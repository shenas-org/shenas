# RescueTime (`shenas-source-rescuetime`)

RescueTime productivity-tracking connector for Shenas.

## Basis

This plugin is part of Shenas's source-plugin cohort. It ships under the [Shenas inclusion policy for source plugins](https://shenas.org/policy/sources) because RescueTime's developer documentation describes user-issued API keys as the canonical authorization mode for third-party clients reading the user's own activity data. Terms reference: [RescueTime Developer Documentation](https://www.rescuetime.com/rtx/developers) (canonical published authorization surface). Load-bearing clause: "Users can set up an API key by going to their key management page and creating a new key. That key must be included with each API request. The user can revoke keys at any time." Scope: this plugin reads the user's own RescueTime activity data using an API key the user has generated and can revoke at any time; the key is the only thing presented to RescueTime.

> Note: the canonical authorization surface cited here is the publicly-published developer-documentation page; the `/anapi/setup` setup screen is auth-gated and could not be used as the v1 cite. If RescueTime later changes the published developer policy, this basis must be re-reviewed. See the [SHE-489 audit-table](/SHE/issues/SHE-489#document-audit-table) for the audit trail.
