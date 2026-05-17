# Paperclip plugins

In-mono home for shenas-owned Paperclip-platform plugins.

These target the Paperclip control plane (the agent harness used to coordinate shenas's internal agents), not the Shenas data app. They build with `esbuild`, test with `vitest`, and depend on `@paperclipai/plugin-sdk` from npm.

Plugins here are operator-internal — they are excluded from the OSS mirror via `.copybara/copy.bara.sky` (`plugins/**/paperclip*/**`). If we ever want to expose paperclip plugins externally, we do it via a Copybara mirror workflow (see ADR `docs/adr/0001-paperclip-plugins-in-monorepo.md`).

## Layout

- `<plugin-short-name>/` — one directory per plugin
  - `src/`, `tests/`, `package.json`, `tsconfig.json`, `vitest.config.ts`, `esbuild.config.mjs`, `moon.yml`, `LICENSE`, `README.md`

## Authoring a new plugin

1. Read [`docs/adr/0001-paperclip-plugins-in-monorepo.md`](../../docs/adr/0001-paperclip-plugins-in-monorepo.md) for the consolidation context.
2. Scaffold under `plugins/paperclip/<name>/` following the existing plugins' structure.
3. Add a `moon.yml` matching the template in either existing plugin.
4. The plugin is picked up automatically by `.moon/workspace.yml` (`plugins/paperclip/*`).
5. CI runs `moon run :test` and `moon run :lint`; the inherited typescript task patterns from `.moon/tasks/node.yml` cover lint and type-check.

The upstream Paperclip plugin SDK lives at `paperclipai/paperclip` `packages/plugins/sdk` — it is consumed from npm here.
