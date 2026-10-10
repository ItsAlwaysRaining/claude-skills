---
name: brand-palette
description: Build an accessible brand color palette with light and dark mode values, checked against WCAG 2.2 AA (AAA flagged) and simulated for color blindness, then published as a swatch board. Each brand color gets Dark, Light and Surface steps, the four neutrals get short role labels, and a notes column explains what each step is for, which text works on which color, and any color-blindness or low-vision issues. Starts from a brand description, up to 4 seed hex codes, an image or logo, or any mix of them. Use whenever the user wants a color palette, brand colors, a color scheme, theme colors or design tokens for a brand, product or site, e.g. "make me a palette for a calm fintech brand", "build a palette around #1F3A5F and #FF7A59", "pull brand colors from this logo", "I need light and dark mode colors that pass accessibility", or "are these brand colors accessible?".
---

# Brand Palette

Turn a brand idea into a palette board. It has a row of brand colors, each with Dark, Light and Surface steps; a row of four neutrals, each labeled with its job ("Headings, body text"); and a notes column that says what each step is for, which text works on which color, and where colors fall short for color-blind or low-vision readers. Every palette has a light-mode board and a dark-mode board.

**Contrast and color-blindness results come only from `scripts/check_palette.py`.** Never estimate a ratio or guess whether two colors can be told apart. The script writes the notes itself from what it measures.

## Step 1: Read the inputs

Accept any mix of these:

- **A brand description:** industry, mood, audience, words like "calm", "playful" or "premium".
- **Seed hex codes, 1 to 4:** existing brand colors. Each seed becomes a brand color's `base`, exactly as given. If more than 4 are given, ask which 4 matter most.
- **An image or logo:** look at it and pick out 2–4 dominant brand colors. Ignore the background, anti-aliasing and shadows. Tell the user which hex codes you took from it, since your reading is approximate. If they know the exact values, those win.

If there's nothing to go on (e.g. just "make me a palette"), ask one short question: what is the brand, and are there existing colors? Otherwise, don't ask. Make reasonable choices and say what you assumed. With only a description, 3–4 brand colors is a good default.

## Step 2: Draft the palette

Read `references/palette-format.md`. It covers the steps and their jobs, the four neutrals, what is required versus only noted, how to build the dark mode, and the JSON format.

Write the palette JSON to the scratchpad directory (or a temp folder if there isn't one), e.g. `<scratchpad>/<brand>-palette.json`. Give every brand color a 2–5 word `usage` label ("Primary buttons, links, headers") and all four steps for both modes.

## Step 3: Check and fix

Run from this skill's folder:

```bash
python3 scripts/check_palette.py <palette.json>
```

It prints each board's notes column exactly as it will appear.

- **"Must fix" items** are required pairs below AA. Each comes with a `Try #XXXXXX` suggestion: the same hue with just enough lightness change to pass. Apply it to the step it names, never to a seed `base`, and run the script again until it prints `OK`.
- **Everything else is a caveat,** and it goes on the board. That's what the user asked for. Before building, fix whatever is cheap to fix. For example, if two brand colors look alike for everyone, move them apart in lightness, or darken a strong step so white text passes on it. Leave a caveat when fixing it would change a seed color.
- If something important isn't covered (like "the gold seed was read from a JPEG, so confirm the exact hex"), add it to `notes`. Don't repeat what the script already says.

Use `--all` to see every checked pair, and `--pair FG BG` to test one combination quickly.

## Step 4: Build the board

```bash
python3 scripts/check_palette.py <palette.json> --html <out-dir>/<brand>-palette.html
```

This fills in `references/page-template.html`: a light-mode board and a dark-mode board in the layout above, then the full contrast tables, a color-blindness preview and copyable CSS tokens. Clicking any swatch copies its hex. Don't edit the generated HTML by hand. Change the JSON and run the script again.

Save it to the user's current working directory unless they named another place. Then:
- If the Artifact tool is available, publish the file as a private artifact (icon `palette`, description: one sentence naming the brand and the mood).
- If it isn't, tell the user the file path and say to open it in a browser.

## Step 5: Report back

Keep the chat summary short:
- the link or file path
- one line on the direction ("Navy and teal for trust, rose and gold for warmth; dark mode on blue-black")
- the counts from the script (required pairs passed, AAA passes)
- the two or three caveats that matter most, in a few words each, e.g. "Gold needs dark text; white only works on Dark gold"
- any assumptions you made, such as hex codes read from an image

If the user asks for changes ("warmer", "swap the teal", "add a fifth color"), edit the JSON, run Steps 3–4 again, and republish to the same artifact.
