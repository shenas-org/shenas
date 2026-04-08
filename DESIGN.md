# shenas design system

## 1. Visual theme

shenas is a calm, paper-toned interface for personal data work. The default
look is warm cream paper with sage-green accents -- restrained, readable, and
explicitly *not* enterprise-flat or neon-cyberpunk. The visual goal is "well-set
table": generous whitespace, soft borders, minimal chrome, and just enough color
to guide the eye without distracting from the data.

There are two surfaces with the same vocabulary but different render paths:

- **The shenas app** (Lit web components served from the Python server): styles
  via CSS custom properties exposed by an active *theme plugin*. Two themes
  ship: `default` (warm cream) and `dark` (deep navy). Components consume the
  variables, themes provide them.
- **The shenas.net website** (Astro static site): inlines the same warm-cream
  palette as plain CSS variables in the `Base.astro` and `Dashboard.astro`
  layouts. Same colors, same vibe, no plugin system.

Both surfaces use **system fonts only** (`Arial, Helvetica, sans-serif`) for
sans-serif and `JetBrains Mono` / `Fira Code` as the monospace fallback. There
is no custom display font.

**Key characteristics:**

- Warm cream background (`#faf8f5`) with oat-toned borders (`#d8d4cc`)
- Sage green primary (`#728f67`) -- the only saturated accent
- Muted, monochromatic supporting palette -- no swatch system
- System font stack -- no custom display typeface
- Modest border radius: 4px inputs, 8px small cards, 12px feature cards
- Simple shadows -- single soft layer, no multi-layer/inset tricks
- Theme plugin pattern: components reference `var(--shenas-*)`, themes set them
- Two ships-with themes (`default`, `dark`); third-party themes plug in via
  `shenas.theme` entry point

## 2. Color palette

The same names appear in two CSS variable schemes that need to stay in sync:

- App components (Lit, in `app/vendor/src/shenas-frontends/`) read
  `--shenas-*` variables
- Website (Astro, in `server/shenas.net/`) reads `--color-*` variables

Both schemes are populated by the same hex values below.

### Default theme (warm cream)

| Role | App var | Website var | Hex |
|---|---|---|---|
| Page background | `--shenas-bg` | `--color-bg` | `#faf8f5` |
| Elevated background | `--shenas-bg-secondary` | `--color-bg-elevated` | `#f3f0eb` |
| Card background | -- | `--color-bg-card` | `#fff` |
| Hover surface | `--shenas-bg-hover` | `--color-surface` | `#edeae4` |
| Selected row | `--shenas-bg-selected` | -- | `#e6efe3` |
| Body text | `--shenas-text` | `--color-text` | `#2c2c28` |
| Secondary text | `--shenas-text-secondary` | `--color-warm` | `#5a5850` |
| Muted text | `--shenas-text-muted` | `--color-text-muted` | `#8a8780` |
| Faint text | `--shenas-text-faint` | -- | `#b0ada6` |
| Border | `--shenas-border` | `--color-border` | `#d8d4cc` |
| Light border | `--shenas-border-light` | -- | `#e8e4dc` |
| Input border | `--shenas-border-input` | -- | `#ccc8c0` |
| Primary accent (sage) | `--shenas-primary` | `--color-accent` | `#728f67` |
| Accent dark | -- | `--color-accent-light` | `#628261` |
| Accent glow | -- | `--color-accent-glow` | `rgba(114, 143, 103, 0.12)` |
| Success | `--shenas-success` | `--color-green` | `#628261` |
| Success bg | `--shenas-success-bg` | -- | `#e6efe3` |
| Error / danger | `--shenas-error` / `--shenas-danger` | -- | `#a0522d` |
| Error bg | `--shenas-error-bg` / `--shenas-danger-bg` | -- | `#fdf0e8` |
| Danger border | `--shenas-danger-border` | -- | `#dbc4b0` |

### Data-flow node colors

The pipeline overview component renders sources, datasets, and dashboards as
graph nodes with distinct hues. Sage by default, then olive, then warm gold.

| Node kind | App var | Hex |
|---|---|---|
| Source / pipe | `--shenas-node-pipe` | `#728f67` |
| Dataset / schema | `--shenas-node-schema` | `#8faa60` |
| Dashboard / component | `--shenas-node-component` | `#c4a35a` |

### Dark theme

Same variable names, deep navy palette. Lives in `plugins/themes/dark/`.

| Role | Hex |
|---|---|
| Page background | `#1a1a2e` |
| Elevated background | `#16213e` |
| Hover surface | `#1f2b47` |
| Selected row | `#1a2744` |
| Body text | `#e0e0e0` |
| Secondary text | `#a0a0b0` |
| Muted text | `#707080` |
| Faint text | `#505060` |
| Border | `#2a2a3e` |
| Light border | `#222238` |
| Input border | `#3a3a50` |
| Primary accent (steel blue) | `#5b9bd5` |
| Success | `#66bb6a` |
| Error | `#ef5350` |
| Source node | `#5b9bd5` |
| Dataset node | `#66bb6a` |
| Dashboard node | `#ffa726` |

The dark theme deliberately substitutes the sage primary for steel blue and
the warm gold for amber, since sage on navy reads muddy.

## 3. Typography

### Font families

```css
--font-sans: Arial, Helvetica, sans-serif;
--font-mono: "JetBrains Mono", "Fira Code", monospace;
```

Components in `shared-styles.ts` declare `system-ui, -apple-system, sans-serif`
as their default. There is **no custom display font**, no web font loading, no
OpenType stylistic sets. The interface intentionally uses whatever the OS
provides so it feels native everywhere.

### Hierarchy (current usage)

| Role | Font | Size | Weight | Notes |
|---|---|---|---|---|
| Page H1 | sans | 2rem (32px) | 600 | Used in dashboard, devices headers |
| Section H2 | sans | 1.5rem (24px) | 600 | Cards, settings sections |
| Card H3 | sans | 1.05-1.2rem (17-19px) | 600 | Card titles |
| Body | sans | 1rem (16px) | 400 | Default body text |
| Body small | sans | 0.9rem (14px) | 400 | Tables, descriptions |
| UI label | sans | 0.85rem (14px) | 500 | Buttons, form labels |
| Caption | sans | 0.8rem (13px) | 400 | Meta info, helper text |
| Code / monospace | mono | 0.85-0.9rem | 400 | Inline code, IDs, paths |

### Principles

- **No display weights above 600** -- regular and semibold cover everything.
  There is no use of 700/800/900 anywhere in the codebase.
- **No letter-spacing tricks** -- default tracking everywhere except a few
  uppercase labels (which use natural sentence-case, not aggressive spacing).
- **Generous line-height** -- 1.5 for body, 1.2-1.4 for headings.
- **Monospace for stable identifiers** -- table column names, plugin names,
  config keys, SQL.

## 4. Components

### Buttons

Defined in `app/vendor/src/shenas-frontends/shared-styles.ts` `buttonStyles`:

```css
button {
  padding: 0.3rem 0.7rem;
  border: 1px solid var(--shenas-border-input, #ddd);
  border-radius: 4px;
  background: var(--shenas-bg, #fff);
  color: var(--shenas-text, #222);
  cursor: pointer;
  font-size: 0.8rem;
}
button:hover {
  background: var(--shenas-bg-hover, #f5f5f5);
}
button.danger {
  color: var(--shenas-danger, #c00);
  border-color: var(--shenas-danger-border, #e8c0c0);
}
button.danger:hover {
  background: var(--shenas-danger-bg, #fef0f0);
}
```

- Single button style: thin border, 4px radius, soft hover background
- One variant: `.danger` (warm rust color, not red-red)
- No primary CTA color outside of the website's `Sign in` button which uses
  the sage accent
- No rotating, hard-shadow, or otherwise playful interactions

### Cards & containers

- Background: `--shenas-bg` (cream) or `var(--color-bg-card)` (white) on the website
- Border: `1px solid var(--shenas-border)` (`#d8d4cc`)
- Radius: **4-12px** -- 4px on inputs, 8px on small cards, 12px on feature cards
- Shadow: usually none. When present, a single soft layer:
  `0 1px 3px rgba(0, 0, 0, 0.04)` or similar.
- No nested radius, no inset highlights, no dashed borders

### Forms (`formStyles`)

- Stacked field/label pattern
- Label: 0.8rem secondary text color
- Input: 0.4rem 0.6rem padding, 4px radius, 0.85rem font, full width
- Action row: right-aligned, 0.5rem gap

### Tables (`tableStyles`)

- Borderless except a 1px bottom rule on each row
- Header text in `--shenas-text-secondary`, weight 500
- 0.9rem font, compact 0.4rem 0.6rem cell padding
- Used by the data-list component, dashboards, settings page

### Tabs (`tabStyles`)

- Bottom border underline (2px), no rounded backgrounds
- Selected tab: sage primary underline + bold text
- 0.9rem font, 0.5rem 1rem padding

### Messages (`messageStyles`)

- 4px radius pill, 0.85rem text
- `.message.success` -- soft green bg + dark green text
- `.message.error` -- soft pink bg + warm rust text

### Sidebar navigation

The shenas.net dashboard layout (`Dashboard.astro`) and the shenas app shell
(`app-shell.ts`) both use a left sidebar with:

- 240px fixed width on desktop
- Brand row at top, separated by a thin border
- Nav items: 0.6rem padding, 8px radius, hover swap to surface color
- Active item: accent-glow background + sage text + 600 weight
- Logout/destructive items: hover to warm rust color

## 5. Layout

### Spacing

8px base unit. The most common values: 0.25rem, 0.5rem, 0.75rem, 1rem, 1.5rem,
2rem, 3rem. No fractional pixel values, no rigid scale enforcement.

### Containers

- App shell uses a sidebar + main grid (`grid-template-columns: 240px 1fr`)
- Website pages use `max-width: 1100px` centered with 2rem padding
- Dashboards/widgets use the parent's grid -- they never set their own
  max-width

### Breakpoints

| Name | Width | Behavior |
|---|---|---|
| Mobile | <720px | Sidebar collapses to top bar; cards stack |
| Tablet | 720-1024px | 2-column card grids |
| Desktop | 1024px+ | Full sidebar + multi-column grids |

The exact pixel value isn't sacred -- 720px is the most common because it's
where the dashboard's sidebar+main grid gets uncomfortable.

### Border radius scale

- 4px: inputs, buttons, badges
- 6-8px: nav items, small cards, message pills
- 10-12px: feature cards, dashboard cards
- Larger values are not used. There are no pill (>16px radius) buttons.

## 6. Shadows & elevation

Three levels, all minimal:

| Level | Treatment | Use |
|---|---|---|
| Flat | No shadow | Page background, sidebars, sticky nav |
| Resting | `0 1px 3px rgba(0, 0, 0, 0.04)` | Cards on the website, modal panels |
| Hover | Background swap to `--shenas-bg-hover` | Interactive surfaces |

Focus rings use the browser default. There is no `outline: 2px solid blue`
override.

## 7. Do's and don'ts

### Do

- Use the `--shenas-*` variables in app components and `--color-*` on the website
- Match the warm cream + sage default for any new component
- Keep border radius modest (4-12px)
- Use system fonts -- no web font imports
- Stick to two weights (400 + 600) and reach for 500 only on UI labels
- Make new themes by creating a `plugins/themes/<name>/` package that defines
  the `--shenas-*` variables for `body`
- Test new components in both the default and dark themes

### Don't

- Don't introduce a new color outside the existing palette without adding it
  to both `--shenas-*` and `--color-*` schemes
- Don't load custom fonts -- system fonts only
- Don't use rotating/playful hover animations
- Don't use multi-layer or inset shadows
- Don't use pill (>16px) border radius -- it doesn't match the visual language
- Don't hardcode hex values in component styles -- always use a CSS variable
  with a sane fallback
- Don't add a third theme to `plugins/themes/` without also documenting its
  variable values here

## 8. Responsive behavior

### Sidebar collapse

The dashboard layout collapses the sidebar to a top bar at <720px:

```css
@media (max-width: 720px) {
  .dashboard-layout {
    grid-template-columns: 1fr;
  }
  .dashboard-sidebar {
    border-right: none;
    border-bottom: 1px solid var(--color-border);
  }
}
```

### Card grids

`grid-template-columns: repeat(auto-fill, minmax(280px, 1fr))` is the default
pattern. It naturally collapses from 3-column to 2-column to 1-column without
explicit breakpoints.

### Touch targets

Buttons and nav items use ~0.6rem vertical padding which gives ~36-40px touch
height. No special mobile-only sizes -- the default is already touch-friendly.

## 9. Theme plugin model

Themes are first-class plugins. The Theme ABC (`plugins/themes/core/`) defines:

- `name` -- machine name used in entry points
- `display_name` -- human label
- `static_dir / css` -- the CSS file containing the variable definitions

A theme plugin's CSS file simply sets the `--shenas-*` variables on `body`.
The active theme is selected via the plugin database, exclusive (only one
active at a time, enforced by `_SelectOneMixin`).

To add a third theme:

1. Create `plugins/themes/<name>/` with `pyproject.toml`, `__init__.py`
   (subclassing `Theme`), and `static/<name>.css`
2. Define all `--shenas-*` variables in the CSS file's `body` rule
3. Register the entry point in `pyproject.toml`:
   `[project.entry-points."shenas.themes"]`
4. Document the palette in this file's section 2

The `dark` theme is the reference implementation for non-default palettes.

## 10. Quick reference

### Default palette (cheat sheet)

```
bg                #faf8f5 (warm cream)
bg-secondary      #f3f0eb (slightly darker cream)
text              #2c2c28 (near-black)
text-muted        #8a8780 (warm gray)
border            #d8d4cc (oat)
primary           #728f67 (sage)
success           #628261 (deep sage)
danger            #a0522d (warm rust)
```

### When in doubt

- Background: `#faf8f5`
- Text: `#2c2c28`
- Border: `#d8d4cc`
- Accent: `#728f67`
- Use a CSS variable, not a hex literal
- Don't add a custom font
- Don't add a new shadow style
