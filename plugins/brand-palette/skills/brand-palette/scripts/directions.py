#!/usr/bin/env python3
"""Draw random starting directions for a brand palette, and write a draft palette for one of them.

Left alone, palettes drift to the same few hues (a blue primary, a red, a green, a gold).
This draws the primary hue, color scheme and character at random instead. It leans away
from the plain red/blue/green/yellow families and from primaries used in recent palettes
(history is kept in ~/.claude/brand-palette/history.json).

Usage:
  python3 directions.py                                   # 3 random directions
  python3 directions.py --seed-hex "#2C517A"              # keep a seed as the primary, randomize the rest
  python3 directions.py --rng 4821 --pick 2 --name "Acme" --out draft.json
                                                          # write a draft palette for direction 2 of draw 4821

The draft fills every step for light and dark mode and leaves each `usage` empty;
check_palette.py refuses the draft until every usage label is written.
Standard library only.
"""
import argparse
import json
import random
import sys
from pathlib import Path

from check_palette import FAMILIES, USUAL_FAMILIES, family_of, from_oklch, parse_hex, recent_families, to_hex, to_oklch

# Offsets from the primary hue for the other colors, by color scheme.
SCHEMES = {
    "split-complementary": [150, 210, 60],
    "triadic": [120, 240, 30],
    "complementary": [180, 25, -40],
    "analogous": [35, -35, 70],
    "tonal with one accent": [14, 180, -60],
}
# Chroma range for each character. Lightness is set per position so colors differ in lightness too.
CHARACTERS = {"dusty": (0.045, 0.075), "earthy": (0.075, 0.11), "jewel-toned": (0.10, 0.14), "clear": (0.12, 0.165)}
# Lightness for color 1 (primary, carries white text), 2 (supporting), 3 (light accent), 4 (extra).
LIGHTNESS = [(0.38, 0.48), (0.47, 0.60), (0.68, 0.80), (0.55, 0.66)]
USUAL_WEIGHT, RECENT_WEIGHT = 0.35, 0.1


def weighted_families(rng, recent, k):
    """k distinct families for primaries, leaning away from the usual and the recently used."""
    pool = []
    for hue, name in FAMILIES:
        w = 1.0
        if name in USUAL_FAMILIES:
            w *= USUAL_WEIGHT
        if name in recent:
            w *= RECENT_WEIGHT
        pool.append([hue, name, w])
    picked = []
    for _ in range(k):
        total = sum(p[2] for p in pool)
        x = rng.uniform(0, total)
        for p in pool:
            x -= p[2]
            if x <= 0:
                picked.append((p[0], p[1]))
                pool.remove(p)
                break
    return picked


def draw(rng, count, colors, seeds, recent):
    schemes = rng.sample(list(SCHEMES), k=min(count, len(SCHEMES)))
    if seeds:
        anchors = [(to_oklch(seeds[0])[2], family_of(seeds[0]))] * count
    else:
        anchors = weighted_families(rng, recent, count)
    out = []
    for i in range(count):
        scheme, character = schemes[i % len(schemes)], rng.choice(list(CHARACTERS))
        lo, hi = CHARACTERS[character]
        h0 = (anchors[i][0] + (0 if seeds else rng.uniform(-8, 8))) % 360
        hexes = []
        for pos in range(colors):
            if pos < len(seeds):
                hexes.append(seeds[pos])
                continue
            h = h0 if pos == 0 else (h0 + SCHEMES[scheme][pos - 1] + rng.uniform(-6, 6)) % 360
            c = rng.uniform(lo, hi)
            hexes.append(from_oklch(rng.uniform(*LIGHTNESS[pos]), c, h))
        out.append({"scheme": scheme, "character": character, "colors": hexes,
                    "families": [family_of(x) for x in hexes]})
    return out


def describe(d):
    fams = d["families"]
    return f"{d['character']} {fams[0]}, {d['scheme']}: " + " + ".join(
        f"{f} {x}" for f, x in zip(fams, d["colors"]))


def steps(hex_):
    """Light- and dark-mode steps for one brand color, from its OKLCH lightness and chroma."""
    L, C, h = to_oklch(hex_)
    light = {"base": hex_, "strong": from_oklch(max(0.2, L - 0.13), C * 0.95, h),
             "soft": from_oklch(0.70 + (min(max(L, 0.38), 0.8) - 0.38) * 0.36, C * 0.55, h), "surface": from_oklch(0.965, min(C * 0.15, 0.02), h)}
    # Keep the light-mode lightness order in dark mode, so colors that differ in lightness still do.
    dL = min(0.9, max(0.68, 0.68 + (L - 0.38) * 0.5))
    dark = {"base": from_oklch(dL, C * 0.8, h), "strong": from_oklch(min(0.9, dL + 0.08), C * 0.7, h),
            "soft": from_oklch(0.34 + (min(max(L, 0.38), 0.8) - 0.38) * 0.3, C * 0.5, h), "surface": from_oklch(0.25, min(C * 0.25, 0.03), h)}
    return light, dark


def draft(name, d):
    brand, used = [], set()
    for hex_, fam in zip(d["colors"], d["families"]):
        nm = fam.title()
        if nm in used:
            nm = ("Pale " if to_oklch(hex_)[0] > 0.6 else "Deep ") + nm
        used.add(nm)
        light, dark = steps(hex_)
        brand.append({"key": nm.lower().replace(" ", "-"), "name": nm, "usage": "", "light": light, "dark": dark})
    h = to_oklch(d["colors"][0])[2]
    n = lambda L, C: from_oklch(L, C, h)  # neutrals tinted toward the primary
    neutrals = {
        "text": {"light": n(0.27, 0.012), "dark": n(0.92, 0.008)},
        "muted": {"light": n(0.50, 0.016), "dark": n(0.74, 0.014)},
        "line": {"light": n(0.74, 0.012), "dark": n(0.42, 0.012)},
        "page": {"light": n(0.96, 0.006), "dark": n(0.21, 0.008)},
    }
    return {"name": name, "description": "", "seeds": [], "brand": brand, "neutrals": neutrals, "notes": []}


def main():
    ap = argparse.ArgumentParser(description="Draw random starting directions for a brand palette.")
    ap.add_argument("--count", type=int, default=3, help="how many directions to draw (default 3)")
    ap.add_argument("--colors", type=int, choices=[2, 3, 4], default=None, help="brand colors per direction (default: 3 or 4 at random)")
    ap.add_argument("--seed-hex", nargs="+", default=[], metavar="HEX", help="1-4 seed colors to keep; the first is the primary")
    ap.add_argument("--rng", type=int, help="draw number, to repeat a draw exactly")
    ap.add_argument("--pick", type=int, help="write a draft palette for this direction (1-based)")
    ap.add_argument("--name", default="Brand", help="brand name for the draft")
    ap.add_argument("--out", help="where to write the draft JSON")
    args = ap.parse_args()

    try:
        seeds = [to_hex(parse_hex(s)) for s in args.seed_hex]
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2
    if len(seeds) > 4:
        print("use at most 4 seed colors", file=sys.stderr)
        return 2

    number = args.rng if args.rng is not None else random.SystemRandom().randrange(1, 100000)
    rng = random.Random(number)
    colors = args.colors or max(len(seeds), rng.choice([3, 4]))
    recent = recent_families()
    directions = draw(rng, args.count, max(colors, len(seeds)), seeds, recent)

    if args.pick:
        if not 1 <= args.pick <= len(directions) or not args.out:
            print("--pick needs a direction number from the draw and --out", file=sys.stderr)
            return 2
        d = directions[args.pick - 1]
        palette = draft(args.name, d)
        palette["seeds"] = seeds
        Path(args.out).write_text(json.dumps(palette, indent=2))
        print(f"Wrote draft for direction {args.pick} ({describe(d)}) to {args.out}")
        return 0

    print(f"Draw {number}" + (f" (leaning away from recent: {', '.join(recent)})" if recent else ""))
    for i, d in enumerate(directions, 1):
        print(f"  {i}. {describe(d)}")
    print(f"\nTo draft one: python3 scripts/directions.py --rng {number} --pick N --name \"<brand>\" --out <file>"
          + (f" --count {args.count}" if args.count != 3 else "") + (f" --colors {args.colors}" if args.colors else "")
          + (" --seed-hex " + " ".join(seeds) if seeds else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
