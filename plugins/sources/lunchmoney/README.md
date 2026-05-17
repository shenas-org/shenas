# Lunch Money (`shenas-source-lunchmoney`)

Lunch Money personal-finance connector for Shenas.

## Basis

This plugin is part of Shenas's source-plugin cohort. It ships under the [Shenas inclusion policy for source plugins](https://shenas.org/policy/sources) because Lunch Money's developer documentation describes user-issued Bearer tokens as the canonical authorization mode for third-party clients reading the user's own financial data. Terms reference: [Lunch Money Developer Documentation](https://lunchmoney.dev/) (canonical authorization surface for the PAT/API path). Load-bearing clauses: "Get your access token by going to the developers page in the Lunch Money app." "Lunch Money API requests are authenticated using the Bearer Token authentication method." Scope: this plugin reads the user's own Lunch Money transactions, budgets, and categories using a Bearer token the user has generated in their own Lunch Money account and can revoke at any time; the token is the only thing presented to Lunch Money.

> Note: the canonical authorization surface cited here is the developer-documentation portal at `lunchmoney.dev`; the human-readable consumer ToS at `lunchmoney.app/terms` returns HTTP 403 to unauthenticated fetchers and could not be used as the v1 cite. If Lunch Money later publishes a more restrictive clause via a member-only channel, this basis must be re-reviewed. See the [SHE-489 audit-table](/SHE/issues/SHE-489#document-audit-table) for the audit trail.
