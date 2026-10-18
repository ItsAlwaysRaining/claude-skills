---
name: brand-typography
description: Pick typography for a brand. Shortlists three free font pairings (Google Fonts, Fontshare or other open-licence fonts), measures each one against WCAG 2.2, APCA, the British Dyslexia Association style guide and letter-shape legibility (x-height, I/l/1 and rn/m confusion, apertures, tabular figures), checks licence, language support and weights, and publishes a specimen page showing each option on web and app UI, print, data and charts and the wordmark, with a readability table for each and one marked as the pick. Starts from a brand description, a palette, a logo or image, or fonts already chosen, in any mix. Use whenever the user wants fonts, typefaces, a font pairing, a type scale or typography for a brand, product or site, e.g. "what fonts should my bakery use", "find a body font to go with Fraunces", "pick type that matches this logo", "are these fonts readable enough", "which free fonts suit a calm fintech brand", even if they don't say "typography". brand-builder also uses it for its typography section.
---

# Brand Typography

Turn a brand idea into three typography options, check each one against readability standards, and show them on one specimen page: the wordmark, a web page with buttons and a form, a printed document and a business card, a data table and a chart, and the type scale. Each option has a readability table, and one is marked as the pick.

**The measurements are the script's.** `scripts/check_type.py` fetches each font, reads its files, and writes every result: licence, coverage, weights, WCAG and APCA contrast, BDA spacing, x-height and letter shapes. Never state a contrast value, an x-height or a pass from memory. Your job is the taste: which fonts suit the brand, how they pair, and the scale.

## Step 1: Read the inputs

Accept any mix of these. If the brief is thin ("a bakery brand"), don't ask questions. Make reasonable choices and record them in the spec's `assumptions`, so they show on the page.

- **A brand description:** industry, audience, personality words, where the type will be used.
- **A palette:** a brand-palette JSON, or a published palette board (read it with the Artifact tool and save its `palette-data` JSON as brand-builder's Step 1 describes). The checks use its text, muted, page and surface colors. **With no palette, leave `palette` out and the checks use greyscale.** Don't invent brand colors for this.
- **A logo or image:** look at its letterforms. Is it serif or sans? Geometric (round o, single-storey a) or humanist (calligraphic stress, open shapes)? What's its weight, width and stroke contrast? Then decide whether the display face should echo it or deliberately contrast with it, and say which in `why`. Don't claim to identify the exact font in a logo. Say it "looks like a geometric sans in the spirit of…".
- **Fonts already chosen:** keep them exactly as given, in every option, and find partners for them. If one fails a check, report the failure and the cheapest way to work around it (a larger size, a different role) but don't replace the font. The user chose it.

Pick the `languages` from the brief: `latin` by default, `latin-ext` for most European markets, and others when the brief names them.

## Step 2: Shortlist three options

Make the three options genuinely different, not three versions of one idea. A useful spread:

1. **The pick:** the best fit for the personality.
2. **A quieter alternative:** more neutral or more readable, often a single family.
3. **A bolder alternative:** more character in the display face.

For each option choose 1–3 fonts. Use a display face only when the brand has a voice that body type can't carry. Use one workhorse UI/body face. Add a mono face only when the brand shows code, IDs or many figures. A superfamily (Plex, Source, Noto) is fine when it suits the brand.

Pairing that works:
- Contrast in structure (serif with sans, geometric with humanist), similarity in proportion (x-height, width). Two fonts that differ only slightly look like a mistake.
- The body face carries the readability burden. Prefer large x-heights, open apertures and distinct I/l/1 there. Display faces can be more expressive because they're set large.
- Look beyond the most common defaults (Inter, Roboto, Montserrat, Poppins, Open Sans). Use one only when it's genuinely the best fit, and say why.

Fonts must be free for commercial use: Google Fonts (`google`), Fontshare (`fontshare`), or a file the user has from another open-licence foundry (`file`, with its licence). To check a candidate before committing, run:

```bash
python3 scripts/check_type.py --font "Atkinson Hyperlegible Next"
python3 scripts/check_type.py --font "Satoshi" --source fontshare
```

## Step 3: Write the type spec

Read `references/type-spec.md` for every field. Save the spec as `<brand>-type.json` in the scratchpad (or next to the palette, if the user is working in a folder of brand files). Give each option a full scale (5–8 rows with a `use` on each) and real sample copy from the brand's domain, never lorem ipsum.

## Step 4: Check and fix

Run from this skill's folder:

```bash
python3 scripts/check_type.py <type.json>
```

It prints every check for every option. The groups are Licence, Languages, Weights, WCAG 2.2, APCA, BDA and Legibility, each marked ok, WATCH, FAIL or TEST, and each non-pass has a fix line.

- **FAIL means don't recommend it as it is.** Fix every failure in the spec and run again:
  - APCA or WCAG contrast: raise the size or weight the fix names, or move the row to the main text color. Muted text often needs 500 weight or a larger size to pass APCA.
  - A missing weight: use a weight the font has.
  - No tabular figures: set the data rows in the mono face or in a font with `tnum`.
  - Licence or language: swap the font, unless the user chose it (then leave it and report it).
- **WATCH is a trade-off the reader should know about.** Fix it when that's cheap and doesn't change the brand: paragraph spacing, measure, line height, rem instead of px. Keep the rest as notes. BDA letter spacing usually stays as a watch, because tracking body text to 35% changes the brand's texture. The page gives the CSS for readers who need it.
- **TEST is 1.4.12 text spacing.** Check it on the page with the Text spacing switch after building.

## Step 5: Build the page and publish

```bash
python3 scripts/check_type.py <type.json> --out <brand>-type.html
```

Don't edit the generated HTML by hand. Change the spec and build again. Google fonts load from Google Fonts. Fontshare and local fonts are inlined, so the page works as an artifact.

Save it in the user's working directory unless they named another place. If that directory is a skill or plugin repo, save it in the scratchpad instead. If the Artifact tool is available, publish the page as a private artifact with the icon `text` and a one-sentence description naming the brand and the pick. Republish to the same URL for changes. If the tool isn't available, give the file path and say to open it in a browser.

## Step 6: Report back

Keep the chat summary short:
- the link or file path
- the pick in one line (fonts and why), and the other two options in a few words each
- the pick's check counts, and the two or three watches that matter most
- your assumptions, including "greyscale" when there was no palette, and any font you read from a logo

For changes ("make the body bigger", "try a different serif"), edit the spec and run Steps 4 and 5 again.

## Step 7: Hand the pick to brand-builder

When brand-builder is running, or the user wants a full brand page next, export the chosen option as brand-builder's `type` block:

```bash
python3 scripts/check_type.py <type.json> --brand-type <id> --fonts-dir <dir next to the brand spec>/fonts
```

It prints JSON to paste as the brand spec's `type` field. Fontshare and local fonts are copied into `--fonts-dir` and listed under `files` as paths relative to the brand spec, so keep that folder next to it and brand-builder can inline them. It warns if the option still fails a check. Edit only the `title`, `lede`, `sample` and `use` text afterwards, never the families, sizes or weights. Those are what was checked.

## Notes on the standards

- **WCAG 2.2:** 1.4.3 contrast (AA, 4.5:1, or 3:1 for large text), 1.4.4 resize text (AA, rem sizes), 1.4.8 visual presentation (AAA: 80 characters, 1.5 line height, paragraph spacing 1.5× the line spacing, not justified), 1.4.12 text spacing (AA, tested on the page).
- **APCA** is the WCAG 3 draft method. The script reads apca-w3's own constants and font lookup table at run time (pinned version, checksum verified) rather than copying them, because APCA is licensed for WCAG web content only. Treat its results as screen guidance, not print.
- **BDA Dyslexia Style Guide (2023):** 16–19px body, sans serif body, 1.5 line spacing, 60–70 characters, no italics or capitals for reading text, letter spacing about 35% of the average letter width, word spacing at least 3.5× the letter spacing, and letters that aren't mirror images.
- **Legibility** is measured on the regular weight: x-height (8px or more at body size), how alike I/l/1, rn/m and cl/d look (80% shared ink or more is flagged), the opening of c (30% of its height or more), tabular figures for data, and a distinct zero for codes.

The script uses only the Python standard library, plus Pillow for the letter-shape measurements. Without Pillow those checks show a watch saying how to install it.
