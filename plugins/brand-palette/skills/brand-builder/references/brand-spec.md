# Brand spec format

A brand spec is a JSON file with the words and art for the page. The palette supplies the colors, and `build_brand.py` measures everything else. Only `palette` and `roles` are required. Every other field has a fallback, but a page without the brand fields reads like a template.

Fields marked *HTML* are inserted as HTML, so you can use `<b>`, `<code>` and `&amp;` in them. All other strings are plain text.

## Top level

| Field | Required | What it is |
|---|---|---|
| `palette` | yes | Path to the brand-palette JSON, relative to this spec. |
| `roles` | yes | `{"primary", "accent", "data", "highlight"}`, each a palette `key`. `highlight` defaults to the first unused key. See "Roles" below. |
| `name` | | The brand name, used as the h1. Defaults to the palette's name. |
| `title_accent` | | A word or phrase in `name` to color with the primary text color. |
| `title` | | The browser tab title. Defaults to "<name> Brand". Keep it to 2–4 words. |
| `kicker` | | A small mono line above the h1 ("UI/UX design · data engineering · brand reference"). |
| `lede` | | 2–3 sentences: what the brand looks like and why. *HTML* |
| `hero_svg`, `hero_label` | | Inline SVG for the hero (viewBox `0 0 400 320`) and its alt text. See "Art" below. |
| `stat` | | One extra hero stat as `["1", "glow per view"]`, usually the signature move. |
| `default_theme` | | `"auto"` (the default, follows the system), `"light"` or `"dark"`: the mode the page opens in. Use `"light"` when the user says to prioritize light mode. A viewer's own choice on the switch still wins. |
| `error` | | A palette key that doubles as the error color, instead of the derived red. Use it when the palette already has a red or coral, so two reds don't compete. That color is left out of the default chart series. |
| `brand` | | `{"title", "lede"}` for section 1. The lede is *HTML*. |
| `motifs` | | Up to 4 `{"name", "color", "role", "text", "glyph_svg"}`. `color` is a palette key and colors the role line. `role` follows an arrow ("→ the data"). `text` is *HTML*. |
| `personality` | | `{"caption", "is": [...], "is_not": [...]}`: 3–6 words each. `is_not` is shown struck through. |
| `names` | | Rows of `["In headlines", "<b>Story and Structure</b>, …"]` covering how to write the name. The second item is *HTML*. |
| `color_rules` | | `{key: "one or two sentences"}` shown under each brand color card. *HTML*. Keep them consistent with the measurements. |
| `charts` | | See "Charts" below. |
| `signature` | | See "Signature" below. |
| `type` | | See "Type" below. |
| `layout` | | See "Layout" below. |
| `samples` | | Copy for the component specimens. See "Samples" below. |
| `components_title`, `components_lede` | | Override section 7's heading and lede. The lede is *HTML*. |
| `always` | | The "Always" list in the accessibility section, as *HTML* strings. |
| `files`, `files_title`, `files_lede`, `change_process` | | Optional "Where it lives" section. `files` is a list of `{"path", "text"}`, where `text` is *HTML*. `change_process` is a paragraph of *HTML*. Leave these out when the brand has no codebase. |
| `footer` | | Footer text. Defaults to the brand and palette name. |

## Roles

Components refer to roles, never to brand keys. The tokens include `--primary`, `--primary-strong`, `--primary-soft`, `--primary-surface`, `--primary-fill`, `--primary-text` and `--on-primary`, and the same set for `accent`, `data` and `highlight`.

- `-fill` is the background for anything that carries text: the base, or the strong step when no text color passes on the base. `--on-<role>` is the text color for it.
- `-text` is the step that works as colored text on the page, cards and its own surface. When neither step does, it falls back to the body text color.

| Role | Used for |
|---|---|
| `primary` | Primary buttons, links, focus rings, selected tabs and rows, the up delta. Pick a color whose base carries text in both modes. |
| `accent` | The accent button and the highlight notice: the brand's one warm or light moment. A light seed (pale pink, gold) belongs here. |
| `data` | Info notices, the progress bar and the heatmap ramp (by default). It is usually the first chart series. |
| `highlight` | Tags, and usually the third chart series. |

## Charts

```json
"charts": {
  "series": [{"key": "ink", "label": "primary measure: rows, events, runs"}, {"key": "forest", "label": "comparison"}],
  "ramp": "ink",
  "title": "…", "lede": "…",
  "bars_label": "Example data · pipeline runs per month",
  "heat_label": "Example data · events by hour",
  "rules": ["Series order is fixed: …", "…"]
}
```

- `series` sets the chart colors in order. The script gives each one its own mid-tone step (`--chart-<key>`), at least 3:1 on the page and on cards in both modes. Each series after the first gets the lightness that keeps it furthest from the others under simulated color blindness. Leave out the accent when it's too light to be a mark. By default every brand color except the accent is a series.
- `ramp` is the palette key the 10-step heatmap ramp is built from. It defaults to the `data` role.
- `rules` are *HTML* strings. Cover series order, what never becomes a series, label colors and errors.

## Signature

The brand's one recognisable move, which people could overdo.

```json
"signature": {
  "nav": "Signature",
  "title": "One story thread per view",
  "lede": "…",
  "do":   {"html": "<div class=\"ss-card\">…</div>", "caption": "…"},
  "dont": {"html": "…", "caption": "…"},
  "css": ".thread { background: var(--accent-fill); color: var(--on-accent); … }"
}
```

`css` is injected into the page and also shown as code under the examples. Put both the real rule and the classes your examples need in it. Use tokens, not hex codes, so the examples follow the theme. Write the don't caption from measured facts, using the ratios `--check` prints.

Classes you can use in the examples: `btn primary`, `btn secondary`, `btn accent`, `btn danger`, `eyebrow`, `cap`, `notice info|highlight|error`, `tag`, `delta up|down`.

## Type

```json
"type": {
  "title": "…", "lede": "…",
  "display": {"family": "Fraunces", "weights": [400, 600], "role": "Story · headlines", "sample": "Story and Structure", "chars": "Aa Bb Cc · …", "use": "Headlines and pull quotes."},
  "ui":      {"family": "IBM Plex Sans", "weights": [400, 500, 600], "role": "Interface", "sample": "…", "chars": "…", "use": "…"},
  "mono":    {"family": "IBM Plex Mono", "weights": [400, 500], "role": "Code", "sample": "…", "chars": "…", "use": "…"},
  "scale": [{"label": "Display", "spec": "h1 · Fraunces 3rem / 600", "font": "display", "size": "3rem", "weight": 600, "line": 1.1, "sample": "…"}]
}
```

- Write this block with brand-typography's `check_type.py --brand-type <option>`, not by hand, so the fonts and scale are the ones it checked.
- Fonts load from Google Fonts. Set `"google": false` for a font that isn't on Google Fonts, and add `"fallback"` to change its fallback stack. To show such a font on the page, add `"files": {"400": "fonts/general-sans-400.ttf", …}`: one font file per weight, relative to this spec or absolute. The builder inlines them. brand-typography fills this in for Fontshare and local fonts.
- Leave out `display` (or give it the same family as `ui`) for a brand with one face. The page then shows two font cards.
- `scale` rows take `font` (`display`, `ui` or `mono`), `size`, `weight`, `line`, `muted: true` for secondary text and `tabular: true` for figures. Show 6–8 rows that cover the real UI.

## Layout

```json
"layout": {
  "title": "…", "lede": "…",
  "shell": "site",
  "shell_label": "12 columns · max 1200px · 24px gutters",
  "radius": "0.5rem",
  "spacing": [4, 8, 12, 16, 24, 32, 48, 64],
  "facts": [["--radius", "0.5rem on buttons…"], ["breakpoint", "768px: …"]]
}
```

`shell` is `site` (a top bar over a 12-column grid) or `sidebar` (a sidebar beside the main column). `radius` and `spacing` become the `--radius` and `--space-N` tokens. The second item of each fact is *HTML*.

## Samples

Everything defaults to generic copy, so override it with real copy from the brand's domain.

```json
"samples": {
  "kpis": [{"label": "Rows processed", "value": "1.28M", "delta": "+18%", "up": true}],
  "tabs": ["Overview", "Research"], "segments": ["Weekly", "Monthly"],
  "buttons": {"primary": "…", "secondary": "…", "accent": "…", "danger": "…"},
  "input": {"label": "…", "placeholder": "…", "help": "…", "error": "…"},
  "notices": {"info": "…", "highlight": "…", "error": "…"},
  "rows": [["Discovery workshop", "done"], ["Data model review", "hover"], ["Prototype v2", "selected"]],
  "progress": 62,
  "tags": {"forest": "UX research"}
}
```

A row whose second item is `hover` or `selected` is drawn in that state.

## Art

- Color only with `style="fill:var(--token)"` or `style="stroke:var(--token)"`, never hex codes, so the art switches with the theme. These tokens are available: brand steps (`--forest`, `--forest-soft`…), `--<key>-text`, `--chart-<key>`, `--ramp-1` to `--ramp-10`, and the neutrals `--page`, `--surface`, `--raised`, `--divider`, `--line`, `--text-muted` and `--text`.
- The hero sits on `--surface`. Outlines that must read in both modes should use `--<key>-text` or `--text`.
- Draw the concept, not a logo: the reference image, or the method behind the name. Keep it to a few shapes.
- Give `<pattern>` and gradient ids a brand prefix so they can't collide with each other.
