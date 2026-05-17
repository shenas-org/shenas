> Lives in `shenas-net/shenas` at `plugins/paperclip/spend-telemetry/`. Migrated 2026-05-17 per [SHE-616](/SHE/issues/SHE-616).

# paperclip-plugin-spend-telemetry

A [Paperclip](https://paperclip.ing) plugin that surfaces per-issue and per-run spend telemetry
for [shenas.ai](https://shenas.ai).

## Data handlers

| Handler | Description |
|---------|-------------|
| `spend-by-issue` | 30-day aggregation of `cost_events` grouped by `issue_id`, joined to `issues.origin_kind` / `issues.work_mode` |
| `spend-detail` | Per-event breakdown for a specific issue (up to 200 most-recent rows) |

## Surfaces (planned)

| Surface | Issue |
|---------|-------|
| Issue detail → **Spend** tab | SHE-603 |
| Dashboard widget | SHE-604 |

## Development

```bash
pnpm install
pnpm dev        # watch build (worker + manifest + ui)
pnpm dev:ui     # local dev server at http://localhost:4177
pnpm test
pnpm typecheck
pnpm build
```

## Install into Paperclip

Clone this repo, then install the plugin from its local path:

```bash
PLUGIN_PATH="$(pwd)/paperclip-plugin-spend-telemetry"

curl -X POST http://127.0.0.1:3100/api/plugins/install \
  -H "Content-Type: application/json" \
  -d "{\"packageName\":\"${PLUGIN_PATH}\",\"isLocalPath\":true}"
```

## License

MIT
