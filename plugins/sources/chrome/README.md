# Chrome (`shenas-source-chrome`)

Google Chrome local browsing-history connector for Shenas.

## Basis

This plugin is part of Shenas's source-plugin cohort. It ships under the [Shenas inclusion policy for source plugins](https://shenas.org/policy/sources) because Chrome stores the user's own browsing data in a local profile on the user's device, and Google's terms affirm that the user retains the rights to that content. The plugin reads that local profile directly; no Google service is contacted. Terms reference: [Google Terms of Service](https://policies.google.com/terms) (incorporated into Chrome via the [Chrome and Chrome OS Additional Terms](https://www.google.com/chrome/terms/)). Load-bearing clause: "Your content remains yours, which means that you retain any intellectual property rights that you have in your content." Scope: this plugin reads the user's own Chrome profile (history, bookmarks, etc.) from the local filesystem; no data is sent off-device by the plugin and no Google service is contacted.

> Note: this plugin operates entirely user-side. Service-ToS scope does not reach local-file reads of the user's own profile data. If Google later publishes an explicit prohibition on third-party reads of the on-device Chrome profile, this basis must be re-reviewed. See [SHE-408 plan §7.2](/SHE/issues/SHE-408#document-plan) and the [SHE-489 audit-table](/SHE/issues/SHE-489#document-audit-table) for the audit trail.
