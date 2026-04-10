# Discourse theming

How to create and deploy a Discourse community forum theme that matches the
shenas design system.

## Approach: Git Repository Sync

The recommended way to manage a Discourse theme is via a **Git repository**
synced to the Discourse instance. This works on all Discourse SaaS tiers
(including the cheapest) and avoids any API tier restrictions.

### Workflow

1. Maintain the theme in a GitHub repository with the standard Discourse theme
   file structure (see below).
2. In the Discourse admin panel, go to **Customize > Themes > Install** and
   paste the GitHub repository URL.
3. To update: push a commit to the default branch, then pull the update from
   the Discourse admin panel. (Discourse detects remote changes and offers a
   one-click pull.)

### Alternative approaches (tier-dependent)

| Method | Availability | Notes |
|---|---|---|
| Git Repository Sync | All tiers | Best practice. No API needed. |
| Admin API (`/admin/themes`) | Business+ | Full CRUD; can automate deploys via CI. |
| Theme CLI (`discourse_theme`) | Business+ | Local dev server with live reload. Requires API key. |

For most setups, Git sync is sufficient. The API and CLI routes are useful if
you want CI-driven deploys or a local preview server.

## Discourse theme file structure

```
discourse-shenas-theme/
  about.json
  common/
    common.scss
  settings.yml         (optional: user-facing toggle for light/dark)
  locales/
    en.yml
```

### about.json

```json
{
  "name": "shenas",
  "about_url": "https://github.com/afuncke/shenas",
  "license_url": "https://github.com/afuncke/shenas/blob/main/LICENSE",
  "component": false,
  "color_schemes": {
    "shenas (light)": {
      "primary":           "2c2c28",
      "secondary":         "faf8f5",
      "tertiary":          "728f67",
      "quaternary":        "8faa60",
      "header_background": "f3f0eb",
      "header_primary":    "2c2c28",
      "highlight":         "e6efe3",
      "danger":            "a0522d",
      "success":           "628261",
      "love":              "a0522d"
    },
    "shenas (dark)": {
      "primary":           "e0e0e0",
      "secondary":         "1a1a2e",
      "tertiary":          "5b9bd5",
      "quaternary":        "66bb6a",
      "header_background": "16213e",
      "header_primary":    "e0e0e0",
      "highlight":         "1a2744",
      "danger":            "ef5350",
      "success":           "66bb6a",
      "love":              "ef5350"
    }
  }
}
```

### Color mapping

Discourse defines a small set of semantic color slots. Here is how they map to
the shenas design system variables:

| Discourse slot | Role | shenas light | shenas dark |
|---|---|---|---|
| `primary` | Body text | `--shenas-text` `#2c2c28` | `#e0e0e0` |
| `secondary` | Page background | `--shenas-bg` `#faf8f5` | `#1a1a2e` |
| `tertiary` | Links, accent | `--shenas-primary` `#728f67` | `#5b9bd5` |
| `quaternary` | Nav highlights | `--shenas-node-schema` `#8faa60` | `#66bb6a` |
| `header_background` | Header bar | `--shenas-bg-secondary` `#f3f0eb` | `#16213e` |
| `header_primary` | Header text | `--shenas-text` `#2c2c28` | `#e0e0e0` |
| `highlight` | Selection bg | `--shenas-bg-selected` `#e6efe3` | `#1a2744` |
| `danger` | Errors, flags | `--shenas-danger` `#a0522d` | `#ef5350` |
| `success` | Positive actions | `--shenas-success` `#628261` | `#66bb6a` |
| `love` | Like hearts | `--shenas-danger` `#a0522d` | `#ef5350` |

Discourse auto-generates a full range of tints/shades from these base slots
(e.g. `primary-low`, `primary-medium`, `secondary-high`). The warm cream +
sage palette produces good intermediate values without further tweaking.

### common/common.scss

Custom SCSS that layers on top of the color scheme. This handles the details
that color slots alone cannot express: fonts, border radius, shadows, and
component-level overrides.

```scss
// -- Fonts ---------------------------------------------------------------
// Match shenas: system fonts only, no custom font loading.
html {
  font-family: system-ui, -apple-system, Arial, Helvetica, sans-serif;
}

.d-header,
.topic-list,
.category-list {
  font-family: system-ui, -apple-system, Arial, Helvetica, sans-serif;
}

code, pre {
  font-family: "JetBrains Mono", "Fira Code", monospace;
}

// -- Border radius -------------------------------------------------------
// shenas uses modest radii: 4px inputs, 8px cards, 12px feature panels.
// Discourse default is 3-4px which is close enough. Nudge a few spots:
.topic-list .topic-list-item,
.category-list-item {
  border-radius: 8px;
}

.btn {
  border-radius: 4px;
}

// -- Borders & shadows ---------------------------------------------------
// Oat-toned borders instead of Discourse's default gray.
.topic-list .topic-list-item {
  border-bottom: 1px solid var(--primary-low);
}

// Single soft shadow, matching shenas elevation level "resting".
.d-header {
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

// -- Typography ----------------------------------------------------------
// Two weights only: 400 (regular) and 600 (semibold). No bold (700+).
h1, h2, h3, h4, h5, h6 {
  font-weight: 600;
}

.topic-list .topic-list-item .link-top-line a.title {
  font-weight: 600;
}

// -- Buttons -------------------------------------------------------------
// Tone down primary button to match shenas's restrained button style.
.btn-primary {
  background: var(--tertiary);
  border: 1px solid var(--tertiary);

  &:hover {
    filter: brightness(0.95);
  }
}

// -- Category badges -----------------------------------------------------
// Softer pill style consistent with shenas message pills.
.badge-category__wrapper .badge-category {
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 500;
}

// -- Sidebar navigation --------------------------------------------------
// Match the 240px sidebar pattern from the shenas app shell.
.sidebar-wrapper {
  .sidebar-section-link {
    border-radius: 8px;
    padding: 0.4rem 0.6rem;

    &:hover {
      background: var(--primary-very-low);
    }
  }
}
```

### settings.yml (optional)

If the Discourse instance supports only a single color scheme at a time, you
can expose a user-facing toggle:

```yaml
dark_mode:
  type: bool
  default: false
  description: "Enable the shenas dark color scheme"
```

Then wrap the dark-specific overrides in `common.scss` with:

```scss
@if $dark_mode {
  // dark-only overrides (if any beyond the color scheme)
}
```

In practice, Discourse's built-in dark mode selector (`/u/<user>/preferences/interface`)
handles this automatically when both color schemes are registered in `about.json`,
so `settings.yml` is usually unnecessary.

## Deploying

### First install

1. Push the theme repository to GitHub (public or private; private requires a
   deploy key configured in Discourse).
2. In Discourse admin: **Customize > Themes > Install > From a Git Repository**.
3. Paste the repo URL. Select the branch (default: `main`).
4. Set the "shenas (light)" color scheme as default, and add "shenas (dark)"
   as the user-selectable dark variant.
5. Activate the theme.

### Updating

Push to the repository, then in Discourse admin click the **Update** button on
the theme page. Discourse fetches the latest commit and applies it immediately.

### Automated deploys (Business+ tier)

With API access, you can trigger a theme update from CI:

```bash
curl -X PUT "https://forum.example.com/admin/themes/<theme_id>" \
  -H "Api-Key: $DISCOURSE_API_KEY" \
  -H "Api-Username: system" \
  -d "theme[remote_update]=true"
```

This can run as a GitHub Actions step on push to `main`.

## Design principles

When extending the Discourse theme, follow the same conventions as the shenas
app (documented in `DESIGN.md`):

- **System fonts only** -- no web font imports.
- **Two weights**: 400 (regular) and 600 (semibold). No bold/black weights.
- **Modest border radius**: 4px inputs/buttons, 8px cards, 12px feature panels.
  No pill shapes (>16px).
- **Minimal shadows**: single soft layer (`0 1px 3px rgba(0,0,0,0.04)`) or none.
- **Warm palette**: cream backgrounds, oat borders, sage accents. No neon, no
  enterprise-flat gray.
- **CSS variables over hex literals**: use Discourse's `var(--tertiary)` etc.
  instead of hardcoding hex values.
- **No playful animations**: no rotating, bouncing, or parallax effects.
