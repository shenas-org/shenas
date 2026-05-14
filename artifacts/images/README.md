# Brand assets — source of truth

Canonical SVG sources for the shenas mark and full logo. **Edit here first, then `make logos-generate` to propagate everywhere downstream.**

## Files

| File | Purpose | Specs |
|---|---|---|
| `shenas-mark.svg` | Master primary mark (transparent) | viewBox 100×80, single stroke weight 3, sage `#728f67`, full ECG trace + bump |
| `shenas.svg` | Full logo for square contexts (app icons, hero, social) | viewBox 100×100, mark centred in cream `#faf8f5` rounded-square (rx=18) |
| `shenas-lockup-horizontal.svg` | Mark + "shenas" side-by-side, for nav | viewBox 260×80, wordmark Arial 600 at 48u, sage `#728f67`, letter-spacing -0.015em |
| `shenas-lockup-stacked.svg` | Mark above "shenas", for splash / app icon | viewBox 100×122, wordmark Arial 600 at 32u, sage `#728f67`, letter-spacing -0.015em |

The PNGs in this folder (`shenas-192.png`, `shenas-512.png`, `shenas-mark-192.png`, `shenas-mark.png`, `shenas.png`) are **generated** from the SVGs above via `make logos-generate`. Don't edit the PNGs directly; rerun the target after editing the SVGs.

The lockup wordmark is set in system Arial/Helvetica rather than a custom typeface — the SVG renders consistently when served as `<img>` without external font CSS. If we later adopt a custom brand face, replace the `font-family` attribute in both lockup files.

## Construction notes

From the Claude Design study (`logo-mark.html`, round 6, 2026-05-11):

- **One grid, two baselines.** ECG and x-axis share `y=60`. Y-axis sits at `x=50` (the optical centre). Gap between ECG end (`x=44`) and y-axis = 6 units, equal to the left margin (also 6 units).
- **Clear space.** 6 units on all four sides — no other element enters that rectangle.
- **Three dots ("shin").** Triangle at the upper right of the quadrant, `(68,34) (80,34) (74,24)` radius 2.6 — references the Hebrew/Persian-Arabic root for *shin* (the first letter of *shenas*). Single semantic unit, not decoration.
- **Same vocabulary across sizes.** Master uses stroke 3; at ≤24px contexts the mark can be redrawn with stroke 8 and the small ECG bump dropped for legibility. (The `<24px` favicon variant isn't a separate file today; if pixel-perfect 16px matters, add `shenas-mark-favicon.svg` here with the simplified geometry.)

## Where the mark gets used

`make logos-generate` propagates from these sources to:

- `server/shenas.ai/public/favicon.svg` ← copy of `shenas-mark.svg`
- `server/shenas.ai/public/logo.svg` ← copy of `shenas.svg`
- `server/shenas.ai/public/logo.png` ← rendered 512px from `shenas.svg`
- `server/shenas.ai/public/logo-192.png` ← rendered 192px from `shenas.svg`
- `server/shenas.ai/public/logo-horizontal.svg` ← copy of `shenas-lockup-horizontal.svg`
- `server/shenas.ai/public/logo-stacked.svg` ← copy of `shenas-lockup-stacked.svg`
- `server/shenas.org/public/favicon.svg` ← copy of `shenas-mark.svg`
- `server/shenas.org/public/logo-horizontal.svg` ← copy of `shenas-org-lockup-horizontal.svg`
- `server/shenas.org/public/logo-stacked.svg` ← copy of `shenas-org-lockup-stacked.svg`
- `server/shenas.net/public/favicon.svg` ← copy of `shenas-mark.svg`
- `server/shenas.net/public/logo.svg` ← copy of `shenas.svg`
- `server/shenas.net/public/shenas-lockup.svg` ← copy of `shenas-lockup-horizontal.svg`
- `server/shenas.net/public/shenas-org-lockup.svg` ← copy of `shenas-org-lockup-horizontal.svg`
- `app/desktop/src-tauri/icons/{32,128,256,512}x{32,128,256,512}.png` + `icon.png` + `icon.ico` ← from `shenas-mark.svg`
- `app/mobile/src-tauri/icons/{32,128,256,512}x{32,128,256,512}.png` + `icon.png` ← from `shenas-mark.svg`

Pages reference via `<img src="/favicon.svg">` or `<img src="/logo.svg">` (where `/logo.svg` is the new-design master mark, kept hand-synced from `shenas-mark.svg`). **No inline SVG of the brand mark anywhere** — always go through the file. This keeps "one source of truth" honest.

## What changed (2026-05-11)

Replaced the earlier mark (cream rounded-square + sage line + lowercase "s" composition) with the design-study mark from Claude Design `logo-mark.html`: coordinate-system + ECG + shin-triangle, all on a 100×80 unit grid. Operator-approved after a six-round design iteration.

The earlier mark was a starter from before the design study. The new one is what the design study landed on. Do not use the earlier mark.

## Don't put here

- Photographs, illustrations, marketing imagery — those go in `server/<site>/public/` per-site.
- Diagrams (entity graph, architecture, etc.) — those are content, not brand. They stay inline in their pages.
- Per-platform icon variants (Apple touch icon at exact sizes, Microsoft tile, etc.). When we need those, add them here with explicit per-size names like `shenas-apple-touch-180.png`.
