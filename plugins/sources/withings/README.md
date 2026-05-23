# Withings source plugin

Syncs body measurements (weight, body fat, blood pressure, SpO₂), sleep summaries, daily activity, and device info from your Withings account via OAuth 2.0.

## Setup

### 1. Register a Withings developer application

1. Go to [developer.withings.com](https://developer.withings.com/) and sign in.
2. Create a new application. Select **"Web"** as the application type.
3. Under **Redirect URIs**, add the redirect URI shown in the Shenas auth screen (typically `http://localhost:<port>/oauth/callback/withings`).
4. Note the **Client ID** and **Client Secret** shown after creation.

### 2. Configure credentials

Set the following environment variables before starting Shenas:

```bash
export SHENAS_WITHINGS_CLIENT_ID=<your-client-id>
export SHENAS_WITHINGS_CLIENT_SECRET=<your-client-secret>
```

For a persistent setup, add them to your shell profile or your Shenas configuration file.

### 3. Authenticate

Open Shenas, go to **Sources → Withings**, and click **Authenticate**. You will be redirected to Withings to grant access.

## Data synced

| Table | Contents |
|---|---|
| `measurements` | Weight, BMI, body fat %, muscle mass, bone mass, hydration, blood pressure, SpO₂, temperature |
| `sleep` | Sleep duration, phases (light/deep/REM), score, heart rate during sleep |
| `activity` | Steps, distance, calories, active duration |
| `devices` | Device model, battery level, last sync time |

## Permissions required

The plugin requests the following Withings API scopes:

- `user.info` — account profile
- `user.metrics` — measurements and body composition
- `user.activity` — daily activity data
- `user.sleepevents` — sleep tracking data
