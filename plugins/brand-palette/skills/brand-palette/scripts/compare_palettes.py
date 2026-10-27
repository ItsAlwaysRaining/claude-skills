#!/usr/bin/env python3
"""Show up to three palettes side by side on one page, so the user can pick one.

Each palette is a finished brand-palette JSON (usage labels written). The page shows every
palette in light and dark mode: its brand colors and neutrals, a small sample of real UI drawn
with them (heading, body, caption, button, tag, card), and the checker's counts and main caveats.

Usage:
  python3 compare_palettes.py a.json b.json c.json --html compare.html
  python3 compare_palettes.py a.json b.json c.json --pick 1 --labels "Forest and blush" "…" "…" \\
      --display-font "Fraunces" --body-font "IBM Plex Sans" --html compare.html

--display-font and --body-font load from Google Fonts, so the samples use the brand's chosen type.
Exit codes: 0 written, 1 a palette fails a required pair, 2 bad input. Standard library only.
"""
import argparse
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_palette as cp  # noqa: E402

LETTERS = "ABC"


def esc(s):
    return html.escape(str(s), quote=True)


def on_color(bg, candidates):
    return max(candidates, key=lambda c: cp.contrast(c, bg))


def panel(p, mode, sample):
    N = {job: p["neutrals"][job][mode] for job, _ in cp.NEUTRALS}
    first = p["brand"][0][mode]
    fill = first["base"]
    on = on_color(fill, [cp.WHITE, N["text"], N["page"]])
    if cp.contrast(on, fill) < cp.TEXT_AA:  # the base can't carry text: buttons use the strong step
        fill = first["strong"]
        on = on_color(fill, [cp.WHITE, N["text"], N["page"]])
    second = p["brand"][1][mode] if len(p["brand"]) > 1 else first
    tag_text = on_color(second["soft"], [N["text"], cp.WHITE])
    chips = "".join(
        f'<div class="chip" style="background:{b[mode]["base"]};color:{on_color(b[mode]["base"], [cp.WHITE, N["text"], N["page"]])}">'
        f'<b>{esc(b["name"])}</b><span>{b[mode]["base"]}</span></div>' for b in p["brand"])
    steps = "".join(
        f'<div class="steps">' + "".join(f'<i style="background:{b[mode][s]}" title="{esc(b["name"])} {s} {b[mode][s]}"></i>'
                                         for s in cp.STEPS) + "</div>" for b in p["brand"])
    neutrals = "".join(f'<i style="background:{N[j]}" title="{j} {N[j]}"></i>' for j, _ in cp.NEUTRALS)
    return f'''<div class="panel" style="background:{N["page"]};color:{N["text"]};border-color:{N["line"]}">
  <div class="mode" style="color:{N["muted"]}">{mode.title()} mode</div>
  <div class="chips">{chips}</div>
  <div class="steprow">{steps}<div class="steps neutral">{neutrals}</div></div>
  <div class="ui" style="background:{first["surface"]};border-color:{N["line"]}">
    <div class="h" style="color:{N["text"]}">{esc(sample["headline"])}</div>
    <p style="color:{N["text"]}">{esc(sample["body"])}</p>
    <p class="cap" style="color:{N["muted"]}">{esc(sample["caption"])}</p>
    <div class="row"><span class="btn" style="background:{fill};color:{on}">{esc(sample["button"])}</span>
    <span class="tag" style="background:{second["soft"]};color:{tag_text}">{esc(sample["tag"])}</span></div>
  </div>
</div>'''


def caveats(report, limit=3):
    items = []
    for m in cp.MODES:
        for sec in report["modes"][m]["sections"]:
            if sec["heading"] in ("Color blindness:", "Also watch:"):
                for i in sec["items"]:
                    if "stay distinct" not in i and i not in items:
                        items.append(i)
    return items[:limit]


def main():
    ap = argparse.ArgumentParser(description="Compare up to three palettes on one page.")
    ap.add_argument("palettes", nargs="+", help="1–3 palette JSON files")
    ap.add_argument("--html", required=True, metavar="OUT", help="where to write the page")
    ap.add_argument("--labels", nargs="+", help="a short name per palette (defaults to each palette's name)")
    ap.add_argument("--pick", type=int, help="mark this palette (1-based) as the recommendation")
    ap.add_argument("--brand", help="brand name for the title and the sample heading")
    ap.add_argument("--display-font", help="Google Fonts family for headings")
    ap.add_argument("--body-font", help="Google Fonts family for body text")
    ap.add_argument("--headline", help="sample heading")
    ap.add_argument("--body", help="sample body sentence")
    args = ap.parse_args()
    if not 1 <= len(args.palettes) <= 3:
        ap.error("give 1 to 3 palettes")
    try:
        pals = [cp.load_palette(p) for p in args.palettes]
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    labels = (args.labels or []) + [p["name"] for p in pals][len(args.labels or []):]
    brand = args.brand or pals[0]["name"]
    sample = {"headline": args.headline or brand, "body": args.body or "Body text on the tinted card, at the size people will read it.",
              "caption": "Secondary text · updated today", "button": "Get started", "tag": "Tag"}
    fams = [f for f in (args.display_font, args.body_font) if f]
    link = ("" if not fams else '<link rel="preconnect" href="https://fonts.googleapis.com">'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
            + "&".join("family=" + f.replace(" ", "+") + ":wght@400;600" for f in dict.fromkeys(fams)) + '&display=swap">')
    disp = f'"{args.display_font}", ' if args.display_font else ""
    body = f'"{args.body_font}", ' if args.body_font else ""

    failed = False
    cards = []
    for i, (p, label) in enumerate(zip(pals, labels)):
        rep = cp.check(p)
        c = rep["counts"]
        failed |= not rep["ok"]
        pick = args.pick == i + 1
        cav = "".join(f"<li>{esc(x)}</li>" for x in caveats(rep))
        cards.append(f'''<section class="opt{' picked' if pick else ''}" id="palette-{LETTERS[i].lower()}">
  <header><div class="eyebrow">Direction {LETTERS[i]}{' · <span class="pick">Our pick</span>' if pick else ''}</div>
  <h2>{esc(label)}</h2>{f'<p class="desc">{esc(p.get("description"))}</p>' if p.get("description") else ""}
  <p class="stats"><b>{c["aa_pass"]}/{c["pairs"]}</b> required pairs pass AA · <b>{c["aaa_pass"]}</b> also AAA · <b>{c["cvd_warnings"]}</b> color-blindness notes{"" if rep["ok"] else ' · <b class="bad">fails a required pair</b>'}</p></header>
  <div class="panels">{panel(p, "light", sample)}{panel(p, "dark", sample)}</div>
  {f'<details><summary>Main caveats</summary><ul>{cav}</ul></details>' if cav else '<p class="desc">No caveats from the checker.</p>'}
</section>''')

    page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(brand)} Palettes</title>
{link}
<style>
:root {{ --bg: #F7F7F8; --fg: #1E2126; --muted: #5C626B; --line: #D9DCE1; --accent: #2B4C7E;
  --disp: {disp}ui-serif, Georgia, serif; --body: {body}ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg: #15171A; --fg: #E6E8EB; --muted: #A2A8B1; --line: #343940; --accent: #9DB8E4; color-scheme: dark }} }}
:root[data-theme="dark"] {{ --bg: #15171A; --fg: #E6E8EB; --muted: #A2A8B1; --line: #343940; --accent: #9DB8E4; color-scheme: dark }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--bg); color: var(--fg); font: 16px/1.5 var(--body); }}
main {{ max-width: 1120px; margin: 0 auto; padding: 32px max(16px, env(safe-area-inset-right, 0px)) 64px max(16px, env(safe-area-inset-left, 0px)); display: grid; gap: 40px; }}
h1, h2 {{ font-family: var(--disp); margin: 0; line-height: 1.15; text-wrap: balance; }}
h1 {{ font-size: clamp(1.8rem, 5vw, 2.4rem); }}
h2 {{ font-size: 1.5rem; }}
.eyebrow {{ font-size: .75rem; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); font-weight: 600; }}
.pick {{ background: var(--accent); color: var(--bg); padding: 1px 9px; border-radius: 999px; letter-spacing: .04em; }}
.desc, .lede {{ color: var(--muted); margin: 4px 0 0; max-width: 70ch; }}
.stats {{ margin: 6px 0 0; font-size: .92rem; }}
.stats b {{ font-variant-numeric: tabular-nums; }}
.bad {{ color: #B3261E; }}
.opt {{ display: grid; gap: 14px; border-top: 1px solid var(--line); padding-top: 24px; }}
.opt.picked {{ border-top: 3px solid var(--accent); }}
.panels {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 14px; }}
.panel {{ border: 1px solid; border-radius: 12px; padding: 16px; display: grid; gap: 12px; min-width: 0; }}
.mode {{ font-size: .75rem; letter-spacing: .1em; text-transform: uppercase; font-weight: 600; }}
.chips {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(90px, 1fr)); gap: 8px; }}
.chip {{ border-radius: 8px; padding: 10px; min-height: 64px; display: flex; flex-direction: column; justify-content: flex-end; font-size: .8rem; }}
.chip span {{ font-family: ui-monospace, Menlo, monospace; font-size: .72rem; opacity: .9; }}
.steprow {{ display: grid; gap: 4px; }}
.steps {{ display: grid; grid-template-columns: repeat(4, 1fr); height: 14px; border-radius: 4px; overflow: hidden; }}
.steps.neutral {{ margin-top: 4px; }}
.steps i {{ display: block; }}
.ui {{ border: 1px solid; border-radius: 10px; padding: 14px; display: grid; gap: 6px; }}
.ui .h {{ font-family: var(--disp); font-size: 1.3rem; font-weight: 600; line-height: 1.2; }}
.ui p {{ margin: 0; }}
.ui .cap {{ font-size: .875rem; }}
.row {{ display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-top: 6px; }}
.btn {{ padding: 7px 14px; border-radius: 8px; font-weight: 600; font-size: .92rem; }}
.tag {{ padding: 2px 10px; border-radius: 999px; font-size: .82rem; }}
details summary {{ cursor: pointer; font-weight: 600; }}
details ul {{ margin: 8px 0 0; padding-left: 20px; color: var(--muted); display: grid; gap: 4px; max-width: 80ch; }}
</style></head><body><main>
<header><div class="eyebrow">Palette directions · {esc(brand)}</div><h1>Pick a palette for {esc(brand)}</h1>
<p class="lede">Each direction in light and dark mode: brand colors, their four steps (base, strong, soft, surface), the neutrals, and a sample card drawn with them. Counts come from the palette checker.</p></header>
{"".join(cards)}
</main></body></html>'''
    Path(args.html).write_text(page)
    print(f"Wrote {args.html}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
