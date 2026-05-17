# Spotify — onboarding

The Spotify source plugin reads your own listening data using an OAuth2 PKCE
app that **you** register on the Spotify Developer Dashboard. Shenas does not
ship a named application identity for Spotify; the OAuth flow is between you
and Spotify, mediated by the plugin running locally.

This walkthrough takes ~5 minutes.

## 1. Open the Spotify Developer Dashboard

Go to <https://developer.spotify.com/dashboard> and sign in with the Spotify
account whose data you want to sync. The dashboard is a free product surface
on top of your normal Spotify account — no separate developer signup is
required.

Accept the Developer Terms of Service if prompted. The current TOS lives at
<https://developer.spotify.com/terms>.

## 2. Create an app

Click **Create app**. Fill in:

- **App name** — anything memorable to you, e.g. `shenas-sync`. Spotify
  surfaces this to you on the consent screen during authorize, so use a name
  you'll recognise.
- **App description** — short free-text, e.g. `Personal listening history sync
  via Shenas (self-hosted)`.
- **Redirect URI** — paste **exactly**:

  ```
  http://127.0.0.1:7280/api/auth/source/spotify/callback
  ```

  Spotify is strict about exact-match redirect URIs (including trailing
  slashes and host vs. `localhost`). Use `127.0.0.1`, not `localhost`.

  > If your Shenas server runs on a non-default port or behind a reverse
  > proxy, substitute the host:port your Shenas frontend reaches — but the
  > path must stay `/api/auth/source/spotify/callback`.

- **Which API/SDKs are you planning to use?** — tick **Web API**. (You can
  leave the others unticked.)
- Tick the box agreeing to Spotify's Developer Terms.

Click **Save**. You'll land on the new app's settings page.

## 3. Copy your `client_id`

On the app's settings page, copy the value labelled **Client ID** (a 32-char
hex string). You do **not** need the client secret — the plugin uses PKCE,
which does not require an embedded secret.

## 4. Paste the `client_id` into Shenas

In Shenas:

1. Go to **Sources → Spotify**.
2. Open the **Auth** tab.
3. Paste your `client_id` into the **Spotify app client_id** field.
4. Click **Authenticate**. Your browser opens Spotify's consent page; approve
   the requested scopes and you'll be redirected back to Shenas. Tokens are
   stored locally alongside the `client_id` so refresh works without you
   needing to re-paste it.

If you prefer not to type the `client_id` into the UI, you can also set it as
the environment variable `SPOTIFY_CLIENT_ID` before starting Shenas; the
plugin will fall back to that value if no `client_id` is supplied in the Auth
tab.

## 5. Scopes the plugin requests

Spotify will show you a consent screen listing these scopes:

- `user-read-recently-played` — recently played tracks (primary table)
- `user-top-read` — top artists / tracks over time windows
- `user-library-read` — saved tracks
- `user-follow-read` — followed artists
- `playlist-read-private` — your own playlists
- `user-read-email` — account email (used as a stable account identifier)

If you don't need a particular table you can revoke the corresponding scope
from your Spotify account at <https://www.spotify.com/account/apps/>, but the
plugin assumes the full set above.

## 6. Development Mode vs. Production

Newly-created Spotify apps start in **Development Mode**. In Development
Mode:

- Only Spotify users you explicitly add to the app's **User Management** page
  can authorise it (up to 25 users). For a self-hosted personal-use install
  this is normally fine — add yourself (and any other family/household
  accounts you sync) and you're done.
- The app is not subject to Spotify's app-review process.

If you ever want to share your Shenas install with more than 25 Spotify
accounts, you'll need to apply for **Production Mode** via the dashboard's
**Extended Quota Mode** flow. That review process is run by you with Spotify;
it is not part of Shenas.

## 7. Per-provider gotchas

- **Brand display rules.** Spotify's Developer Policy requires that your app
  doesn't impersonate Spotify or imply official endorsement. Because your app
  is your own personal-use app under your own developer identity, the bar
  here is low — but if you screenshot the consent screen or share your app
  publicly, follow Spotify's [Design Guidelines](https://developer.spotify.com/documentation/design)
  for use of the Spotify logo and marks.
- **Sensitive-scope warnings.** None of the scopes used by this plugin are
  flagged as "sensitive" in Spotify's policy as of 2026 — the consent screen
  will list them but won't show an extra warning panel.
- **Token rotation.** Refresh tokens are long-lived. If you revoke the app
  from <https://www.spotify.com/account/apps/> you'll need to click
  Authenticate again in Shenas.

## 8. Troubleshooting

- **"Spotify client_id is required"** — you clicked Authenticate without
  pasting a `client_id`. See step 4.
- **"INVALID_CLIENT: Invalid redirect URI"** — your dashboard app's redirect
  URI doesn't match the one Shenas uses. Re-check step 2; the URI is
  case-sensitive and must include the full path.
- **"INVALID_CLIENT: Invalid client"** — the `client_id` you pasted doesn't
  match an active app on the dashboard. Re-copy it from the app's settings
  page; make sure there's no leading/trailing whitespace.

## Reference

- Spotify Developer Dashboard: <https://developer.spotify.com/dashboard>
- Spotify Developer Terms of Service: <https://developer.spotify.com/terms>
- Shenas plugin source: [`shenas_sources/spotify/source.py`](shenas_sources/spotify/source.py)
- Architectural rationale (Option A — user-registered client_id): [SHE-490](https://shenas.org/issues/SHE-490)
