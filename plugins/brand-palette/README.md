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

Your seed colors are used exactly as given. When white text doesn't work on one, the notes say so and point to the step or neutral that does.

## How the checks work

Claude doesn't estimate any of the numbers. A bundled script, [`check_palette.py`](skills/brand-palette/scripts/check_palette.py) (standard-library Python), does all of the math:

- WCAG 2.x contrast ratios, never rounded up
- color-blindness simulation with the Machado (2009) matrices, and CIEDE2000 color difference for the pairs that need to stay distinct
- a tip about halation (glowing or blurry text for readers with astigmatism) when dark-mode text is very bright
- for every failing required pair, a fix with the same hue and just enough lightness change to pass

The script also writes the notes column itself, from these measurements. Claude drafts the palette, runs the script, applies the fixes, and builds the board only once every required pair passes AA.

You can also run the script on its own:

```bash
python3 check_palette.py --pair "#767676" "#ffffff"      # one pair
python3 check_palette.py palette.json --all              # every pair in a palette
python3 check_palette.py palette.json --html out.html    # build the swatch board
```

See [`examples/sample-palette.json`](examples/sample-palette.json) for a full palette file.

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
```

It needs Python 3 and nothing else. No accounts or setup.
