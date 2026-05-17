> Lives in `shenas-net/shenas` at `plugins/paperclip/agent-token-monitor/`. Migrated 2026-05-17 per [SHE-616](/SHE/issues/SHE-616).

# plugin-agent-token-monitor

A [Paperclip](https://paperclip.ing) plugin that surfaces per-agent monthly token totals and a per-run cost view.

## Surfaces

| Surface | Description |
|---------|-------------|
| Dashboard widget | Monthly token summary for all agents in the company |
| Agent detail → **Tokens** tab | Monthly input / cached / output tokens + run counts for the current agent |
| Agent detail → **Runs** tab | Sortable run list (timestamp, status, model, tokens, cost) for the current agent |
| Dedicated page | Full sortable runs list with agent filter |
| Sidebar | Link to the dedicated runs page |

## Development

```bash
pnpm install
pnpm dev        # watch build (worker + manifest + ui)
pnpm dev:ui     # local dev server with hot-reload at http://localhost:4177
pnpm test
pnpm typecheck
pnpm build
```

## Install Into Paperclip

Clone this repo, then install the plugin from its local path:

```bash
# From the directory containing this repo
PLUGIN_PATH="$(pwd)/plugin-agent-token-monitor"

curl -X POST http://127.0.0.1:3100/api/plugins/install \
  -H "Content-Type: application/json" \
  -d "{\"packageName\":\"${PLUGIN_PATH}\",\"isLocalPath\":true}"
```

Or install via the Paperclip CLI if available:

```bash
paperclipai plugin install "$(pwd)/plugin-agent-token-monitor"
```

After installing, open any agent's detail page and look for the **Tokens** and **Runs** tabs.

## License

MIT
