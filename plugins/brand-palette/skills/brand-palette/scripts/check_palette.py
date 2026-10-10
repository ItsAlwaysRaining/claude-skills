#!/usr/bin/env python3
"""Check a brand palette for WCAG contrast and color-vision problems, and build its swatch board.

A palette is a row of brand colors, each with three tonal steps, plus four neutrals,
all with a light-mode and a dark-mode value. See references/palette-format.md.

Usage:
  python3 check_palette.py palette.json                 # failures + the notes that go on the board
  python3 check_palette.py palette.json --all           # also list every checked pair
  python3 check_palette.py palette.json --json          # full machine-readable report
  python3 check_palette.py palette.json --html out.html # write the swatch board (refuses on AA failures)
  python3 check_palette.py --pair "#767676" "#ffffff"   # contrast of one pair

Exit codes: 0 every required pair passes AA, 1 at least one fails, 2 bad input.
Standard library only.
"""
import argparse
import html
import json
import math
import re
import sys
from pathlib import Path

MODES = ["light", "dark"]
STEPS = ["base", "strong", "soft", "surface"]
# What each step is called on the board. Names follow lightness, so they differ by mode.
STEP_NAMES = {
    "light": {"base": "Base", "strong": "Dark", "soft": "Light", "surface": "Surface"},
    "dark": {"base": "Base", "strong": "Bright", "soft": "Muted", "surface": "Surface"},
}
NEUTRALS = [
    ("text", "Headings, body text"),
    ("muted", "Secondary text, captions, icons"),
    ("line", "Borders, dividers, disabled states, placeholders"),
    ("page", "Page and card backgrounds, input fills"),
]
NEUTRAL_CSS = {"text": "text", "muted": "text-muted", "line": "line", "page": "page"}
WHITE = "#FFFFFF"
MAX_BRAND = 6

TEXT_AA, TEXT_AAA, UI_AA = 4.5, 7.0, 3.0
TOO_CLOSE = 10.0  # CIEDE2000; below this, two colors are hard to tell apart at a glance
HALATION = 15.0   # dark-mode body text above this ratio can blur for readers with astigmatism

# Machado, Oliveira & Fernandes (2009), severity 1.0, applied to linear RGB.
CVD = {
    "protanopia": [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
    "deuteranopia": [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
    "tritanopia": [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]],
}
VISION_NOTES = {
    "protanopia": "red-blind, about 1% of men",
    "deuteranopia": "green-blind, about 1% of men, plus 5% with weak green",
    "tritanopia": "blue-blind, rare",
    "grayscale": "no color vision, or grayscale print",
}

HEX_RE = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
KEY_RE = re.compile(r"^[a-z][a-z0-9-]*$")


# ---------- color math ----------

def parse_hex(value):
    m = HEX_RE.match(str(value).strip())
    if not m:
        raise ValueError(f"not a hex color: {value!r}")
    h = m.group(1)
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def to_hex(rgb):
    return "#" + "".join(f"{round(min(1, max(0, c)) * 255):02X}" for c in rgb)


def lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def delin(c):
    c = min(1, max(0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def luminance(hex_):
    r, g, b = (lin(c) for c in parse_hex(hex_))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def floor2(r):
    # WCAG allows no rounding up: 4.499 fails, so never show it as 4.50.
    return math.floor(r * 100) / 100


def about(r):
    """Ratio as it reads in a note: 'about 8:1', 'about 3.4:1'."""
    return f"{int(r)}:1" if r >= 7 else f"{math.floor(r * 10) / 10:.1f}:1"


def to_lab(rgb):
    r, g, b = (lin(c) for c in rgb)
    x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / 1.08883

    def f(t):
        return t ** (1 / 3) if t > (6 / 29) ** 3 else t / (3 * (6 / 29) ** 2) + 4 / 29

    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e2000(lab1, lab2):
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2
    cbar = (math.hypot(a1, b1) + math.hypot(a2, b2)) / 2
    g = 0.5 * (1 - math.sqrt(cbar ** 7 / (cbar ** 7 + 25 ** 7)))
    a1p, a2p = (1 + g) * a1, (1 + g) * a2
    c1p, c2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360
    h2p = math.degrees(math.atan2(b2, a2p)) % 360

    dlp, dcp = L2 - L1, c2p - c1p
    if c1p * c2p == 0:
        dhp = 0
    else:
        dhp = h2p - h1p
        if dhp > 180:
            dhp -= 360
        elif dhp < -180:
            dhp += 360
    dHp = 2 * math.sqrt(c1p * c2p) * math.sin(math.radians(dhp / 2))

    lbp, cbp = (L1 + L2) / 2, (c1p + c2p) / 2
    if c1p * c2p == 0:
        hbp = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hbp = (h1p + h2p) / 2
    elif h1p + h2p < 360:
        hbp = (h1p + h2p + 360) / 2
    else:
        hbp = (h1p + h2p - 360) / 2

    t = (1 - 0.17 * math.cos(math.radians(hbp - 30)) + 0.24 * math.cos(math.radians(2 * hbp))
         + 0.32 * math.cos(math.radians(3 * hbp + 6)) - 0.20 * math.cos(math.radians(4 * hbp - 63)))
    dtheta = 30 * math.exp(-(((hbp - 275) / 25) ** 2))
    rc = 2 * math.sqrt(cbp ** 7 / (cbp ** 7 + 25 ** 7))
    sl = 1 + 0.015 * (lbp - 50) ** 2 / math.sqrt(20 + (lbp - 50) ** 2)
    sc = 1 + 0.045 * cbp
    sh = 1 + 0.015 * cbp * t
    rt = -math.sin(math.radians(2 * dtheta)) * rc
    return math.sqrt((dlp / sl) ** 2 + (dcp / sc) ** 2 + (dHp / sh) ** 2 + rt * (dcp / sc) * (dHp / sh))


def simulate(hex_, vision):
    if vision == "grayscale":
        y = delin(luminance(hex_))
        return to_hex((y, y, y))
    r, g, b = (lin(c) for c in parse_hex(hex_))
    return to_hex(tuple(delin(row[0] * r + row[1] * g + row[2] * b) for row in CVD[vision]))


def distance(a_hex, b_hex):
    return delta_e2000(to_lab(parse_hex(a_hex)), to_lab(parse_hex(b_hex)))


def cbrt(x):
    return math.copysign(abs(x) ** (1 / 3), x)


def to_oklch(hex_):
    r, g, b = (lin(c) for c in parse_hex(hex_))
    l_ = cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
    m_ = cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
    s_ = cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return L, math.hypot(a, bb), math.degrees(math.atan2(bb, a)) % 360


def from_oklch(L, C, h):
    """OKLCH to hex, lowering chroma until the color fits the sRGB gamut."""
    while True:
        a, b = C * math.cos(math.radians(h)), C * math.sin(math.radians(h))
        l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
        m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
        s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
        rgb_lin = (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
                   -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
                   -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)
        if all(-1e-4 <= c <= 1 + 1e-4 for c in rgb_lin) or C <= 0:
            return to_hex(tuple(delin(c) for c in rgb_lin))
        C = max(0, C - 0.002)


def suggest(change_hex, against_hex, target):
    """Closest lightness change to change_hex (same hue) that reaches target contrast with against_hex."""
    L0, C, h = to_oklch(change_hex)
    best = None
    for direction in (-1, 1):
        for step in range(1, 201):
            L = L0 + direction * step * 0.005
            if not 0 <= L <= 1:
                break
            cand = from_oklch(L, C, h)
            ratio = contrast(cand, against_hex)
            if ratio >= target:
                if best is None or step < best[0]:
                    best = (step, cand, ratio)
                break
    return (best[1], floor2(best[2])) if best else (None, None)


def deepen(hex_, amount):
    L, C, h = to_oklch(hex_)
    return from_oklch(max(0, L - amount), C, h)


# ---------- loading ----------

def load_palette(path):
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"can't read {path}: {e}")
    problems = []

    def hexes(where, obj, keys):
        for k in keys:
            try:
                obj[k] = to_hex(parse_hex(obj[k]))
            except (KeyError, TypeError):
                problems.append(f"{where}: missing {k}")
            except ValueError as e:
                problems.append(f"{where}.{k}: {e}")

    brand = data.get("brand")
    if not isinstance(brand, list) or not 1 <= len(brand) <= MAX_BRAND:
        problems.append(f'"brand" must be a list of 1 to {MAX_BRAND} colors')
        brand = []
    seen = set()
    for i, b in enumerate(brand):
        key = b.get("key", "")
        where = f"brand[{i}] {key or ''}".strip()
        if not KEY_RE.match(key) or key in seen or key in NEUTRAL_CSS.values():
            problems.append(f"{where}: key must be unique, lowercase letters, digits and hyphens")
        seen.add(key)
        for field in ("name", "usage"):
            if not b.get(field):
                problems.append(f"{where}: missing {field}")
        for mode in MODES:
            if not isinstance(b.get(mode), dict):
                problems.append(f"{where}: missing {mode} steps")
            else:
                hexes(f"{where}.{mode}", b[mode], STEPS)

    neutrals = data.get("neutrals")
    if not isinstance(neutrals, dict):
        problems.append('"neutrals" must be an object with text, muted, line and page')
        neutrals = {}
    for job, default_label in NEUTRALS:
        n = neutrals.get(job)
        if not isinstance(n, dict):
            problems.append(f"neutrals: missing {job}")
            continue
        n.setdefault("label", default_label)
        hexes(f"neutrals.{job}", n, MODES)

    seeds = data.get("seeds") or []
    if len(seeds) > 4:
        problems.append("use at most 4 seed colors")
    try:
        data["seeds"] = [to_hex(parse_hex(s)) for s in seeds]
    except ValueError as e:
        problems.append(f"seeds: {e}")

    notes = []
    for n in data.get("notes") or []:
        if isinstance(n, str):
            notes.append({"mode": "both", "text": n})
        elif isinstance(n, dict) and n.get("text") and n.get("mode", "both") in ("light", "dark", "both"):
            notes.append({"mode": n.get("mode", "both"), "text": n["text"]})
        else:
            problems.append(f"notes: can't read {n!r}")
    data["notes"] = notes

    if problems:
        raise ValueError("; ".join(problems))
    data.setdefault("name", "Brand")
    return data


# ---------- checks ----------

def join(items):
    items = list(items)
    if len(items) <= 2:
        return " and ".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def check(palette):
    brand, neutrals = palette["brand"], palette["neutrals"]
    report = {"modes": {}, "fails": []}

    for mode in MODES:
        names = STEP_NAMES[mode]
        N = {job: neutrals[job][mode] for job, _ in NEUTRALS}
        darkest = min(N.values(), key=luminance)
        # Button text: white on light-mode brand colors, the darkest neutral on dark-mode ones.
        if mode == "light":
            main_text, main_word, alt_text, alt_word = WHITE, "white text", darkest, "your darkest neutral"
        else:
            main_text, main_word, alt_text, alt_word = darkest, "dark text", WHITE, "white text"

        rows, fails = [], []

        def row(fg, bg, fg_name, bg_name, use, level, required):
            ratio = contrast(fg, bg)
            need = TEXT_AA if level == "text" else UI_AA
            entry = {"mode": mode, "fg_hex": fg, "bg_hex": bg, "fg_name": fg_name, "bg_name": bg_name,
                     "use": use, "level": level, "required": required, "ratio": floor2(ratio), "need": need,
                     "aa": ratio >= need, "aaa": (ratio >= TEXT_AAA) if level == "text" else None}
            if required and not entry["aa"]:
                hex_, sr = suggest(fg, bg, need)
                entry["suggest"], entry["suggest_ratio"] = hex_, sr
                fix = f" Try {hex_} for the {fg_name.lower()} ({about(sr)}, same hue)." if hex_ else ""
                fails.append(f"{mode.title()} mode: {fg_name} on {bg_name.lower()} is {floor2(ratio):.2f}:1; "
                             f"{use} needs {need}:1.{fix}")
            rows.append(entry)
            return entry

        text_page = row(N["text"], N["page"], "Body text", "Page background", "body text", "text", True)
        row(N["muted"], N["page"], "Secondary text", "Page background", "body text", "text", True)
        placeholder = row(N["line"], N["page"], "Border grey", "Page background", "placeholder text", "text", False)
        outline = row(N["line"], N["page"], "Border grey", "Page background", "input outlines", "ui", False)

        per_brand = {}
        for b in brand:
            s = b[mode]
            nm = b["name"]
            strong_name = f"{names['strong']} {nm.lower()}"
            soft_name = f"{names['soft']} {nm.lower()}"
            row(N["text"], s["surface"], "Body text", f"{nm} surface", "body text", "text", True)
            row(N["muted"], s["surface"], "Secondary text", f"{nm} surface", "body text", "text", True)
            row(N["text"], s["soft"], "Body text", soft_name, "tag text", "text", True)
            main_base = row(main_text, s["base"], main_word.capitalize(), nm, "button text", "text", False)
            alt_base = row(alt_text, s["base"], alt_word.capitalize(), nm, "button text", "text", False)
            main_strong = row(main_text, s["strong"], main_word.capitalize(), strong_name, "button text", "text", False)
            fill = row(s["soft"], N["page"], soft_name, "Page background", "chart fills", "ui", False)
            row(s["base"], N["page"], nm, "Page background", "colored text", "text", False)
            strong_text = row(s["strong"], N["page"], strong_name, "Page background", "colored text", "text", False)
            per_brand[b["key"]] = {"main_base": main_base, "alt_base": alt_base, "main_strong": main_strong,
                                   "fill": fill, "strong_text": strong_text}
            if not (main_base["aa"] or alt_base["aa"] or main_strong["aa"]):
                hex_, sr = suggest(s["strong"], main_text, TEXT_AA)
                fails.append(f"{mode.title()} mode: no text color reaches 4.5:1 on {nm} ({main_word} "
                             f"{about(main_base['ratio'])}, {alt_word} {about(alt_base['ratio'])}, {main_word} on "
                             f"{strong_name} {about(main_strong['ratio'])})."
                             + (f" Try {hex_} for the {strong_name} ({about(sr)} with {main_word})." if hex_ else ""))

        # Color vision: brand colors and their chart fills need to stay apart.
        cvd_rows, cvd_notes = [], []
        for step in ("base", "soft"):
            alike, everyone = [], []
            for i, a in enumerate(brand):
                for b in brand[i + 1:]:
                    ha, hb = a[mode][step], b[mode][step]
                    close = []
                    for vision in list(CVD) + ["grayscale"]:
                        de = distance(simulate(ha, vision), simulate(hb, vision))
                        cvd_rows.append({"step": step, "a": a["key"], "b": b["key"], "vision": vision,
                                         "delta_e": round(de, 1), "close": de < TOO_CLOSE})
                        if de < TOO_CLOSE and vision in CVD:
                            close.append(vision)
                    pair = f"{a['name'].lower()}/{b['name'].lower()}"
                    if distance(ha, hb) < TOO_CLOSE:
                        everyone.append(pair)
                    elif close:
                        alike.append(f"{pair} ({join(close)})")
            what = "Brand colors" if step == "base" else f"{names['soft']} chart fills"
            if everyone:
                cvd_notes.append(f"{what} that look alike for everyone: {join(everyone)}. Move them further apart in lightness.")
            if alike:
                fix = ("Don't let color alone tell them apart; add labels or icons." if step == "base"
                       else "Label chart series directly or add patterns.")
                cvd_notes.append(f"{what} that look alike with color blindness: {'; '.join(alike)}. {fix}")

        # ---- the notes column, in the voice of the board ----
        sections = []
        if fails:
            sections.append({"heading": "Must fix:", "items": fails})

        def pct_range(sign):
            diffs = []
            for b in brand:
                lb, ls = to_oklch(b[mode]["base"])[0], to_oklch(b[mode]["strong"])[0]
                diffs.append(round(sign * (lb - ls) * 100 / 5) * 5)  # OKLCH lightness points
            lo, hi = min(diffs), max(diffs)
            return f"{lo}%" if lo == hi else f"{lo}–{hi}%"

        rescue = [b["name"].lower() for b in brand
                  if not per_brand[b["key"]]["main_base"]["aa"] and per_brand[b["key"]]["main_strong"]["aa"]]
        if mode == "light":
            strong_line = (f"{names['strong']} is about {pct_range(1)} darker than its base, with the same hue. "
                           f"Use it for hover and pressed states")
        else:
            strong_line = (f"{names['strong']} is about {pct_range(-1)} lighter than its base, with the same hue. "
                           f"Use it for hover and pressed states")
            if all(per_brand[b["key"]]["strong_text"]["aa"] for b in brand):
                strong_line += ", colored text and icons"
        strong_line += f", and behind {main_word} on {join(rescue)}." if rescue else "."
        sections.append({"heading": "What each step is for:", "items": [
            strong_line,
            f"{names['soft']} is for chart fills, tags and borders.",
            "Surface is for tinted card and section backgrounds.",
        ]})

        contrast_items, passing = [], []
        for b in brand:
            pb = per_brand[b["key"]]
            r = pb["main_base"]["ratio"]
            strong_name = f"{names['strong']} {b['name'].lower()}"
            strong_hex, rs = b[mode]["strong"], pb["main_strong"]["ratio"]
            if pb["main_base"]["aa"]:
                passing.append((b["name"], r))
            elif r >= UI_AA:
                if pb["main_strong"]["aa"]:
                    tail = f", or use the {strong_name} ({strong_hex}, about {about(rs)}) for buttons."
                elif pb["alt_base"]["aa"]:
                    tail = f", or put {alt_word} on it (about {about(pb['alt_base']['ratio'])})."
                else:
                    tail = "."
                contrast_items.append(f"{b['name']}: {main_word} is only about {about(r)}. Use it for large text "
                                      f"or icons only{tail}")
            else:
                parts = []
                if pb["alt_base"]["aa"]:
                    parts.append(f"put {alt_word} on it for text")
                if pb["main_strong"]["aa"]:
                    parts.append(f"use the {strong_name} ({strong_hex}, about {about(rs)}) when you need {main_word}")
                advice = (", or ".join(parts) + ".") if parts else "use it for decoration only."
                contrast_items.append(f"{b['name']}: {main_word} fails at about {about(r)}. {advice[0].upper()}{advice[1:]}")
        if passing:
            who = join([passing[0][0]] + [n.lower() for n, _ in passing[1:]])
            how = "passes easily" if all(r >= TEXT_AAA for _, r in passing) else "passes"
            contrast_items.insert(0, f"{who}: {main_word} {how}, at about {join(about(r) for _, r in passing)}.")
        sections.append({"heading": "Text contrast to keep in mind:", "items": contrast_items})

        sections.append({"heading": "Color blindness:", "items": cvd_notes or [
            "All brand colors and chart fills stay distinct with protanopia, deuteranopia and tritanopia."]})

        watch = []
        if not placeholder["aa"]:
            line = (f"The border grey is about {about(placeholder['ratio'])} on the page. That's fine for dividers and "
                    f"disabled states, but placeholder text needs 4.5:1, so use the secondary text grey for placeholders")
            line += " and input outlines." if not outline["aa"] else "."
            watch.append(line)
        low_fills = [b["name"].lower() for b in brand if not per_brand[b["key"]]["fill"]["aa"]]
        if low_fills:
            watch.append(f"The {names['soft'].lower()} {join(low_fills)} fills are under 3:1 against the page. When a chart "
                         f"relies on them, add a darker outline or direct labels.")
        if mode == "dark" and text_page["ratio"] > HALATION:
            watch.append(f"Body text is about {about(text_page['ratio'])} on the page. Very bright text on a very dark "
                         f"background can blur for readers with astigmatism; a slightly softer text grey helps.")
        if watch:
            sections.append({"heading": "Also watch:", "items": watch})

        extra = [n["text"] for n in palette["notes"] if n["mode"] in (mode, "both")]

        sim = {v: {f"{b['key']}-{step}": simulate(b[mode][step], v) for b in brand for step in ("base", "soft")}
               for v in list(CVD) + ["grayscale"]}
        report["modes"][mode] = {"pairs": rows, "cvd": cvd_rows, "sections": sections, "notes": extra,
                                 "simulated": sim, "cvd_warnings": sum(1 for r in cvd_rows if r["close"] and r["vision"] in CVD)}
        report["fails"] += fails

    required = [p for m in MODES for p in report["modes"][m]["pairs"] if p["required"]]
    report["counts"] = {
        "pairs": len(required),
        "aa_pass": sum(p["aa"] for p in required),
        "aaa_pass": sum(bool(p["aaa"]) for p in required),
        "cvd_warnings": sum(report["modes"][m]["cvd_warnings"] for m in MODES),
    }
    report["ok"] = not report["fails"]
    return report


# ---------- output ----------

def print_summary(palette, report, show_all):
    print(f"Palette: {palette['name']}")
    for mode in MODES:
        m = report["modes"][mode]
        print(f"\n== {mode.upper()} MODE ==")
        if show_all:
            for p in m["pairs"]:
                status = ("AAA " if p["aaa"] else "AA  ") if p["aa"] else ("FAIL" if p["required"] else "note")
                print(f"  {status} {p['fg_name']} {p['fg_hex']} on {p['bg_name']} {p['bg_hex']}".ljust(74)
                      + f"{p['ratio']:.2f}:1  ({p['use']}{', required' if p['required'] else ''})")
            print()
        for s in m["sections"]:
            print(s["heading"])
            for item in s["items"]:
                print(f"  • {item}")
        for n in m["notes"]:
            print(n)
    c = report["counts"]
    print(f"\n{c['aa_pass']}/{c['pairs']} required pairs pass AA; {c['aaa_pass']} of them also pass AAA; "
          f"{c['cvd_warnings']} color-blindness notes.")
    print("OK: ready for the board." if report["ok"] else "Fix the 'Must fix' items, then run this again.")


def css_tokens(palette):
    def decls(mode, indent):
        out = []
        for b in palette["brand"]:
            for step in STEPS:
                suffix = "" if step == "base" else f"-{step}"
                out.append(f"--{b['key']}{suffix}: {b[mode][step]};")
        for job, _ in NEUTRALS:
            out.append(f"--{NEUTRAL_CSS[job]}: {palette['neutrals'][job][mode]};")
        return "\n".join(indent + d for d in out)

    return (":root {\n" + decls("light", "  ") + "\n}\n"
            "@media (prefers-color-scheme: dark) {\n  :root:not([data-theme=\"light\"]) {\n"
            + decls("dark", "    ") + "\n    color-scheme: dark;\n  }\n}\n"
            ":root[data-theme=\"dark\"] {\n" + decls("dark", "  ") + "\n  color-scheme: dark;\n}")


def chrome_css(palette):
    """Tokens for the page around the boards, drawn from the palette's own neutrals."""
    n, first = palette["neutrals"], palette["brand"][0]
    canvas = {"light": WHITE, "dark": deepen(n["page"]["dark"], 0.035)}

    def decls(mode):
        return (f"--c-bg: {canvas[mode]}; --c-fg: {n['text'][mode]}; --c-muted: {n['muted'][mode]}; "
                f"--c-line: {n['page'][mode] if mode == 'light' else n['line'][mode]}; --c-panel: {n['page'][mode]}; "
                f"--c-focus: {first[mode]['base']}")
    css = (f":root {{ {decls('light')} }}\n"
           f"@media (prefers-color-scheme: dark) {{ :root:not([data-theme=\"light\"]) {{ {decls('dark')}; color-scheme: dark }} }}\n"
           f":root[data-theme=\"dark\"] {{ {decls('dark')}; color-scheme: dark }}")
    return css, canvas


def write_html(palette, report, out):
    template = (Path(__file__).resolve().parent.parent / "references" / "page-template.html").read_text()
    css, canvas = chrome_css(palette)
    data = {
        "name": palette["name"],
        "description": palette.get("description", ""),
        "seeds": palette["seeds"],
        "brand": palette["brand"],
        "neutrals": [{"job": job, **palette["neutrals"][job]} for job, _ in NEUTRALS],
        "stepNames": STEP_NAMES,
        "canvas": canvas,
        "visionNotes": VISION_NOTES,
        "report": report,
        "css": css_tokens(palette),
    }
    payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    page = (template.replace("__TITLE__", html.escape(palette["name"]))
            .replace("/*__THEME_CSS__*/", css)
            .replace("__DATA_JSON__", payload))
    Path(out).write_text(page)
    print(f"Wrote {out}")


def main():
    ap = argparse.ArgumentParser(description="Check a brand palette for WCAG contrast and color-vision problems.")
    ap.add_argument("palette", nargs="?", help="palette JSON file")
    ap.add_argument("--all", action="store_true", help="also list every checked pair")
    ap.add_argument("--json", action="store_true", help="print the full report as JSON")
    ap.add_argument("--html", metavar="OUT", help="write the swatch board to OUT")
    ap.add_argument("--allow-failures", action="store_true", help="write the board even if required pairs fail")
    ap.add_argument("--pair", nargs=2, metavar=("FG", "BG"), help="contrast of a single pair")
    args = ap.parse_args()

    if args.pair:
        try:
            fg, bg = (to_hex(parse_hex(x)) for x in args.pair)
        except ValueError as e:
            print(e, file=sys.stderr)
            return 2
        r = contrast(fg, bg)
        verdict = "AAA" if r >= 7 else "AA" if r >= 4.5 else "AA large text/UI only" if r >= 3 else "fails"
        print(f"{fg} on {bg}: {floor2(r):.2f}:1 ({verdict})")
        return 0
    if not args.palette:
        ap.error("give a palette file or --pair FG BG")

    try:
        palette = load_palette(args.palette)
    except ValueError as e:
        print(f"Bad palette: {e}", file=sys.stderr)
        return 2
    report = check(palette)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_summary(palette, report, args.all)

    if args.html:
        if not report["ok"] and not args.allow_failures:
            print("Not writing the board: fix the 'Must fix' items first (or pass --allow-failures).", file=sys.stderr)
            return 1
        write_html(palette, report, args.html)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
