# Cronometer (`shenas-source-cronometer`)

Cronometer nutrition-data connector for Shenas — runs as a **thin third-party client** in the user's own environment.

## Basis

This plugin is part of Shenas's source-plugin cohort. It ships under the [Shenas inclusion policy for source plugins](https://shenas.org/policy/sources) under a **thin-client interpretation** (CEO-confirmed): the plugin runs in the user's own environment, authenticates with the user's own Cronometer credentials, fetches the user's own data, and stores it locally. Shenas does **not** redistribute aggregated Cronometer data. The Cronometer Terms of Service user-side-use clause applies to the user-as-actor, not to Shenas as a data redistributor. Terms reference: [Cronometer Terms of Service](https://cronometer.com/terms/). Scope: this plugin reads the user's own Cronometer nutrition logs using credentials the user has supplied; no data is sent off-device by the plugin, and no aggregated Cronometer data is redistributed by Shenas.

> ## Reviewer note — thin-client framing
>
> This plugin is shipped as a third-party client that the user runs themselves, **not** as a Shenas-hosted service that calls Cronometer on a population of users' behalf. The legal posture rests on four invariants:
>
> 1. **User-as-actor** — the user, not Shenas, is the party making API calls to Cronometer.
> 2. **User credentials** — only the user's own credentials are used; no shared Shenas-side account.
> 3. **No off-device transmission** — fetched data is stored locally and is not sent off-device by the plugin.
> 4. **No aggregation** — Shenas does not aggregate, resell, or redistribute Cronometer-sourced data.
>
> If any of these change, the basis must be re-reviewed before shipping. See [SHE-408 plan §7.1](/SHE/issues/SHE-408#document-plan) and the [SHE-409](/SHE/issues/SHE-409) audit-table for the audit trail.
