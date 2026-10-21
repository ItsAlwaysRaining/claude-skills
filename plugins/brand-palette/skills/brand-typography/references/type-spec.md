# Type spec format

A type spec is a JSON file that holds 1–3 typography options for one brand. You write the fonts, the scale and the words. `check_type.py` fetches the fonts, measures them and writes every result. Never type a contrast value, an x-height or a pass/fail into the spec.

## Top level

| Field | Required | What it is |
|---|---|---|
| `brand` | yes | The brand name. It's also the wordmark unless `wordmark` is set. |
| `options` | yes | 1–3 options (3 for a specimen page). See "Options" below. |
| `brief` | | One or two sentences on the brand, shown under the page title. |
| `palette` | | Path to a brand-palette JSON, relative to this spec. Leave it out to check against greyscale. |
| `primary` | | The palette `key` used for buttons and the reversed wordmark. Defaults to the first brand color. |
| `fill` | | The primary step buttons sit on in each mode, e.g. `{"dark": "strong"}`. Defaults to `base`. Use it when no text passes on a mid-tone base, as brand-builder's `-fill` token does. |
| `languages` | | Character sets the fonts must cover: `latin` (the default), `latin-ext`, `vietnamese`, `cyrillic`, `cyrillic-ext`, `greek`. |
| `assumptions` | | Strings listing what you assumed, shown on the page. Always include them when the brief was thin. |
| `wordmark` | | The name as it should be set in the wordmark specimen, if it differs from `brand`. |
| `title`, `page_title` | | The page's h1 (defaults to "Type for <brand>") and its browser tab title (defaults to "<brand> Type"; keep it to 2–4 words). |
| `samples` | | Real copy from the brand's domain for the specimens. See "Samples" below. |

## Options

```json
{
  "id": "a", "name": "Soft serif + Plex", "pick": true,
  "character": "Warm headlines, engineered body.",
  "why": "Fraunces carries the story; Plex Sans and Mono share proportions, so prose and data sit together.",
  "fonts": {
    "display": {"family": "Fraunces", "weights": [400, 600], "role": "Headlines", "use": "Headlines and pull quotes. Never below 20px."},
    "ui":      {"family": "IBM Plex Sans", "weights": [400, 600], "role": "Interface and body"},
    "mono":    {"family": "IBM Plex Mono", "weights": [400], "role": "Code and figures"}
  },
  "body": {"measure": 66, "paragraph_spacing": "2.4em", "letter_spacing": "0", "word_spacing": "0", "align": "left"},
  "scale": [
    {"label": "Display", "font": "display", "size": "3rem", "weight": 600, "line": 1.1, "use": "heading"}
  ]
}
```

- `id` is a short letter. Exactly one option has `"pick": true`.
- `character` is a few words on how the option feels. `why` is one or two sentences on why it fits this brand.
- `fonts`: `ui` is required. Leave out `display` for a one-family option, and leave out `mono` when nothing needs it. `weights` lists the weights to load beyond those the scale uses. Add `"given": true` to a font the user chose, in every option that uses it, so the "noticeably different" check compares the other roles instead.
- `body` describes the reading text. `measure` is the line length in characters (the `max-width` in ch). `paragraph_spacing`, `letter_spacing` and `word_spacing` are CSS lengths in em.

### Font sources

| `source` | Use for | Extra fields |
|---|---|---|
| `google` (the default) | Anything on Google Fonts | none |
| `fontshare` | Fontshare's free fonts (ITF Free Font License) | none |
| `file` | Other free fonts the user has a file for (League of Moveable Type, Velvetyne, Collletttivo…) | `file`: a .ttf or .otf path relative to the spec; `licence`: `OFL`, `APACHE2`, `UFL` or `ITF_FFL`; `category`: `sans`, `serif`, `mono`, `display` or `script` |

The licence check fails for any `file` font whose licence isn't one of those, so you can't recommend it until the user confirms its terms.

### Scale rows

| Field | What it is |
|---|---|
| `label` | The row name ("Body", "Caption"). |
| `font` | `display`, `ui` (the default) or `mono`. |
| `size` | A CSS size, in rem (`1rem` is 16px). px works but fails WCAG 1.4.4's "watch". |
| `weight`, `line` | The weight (100–900) and the unitless line height. |
| `use` | What the row is for: `heading`, `body`, `ui` (buttons, labels, nav), `caption` or `data` (table figures, KPIs). The checks rely on this: `body` rows are held to the body-text rules, and `data` rows decide which font needs tabular figures. Give at least one row `"use": "body"`. |
| `color` | `text` (the default), `muted`, `primary`, or `on-primary` for text on the primary fill (button labels). |
| `caps`, `italic`, `tracking`, `tabular` | Uppercase, italic, letter-spacing (CSS) and tabular figures. |
| `sample` | Text for this row in the type scale. |

Write 5–8 rows that cover what the brand actually sets: one or two headings, body, a UI row with `"color": "on-primary"` for buttons, a muted caption, and a data row when the brand shows numbers.

## Samples

Defaults are generic, so replace them with copy from the brand's world.

```json
"samples": {
  "headline": "Research that ships",
  "paragraph": ["First body paragraph…", "Second body paragraph…"],
  "nav": ["Work", "Method", "Writing", "Contact"],
  "buttons": ["Book a call", "See the work"],
  "input": {"label": "Work email", "placeholder": "you@company.com", "help": "We reply within two working days."},
  "doc": {"title": "Discovery report", "subtitle": "What we heard, and what it means", "quote": "…", "caption": "Figure 1 · …"},
  "card": {"name": "…", "role": "…", "contact": "…"},
  "table": {"caption": "Example data · …", "columns": ["Month", "Rows", "Runs", "Change"], "rows": [["Jan", "1,204", "88", "+4.2%"]]},
  "chart": {"title": "…", "bars": [["Jan", 1204], ["Feb", 1118]]}
}
```

Don't invent facts the user didn't give, such as a client name or a phone number. Use clearly fictional details, and say on the page that they're examples.
