---
name: brand-builder
description: Turn a brand idea or palette into a full brand reference page, a one-page design system with light and dark mode. It first lets the user pick the fonts from three checked typography options, then the colors from three palette directions, and only then builds the page. The page covers the brand story and motifs, personality and naming rules, the colors with a measured contrast table, chart colors and a heatmap ramp, a signature design move with do and don't examples, typography, layout and spacing, live components, accessibility notes and copyable CSS tokens. Use whenever the user wants a brand guide, brand book, style guide, design reference, design system page or brand identity, e.g. "turn this palette into a brand guide", "make a design reference like this one for my studio", "build the brand page for Story and Structure", or "expand the palette board into a full brand system".
---

# Brand Builder

Turn a brand into a reference page: one scrolling page with a sticky section nav and an Auto/Light/Dark switch. Its sections are Brand, Color, Charts, Signature, Typography, Layout, Components, Accessibility and Tokens, plus an optional Where it lives section. Every specimen on the page is drawn with the brand's own tokens, so the page is the proof that the system works.

**The user picks the fonts and the colors; you build the rest.** Fonts come first, then colors, and each is a checkpoint: show the options, stop, and wait for the user's choice before going on. Don't build the page until both are chosen.

**The words are yours and the numbers are the scripts'.** You write the brand spec: the story, motifs, personality, the signature move and the sample copy. brand-typography measures the type, brand-palette's checker measures the colors, and `scripts/build_brand.py` measures everything else: the card and divider surfaces, an error red, the chart steps, the heatmap ramp, the contrast table, the stats and the accessibility notes. Never type a contrast ratio or ΔE into a spec by hand.

## Step 1: The user picks the fonts

- **The user already named every font they want** ("use Fraunces and Plex"): that's their pick, so skip the choice. Still check them with brand-typography (Step 3 below does this).
- **Otherwise:** follow the brand-typography skill (`../brand-typography/SKILL.md`) Steps 1–5. It shortlists three free pairings, checks them and publishes the specimen page. If the user already has a palette, give it to brand-typography now; if not, the checks run in greyscale, and that's fine at this stage.

**Checkpoint.** Give the specimen link and a one-line summary of each option, mark the recommendation, and ask which one the user wants. Use the AskUserQuestion tool when it's available, with the recommended option first and a short description of each; otherwise ask in chat. **Stop here and wait for the answer.** If the user asks for changes ("a warmer serif", "mix A's headings with B's body"), revise the type spec, rebuild the specimen, and ask again.

## Step 2: The user picks the colors

The page builds on a brand-palette JSON file (brand colors with base, strong, soft and surface steps, and four neutrals, in both modes).

- **The user has a palette** (a palette JSON, or a palette made earlier in the conversation): that's their pick. Use it and skip the choice.
- **The user points at a published palette board:** read it with the Artifact tool. The palette is the `palette-data` JSON inside it. Save its `name`, `description`, `seeds`, `brand`, `neutrals` and `notes` fields as a palette JSON, turning `neutrals` from a list back into an object keyed by `job`. That's their pick too.
- **There is no palette yet:** follow the brand-palette skill (`../brand-palette/SKILL.md`) Steps 1–4 for **all three** directions instead of one. Draft each one with `directions.py --pick 1`, `--pick 2` and `--pick 3` (same `--rng`) into separate files, finish each draft (usage labels, names, description), and run the checker on each until it prints `OK`. Then put them side by side, in the fonts the user just picked:

  ```bash
  python3 ../brand-palette/scripts/compare_palettes.py a.json b.json c.json --pick <N> \
    --labels "<short name>" "<short name>" "<short name>" --brand "<Brand>" \
    --display-font "<chosen display font>" --body-font "<chosen body font>" --html <brand>-palettes.html
  ```

  `--display-font` and `--body-font` load from Google Fonts. Leave out any font that isn't on Google Fonts (the page falls back to system fonts). Publish the page as a private artifact (icon `palette`).

**Checkpoint.** Give the comparison link, one line per direction (its colors, the wildcard, the checker's counts), mark the recommendation, and ask which one the user wants, the same way as in Step 1. **Stop here and wait for the answer.** If they want changes ("warmer", "swap the wildcard"), edit or redraw that direction, rerun the checker, rebuild the comparison and ask again.

Run `python3 ../brand-palette/scripts/check_palette.py <palette.json>` on the chosen palette once more. If it prints "Must fix" items, fix them as brand-palette describes. The builder refuses palettes that fail a required pair.

## Step 3: Check the chosen fonts against the chosen colors

The fonts were checked before the colors existed (or against greyscale), so check them again with the real palette:

1. In the type spec, set `"palette"` to the chosen palette's path and `"primary"` to the key you'll use as the `primary` role (Step 4). Keep only the chosen option, or leave all three, since only the chosen one matters.
2. Run `python3 ../brand-typography/scripts/check_type.py <type.json>` and fix any new failure in that option's scale, as brand-typography's Step 4 describes. Don't change the fonts: the user picked them. If a dark-mode button fails on a mid-tone base, set `"fill": {"dark": "strong"}`.
3. Export the option as the brand spec's `type` block:

   ```bash
   python3 ../brand-typography/scripts/check_type.py <type.json> --brand-type <id> --fonts-dir <dir next to the brand spec>/fonts
   ```

If the fixes changed the scale noticeably (a larger caption, a heavier button), tell the user in the report.

## Step 4: Write the brand spec

Read `references/brand-spec.md` for every field. Save the spec next to the palette as `<brand>-brand.json`, with `"palette"` set to the palette's path relative to the spec and `"type"` set to the block from Step 3. `../../examples/story-structure-brand.json` is a complete example.

Decide these yourself from the brief, without asking, and say what you assumed:

- **Roles.** Choose which brand color is `primary` (buttons, links, focus: usually the deepest seed), `accent` (one warm or light moment), `data` (the first chart series and info states) and `highlight` (tags and a third series). Components use the roles, so this choice shapes the whole page.
- **The concept.** One sentence on where the look comes from (a reference image, the name, the method) and one job per brand color. Those jobs become the motifs.
- **The signature move.** One rule that makes the brand recognisable and that people could overdo, like "one glow per view" or "one story thread per view". Write a do example and a don't example in HTML using the page's classes and your own `css`. The don't example should break a real rule the checker reports, such as light text on a light accent.
- **Art.** Draw the hero as an inline SVG (viewBox `0 0 400 320`), plus a 64×40 glyph for each motif. Color them only with `style="fill:var(--token)"` or `style="stroke:var(--token)"`, using brand, chart and neutral tokens, so the art follows the theme switch. Use `--<key>-text` for strokes that must read on the card in both modes, and give any `<pattern>` or gradient a unique id.
- **Sample copy.** Write button labels, KPIs, tabs, notices and table rows in the brand's real domain, never lorem ipsum.
- **Mode and status.** If the user says to prioritize one mode, set `default_theme` and judge trade-offs, such as which chart series to keep, by that mode's measurements. If the palette already has a red or coral, set `error` to it instead of adding a derived red.

Don't invent facts the user didn't give, like a domain, a repo or a client name. Leave out `files` unless the brand has a real codebase whose files hold the tokens.

## Step 5: Check and build

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

## Step 6: Publish

If the Artifact tool is available, publish the HTML as a private artifact. Use the icon `palette` and a one-sentence description naming the brand and its concept. When updating a page published earlier, republish to the same URL.

## Step 7: Report back

Keep the summary short:
- the link or file path
- one line on the concept and the roles ("Forest is structure and primary actions, blush is the one story thread, ink is the data")
- the chosen fonts and palette, with any scale changes Step 3 made, and the signature move in a few words
- the counts (required pairs passing AA and AAA) and the two or three Watch items that matter most
- your assumptions (roles, any copy you invented for the samples)

For changes ("make the display font bolder", "swap the accent", "add our repo's files"), edit the spec and run Steps 5 and 6 again. For a different font, go back to the type spec and run Step 3 again. For a color change, edit the palette, run brand-palette's checker, then run Step 3 and rebuild.
