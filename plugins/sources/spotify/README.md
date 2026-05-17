# shenas-source-spotify

Syncs your Spotify listening data — recently played tracks, top artists and
tracks, saved tracks, followed artists, playlists, and account profile — into
your local Shenas store.

## Basis

This plugin is part of Shenas's source-plugin cohort. It ships under the
[Shenas inclusion policy for source plugins](https://shenas.org/policy/sources)
because: **Spotify Web API access is gated on a user-registered OAuth
application, and this plugin only reads the authenticated user's own data via
that user-owned OAuth identity** — Shenas does not ship a named-application
identity for Spotify and does not redistribute Spotify data. Each user
creates their own app at the Spotify Developer Dashboard, agrees to
[Spotify's Developer Terms of Service](https://developer.spotify.com/terms),
and pastes the resulting `client_id` into Shenas; the OAuth2 PKCE flow runs
provider-to-user with the plugin acting as a local third-party client.

Terms reference: <https://developer.spotify.com/terms> (interim — canonical
terms link lands via SHE-489 v1).

Scope: this plugin reads the authenticated user's own Spotify account data on
the user's behalf; no data is sent off-device by the plugin.

## Onboarding

See [`ONBOARDING.md`](ONBOARDING.md) for the step-by-step walkthrough on
registering your own Spotify Developer Dashboard app and supplying its
`client_id` to Shenas.

## OAuth client_id model

This plugin ships in **user-registered `client_id` mode** per the
[SHE-490](https://shenas.org/issues/SHE-490) board decision. Shenas does not
maintain a named OAuth application identity for Spotify. If a partnership
relationship with Spotify is ever established the plugin may migrate to a
Shenas-registered model; that change would land as a separate version.

## Configuration

| Field         | Source       | Required | Notes                                              |
| ------------- | ------------ | -------- | -------------------------------------------------- |
| `client_id`   | Auth tab     | yes      | From your Spotify Developer Dashboard app         |
| `client_id`   | env var      | optional | `SPOTIFY_CLIENT_ID` fallback for headless installs |
| OAuth tokens  | (auto)       | n/a      | Captured via OAuth redirect; stored locally       |

## Attribution

Spotify Web API data accessed via this plugin remains subject to Spotify's
Developer Terms; the user-side app you register is the relying party, not
Shenas.
