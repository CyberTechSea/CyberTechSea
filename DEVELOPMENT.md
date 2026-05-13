# How this profile repository works

This is the **special repository** `CyberTechSea/CyberTechSea` whose `README.md`
becomes the public profile page on GitHub. The page you actually see at
<https://github.com/CyberTechSea> is the rendered output of `README.md` in this
repo.

## TL;DR — how to update the profile

| Task                                | What to edit                                     |
|-------------------------------------|--------------------------------------------------|
| Change the origin story             | `content/01-origin-story.md`                     |
| Reword Cyber / Tech / Sea pillars   | `content/02-the-archive.md`                      |
| Add or remove a project card        | `content/03-projects.md`                         |
| Rotate the "From the Vault" piece   | `content/04-tech-heritage.md` (marked block)     |
| Replace the dispersal map           | `assets/easter-egg/_placeholder_dispersal.png`   |
| Add a new publication               | `content/06-publications.md`                     |
| Change the default banner / theme   | `scripts/header.md` (change the `<img src>` line)|

**Never edit `README.md` directly.** It is regenerated.

## The build pipeline

```
content/*.md  ─┐
               ├─►  scripts/build_readme.py  ─►  README.md
scripts/header.md ─┤
                   │     ▲
       live data ──┘     │
   (YouTube RSS,         │
    Zenodo API by ORCID, │
    GitHub stats card)   │
                         │
       .github/workflows/build-readme.yml
       (runs daily at 04:17 UTC + on every push)
```

The build script (`scripts/build_readme.py`) only uses the Python
**standard library** — no `pip install` needed. The dynamic block between the
`<!-- BEGIN_DYNAMIC_BLOCK -->` / `<!-- END_DYNAMIC_BLOCK -->` markers is the
only part the script overwrites; everything else is your editorial content.

## Themes (three banners)

Three SVG banners coexist in `assets/header/`. Only one is displayed at a time
(the one referenced in `scripts/header.md`). The other two are exposed as
**clickable preview badges**, so a visitor can open them full-size.

GitHub's README renderer does not run JavaScript, so a true in-page toggle is
not possible. To make a different theme the default, change one line in
`scripts/header.md`:

```html
<img src="assets/header/banner-deepsea.svg" ... />
                 └──────────────────────┘
              replace with retro / museum
```

## Live data: what fails gracefully

- **YouTube RSS** — public, no API key required. If it's ever down, the README
  still builds, with a polite "data unavailable" notice instead of the cards.
- **Zenodo API** — filtered by your ORCID (`0000-0002-7975-2947`). Same fallback.
- **github-readme-stats** — third-party SVG service (anuraghazra/github-readme-stats).
  Cached by Vercel; very reliable. If it ever disappears, swap the URLs.

## PETSCII / Amiga easter egg

```
your dispersal PNG  ─►  scripts/make_petscii.py  ─►  text mosaic + SVG mosaic
```

Requires Pillow (`pip install pillow`). Run locally — the result is committed
as static assets.

## Photos to add

The README references these placeholders (they hide automatically if missing):

- `assets/photos/stakar-1994.jpg`     ← the Stakar 486 minitower
- `assets/photos/vault-feature.jpg`   ← rotating "From the Vault" piece
- `assets/photos/commodore-pet.jpg`
- `assets/photos/amiga-1200.jpg`
- `assets/photos/ibm-pc.jpg`

JPG is preferred over PNG for photo size; aim for ~800–1200 px on the long
edge. They will be rendered at 160–420 px in the README.

## Licence

MIT — see `LICENSE`.
