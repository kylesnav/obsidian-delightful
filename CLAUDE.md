# obsidian-delightful

Obsidian community theme — neo-brutalist with OKLCH tokens, 18 CSS source modules.

## Source of Truth

Token values come from [delightful-design-system](https://github.com/kylesnav/delightful-design-system). The token definitions live in `src/00-tokens.css` as CSS custom properties.

## Build

```sh
node build.js
```

Concatenates 18 `src/` modules (12 core + 6 plugin) into a single `theme.css`. **Never edit `theme.css` directly** — edit the source modules and rebuild.

Watch mode: `node build.js --watch`

## Deploy to Obsidian

```sh
bash scripts/deploy.sh
```

Copies `theme.css` + `manifest.json` to the vault's `.obsidian/themes/Delightful/` directory.

## Visual Testing

Uses Chrome DevTools Protocol to connect to Obsidian (Electron app):

```sh
# Launch Obsidian with CDP
open -a Obsidian --args --remote-debugging-port=8315

# Run visual audit
python3 scripts/visual-audit.py
```

## Key Files

- `src/00-tokens.css` — Full 3-tier token architecture (primitives → semantic → component)
- `src/01-obsidian-vars.css` — ~250 Obsidian CSS variable → DS token bridge mappings
- `src/05-components.css` — Buttons, forms, toggles, search containers
- `src/plugins/` — Plugin-specific overrides (Dataview, Kanban, Calendar, Tasks, Excalidraw)
- `manifest.json` — Obsidian theme manifest (name, version, minAppVersion)
- `build.js` — Build script (concatenator with headers)

## Conventions

- OKLCH colors only in token definitions. Hex never appears in source.
- Neo-brutalist aesthetic: 2px borders, solid zero-blur shadows, warm cream neutrals.
- Plugin overrides go in `src/plugins/<plugin-name>.css`, not in core modules.
- `body` prefix on selectors for specificity over Obsidian's `app.css` where needed.
