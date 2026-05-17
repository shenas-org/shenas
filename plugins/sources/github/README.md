# GitHub (`shenas-source-github`)

GitHub activity and repository connector for Shenas.

## Basis

This plugin is part of Shenas's source-plugin cohort. It ships under the [Shenas inclusion policy for source plugins](https://shenas.org/policy/sources) because GitHub explicitly supports user-issued Personal Access Tokens as a first-class third-party authorization mode, and GitHub's Terms of Service affirm that the user owns the content the plugin reads. Terms reference: [GitHub Terms of Service](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service) (§D.3 — "Your Content") and the [Personal Access Tokens documentation](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens). Load-bearing clauses: ToS §D.3 — "You own Your Content." PAT documentation — "Personal access tokens are an alternative to using passwords for authentication to GitHub when using the GitHub API or the command line." Scope: this plugin reads the user's own GitHub activity and repository metadata using a Personal Access Token the user has issued and can revoke at any time; the token is the only thing presented to GitHub, and GitHub sees the user (not Shenas) as the requester.
