---
name: brand-builder
description: Turn a brand palette into a full brand reference page, a one-page design system with light and dark mode. The page covers the brand story and motifs, personality and naming rules, the colors with a measured contrast table, chart colors and a heatmap ramp, a signature design move with do and don't examples, typography, layout and spacing, live components, accessibility notes and copyable CSS tokens. Use whenever the user wants a brand guide, brand book, style guide, design reference, design system page or brand identity built from a palette or brand idea, e.g. "turn this palette into a brand guide", "make a design reference like this one for my studio", "build the brand page for Story and Structure", or "expand the palette board into a full brand system". If no palette exists yet, it builds one first with brand-palette.
---

# Brand Builder

Turn a checked palette into a brand reference page: one scrolling page with a sticky section nav and an Auto/Light/Dark switch. Its sections are Brand, Color, Charts, Signature, Typography, Layout, Components, Accessibility and Tokens, plus an optional Where it lives section. Every specimen on the page is drawn with the brand's own tokens, so the page is the proof that the system works.

**The words are yours and the numbers are the script's.** You write the brand spec: the story, motifs, personality, fonts, the signature move and the sample copy. `scripts/build_brand.py` measures everything else, reusing brand-palette's checker: the card and divider surfaces, an error red, the chart steps, the heatmap ramp, the contrast table, the stats and the accessibility notes. Never type a contrast ratio or ΔE into the spec by hand.

## Step 1: Get a palette

The page builds on a brand-palette JSON file (brand colors with base, strong, soft and surface steps, and four neutrals, in both modes).

- **The user has one** (a palette JSON, or a palette made earlier in the conversation): use that file.
- **The user points at a published palette board:** read it with the Artifact tool. The palette is the `palette-data` JSON inside it. Save its `name`, `description`, `seeds`, `brand`, `neutrals` and `notes` fields as a palette JSON. Turn `neutrals` from a list back into an object keyed by `job`.
- **There is no palette yet:** follow the brand-palette skill first (`../brand-palette/SKILL.md`) and use the palette it drafts. Stop at its Step 4, once the checker prints `OK`, because this page replaces its board.

Run `python3 ../brand-palette/scripts/check_palette.py <palette.json>` once. If it prints "Must fix" items, fix them as brand-palette describes before going on. The builder refuses palettes that fail a required pair.

## Step 2: Write the brand spec

Read `references/brand-spec.md` for every field. Save the spec next to the palette as `<brand>-brand.json`, with `"palette"` set to the palette's path relative to the spec. `../../examples/story-structure-brand.json` is a complete example.

Decide these yourself from the brief, without asking, and say what you assumed:

- **Roles.** Choose which brand color is `primary` (buttons, links, focus: usually the deepest seed), `accent` (one warm or light moment), `data` (the first chart series and info states) and `highlight` (tags and a third series). Components use the roles, so this choice shapes the whole page.
- **The concept.** One sentence on where the look comes from (a reference image, the name, the method) and one job per brand color. Those jobs become the motifs.
- **The signature move.** One rule that makes the brand recognisable and that people could overdo, like "one glow per view" or "one story thread per view". Write a do example and a don't example in HTML using the page's classes and your own `css`. The don't example should break a real rule the checker reports, such as light text on a light accent.
- **Fonts.** Two or three Google Fonts that fit the personality: a display face if the brand has a voice, a UI face and a mono face. Give each one a role, a sample and a use line.
- **Art.** Draw the hero as an inline SVG (viewBox `0 0 400 320`), plus a 64×40 glyph for each motif. Color them only with `style="fill:var(--token)"` or `style="stroke:var(--token)"`, using brand, chart and neutral tokens, so the art follows the theme switch. Use `--<key>-text` for strokes that must read on the card in both modes, and give any `<pattern>` or gradient a unique id.
- **Sample copy.** Write button labels, KPIs, tabs, notices and table rows in the brand's real domain, never lorem ipsum.
- **Mode and status.** If the user says to prioritize one mode, set `default_theme` and judge trade-offs, such as which chart series to keep, by that mode's measurements. If the palette already has a red or coral, set `error` to it instead of adding a derived red.

Don't invent facts the user didn't give, like a domain, a repo or a client name. Leave out `files` unless the brand has a real codebase whose files hold the tokens.

## Step 3: Check and build

Run from this skill's folder:

```bash
python3 scripts/build_brand.py <brand.json> --check              # measurements only
python3 scripts/build_brand.py <brand.json> --out <brand>-brand.html
```

`--check` prints the derived neutrals, the error red, the chart steps and ramp for both modes, the contrast table and the Passes and Watch notes that go on the page.

- If a chart step pair is flagged as too close under color blindness, try reordering `charts.series` or dropping the weakest series before accepting the caveat.
- If your `color_rules` or motif text contradicts a measurement (you wrote "white text passes" but the table says otherwise), fix the text.
- Don't edit the generated HTML by hand. Change the spec or the palette and build again.

Save the page in the user's working directory unless they named another place. If that directory is a skill or plugin repo, save it in the scratchpad instead.

## Step 4: Publish

If the Artifact tool is available, publish the HTML as a private artifact. Use the icon `palette` and a one-sentence description naming the brand and its concept. When updating a page published earlier, republish to the same URL.

## Step 5: Report back

Keep the summary short:
- the link or file path
- one line on the concept and the roles ("Forest is structure and primary actions, blush is the one story thread, ink is the data")
- the fonts, and the signature move in a few words
- the counts (required pairs passing AA and AAA) and the two or three Watch items that matter most
- your assumptions (roles, fonts, any copy you invented for the samples)

For changes ("make the display font bolder", "swap the accent", "add our repo's files"), edit the spec and run Steps 3 and 4 again. For a color change, edit the palette, run brand-palette's checker, then rebuild.
