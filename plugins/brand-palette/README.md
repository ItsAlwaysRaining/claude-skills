# Brand Palette

A Claude skill that builds a brand color palette that works in light and dark mode, meets WCAG 2.2 AA contrast, and says plainly where it falls short for color-blind or low-vision readers.

Ask Claude for a palette and give it any mix of:

- **A brand description:** "a calm, trustworthy fintech app"
- **Up to 4 seed hex codes:** "build it around #1F3A5F and #FF7A59"
- **An image or logo:** "pull the brand colors from this logo"

It returns a swatch board for light mode and another for dark mode:

- **Brand colors with steps.** Each brand color has three smaller steps under it: Dark (hover and pressed states, and the version that carries white text), Light (chart fills, tags, borders) and Surface (tinted card backgrounds). Each one also gets a short usage label.
- **Four neutrals with jobs.** "Headings, body text", "Secondary text, captions, icons", "Borders, dividers, disabled states, placeholders" and "Page and card backgrounds, input fills".
- **A notes column** in plain language: what each step is for, which text works on which color ("Gold: white text fails at about 2.4:1. Put your darkest neutral on it for text, or use the Dark gold (#826117, about 5.7:1) when you need white text"), which colors look alike to color-blind readers, and anything else to watch, like placeholder contrast.
- **Below the boards:** every contrast check behind the notes, a color-blindness preview, and CSS tokens for both modes. Click any swatch to copy its hex.

**Colors that fit the industry, plus one surprise.** A small script suggests three directions from the brand's industry (finance, food, wellness, tech and 16 more). The primary and supporting hues are the families that industry's customers expect, like cobalt and pine for a bank or brick and mustard for a restaurant. One wildcard color per direction is drawn at random, leaning toward hues that still suit the industry, so two palettes for the same industry don't match. Every color is spaced in OKLCH so it stays a clear distance from the others in both light and dark mode. Claude picks the direction that fits the brand and mentions the other two.

Your seed colors are used exactly as given. When white text doesn't work on one, the notes say so and point to the step or neutral that does.

## How the checks work

Claude doesn't estimate any of the numbers. A bundled script, [`check_palette.py`](skills/brand-palette/scripts/check_palette.py) (standard-library Python), does all of the math:

- WCAG 2.x contrast ratios, never rounded up
- color-blindness simulation with the Machado (2009) matrices, and OKLab distance (ΔEOK) for the pairs that need to stay distinct
- a tip about halation (glowing or blurry text for readers with astigmatism) when dark-mode text is very bright
- for every failing required pair, a fix with the same hue and just enough lightness change to pass

The script also writes the notes column itself, from these measurements. Claude drafts the palette, runs the script, applies the fixes, and builds the board only once every required pair passes AA.

You can also run the script on its own:

```bash
python3 check_palette.py --pair "#767676" "#ffffff"      # one pair
python3 check_palette.py palette.json --all              # every pair in a palette
python3 check_palette.py palette.json --html out.html    # build the swatch board
python3 directions.py --industries                       # list the industries
python3 directions.py --industry finance                 # 3 directions for a finance brand
```

See [`examples/sample-palette.json`](examples/sample-palette.json) for a full palette file.

## Brand Builder

This plugin has a second skill, **brand-builder**, that turns a palette into a full brand reference page: a one-page design system with a sticky section nav and an Auto/Light/Dark switch. Ask for "a brand guide", "a design reference" or "the full brand page" and it builds:

- **Brand:** the concept, one motif per brand color with its job, the personality (what the brand is and isn't) and how to write the name
- **Color:** seven neutrals, each brand color with its steps and usage rule, and a contrast table for both modes
- **Charts:** chart colors with their own mid-tone steps, a 10-step heatmap ramp, live example charts and series rules
- **Signature:** the brand's one recognisable move, with do and don't examples and the CSS for it
- **Typography, Layout and Components:** font specimens and a type scale, the grid and spacing scale, and live buttons, KPI cards, tabs, form fields, notices, rows and tags
- **Accessibility and Tokens:** what passes, what to watch and what to always do, plus copyable CSS tokens for both modes

Claude writes the words and draws the art (the hero and motif SVGs) in a small brand spec. [`build_brand.py`](skills/brand-builder/scripts/build_brand.py) measures everything else with the same checker, using standard-library Python:

- card, raised and divider surfaces derived from the palette's page and border grey
- an error red that passes in both modes
- a fill step per brand color for buttons: the base, or the strong step when no text passes on the base
- chart steps that are at least 3:1 on the page and on cards, spaced apart in lightness so they stay distinct under simulated color blindness
- the contrast table, the stats and the accessibility notes

You choose the type and the colors before it builds anything, fonts first:

1. **Fonts:** it runs brand-typography and publishes three checked typography options on a specimen page, then waits for you to pick one.
2. **Colors:** if you don't have a palette yet, it drafts three brand-palette directions, checks them, and shows them side by side in light and dark mode, set in your chosen fonts ([`compare_palettes.py`](skills/brand-palette/scripts/compare_palettes.py)). Then it waits for you to pick one.
3. **Recheck:** it checks the chosen fonts again against the chosen palette, fixes the scale if needed, and only then builds the page.

If you already named your fonts or have a palette, that step is skipped.

```bash
python3 build_brand.py brand.json --check             # print the measurements
python3 build_brand.py brand.json --out brand.html    # build the page
```

See [`examples/story-structure-brand.json`](examples/story-structure-brand.json) for a full brand spec, built on [`examples/story-structure-palette.json`](examples/story-structure-palette.json).

## Brand Typography

The third skill, **brand-typography**, picks fonts for a brand. Ask for "fonts for my bakery", "a body font to go with Fraunces" or "type that matches this logo". Give it any mix of a brand description, a palette, a logo or image, or fonts you've already chosen (it keeps those and builds around them). With no palette, it checks against greyscale.

It shortlists three free pairings (Google Fonts, Fontshare, or an open-licence font file you supply) and publishes a specimen page. The page shows each option as a wordmark, on a web page with buttons and a form, in a printed document and on a business card, in a data table and a chart, and as a type scale. One option is marked as the pick. Each option has a readability table, with a fix next to anything that doesn't pass:

- **Licence, languages and weights:** free for commercial use and logos, covers the brand's character sets, and has the weights the scale uses
- **WCAG 2.2:** 1.4.3 contrast, 1.4.4 resize text, 1.4.8 visual presentation (AAA), and a Text spacing switch on the page to test 1.4.12
- **APCA (WCAG 3 draft):** the minimum font size for each row's weight and contrast, on each background in both modes
- **BDA Dyslexia Style Guide:** body size, line spacing, line length, sans serif body, no italics or capitals for reading text, letter and word spacing, and mirror letters (b/d, p/q)
- **Legibility:** x-height at body size, how alike I/l/1, rn/m and cl/d look, the opening of c, tabular figures and a distinct zero

[`check_type.py`](skills/brand-typography/scripts/check_type.py) fetches the fonts and measures all of this by reading the font files and rendering letter shapes. It uses standard-library Python, plus Pillow for the shape measurements. APCA's constants and font table are read from the published apca-w3 package at run time, pinned and checksum-verified, because APCA's licence covers WCAG web content only.

```bash
python3 check_type.py type.json                         # print the checks
python3 check_type.py type.json --out type.html         # build the specimen page
python3 check_type.py --font "Atkinson Hyperlegible Next"   # measure one font
python3 check_type.py type.json --brand-type a --fonts-dir fonts   # option a as brand-builder's type block
```

brand-builder uses it for its Typography section, so a brand page's fonts are checked the same way.

## Install

In Claude Code, run:
```
/plugin marketplace add ItsAlwaysRaining/claude-skills
/plugin install brand-palette@claude-skills
```

Or copy it manually:
```bash
git clone https://github.com/ItsAlwaysRaining/claude-skills.git
mkdir -p ~/.claude/skills
cp -r claude-skills/plugins/brand-palette/skills/brand-palette ~/.claude/skills/
cp -r claude-skills/plugins/brand-palette/skills/brand-builder ~/.claude/skills/   # optional; needs brand-palette next to it
cp -r claude-skills/plugins/brand-palette/skills/brand-typography ~/.claude/skills/   # optional; needs brand-palette next to it
```

It needs Python 3 and nothing else. No accounts or setup. brand-typography also needs internet access to fetch fonts (cached in `~/.cache/brand-typography`), and uses [Pillow](https://pypi.org/project/pillow/) (`pip install pillow`) for the letter-shape checks if it's installed.
