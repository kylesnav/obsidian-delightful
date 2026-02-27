# Delightful

A warm, neo-brutalist theme for [Obsidian](https://obsidian.md) based on the Delightful Design System.

![Delightful Theme](screenshot.png)

## Features

- **Warm color palette** — OKLCH-based neutrals with a subtle warm tint (hue 70), never cold gray
- **Neo-brutalist aesthetic** — Solid offset shadows, 2px borders, and generous radii on modals, menus, buttons, callouts, code blocks, and tables
- **Inter + JetBrains Mono** — Variable font weights with tight letter-spacing on headings and Inter's alternate character variants (`cv02`, `cv03`, `cv04`, `cv11`)
- **Full light & dark mode** — Carefully tuned for both, with warm dark backgrounds and adjusted accent brightness
- **6 accent colors** — Pink (default), Danger, Gold, Cyan, Green, and Purple, switchable via Style Settings
- **Button micro-interactions** — Lift on hover, flatten on press
- **Pill-shaped tags** — Rounded with accent-tinted backgrounds
- **Fluid heading scale** — 2.488em down to 1em with decreasing variable-font weights (800 to 600)
- **Per-type callout colors** — 12 callout types with semantically matched colors (cyan for info, green for success, red for danger, gold for tips, purple for examples, etc.)
- **16 custom checkboxes** — Alternative task types: cancelled, important, question, forwarded, scheduled, star, info, idea, pro, con, bookmark, location, fire, up, down, win
- **Full graph view theming** — Color-coded nodes for tags (gold), attachments (cyan), unresolved (dimmed), with accent-colored focus and highlight states
- **Canvas styling** — Neo-brutalist canvas nodes with 6 color-coded node types mapped to Delightful families
- **Styled panels** — Properties, search results, backlinks, outline, settings modal, editor gutter, and breadcrumbs all receive neo-brutalist treatment
- **Plugin compatibility** — Dataview tables, Kanban boards, Tasks plugin priority colors, Calendar widget
- **Mobile optimization** — Larger touch targets, reduced shadows, phone heading scale, tablet line width

## Style Settings

Install the [Style Settings](https://github.com/mgmeyers/obsidian-style-settings) plugin for additional customization:

| Setting | Options |
|---|---|
| **Accent Color** | Pink (default), Danger, Gold, Cyan, Green, Purple |
| **Shadow Style** | Neo-brutalist (default), Subtle, None |
| **Border Weight** | 2px (default), 1px |
| **Heading Scale** | Normal (default), Compact, Large |
| **Alternative Checkboxes** | On (default), Off |
| **Colorful Headings** | Off (default), On |

## Installation

### From Obsidian Community Themes
1. Open **Settings** > **Appearance**
2. Click **Manage** next to Themes
3. Search for "Delightful"
4. Click **Install and use**

### Manual Installation
1. Download `manifest.json` and `theme.css` from this repository
2. Create a folder called `Delightful` inside your vault's `.obsidian/themes/` directory
3. Place both files in that folder
4. Open **Settings** > **Appearance** and select **Delightful**

## Design System

This theme is a translation of the [Delightful Design System](https://github.com/kylesnav/delightful-design-system) — a comprehensive token system built on OKLCH color science with a neo-brutalist visual language.

### Color Architecture

| Layer | Purpose |
|---|---|
| **Primitives** | Raw OKLCH values — neutrals (0-950) and six accent families |
| **Semantic tokens** | Background, text, border, and accent colors for light/dark modes |
| **Component tokens** | Typography scale, spacing grid, radii, motion, and easing |

### Typography

- **Interface & text**: Inter (variable, 100-900)
- **Code**: JetBrains Mono (variable, 100-800)
- **Headings**: Tight tracking (-0.03em for h1-h2, -0.02em for h3-h4), heavy weights, compressed line-height

## License

MIT
