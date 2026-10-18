#!/usr/bin/env python3
"""Build a brand reference page from a checked palette and a brand spec.

The palette is a brand-palette JSON file (see ../../brand-palette/references/palette-format.md).
The spec holds the words: the brand story, motifs, personality, type, layout, the signature
move and the sample copy (see references/brand-spec.md). Everything with a number in it is
measured here, reusing brand-palette's checker:

  - three extra surfaces (card, raised, divider) derived from the palette's page and border grey
  - an error red for status, tuned to pass in both modes
  - chart steps: mid-tone marks for each chart series, at least 3:1 on page and card, spread
    apart in lightness so they stay distinct under simulated color blindness
  - a 10-step sequential ramp for heatmaps
  - the contrast table, the stats and the accessibility notes

Usage:
  python3 build_brand.py brand.json --out brand.html   # build the page
  python3 build_brand.py brand.json --check            # print the measurements only

Exit codes: 0 built, 1 the palette fails a required pair, 2 bad input.
Standard library only.
"""
import argparse
import html
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "brand-palette" / "scripts"))
import check_palette as cp  # noqa: E402

MODES = cp.MODES
WHITE = cp.WHITE
VISIONS = ["normal", "protanopia", "deuteranopia", "tritanopia"]
CHART_L = (0.48, 0.67)      # OKLCH lightness range for chart marks
CHART_MIN_C = 0.10          # chart marks need some color to read as a series
ERROR_HUE = 27              # brick red
SPACING = [4, 8, 12, 16, 24, 32, 48, 64]
FALLBACKS = {
    "display": 'ui-serif, Georgia, serif',
    "ui": 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif',
    "mono": "ui-monospace, SFMono-Regular, Menlo, monospace",
}
ROLES = ["primary", "accent", "highlight", "data"]

DEFAULT_SAMPLES = {
    "kpis": [
        {"label": "Active projects", "value": "24", "delta": "+12%", "up": True},
        {"label": "Failed runs", "value": "3", "delta": "−40%", "up": False},
    ],
    "tabs": ["Overview", "Research", "Pipelines", "Handoff"],
    "segments": ["Weekly", "Monthly"],
    "buttons": {"primary": "Get started", "secondary": "Learn more", "accent": "Book a call", "danger": "Delete"},
    "input": {"label": "Work email", "placeholder": "you@company.com",
              "help": "We reply within two working days.", "error": "Enter an email address with an @."},
    "notices": {"info": "New data arrives every hour.",
                "highlight": "This is the one thing to notice on this page.",
                "error": "Sync failed. Check the connection, then try again."},
    "rows": [["First item", "done"], ["Second item", "hover"], ["Third item", "selected"]],
    "progress": 62,
}
DEFAULT_ALWAYS = [
    "Pair the error red with an icon and a word (\"Sync failed\"), never color alone.",
    "Keep a legend or direct labels on any chart with two or more series.",
    "Focus rings: a 2px outline in the primary text color, 2px offset.",
    "Respect prefers-reduced-motion for any animation.",
]


# ---------- color helpers ----------

def lch(L, C, h):
    return cp.from_oklch(min(1, max(0, L)), max(0, C), h % 360)


def mix(a, b, t):
    """Mix two colors in OKLab: t=0 is a, t=1 is b."""
    A, B = cp.to_oklab(a), cp.to_oklab(b)
    L, x, y = (A[i] + (B[i] - A[i]) * t for i in range(3))
    return cp.from_oklch(L, math.hypot(x, y), math.degrees(math.atan2(y, x)) % 360)


def ratio(a, b):
    return cp.floor2(cp.contrast(a, b))


def level(r, ui=False):
    if ui:
        return "ui" if r >= cp.UI_AA else "no"
    if r >= cp.TEXT_AAA:
        return "aaa"
    if r >= cp.TEXT_AA:
        return "aa"
    return "ui" if r >= cp.UI_AA else "no"


# ---------- derived colors ----------

def surfaces(pal, hue):
    """Card, raised and divider steps around the palette's page color, per mode."""
    out = {}
    for mode in MODES:
        n = {k: pal["neutrals"][k][mode] for k in ("page", "line", "text", "muted")}
        Lp, Cp, hp = cp.to_oklch(n["page"])
        # follow the page's own hue when it has one (a beige page stays beige), else the primary's
        if Cp >= 0.015:
            hue = hp
        if mode == "light":
            surface = lch(min(0.995, Lp + 0.035), min(Cp * 0.5, 0.03) if Cp >= 0.015 else min(Cp, 0.004), hue)
            raise_by = [-0.035 + i * 0.005 for i in range(7)]   # darker than the page
        else:
            surface = lch(Lp + 0.035, Cp + 0.004, hue)
            raise_by = [0.075 - i * 0.005 for i in range(14)]   # lighter than the page
        raised = None
        for d in raise_by:
            raised = lch(Lp + d, Cp + (0.006 if mode == "dark" else 0), hue)
            # secondary text must stay at AA on every surface
            if cp.contrast(n["muted"], raised) >= cp.TEXT_AA:
                break
        out[mode] = {"surface": surface, "raised": raised, "divider": mix(n["page"], n["line"], 0.45)}
    return out


def on_color(bg, mode, pal):
    """The text color that works on bg: (label, hex, ratio). White or the darkest neutral."""
    dark = pal["neutrals"]["text"]["light"] if mode == "light" else pal["neutrals"]["page"]["dark"]
    cands = [("White text", WHITE), ("Dark text", dark)] if mode == "light" else [("Dark text", dark), ("White text", WHITE)]
    for label, fg in cands:
        if cp.contrast(fg, bg) >= cp.TEXT_AA:
            return label, fg, ratio(fg, bg)
    label, fg = max(cands, key=lambda c: cp.contrast(c[1], bg))
    return label, fg, ratio(fg, bg)


def text_step(b, mode, pal, surf):
    """The step of a brand color that works as colored text: base, then strong, else body text."""
    page, card = pal["neutrals"]["page"][mode], surf[mode]["surface"]
    for step in ("base", "strong"):
        c = b[mode][step]
        if min(cp.contrast(c, page), cp.contrast(c, card), cp.contrast(c, b[mode]["surface"])) >= cp.TEXT_AA:
            return step, c
    return "text", pal["neutrals"]["text"][mode]


def status_error(mode, pal, surf):
    page, card = pal["neutrals"]["page"][mode], surf[mode]["surface"]
    Lp = cp.to_oklch(page)[0]
    if mode == "light":
        for i in range(80):
            L = 0.60 - i * 0.005
            base = lch(L, 0.19, ERROR_HUE)
            if min(cp.contrast(WHITE, base), cp.contrast(base, page), cp.contrast(base, card)) >= cp.TEXT_AA:
                break
        strong, soft, surface, on = lch(L - 0.08, 0.17, ERROR_HUE), lch(0.86, 0.06, ERROR_HUE), lch(0.965, 0.018, ERROR_HUE), WHITE
    else:
        for i in range(60):
            L = 0.66 + i * 0.005
            base = lch(L, 0.15, ERROR_HUE)
            if min(cp.contrast(page, base), cp.contrast(base, card)) >= cp.TEXT_AA:
                break
        strong, soft, surface, on = lch(L + 0.06, 0.12, ERROR_HUE), lch(Lp + 0.14, 0.06, ERROR_HUE), lch(Lp + 0.04, 0.03, ERROR_HUE), page
    return {"base": base, "strong": strong, "soft": soft, "surface": surface, "on": on}


def min_cvd(colors):
    """Smallest ΔEOK between any two colors, per vision type: {vision: (distance, a, b)}."""
    out = {}
    for v in VISIONS:
        worst = (9, None, None)
        for i, (ka, a) in enumerate(colors):
            for kb, b in colors[i + 1:]:
                sa, sb = (a, b) if v == "normal" else (cp.simulate(a, v), cp.simulate(b, v))
                d = cp.distance(sa, sb)
                if d < worst[0]:
                    worst = (d, ka, kb)
        out[v] = worst
    return out


def chart_steps(series, pal, surf):
    """One mark color per chart series and mode, at least 3:1 on page and card. Each series after
    the first takes the lightness that keeps it furthest from the others under every vision type."""
    out = {m: {} for m in MODES}
    by_key = {b["key"]: b for b in pal["brand"]}
    for mode in MODES:
        page, card = pal["neutrals"]["page"][mode], surf[mode]["surface"]
        target = 0.55 if mode == "light" else 0.64
        grid = [CHART_L[0] + i * 0.005 for i in range(int((CHART_L[1] - CHART_L[0]) / 0.005) + 1)]
        chosen = []
        for key in series:
            _, C0, h = cp.to_oklch(by_key[key][mode]["base"])
            C = max(C0, CHART_MIN_C)
            cands = [lch(L, C, h) for L in grid]
            ok = [c for c in cands if min(cp.contrast(c, page), cp.contrast(c, card)) >= cp.UI_AA] or cands

            def score(c):
                sep = min((min_cvd([("a", c), ("b", o)])[v][0] for o in chosen for v in VISIONS), default=1)
                return (round(sep, 3), -abs(cp.to_oklch(c)[0] - target))
            pick = max(ok, key=score)
            chosen.append(pick)
            out[mode][key] = pick
    return out


def ramp(base, mode):
    """10 steps of one hue, low to high. Light mode runs light to dark, dark mode dark to light."""
    _, C0, h = cp.to_oklch(base)
    C = max(0.09, min(C0, 0.14))
    steps = []
    for i in range(10):
        L = 0.30 + i * (0.62 / 9)
        steps.append(lch(L, C * (1 - 0.55 * ((L - 0.6) / 0.32) ** 2), h))
    return steps[::-1] if mode == "light" else steps


# ---------- spec ----------

def load_spec(path):
    path = Path(path)
    try:
        spec = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"can't read {path}: {e}")
    if not spec.get("palette"):
        raise ValueError('spec needs "palette": the path to a brand-palette JSON file')
    pal_path = (path.parent / spec["palette"]).resolve()
    pal = cp.load_palette(pal_path)
    keys = [b["key"] for b in pal["brand"]]
    roles = spec.get("roles") or {}
    for role in ("primary", "accent", "data"):
        if roles.get(role) not in keys:
            raise ValueError(f'roles.{role} must be one of the palette keys: {", ".join(keys)}')
    if roles.get("highlight") not in keys:
        roles["highlight"] = next((k for k in keys if k not in roles.values()), roles["primary"])
    spec["roles"] = roles
    if spec.get("error") and spec["error"] not in keys:
        raise ValueError(f'error must be one of the palette keys: {", ".join(keys)}')
    if spec.get("default_theme", "auto") not in ("auto", "light", "dark"):
        raise ValueError('default_theme must be "auto", "light" or "dark"')
    charts = spec.setdefault("charts", {})
    series = charts.get("series") or [{"key": k, "label": b["usage"]} for k, b in zip(keys, pal["brand"])
                                      if k not in (roles["accent"], spec.get("error"))]
    for s in series:
        if s.get("key") not in keys:
            raise ValueError(f'charts.series: {s.get("key")!r} is not a palette key')
    charts["series"] = series
    charts.setdefault("ramp", roles["data"])
    samples = dict(DEFAULT_SAMPLES)
    samples.update(spec.get("samples") or {})
    spec["samples"] = samples
    spec.setdefault("name", pal["name"])
    return spec, pal, pal_path


# ---------- build ----------

def build(spec, pal):
    report = cp.check(pal)
    roles = spec["roles"]
    by_key = {b["key"]: b for b in pal["brand"]}
    primary_hue = cp.to_oklch(by_key[roles["primary"]]["light"]["base"])[2]
    surf = surfaces(pal, primary_hue)
    N = pal["neutrals"]
    err = {m: status_error(m, pal, surf) for m in MODES}
    if spec.get("error"):
        # a brand color doubles as the error color: its fill (base, or strong when text fails on base)
        eb = by_key[spec["error"]]
        for m in MODES:
            fill = eb[m]["base"] if on_color(eb[m]["base"], m, pal)[2] >= cp.TEXT_AA else eb[m]["strong"]
            err[m] = {"base": fill, "strong": eb[m]["strong"], "soft": eb[m]["soft"], "surface": eb[m]["surface"],
                      "on": on_color(fill, m, pal)[1]}
    series_keys = [s["key"] for s in spec["charts"]["series"]]
    charts = chart_steps(series_keys, pal, surf)
    ramps = {m: ramp(by_key[spec["charts"]["ramp"]][m]["base"], m) for m in MODES}
    # unselected bars are context: the ramp step furthest from the selected color that is still
    # at least 2:1 on the page and quieter than the selected color
    dim = {}
    for m in MODES:
        page = N["page"][m]
        sel = charts[m].get(spec["charts"]["ramp"]) or by_key[spec["charts"]["ramp"]][m]["base"]
        quiet = [c for c in ramps[m] if 2.0 <= cp.contrast(c, page) < cp.contrast(sel, page)]
        dim[m] = max(quiet, key=lambda c: cp.distance(c, sel)) if quiet else ramps[m][4]
    ramp_on = {m: [max((WHITE, N["text"]["light"]), key=lambda fg: cp.contrast(fg, c)) for c in ramps[m]] for m in MODES}

    neutrals = [
        ("page", "Page", N["page"]["light"], N["page"]["dark"], "Page background"),
        ("surface", "Card", surf["light"]["surface"], surf["dark"]["surface"], "Cards, sidebar, inputs"),
        ("raised", "Raised", surf["light"]["raised"], surf["dark"]["raised"], "Hover rows, raised panels"),
        ("divider", "Divider", surf["light"]["divider"], surf["dark"]["divider"], "Row rules, quiet dividers"),
        ("line", "Border", N["line"]["light"], N["line"]["dark"], "Borders, disabled states"),
        ("text-muted", "Secondary", N["muted"]["light"], N["muted"]["dark"], "Captions, icons, labels"),
        ("text", "Text", N["text"]["light"], N["text"]["dark"], "Headings, body text"),
    ]

    brands, tokens_mode = [], {m: {} for m in MODES}
    for b in pal["brand"]:
        entry = {"key": b["key"], "name": b["name"], "usage": b["usage"],
                 "rule": (spec.get("color_rules") or {}).get(b["key"], ""), "modes": {}}
        for m in MODES:
            base_label, base_on, base_r = on_color(b[m]["base"], m, pal)
            # buttons and filled notices sit on the base when text passes there, otherwise on the strong step
            fill_step = "base" if base_r >= cp.TEXT_AA else "strong"
            on_label, on_hex, on_r = on_color(b[m][fill_step], m, pal)
            _, text_hex = text_step(b, m, pal, surf)
            entry["modes"][m] = {**{s: b[m][s] for s in cp.STEPS}, "on": on_hex, "onLabel": on_label, "onRatio": on_r,
                                 "fillStep": fill_step, "baseOn": base_on, "baseOnRatio": base_r,
                                 "stepNames": cp.STEP_NAMES[m]}
            t = tokens_mode[m]
            for s in cp.STEPS:
                t[b["key"] if s == "base" else f'{b["key"]}-{s}'] = b[m][s]
            t[f'{b["key"]}-fill'] = b[m][fill_step]
            t[f'on-{b["key"]}'] = on_hex
            t[f'{b["key"]}-text'] = text_hex
        brands.append(entry)

    for m in MODES:
        t = tokens_mode[m]
        for tok, _, lv, dv, _ in neutrals:
            t[tok] = lv if m == "light" else dv
        for s in ("base", "strong", "soft", "surface"):
            t["error" if s == "base" else f"error-{s}"] = err[m][s]
        t["on-error"] = err[m]["on"]
        for k in series_keys:
            t[f"chart-{k}"] = charts[m][k]
        for i, c in enumerate(ramps[m]):
            t[f"ramp-{i + 1}"] = c
        t["ramp-dim"] = dim[m]

    # contrast table: the pairs the components on this page rely on
    def T(m, tok):
        return tokens_mode[m][tok]
    rows = []

    def row(label, fg_tok, bg_tok, ui=False):
        cells = {}
        for m in MODES:
            fg, bg = T(m, fg_tok), T(m, bg_tok)
            r = ratio(fg, bg)
            cells[m] = {"fg": fg, "bg": bg, "ratio": r, "level": level(r, ui)}
        rows.append({"label": label, "cells": cells})
    row("Body text on page", "text", "page")
    row("Body text on card", "text", "surface")
    row("Body text on raised", "text", "raised")
    row("Secondary text on page", "text-muted", "page")
    row("Secondary text on card", "text-muted", "surface")
    row("Secondary text on raised", "text-muted", "raised")
    p, d = roles["primary"], roles["data"]
    row(f"Links ({by_key[p]['name']} text) on page", f"{p}-text", "page")
    row(f"Info ({by_key[d]['name']} text) on its surface", f"{d}-text", f"{d}-surface")
    for b in pal["brand"]:
        row(f"Button text on {b['name']}", f"on-{b['key']}", f"{b['key']}-fill")
    row(f"Up delta on {by_key[p]['name']} surface", f"{p}-text", f"{p}-surface")
    row("Error text on error surface", "error-strong", "error-surface")
    row("Button text on error", "on-error", "error")
    row("Border on page", "line", "page", ui=True)

    # chart checks
    cvd = {m: min_cvd([(k, charts[m][k]) for k in series_keys]) if len(series_keys) > 1 else {} for m in MODES}
    series_out = []
    for s in spec["charts"]["series"]:
        k = s["key"]
        series_out.append({"key": k, "name": by_key[k]["name"], "label": s.get("label", ""),
                           "modes": {m: {"hex": charts[m][k], "page": ratio(charts[m][k], N["page"][m]),
                                         "card": ratio(charts[m][k], surf[m]["surface"])} for m in MODES}})

    counts = report["counts"]
    passes = [f'All {counts["aa_pass"]} required text pairs reach AA, and {counts["aaa_pass"]} reach AAA.']
    for m in MODES:
        ons = [(e["name"], e["modes"][m]["onRatio"]) for e in brands]
        lo, hi = min(ons, key=lambda x: x[1]), max(ons, key=lambda x: x[1])
        passes.append(f'{m.title()} mode button text: {cp.about(lo[1])} ({lo[0]}) to {cp.about(hi[1])} ({hi[0]}).')
    watch = []
    for m in MODES:
        if cvd[m]:
            v, (dist, a, b) = min(((v, cvd[m][v]) for v in VISIONS if v != "normal"), key=lambda x: x[1][0])
            line = (f"{m.title()} mode chart steps: closest pair is {by_key[a]['name']}/{by_key[b]['name']} "
                    f"under {v}, ΔEOK {dist:.3f}")
            if dist < cp.TOO_CLOSE:
                watch.append(line + f" (under {cp.TOO_CLOSE}). Label those series directly.")
            else:
                passes.append(line + f" (flag under {cp.TOO_CLOSE}).")
        low = [s["name"] for s in series_out if min(s["modes"][m]["page"], s["modes"][m]["card"]) < cp.UI_AA]
        if low:
            watch.append(f"{m.title()} mode: {cp.join(low)} chart marks are under 3:1. Outline them or label directly.")
    # the checker's caveats, with notes that only differ by mode (ratios, step names) said once
    def gist(text):
        return re.sub(r"\d+(\.\d+)?|\b(light|muted|Light|Muted)\b", "#", text)
    notes = {m: [i for sec in report["modes"][m]["sections"] if sec["heading"] in ("Color blindness:", "Also watch:")
                 for i in sec["items"]] for m in MODES}
    # the checker's all-clear lines are passes, not caveats
    for m in MODES:
        for i in [i for i in notes[m] if "stay distinct" in i]:
            notes[m].remove(i)
            line = f"{m.title()} mode: {i}"
            if m == "dark" and f"Light mode: {i}" in passes:
                passes[passes.index(f"Light mode: {i}")] = f"Both modes: {i}"
            else:
                passes.append(line)
    dark_gists = {gist(i): i for i in notes["dark"]}
    for item in notes["light"]:
        if dark_gists.pop(gist(item), None):
            # name the step by its token, not its light-mode name ("The light forest fills" -> "The soft forest fills")
            both = re.sub(r"\b(The )?[Ll]ight ", lambda mt: (mt.group(1) or "") + "soft ", item, count=1)
            watch.append(f"Both modes: {both[0].upper()}{both[1:]}")
        else:
            watch.append(f"Light mode: {item}")
    watch += [f"Dark mode: {i}" for i in dark_gists.values()]
    for b in pal["brand"]:
        modes = [m for m in MODES if tokens_mode[m][f'{b["key"]}-text'] == N["text"][m]]
        if modes:
            watch.append(f'{b["name"]} fails as colored text in {cp.join(modes)} mode, in both steps. '
                         f'Use it as a fill under {cp.join(sorted({e["modes"][m]["onLabel"].lower() for e in brands if e["key"] == b["key"] for m in modes}))}, never as text.')

    t = spec.get("type") or {}
    fonts = {
        "display": t.get("display") or t.get("ui") or {"family": "Inter", "weights": [400, 600, 700]},
        "ui": t.get("ui") or {"family": "Inter", "weights": [400, 600, 700]},
        "mono": t.get("mono") or {"family": "JetBrains Mono", "weights": [400, 500]},
    }
    layout = spec.get("layout") or {}
    spacing = layout.get("spacing") or SPACING
    radius = layout.get("radius", "0.5rem")

    css = css_tokens(tokens_mode, roles, fonts, radius, spacing, spec["charts"]["ramp"])
    stats = [[str(len(pal["brand"])), "brand colors"], ["7", "neutrals"], ["10", "ramp steps"],
             [f'{counts["aa_pass"]}/{counts["pairs"]}', "text pairs pass AA"]]
    if spec.get("stat"):
        stats.append(spec["stat"])

    return {
        "spec": spec, "roles": roles, "neutrals": [{"token": a, "name": b, "light": c, "dark": d_, "use": e} for a, b, c, d_, e in neutrals],
        "brands": brands, "contrast": rows, "series": series_out, "ramp": {m: ramps[m] for m in MODES},
        "rampFrom": by_key[spec["charts"]["ramp"]]["name"],
        "rampFirst": {m: ratio(ramps[m][0], N["page"][m]) for m in MODES},
        "rampOn": ramp_on, "dimRatio": {m: ratio(dim[m], N["page"][m]) for m in MODES},
        "error": err, "passes": passes, "watch": watch, "always": spec.get("always") or DEFAULT_ALWAYS,
        "stats": stats, "spacing": spacing, "radius": radius, "fonts": fonts, "css": css,
        "counts": counts, "paletteName": pal["name"],
    }


def css_tokens(tokens_mode, roles, fonts, radius, spacing, ramp_key):
    def block(m, indent):
        pad = " " * indent
        t = tokens_mode[m]
        groups = [
            ("Surfaces and text", ["page", "surface", "raised", "divider", "line", "text-muted", "text"]),
            ("Brand colors: base, strong (hover), soft (tags, fills), surface (tinted cards), "
             "fill (button background: base, or strong when text fails on base), on- (text on fill), -text (as colored text)",
             [k for k in t if not k.startswith(("chart-", "ramp-", "error")) and k not in ("page", "surface", "raised", "divider", "line", "text-muted", "text") and not k.startswith("on-error")]),
            ("Status", ["error", "error-strong", "error-soft", "error-surface", "on-error"]),
            ("Chart marks and the sequential ramp", [k for k in t if k.startswith(("chart-", "ramp-"))]),
        ]
        out = []
        for title, keys in groups:
            out.append(f"{pad}/* {title} */")
            out += [f"{pad}--{k}: {t[k]};" for k in keys]
        return out

    def fam(slot):
        f = fonts[slot]
        return f'"{f["family"]}", {f.get("fallback") or FALLBACKS[slot]}'
    lines = [":root {"]
    lines += block("light", 2)
    lines.append("  /* Roles: components use these, so a role can move to another brand color in one place */")
    for role in ROLES:
        k = roles[role]
        for suffix in ("", "-strong", "-soft", "-surface", "-fill", "-text"):
            lines.append(f"  --{role}{suffix}: var(--{k}{suffix});")
        lines.append(f"  --on-{role}: var(--on-{k});")
    lines += ["  /* Type, shape, space */",
              f"  --font-display: {fam('display')};",
              f"  --font: {fam('ui')};",
              f"  --mono: {fam('mono')};",
              f"  --radius: {radius};"]
    lines += [f"  --space-{i + 1}: {s}px;" for i, s in enumerate(spacing)]
    lines += ["  color-scheme: light;", "}"]
    dark = block("dark", 4)
    lines += ["@media (prefers-color-scheme: dark) {", '  :root:not([data-theme="light"]) {']
    lines += dark + ["    color-scheme: dark;", "  }", "}"]
    lines += [':root[data-theme="dark"] {'] + [l[2:] for l in dark] + ["  color-scheme: dark;", "}"]
    return "\n".join(lines)


def google_fonts(fonts):
    seen, fams = set(), []
    for f in fonts.values():
        if f.get("google") is False or f["family"] in seen:
            continue
        seen.add(f["family"])
        weights = sorted({int(w) for v in fonts.values() if v["family"] == f["family"] for w in v.get("weights", [400])})
        fams.append("family=" + f["family"].replace(" ", "+") + ":wght@" + ";".join(map(str, weights)))
    if not fams:
        return ""
    return ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?{"&".join(fams)}&display=swap">')


def write_html(data, out):
    tpl = (HERE.parent / "references" / "brand-template.html").read_text()
    spec = data["spec"]
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    page = (tpl.replace("__TITLE__", html.escape(spec.get("title") or f'{spec["name"]} Brand'))
               .replace("__FONTS__", google_fonts(data["fonts"]))
               .replace("/*__TOKENS__*/", data["css"])
               .replace("/*__SIGNATURE_CSS__*/", (spec.get("signature") or {}).get("css", ""))
               .replace("__DATA__", payload))
    Path(out).write_text(page)


def print_check(data):
    print(f'Brand: {data["spec"]["name"]}  (palette: {data["paletteName"]})')
    for m in MODES:
        print(f"\n== {m.upper()} ==")
        for n in data["neutrals"]:
            print(f'  {n["name"]:<10} {n[m]}')
        print(f'  error      {data["error"][m]["base"]} (strong {data["error"][m]["strong"]}, surface {data["error"][m]["surface"]})')
        for s in data["series"]:
            sm = s["modes"][m]
            print(f'  chart {s["key"]:<10} {sm["hex"]}  {sm["page"]}:1 on page, {sm["card"]}:1 on card')
        print("  ramp       " + " ".join(data["ramp"][m]))
    print("\nContrast:")
    for r in data["contrast"]:
        c = r["cells"]
        print(f'  {r["label"]:<44} light {c["light"]["ratio"]:>5}:1 {c["light"]["level"]:<4} dark {c["dark"]["ratio"]:>5}:1 {c["dark"]["level"]}')
    print("\nPasses:")
    for p in data["passes"]:
        print("  • " + p)
    print("Watch:")
    for w in data["watch"]:
        print("  • " + w)


def main():
    ap = argparse.ArgumentParser(description="Build a brand reference page from a palette and a brand spec.")
    ap.add_argument("spec", help="brand spec JSON (see references/brand-spec.md)")
    ap.add_argument("--out", help="where to write the HTML page")
    ap.add_argument("--check", action="store_true", help="print the measurements and stop")
    args = ap.parse_args()
    try:
        spec, pal, _ = load_spec(args.spec)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    data = build(spec, pal)
    print_check(data)
    if data["counts"]["aa_pass"] < data["counts"]["pairs"]:
        print("\nThe palette fails a required pair. Fix it with brand-palette's check_palette.py first.", file=sys.stderr)
        return 1
    if args.out and not args.check:
        write_html(data, args.out)
        print(f"\nWrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
