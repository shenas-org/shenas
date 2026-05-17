# Firefox (`shenas-source-firefox`)

Firefox local browsing-history connector for Shenas.

## Basis

This plugin is part of Shenas's source-plugin cohort. It ships under the [Shenas inclusion policy for source plugins](https://shenas.org/policy/sources) because Firefox stores the user's own browsing data in a local profile on the user's device, and Mozilla's privacy notice confirms that this data does not leave the device. The plugin reads that local profile directly; no Mozilla service is contacted. Terms reference: [Firefox Privacy Notice](https://www.mozilla.org/en-US/privacy/firefox/) (primary cite) and [Firefox Terms of Use](https://www.mozilla.org/en-US/about/legal/terms/firefox/) (MPL software grant; contains no clause restricting what other software the user runs locally may read). Load-bearing clause: "Firefox processes a variety of personal data in a way that does not leave your device, such as browsing history, web form data, temporary internet files, and cookies." Scope: this plugin reads the user's own Firefox profile (history, bookmarks, etc.) from the local filesystem; no data is sent off-device by the plugin and no Mozilla service is contacted.

> Note: this plugin operates entirely user-side. Service-ToS scope does not reach local-file reads of the user's own profile data. If Mozilla later publishes an explicit prohibition on third-party reads of the on-device Firefox profile, this basis must be re-reviewed. See [SHE-408 plan §7.2](/SHE/issues/SHE-408#document-plan) and the [SHE-489 audit-table](/SHE/issues/SHE-489#document-audit-table) for the audit trail.
