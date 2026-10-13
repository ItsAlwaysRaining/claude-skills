#!/usr/bin/env python3
"""Suggest starting directions for a brand palette from its industry, and write a draft palette for one.

Each industry has hue families its customers expect (finance leans on cobalt, pine and indigo;
food on brick, terracotta and copper). Those set the primary and supporting colors, with no
randomness. One color per direction, the wildcard, is drawn at random so palettes in the same
industry don't all look alike. Every color is placed in OKLCH and moved in lightness until it
is a clear OKLab distance (ΔEOK) from the others, in both light and dark mode.

Usage:
  python3 directions.py --industries                             # list the industries
  python3 directions.py --industry finance                       # 3 directions for a finance brand
  python3 directions.py --industry food --seed-hex "#9C3B2A"     # keep a seed as the primary, fill in the rest
  python3 directions.py --industry finance --rng 4821 --pick 2 --name "Acme" --out draft.json
                                                                 # write a draft for direction 2 of draw 4821

The draft fills every step for light and dark mode and leaves each `usage` empty;
check_palette.py refuses the draft until every usage label is written.
Standard library only.
"""
import argparse
import json
import random
import sys
from pathlib import Path

from check_palette import FAMILIES, FAMILY_HUE, distance, family_of, from_oklch, parse_hex, to_hex, to_oklch

# label, primary families (one per direction), supporting families in order of fit, characters.
INDUSTRIES = {
    "finance": ("Banking, fintech, insurance, investing", ["cobalt", "pine", "indigo"],
                ["teal", "ochre", "jade", "steel", "petrol"], ["jewel-toned", "dusty"]),
    "health": ("Healthcare, medical, pharma, dental", ["teal", "cobalt", "jade"],
               ["jade", "steel", "terracotta", "iris", "petrol"], ["clear", "dusty"]),
    "wellness": ("Wellness, spa, yoga, mental health, skincare", ["jade", "plum", "terracotta"],
                 ["olive", "orchid", "copper", "teal", "moss"], ["dusty", "earthy"]),
    "tech": ("SaaS, software, AI, developer tools", ["indigo", "cobalt", "iris"],
             ["teal", "orchid", "jade", "copper", "petrol"], ["clear", "jewel-toned"]),
    "food": ("Restaurants, food and drink, grocery, coffee, bakery", ["brick", "terracotta", "copper"],
             ["mustard", "olive", "moss", "ochre", "pine"], ["earthy", "clear"]),
    "sustainability": ("Sustainability, outdoors, agriculture, gardening", ["moss", "pine", "olive"],
                       ["ochre", "terracotta", "teal", "jade", "copper"], ["earthy", "dusty"]),
    "energy": ("Utilities, solar, EV, oil and gas", ["cobalt", "teal", "ochre"],
               ["mustard", "jade", "copper", "petrol", "moss"], ["clear", "jewel-toned"]),
    "education": ("Schools, edtech, learning, publishing", ["cobalt", "teal", "raspberry"],
                  ["mustard", "jade", "terracotta", "iris", "brick"], ["clear", "earthy"]),
    "kids": ("Kids, toys, family, games for children", ["teal", "raspberry", "ochre"],
             ["mustard", "cobalt", "jade", "orchid", "copper"], ["clear"]),
    "luxury": ("Luxury, fashion, jewelry, premium goods", ["plum", "pine", "mulberry"],
               ["ochre", "copper", "steel", "indigo", "olive"], ["jewel-toned", "dusty"]),
    "beauty": ("Beauty, cosmetics, salons, fragrance", ["mulberry", "orchid", "raspberry"],
               ["terracotta", "plum", "jade", "copper", "olive"], ["dusty", "clear"]),
    "legal": ("Law, government, consulting, institutions", ["indigo", "pine", "brick"],
              ["ochre", "steel", "petrol", "olive", "cobalt"], ["dusty", "jewel-toned"]),
    "property": ("Real estate, construction, architecture, home goods", ["petrol", "terracotta", "olive"],
                 ["copper", "steel", "mustard", "moss", "teal"], ["earthy", "dusty"]),
    "travel": ("Travel, hospitality, airlines, hotels", ["teal", "petrol", "terracotta"],
               ["ochre", "copper", "cobalt", "jade", "raspberry"], ["clear", "earthy"]),
    "entertainment": ("Media, gaming, music, events", ["iris", "raspberry", "indigo"],
                      ["teal", "orchid", "mustard", "jade", "copper"], ["clear", "jewel-toned"]),
    "sports": ("Sports, fitness, athletics", ["brick", "cobalt", "copper"],
               ["mustard", "teal", "steel", "jade", "indigo"], ["clear"]),
    "industrial": ("Automotive, manufacturing, logistics, B2B services", ["steel", "brick", "petrol"],
                   ["ochre", "copper", "cobalt", "mustard", "teal"], ["dusty", "clear"]),
    "retail": ("Retail, e-commerce, marketplaces", ["raspberry", "cobalt", "copper"],
               ["teal", "mustard", "iris", "jade", "orchid"], ["clear"]),
    "nonprofit": ("Charities, community groups, social causes", ["teal", "terracotta", "iris"],
                  ["ochre", "jade", "cobalt", "raspberry", "moss"], ["earthy", "clear"]),
    "general": ("Anything that fits none of the above", ["cobalt", "teal", "plum"],
                ["ochre", "jade", "terracotta", "iris", "copper"], ["jewel-toned", "earthy"]),
}
# Chroma range for each character. Industry colors use the middle; the wildcard draws within it.
CHARACTERS = {"dusty": (0.045, 0.075), "earthy": (0.075, 0.11), "jewel-toned": (0.10, 0.14), "clear": (0.12, 0.165)}
# Lightness for color 1 (primary, carries white text), 2 (supporting), 3 (light accent), 4 (extra).
LIGHTNESS = [(0.38, 0.48), (0.47, 0.60), (0.68, 0.80), (0.55, 0.66)]
# How far apart, in ΔEOK, any two brand colors must be. Dark mode squeezes lightness, so it gets less.
APART_LIGHT, APART_DARK, APART_SOFT = 0.15, 0.10, 0.08
MIN_HUE_GAP = 25        # degrees; closer hues read as one color in two shades
WILDCARD_JITTER = 10    # degrees the wildcard may drift from its family's hue
INDUSTRY_WEIGHT = 2.0   # the wildcard prefers unused families from the industry's lists this much


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


def hue_gap(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def far_enough(hex_, placed):
    """True when hex_ is a clear ΔEOK from every placed color, in both modes and in the chart fills."""
    light, dark = steps(hex_)
    for other in placed:
        ol, od = steps(other["hex"])
        if (distance(light["base"], ol["base"]) < APART_LIGHT or distance(dark["base"], od["base"]) < APART_DARK
                or distance(light["soft"], ol["soft"]) < APART_SOFT or distance(dark["soft"], od["soft"]) < APART_SOFT):
            return False
    return True


def place(hue, chroma, L0, placed):
    """The lightness nearest L0 at which this hue sits far enough from the placed colors.
    Low-chroma colors can only differ in lightness, so if none fits, chroma rises a little and it tries again."""
    if any(hue_gap(hue, to_oklch(p["hex"])[2]) < MIN_HUE_GAP and to_oklch(p["hex"])[1] > 0.03 for p in placed):
        return None
    for C in (chroma, chroma + 0.02, chroma + 0.04):
        for k in range(37):
            for L in ((L0,) if k == 0 else (L0 + k * 0.015, L0 - k * 0.015)):
                if 0.30 <= L <= 0.85:
                    hex_ = from_oklch(L, C, hue)
                    if far_enough(hex_, placed):
                        return hex_
    return None


def wildcard(rng, ind, chroma_range, slot, placed):
    """One color drawn at random, leaning toward the industry's unused families, placed far enough from the rest."""
    used = {p["family"] for p in placed}
    industry = set(ind[1]) | set(ind[2])
    pool = [(name, INDUSTRY_WEIGHT if name in industry else 1.0) for _, name in FAMILIES if name not in used]
    for _ in range(40):
        x = rng.uniform(0, sum(w for _, w in pool))
        for name, w in pool:
            x -= w
            if x <= 0:
                break
        hue = (FAMILY_HUE[name] + rng.uniform(-WILDCARD_JITTER, WILDCARD_JITTER)) % 360
        hex_ = place(hue, rng.uniform(*chroma_range), rng.uniform(*LIGHTNESS[slot]), placed)
        if hex_:
            return hex_
    return None


def draw(rng, industry, count, colors, seeds, character=None):
    ind = INDUSTRIES[industry]
    _, primaries, supports, characters = ind
    out = []
    for i in range(count):
        char = character or characters[i % len(characters)]
        lo, hi = CHARACTERS[char]
        mid = (lo + hi) / 2
        placed = [{"hex": s, "family": family_of(s), "role": "seed"} for s in seeds]
        if not placed:
            fam = primaries[i % len(primaries)]
            placed.append({"hex": from_oklch(sum(LIGHTNESS[0]) / 2, mid, FAMILY_HUE[fam]), "family": fam, "role": "industry"})
        # Every slot but the last comes from the industry's supporting families, then its other primaries;
        # the last is the wildcard. With only 2 colors there is no wildcard. Seeded directions rotate the
        # supports so they differ.
        industry_slots = colors - 1 if colors >= 3 else colors
        order = supports[i % len(supports):] + supports[:i % len(supports)] if seeds else supports
        for fam in order + primaries:
            if len(placed) >= industry_slots:
                break
            if fam in {p["family"] for p in placed}:
                continue
            slot = len(placed)
            hex_ = place(FAMILY_HUE[fam], mid, sum(LIGHTNESS[slot]) / 2, placed)
            if hex_:
                placed.append({"hex": hex_, "family": fam, "role": "industry"})
        if len(placed) < colors:
            hex_ = wildcard(rng, ind, (lo, hi), min(len(placed), len(LIGHTNESS) - 1), placed)
            if hex_:
                placed.append({"hex": hex_, "family": family_of(hex_), "role": "wildcard"})
        out.append({"industry": industry, "character": char, "colors": [p["hex"] for p in placed],
                    "families": [p["family"] for p in placed], "roles": [p["role"] for p in placed]})
    return out


def describe(d):
    parts = []
    for fam, hex_, role in zip(d["families"], d["colors"], d["roles"]):
        tag = " (seed)" if role == "seed" else " (wildcard)" if role == "wildcard" else ""
        parts.append(f"{fam} {hex_}{tag}")
    return f"{d['character']} {d['families'][0]}: " + " + ".join(parts)


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
    ap = argparse.ArgumentParser(description="Suggest industry-based starting directions for a brand palette.")
    ap.add_argument("--industries", action="store_true", help="list the industries and their hue families")
    ap.add_argument("--industry", choices=list(INDUSTRIES), help="the brand's industry (see --industries)")
    ap.add_argument("--character", choices=list(CHARACTERS), help="override the industry's usual character")
    ap.add_argument("--count", type=int, default=3, help="how many directions (default 3)")
    ap.add_argument("--colors", type=int, choices=[2, 3, 4], default=3, help="brand colors per direction (default 3)")
    ap.add_argument("--seed-hex", nargs="+", default=[], metavar="HEX", help="1-4 seed colors to keep; the first is the primary")
    ap.add_argument("--rng", type=int, help="draw number, to repeat the wildcard colors exactly")
    ap.add_argument("--pick", type=int, help="write a draft palette for this direction (1-based)")
    ap.add_argument("--name", default="Brand", help="brand name for the draft")
    ap.add_argument("--out", help="where to write the draft JSON")
    args = ap.parse_args()

    if args.industries:
        for key, (label, primaries, supports, characters) in INDUSTRIES.items():
            print(f"{key:15} {label}\n{'':15} primaries: {', '.join(primaries)}; supporting: {', '.join(supports)}; "
                  f"{' or '.join(characters)}")
        return 0
    if not args.industry:
        ap.error("give --industry (see --industries; use general when nothing fits)")

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
    colors = max(args.colors, len(seeds))
    directions = draw(rng, args.industry, args.count, colors, seeds, args.character)

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

    print(f"Draw {number}: {args.industry} ({INDUSTRIES[args.industry][0]})")
    for i, d in enumerate(directions, 1):
        print(f"  {i}. {describe(d)}")
        if len(d["colors"]) < colors:
            print(f"     only {len(d['colors'])} colors fit a clear distance apart; add one by hand or draw again")
    print(f"\nTo draft one: python3 scripts/directions.py --industry {args.industry} --rng {number} --pick N "
          f"--name \"<brand>\" --out <file>"
          + (f" --character {args.character}" if args.character else "")
          + (f" --count {args.count}" if args.count != 3 else "") + (f" --colors {args.colors}" if args.colors != 3 else "")
          + (" --seed-hex " + " ".join(seeds) if seeds else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
