# Palette structure, checks and file format

## What a palette contains

**Brand row, 1–6 colors** (usually one per seed, 2–4 total). Each one has a short `usage` label, 2–5 words like "Primary buttons, links, headers", plus four steps in each mode:

| Step key | Light-mode name | Dark-mode name | Job |
|---|---|---|---|
| `base` | — | — | The brand color itself. Buttons and brand moments. |
| `strong` | Dark | Bright | About 10–20% darker (light mode) or 5–15% lighter (dark mode) than base, same hue. Hover and pressed states. It's also the version that carries button text when base can't. |
| `soft` | Light | Muted | Chart fills, tags and borders. |
| `surface` | Surface | Surface | Tinted card and section backgrounds. Very light in light mode, very dark in dark mode. |

**Neutral row, always 4.** Each has a label shown under its tile. The defaults are below; change them only if the brand uses its greys differently.

| Key | Default label | Light mode | Dark mode |
|---|---|---|---|
| `text` | Headings, body text | darkest grey | lightest grey |
| `muted` | Secondary text, captions, icons | dark mid grey | light mid grey |
| `line` | Borders, dividers, disabled states, placeholders | light mid grey | dark mid grey |
| `page` | Page and card backgrounds, input fills | near-white | near-black |

## What the script checks

**Required.** The board isn't built until all of these reach WCAG AA (4.5:1), in both modes:
- body text and secondary text on the page background
- body text and secondary text on each brand surface
- body text on each soft step (tag text)
- each brand color has some way to carry button text: the main text color (white in light mode, the darkest neutral in dark mode) on base, the other text color on base, or the main text color on the strong step

**Reported, not required.** These turn into the board's notes:
- white or dark text on each base and strong step ("Rose: white text is only about 3.3:1…")
- border grey as placeholder text (4.5:1) and as input outlines (3:1)
- soft steps as chart fills against the page (3:1)
- base and strong steps as colored text on the page
- color blindness: every pair of brand bases and every pair of soft steps, simulated for protanopia, deuteranopia and tritanopia (Machado 2009). Pairs closer than CIEDE2000 10 are flagged.
- halation: dark-mode body text above 15:1 can blur for readers with astigmatism

Ratios are never rounded up: 4.49:1 fails. The notes use "about" with the ratio rounded down (about 8:1, about 3.4:1).

## Making the colors

- **Seeds:** use each seed's exact hex as a `base`. Don't adjust a seed to make white text pass. The notes will point to the strong step or the darkest neutral instead, which is how real brand systems handle light brand colors such as gold.
- **Strong step:** same hue, about 10–20 OKLCH lightness points darker than base in light mode. If the notes say white text still fails on it, darken it further. The script's `Try #XXXXXX` gives the smallest change that passes.
- **Soft and surface:** the soft step is a mid-light tint (light mode) or a mid-dark shade (dark mode). The surface step is barely tinted, close to the page color.
- **Neutrals:** tint them slightly toward the main brand hue, so they look chosen rather than default.
- **Dark mode:** design it, don't invert it. Bases get lighter and a little less saturated, so dark text works on them. The page is a tinted near-black (#16191E to #1E2228), not #000. Surfaces are dark tints of each hue.
- **Too many similar hues:** if two brand colors are flagged as alike for everyone, move them apart in lightness, not just hue.

## File format

```json
{
  "name": "Harbor & Field",
  "description": "Navy and teal for trust, rose and gold for warmth, on cool blue-grey neutrals.",
  "seeds": ["#2C517A", "#B77D88"],
  "brand": [
    { "key": "navy", "name": "Navy", "usage": "Primary buttons, links, headers",
      "light": { "base": "#2C517A", "strong": "#1E3752", "soft": "#729CCA", "surface": "#E9EFF7" },
      "dark":  { "base": "#7FA6D4", "strong": "#A8C4E6", "soft": "#34506F", "surface": "#1C2533" } }
  ],
  "neutrals": {
    "text":  { "light": "#2B2F34", "dark": "#E3E7EC" },
    "muted": { "light": "#5D666F", "dark": "#A3ACB6" },
    "line":  { "light": "#9EA8B3", "dark": "#4D5560" },
    "page":  { "light": "#ECF0F4", "dark": "#1A1E23" }
  },
  "notes": [
    "Shown on both boards.",
    { "mode": "light", "text": "Shown on the light board only." }
  ]
}
```

- `key`: lowercase letters, digits and hyphens. It becomes the CSS token name (`--navy`, `--navy-strong`, `--navy-soft`, `--navy-surface`).
- Neutral `label` is optional and defaults to the labels above.
- `seeds` and `notes` are optional. Use `notes` for your own closing remarks, like the last paragraph on the board ("The darkest neutral also covers…"). Don't repeat anything the script already says.

See `../../examples/sample-palette.json` (from the plugin folder: `examples/sample-palette.json`) for a full palette.
