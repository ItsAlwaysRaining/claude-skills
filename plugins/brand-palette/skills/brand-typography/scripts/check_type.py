#!/usr/bin/env python3
"""Check brand typography options against readability standards and build a specimen page.

The type spec (see references/type-spec.md) holds 1–3 options, each with its fonts (display, ui,
mono) and a type scale. This script fetches every font, measures it (fonts.py), and checks each
option against:

  - Licence, language support and weights: can the brand use it, in its languages, at its weights?
  - WCAG 2.2: 1.4.3 contrast, 1.4.4 resize text, 1.4.8 visual presentation (AAA), 1.4.12 text spacing
  - APCA (WCAG 3 draft): the minimum font size for each scale row's weight and contrast (apca.py)
  - The British Dyslexia Association's Dyslexia Style Guide (2023)
  - Legibility: x-height, confusable letters, apertures, tabular figures, zero

Colors come from a brand-palette JSON when the spec names one, otherwise from a greyscale default.

Usage:
  python3 check_type.py type.json                      # print the checks
  python3 check_type.py type.json --out type.html      # build the specimen page
  python3 check_type.py type.json --brand-type b --fonts-dir <dir>
                                                       # print option b as brand-builder's "type" block
  python3 check_type.py --font "Inter"                 # measure one font (add --source fontshare)

Exit codes: 0 no failures, 1 an option has a failing check, 2 bad input.
Standard library only; Pillow, if installed, adds the glyph-shape checks.
"""
import argparse
import html
import json
import math
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "brand-palette" / "scripts"))
import apca as apca_mod  # noqa: E402
import fonts as F  # noqa: E402
import check_palette as cp  # noqa: E402

MODES = ["light", "dark"]
CACHE = Path.home() / ".cache" / "brand-typography"
GREYSCALE = {
    "name": "Greyscale",
    "neutrals": {"text": {"light": "#1C1C1C", "dark": "#E8E8E8"}, "muted": {"light": "#525252", "dark": "#B8B8B8"},
                 "line": {"light": "#949494", "dark": "#5A5A5A"}, "page": {"light": "#FFFFFF", "dark": "#161616"}},
    "brand": [{"key": "ink", "name": "Ink", "light": {"base": "#1C1C1C", "strong": "#000000", "soft": "#BDBDBD", "surface": "#F2F2F2"},
               "dark": {"base": "#E8E8E8", "strong": "#FFFFFF", "soft": "#4A4A4A", "surface": "#222222"}}],
}
SLOTS = ["display", "ui", "mono"]
GROUPS = ["Licence", "Languages", "Weights", "WCAG 2.2", "APCA", "BDA", "Legibility"]
FALLBACK = {"sans": 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif', "serif": "ui-serif, Georgia, serif",
            "mono": "ui-monospace, SFMono-Regular, Menlo, monospace", "display": "ui-sans-serif, system-ui, sans-serif",
            "script": "cursive"}
LIKE = 0.80          # glyph likeness at or above this is hard to tell apart
MIRROR = 0.95        # b/d or p/q this close to a perfect mirror is flagged
APERTURE = 0.30      # c opening under this share of its height reads as closed
XH_PX = 8.0          # body x-height in px below this is small
BDA_LETTER = 0.35    # BDA: letter spacing about 35% of the average letter width
BDA_WORD = 3.5       # BDA: word spacing at least 3.5 times the letter spacing
BODY_LC = 75         # APCA bronze: body text needs Lc 75 at least (90 preferred)

DEFAULT_SAMPLES = {
    "headline": "Make the complicated feel simple",
    "paragraph": ["Good type disappears. Readers notice the ideas, not the letters, and they keep reading because "
                  "nothing gets in the way.",
                  "This paragraph is set at the body size, line height and measure of the scale, so it shows how a long "
                  "page will feel."],
    "nav": ["Overview", "Work", "Journal", "Contact"],
    "buttons": ["Get started", "Learn more"],
    "input": {"label": "Work email", "placeholder": "you@company.com", "help": "We reply within two working days."},
    "doc": {"title": "Annual review", "subtitle": "What changed this year, and why", "quote": "The best systems are the ones people actually use.",
            "caption": "Figure 1 · Projects by quarter"},
    "card": {"name": "Alex Morgan", "role": "Founder", "contact": "hello@example.com · +44 20 7946 0000"},
    "table": {"caption": "Example data · monthly totals", "columns": ["Month", "Orders", "Revenue", "Change"],
              "rows": [["January", "1,204", "£48,160.00", "+4.2%"], ["February", "1,118", "£44,720.50", "−7.1%"],
                       ["March", "1,391", "£55,640.25", "+24.4%"], ["April", "1,011", "£40,440.10", "−27.3%"]]},
    "chart": {"title": "Orders by month", "bars": [["Jan", 1204], ["Feb", 1118], ["Mar", 1391], ["Apr", 1011]]},
}


# ---------- loading ----------

def load(path):
    p = Path(path)
    spec = json.loads(p.read_text())
    if not spec.get("options"):
        raise ValueError("the spec needs an options list with 1–3 options")
    if "palette" in spec:
        pal = json.loads((p.parent / spec["palette"]).read_text())
        pal["_source"] = spec["palette"]
    else:
        pal = dict(GREYSCALE, _source=None)
    for o in spec["options"]:
        if "ui" not in o.get("fonts", {}):
            raise ValueError(f'option {o.get("id")} needs at least a "ui" font')
        if not o.get("scale"):
            raise ValueError(f'option {o.get("id")} needs a scale')
    return spec, pal, p.parent


def px(size):
    m = re.fullmatch(r"\s*([\d.]+)\s*(px|rem|em|pt)?\s*", str(size))
    if not m:
        raise ValueError(f"can't read the size {size!r}")
    v, unit = float(m.group(1)), m.group(2) or "px"
    return {"px": v, "rem": v * 16, "em": v * 16, "pt": v * 4 / 3}[unit]


def em(value):
    """letter-spacing / word-spacing value in em (0 when unset)."""
    if not value:
        return 0.0
    m = re.fullmatch(r"\s*(-?[\d.]+)\s*(em|px)?\s*", str(value))
    v = float(m.group(1))
    return v / 16 if m.group(2) == "px" else v


def colors(pal, primary_key, fill=None):
    """Per mode: the text colors and backgrounds the checks use. `fill` picks the primary step
    buttons sit on in each mode ({"dark": "strong"}), like brand-builder's -fill token."""
    N = pal["neutrals"]
    brand = {b["key"]: b for b in pal["brand"]}
    prim = brand.get(primary_key) or pal["brand"][0]
    out = {}
    for m in MODES:
        base = prim[m][(fill or {}).get(m, "base")]
        on = max([N["page"][m], N["text"][m], "#FFFFFF"], key=lambda c: cp.contrast(c, base))
        out[m] = {
            "fg": {"text": N["text"][m], "muted": N["muted"][m], "primary": base, "on-primary": on},
            "bg": {"page": N["page"][m], "card": prim[m]["surface"]},
            "fill": {"primary": base},
            "line": N["line"][m], "soft": prim[m]["soft"],
        }
    return out, prim


# ---------- checks ----------

def row(group, check, standard, status, detail, fix=None):
    return {"group": group, "check": check, "standard": standard, "status": status, "detail": detail, "fix": fix}


def pairs_for(r, C, m):
    """(fg, bg, label) combinations a scale row is read on in mode m."""
    c = r.get("color", "muted" if r.get("muted") else "text")
    if c == "on-primary":
        return [(C[m]["fg"]["on-primary"], C[m]["fill"]["primary"], "primary fill")]
    return [(C[m]["fg"][c], bg, name) for name, bg in C[m]["bg"].items()]


def check_option(o, measured, spec, C):
    out = []
    langs = spec.get("languages") or ["latin"]
    slots = {s: o["fonts"][s] for s in SLOTS if s in o["fonts"]}
    scale = o["scale"]
    body_rows = [r for r in scale if r.get("use") == "body"] or [r for r in scale if r.get("font", "ui") == "ui"][:1]
    body = o.get("body") or {}
    used_w = {s: sorted({int(r.get("weight", 400)) for r in scale if r.get("font", "ui") == s} | set(map(int, f.get("weights", [])))) for s, f in slots.items()}
    data_slot = next((r.get("font", "ui") for r in scale if r.get("use") == "data"), "mono" if "mono" in slots else "ui")

    # licence, languages, weights: one row per font
    seen = set()
    for s, f in slots.items():
        fam = f["family"]
        meas = measured[fam]
        if fam in seen:
            continue
        seen.add(fam)
        lic = F.LICENCES.get(meas["licence"])
        restricted = meas["fsType"] & 0x0002 or meas["fsType"] & 0x0200
        if lic and not restricted:
            out.append(row("Licence", fam, meas["licence"], "pass", f"{lic[0]}. {lic[1]}"))
        elif restricted:
            out.append(row("Licence", fam, "fsType", "fail", "The font file says it can't be embedded (restricted licence bit).",
                           "Use a different font, or confirm the licence with the foundry."))
        else:
            out.append(row("Licence", fam, meas["licence"] or "unknown", "fail",
                           f"No free licence recorded{(': the file says “' + meas['licence_text'][:120] + '”') if meas['licence_text'] else ''}.",
                           "Confirm the licence allows commercial use, logos and web embedding, and name it in the spec."))
        missing = {k: meas["coverage"][k] for k in langs if meas["coverage"].get(k)}
        if missing:
            out.append(row("Languages", fam, ", ".join(langs), "fail",
                           "; ".join(f"{k}: {len(v)} missing ({''.join(v[:12])}{'…' if len(v) > 12 else ''})" for k, v in missing.items()),
                           "Pick a font that covers these, or drop the language from the brief."))
        else:
            out.append(row("Languages", fam, ", ".join(langs), "pass", f"Covers every {', '.join(langs)} character checked."))
        need = sorted({w for s2, f2 in slots.items() if f2["family"] == fam for w in used_w[s2]})
        avail = meas["weights"]
        wght = next((a for a in meas["axes"] if a["tag"] == "wght"), None)
        lacks = [w for w in need if not (wght and wght["min"] <= w <= wght["max"]) and w not in avail]
        axes = ", ".join(f'{a["tag"]} {a["min"]:g}–{a["max"]:g}' for a in meas["axes"]) or "static"
        detail = f"Uses {', '.join(map(str, need))}; has {avail[0]}–{avail[-1]} ({axes})."
        if lacks:
            out.append(row("Weights", fam, "", "fail", detail + f" Missing {', '.join(map(str, lacks))}.",
                           "Change those scale rows to a weight the font has."))
        else:
            out.append(row("Weights", fam, "", "pass", detail))

    # WCAG 1.4.3 and APCA: every scale row, every background, both modes
    wcag_fail, wcag_low, apca_rows = [], None, []
    for r in scale:
        size, weight = px(r["size"]), int(r.get("weight", 400))
        large = size >= 24 or (size >= 18.66 and weight >= 700)
        need = 3.0 if large else 4.5
        worst = None
        for m in MODES:
            for fg, bg, where in pairs_for(r, C, m):
                ratio = cp.contrast(fg, bg)
                if wcag_low is None or ratio < wcag_low[0]:
                    wcag_low = (ratio, r["label"], where, m)
                if ratio < need:
                    wcag_fail.append(f'{r["label"]} on {where} ({m}): {cp.floor2(ratio):.2f}:1, needs {need:g}:1')
                lc = abs(APCA.lc(fg, bg))
                minpx = APCA.min_size(lc, weight)
                body_short = r.get("use") == "body" and lc < BODY_LC
                ok = minpx < apca_mod.NON_TEXT and size >= minpx and not body_short
                key = (ok, -minpx if minpx < apca_mod.NON_TEXT else -1000, lc)
                if worst is None or key < worst[0]:
                    worst = (key, lc, minpx, where, m, body_short)
        _, lc, minpx, where, m, body_short = worst
        label = f'{r["label"]} · {size:g}px / {weight}'
        lcs = f"Lc {apca_mod.round_lc(lc)} on {where} ({m})"
        if minpx >= apca_mod.NON_TEXT:
            apca_rows.append(row("APCA", label, "font lookup", "fail", f"{lcs}: too low for any text.",
                                 "Use the main text color, or a darker/lighter background."))
        elif body_short:
            apca_rows.append(row("APCA", label, "body text Lc 75+", "fail", f"{lcs}: body text needs Lc 75 or more (90 preferred).",
                                 "Set body text in the main text color."))
        elif size < minpx:
            apca_rows.append(row("APCA", label, "font lookup", "fail", f"{lcs}: needs {minpx:g}px at weight {weight}.",
                                 f"Make it {math.ceil(minpx)}px, or use a heavier weight or higher-contrast color."))
        else:
            apca_rows.append(row("APCA", label, "font lookup", "pass", f"{lcs} (lowest): {minpx:g}px is the minimum at {weight}."))
    n = len(scale) * len(MODES)
    if wcag_fail:
        out.append(row("WCAG 2.2", "1.4.3 Contrast (minimum)", "AA", "fail", "; ".join(wcag_fail),
                       "Use the main text color for those rows, or make them large text."))
    else:
        out.append(row("WCAG 2.2", "1.4.3 Contrast (minimum)", "AA", "pass",
                       f"All {len(scale)} rows pass on every background in both modes (lowest {cp.floor2(wcag_low[0]):.2f}:1, "
                       f"{wcag_low[1]} on {wcag_low[2]}, {wcag_low[3]})."))
    pxs = [r["label"] for r in scale if str(r["size"]).strip().endswith("px")]
    out.append(row("WCAG 2.2", "1.4.4 Resize text", "AA", "watch" if pxs else "pass",
                   f"Set in px: {', '.join(pxs)}." if pxs else "Every size is in rem, so text follows the reader's browser setting.",
                   "Use rem so text scales with the browser's font size." if pxs else None))
    measure = body.get("measure", 66)
    lh = min(float(r.get("line", 1.5)) for r in body_rows)
    para = em(body.get("paragraph_spacing", "1em"))
    out.append(row("WCAG 2.2", "1.4.8 Line length", "AAA", "pass" if measure <= 80 else "watch",
                   f"Body measure {measure} characters (80 at most).", None if measure <= 80 else "Set max-width to 66ch or less."))
    out.append(row("WCAG 2.2", "1.4.8 Line spacing", "AAA", "pass" if lh >= 1.5 else "watch",
                   f"Body line height {lh:g} (1.5 at least).", None if lh >= 1.5 else "Set body line-height to 1.5."))
    para_need = round(1.5 * lh, 3)
    out.append(row("WCAG 2.2", "1.4.8 Paragraph spacing", "AAA", "pass" if para >= para_need else "watch",
                   f"{para:g}em between paragraphs; 1.5× the line spacing is {para_need:g}em.",
                   None if para >= para_need else f"Set paragraph spacing to {math.ceil(para_need * 100) / 100:g}em."))
    if body.get("align") == "justify":
        out.append(row("WCAG 2.2", "1.4.8 Not justified", "AAA", "watch", "Body text is justified.", "Align body text left."))
    out.append(row("WCAG 2.2", "1.4.12 Text spacing", "AA", "test",
                   "Line height 1.5, paragraph spacing 2em, letter spacing 0.12em and word spacing 0.16em must not clip or overlap text.",
                   "Turn on the page's Text spacing switch and check every specimen."))
    out += apca_rows

    # BDA and legibility, on the fonts that carry reading text
    ui = measured[slots["ui"]["family"]]
    sh = ui.get("shapes")
    bsize = min(px(r["size"]) for r in body_rows)
    out.append(row("BDA", "Body size", "16–19px (12–14pt)", "pass" if bsize >= 16 else "watch",
                   f"Body text is {bsize:g}px.", None if bsize >= 16 else "Set body text to 16px (1rem) or more."))
    out.append(row("BDA", "Line spacing", "1.5", "pass" if lh >= 1.5 else "watch", f"Body line height {lh:g}.",
                   None if lh >= 1.5 else "Set body line-height to 1.5."))
    out.append(row("BDA", "Line length", "60–70 characters", "pass" if measure <= 70 else "watch",
                   f"Body measure {measure} characters.", None if measure <= 70 else "Set max-width to 70ch or less."))
    cat = ui["category"]
    out.append(row("BDA", "Sans serif body", "sans serif", "pass" if cat in ("sans", "mono") else "watch",
                   f'{ui["family"]} is {"a sans serif" if cat == "sans" else "a " + cat + " face"}.',
                   None if cat in ("sans", "mono") else "Fine for a brand voice, but offer a sans serif body if readers include people with dyslexia."))
    styled = [r["label"] for r in scale if r.get("use") == "body" and (r.get("italic") or r.get("caps"))]
    caps = [r["label"] for r in scale if r.get("caps") and r.get("use") != "body"]
    out.append(row("BDA", "No italics or capitals for reading text", "emphasis", "watch" if styled else "pass",
                   f"Styled body rows: {', '.join(styled)}." if styled else
                   ("Body text is upright and in sentence case." + (f" Capitals only on short labels ({', '.join(caps)})." if caps else "")),
                   "Use bold for emphasis instead." if styled else None))
    if sh:
        sp = sh["spacing"]
        track = em(body.get("letter_spacing"))
        wordsp = em(body.get("word_spacing"))
        letter = (sp["gap_em"] + track) / sp["ink_em"]
        word = (sp["word"] * sp["gap_em"] + track + wordsp) / (sp["gap_em"] + track) if sp["word"] else None
        need = round(BDA_LETTER * sp["ink_em"] - sp["gap_em"], 3)
        out.append(row("BDA", "Letter spacing", "≈35% of letter width", "pass" if letter >= BDA_LETTER - 0.03 else "watch",
                       f"Space between letters is {letter:.0%} of the average letter width"
                       f"{f' with {track:g}em tracking' if track else ''}.",
                       None if letter >= BDA_LETTER - 0.03 else f"letter-spacing: {need:.2f}em on body text reaches 35%."))
        if word:
            fix_w = round((BDA_WORD * (sp["gap_em"] + track)) - (sp["word"] * sp["gap_em"] + track), 3)
            out.append(row("BDA", "Word spacing", "≥ 3.5× letter spacing", "pass" if word >= BDA_WORD else "watch",
                           f"Word space is {word:.1f}× the letter space.",
                           None if word >= BDA_WORD else f"word-spacing: {fix_w:.2f}em on body text reaches 3.5×."))
        mir = [f'{c["a"]}/{c["b"]} {c["likeness"]:.0%}' for c in sh["mirrors"] if c["likeness"] >= MIRROR]
        out.append(row("BDA", "Mirror letters", "b/d, p/q differ", "watch" if mir else "pass",
                       (f"Near-perfect mirrors: {', '.join(mir)}." if mir else
                        "b/d and p/q aren't exact mirrors (" + ", ".join(f'{c["a"]}/{c["b"]} {c["likeness"]:.0%}' for c in sh["mirrors"]) + ")."),
                       "Readers with dyslexia may swap these; a font with asymmetric bowls helps." if mir else None))
        xh = ui["x_height"] * bsize
        out.append(row("Legibility", f'x-height ({ui["family"]})', f"≥ {XH_PX:g}px at body size", "pass" if xh >= XH_PX else "watch",
                       f'x-height is {ui["x_height"]:.3f} of the size: {xh:.1f}px at {bsize:g}px.',
                       None if xh >= XH_PX else f"Set body text to {math.ceil(XH_PX / ui['x_height'])}px for an {XH_PX:g}px x-height."))
        alike = [c for c in sh["confusable"] if c["likeness"] >= LIKE and not set(c["a"] + c["b"]) <= set("O0")]
        sets = [t for t in ui["features"] if re.fullmatch(r"ss\d\d|cv\d\d", t)]
        out.append(row("Legibility", f'Confusable letters ({ui["family"]})', "I l 1 · rn m · cl d", "watch" if alike else "pass",
                       ("Hard to tell apart: " + ", ".join(f'{c["a"]}/{c["b"]} {c["likeness"]:.0%} alike' for c in alike) + "."
                        if alike else "I, l and 1, rn and m, and cl and d all differ clearly."),
                       (f"Try its stylistic sets ({', '.join(sets[:6])}) for a distinct l or I." if sets else
                        "Fine for headings; check product names and codes set in it.") if alike else None))
        ap = sh["aperture"]["c"]
        out.append(row("Legibility", f'Apertures ({ui["family"]})', f"c opening ≥ {APERTURE:.0%}", "pass" if ap >= APERTURE else "watch",
                       f"The c opening is {ap:.0%} of its height (e: {sh['aperture']['e']:.0%}).",
                       None if ap >= APERTURE else "Closed apertures blur at small sizes. Keep this face above 16px."))
    else:
        out.append(row("Legibility", "Glyph shapes", "", "watch", "Pillow isn't installed, so letter shapes weren't measured.",
                       "pip install pillow, then run again."))
    dm = measured[slots.get(data_slot, slots["ui"])["family"]]
    if dm["tabular_default"]:
        out.append(row("Legibility", f'Tabular figures ({dm["family"]})', "numbers line up", "pass", "Figures are the same width by default."))
    elif "tnum" in dm["features"]:
        out.append(row("Legibility", f'Tabular figures ({dm["family"]})', "numbers line up", "pass",
                       "Has tabular figures; set font-variant-numeric: tabular-nums on tables and KPIs."))
    else:
        out.append(row("Legibility", f'Tabular figures ({dm["family"]})', "numbers line up", "fail",
                       "No tabular figures, so columns of numbers won't line up.", "Set data in a font with tnum, or in the mono face."))
    if dm.get("shapes"):
        o0 = next(c for c in dm["shapes"]["confusable"] if c["a"] == "O")
        z = "zero" in dm["features"]
        out.append(row("Legibility", f'O and 0 ({dm["family"]})', "codes and IDs", "pass" if z or o0["likeness"] < 0.6 else "watch",
                       f'O/0 {o0["likeness"]:.0%} alike' + ("; has a slashed or dotted zero (font-variant-numeric: slashed-zero)." if z else "."),
                       None if z or o0["likeness"] < 0.6 else "Set codes and IDs in the mono face."))
    return sorted(out, key=lambda r: GROUPS.index(r["group"]))  # stable: fonts keep their order inside a group


KIND = {"sans": "sans serif", "serif": "serif", "mono": "monospace", "display": "display face", "script": "script"}
# how far apart two faces of the same kind must be on a measure to look different
APART = {"width": (0.04, "width"), "weight": (0.04, "weight"), "contrast": (0.5, "stroke contrast"),
         "aperture": (0.12, "letter openness"), "x_height": (0.03, "x-height")}


def look(fam, measured):
    m = measured[fam]
    p = dict((m.get("shapes") or {}).get("profile") or {})
    p["x_height"] = m["x_height"]
    return m["category"], p


def face_gap(a, b, measured):
    """How two faces differ, in words: [] when they'd read as the same kind of face."""
    if a == b:
        return []
    ka, pa = look(a, measured)
    kb, pb = look(b, measured)
    if ka != kb:
        return [f"{KIND.get(ka, ka)} vs {KIND.get(kb, kb)}"]
    diffs = [label for k, (gap, label) in APART.items()
             if pa.get(k) is not None and pb.get(k) is not None and abs(pa[k] - pb[k]) >= gap]
    # weight and openness are measured at the regular weight and fade at heading weights, so one
    # of the differences has to be in the letters' shape: width or stroke contrast
    shape = {APART["width"][1], APART["contrast"][1]}
    return diffs if len(diffs) >= 2 and shape & set(diffs) else []


def distinct_rows(spec, measured):
    """Every pair of options must look noticeably different: a different kind of body face, a
    different kind of headline face, or a headline face that differs on two measures. Fonts the
    user chose ("given": true) are shared on purpose and skipped."""
    opts = spec["options"]
    out = []
    for i in range(len(opts)):
        for j in range(i + 1, len(opts)):
            a, b = opts[i], opts[j]
            name = f'{a["id"].upper()} vs {b["id"].upper()}'
            reasons, same = [], []
            for role, label in (("ui", "body"), ("display", "headlines")):
                fa = a["fonts"].get(role) or a["fonts"]["ui"]
                fb = b["fonts"].get(role) or b["fonts"]["ui"]
                if fa.get("given") or fb.get("given"):
                    continue
                gap = face_gap(fa["family"], fb["family"], measured)
                if gap:
                    reasons.append(f'{label}: {fa["family"]} vs {fb["family"]} ({", ".join(gap)})')
                else:
                    ka = KIND.get(measured[fa["family"]]["category"], "")
                    same.append(f'{label} {"both " + fa["family"] if fa["family"] == fb["family"] else "both " + ka + "s"}')
            if reasons:
                out.append(row("Options", name, "noticeably different", "pass", "Differ in " + "; ".join(reasons) + "."))
            else:
                out.append(row("Options", name, "noticeably different", "fail",
                               f"Too alike: {', '.join(same) or 'the same fonts'}. At reading size these look like one option.",
                               "Change one option's headline face to another kind (serif, sans, slab, mono), or give it a different kind of body face."))
    return out


def counts(rows):
    c = {"pass": 0, "watch": 0, "fail": 0, "test": 0}
    for r in rows:
        c[r["status"]] += 1
    return c


# ---------- the page ----------

def esc(s):
    return html.escape(str(s), quote=True)


def font_stack(f, measured):
    return f'"{f["family"]}", {FALLBACK[measured[f["family"]]["category"]]}'


def google_link(spec):
    fams = {}
    for o in spec["options"]:
        for s, f in o["fonts"].items():
            if f.get("source", "google") != "google":
                continue
            ws = set(map(int, f.get("weights", []))) | {int(r.get("weight", 400)) for r in o["scale"] if r.get("font", "ui") == s}
            fams.setdefault(f["family"], set()).update(ws or {400})
    if not fams:
        return ""
    q = "&".join("family=" + k.replace(" ", "+") + ":wght@" + ";".join(map(str, sorted(v))) for k, v in fams.items())
    return ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?{q}&display=swap">')


def embedded(spec, base):
    done, css = set(), []
    for o in spec["options"]:
        for s, f in o["fonts"].items():
            if f.get("source", "google") == "google":
                continue
            ws = sorted(set(map(int, f.get("weights", []))) | {int(r.get("weight", 400)) for r in o["scale"] if r.get("font", "ui") == s})
            key = (f["family"], tuple(ws))
            if key in done:
                continue
            done.add(key)
            css.append(F.embed_css(dict(f, weights=ws or [400]), CACHE, base))
    return "\n".join(css)


def tokens(C):
    def block(m):
        c = C[m]
        return [f'--page: {c["bg"]["page"]};', f'--card: {c["bg"]["card"]};', f'--text: {c["fg"]["text"]};',
                f'--muted: {c["fg"]["muted"]};', f'--line: {c["line"]};', f'--primary: {c["fill"]["primary"]};',
                f'--on-primary: {c["fg"]["on-primary"]};', f'--soft: {c["soft"]};']
    light, dark = block("light"), block("dark")
    return "\n".join([":root {", *("  " + d for d in light), "  color-scheme: light;", "}",
                      "@media (prefers-color-scheme: dark) {", '  :root:not([data-theme="light"]) {',
                      *("    " + d for d in dark), "    color-scheme: dark;", "  }", "}",
                      ':root[data-theme="dark"] {', *("  " + d for d in dark), "  color-scheme: dark;", "}"])


def scale_style(r, o, measured, color=None):
    """Inline CSS for a scale row. `color` overrides the row's color token, for specimens that
    reuse a row's type on another background (a secondary button, a field label)."""
    f = o["fonts"].get(r.get("font", "ui"), o["fonts"]["ui"])
    st = [f"font-family: {font_stack(f, measured)}", f'font-size: {r["size"]}', f'font-weight: {r.get("weight", 400)}',
          f'line-height: {r.get("line", 1.4)}']
    if r.get("tracking"):
        st.append(f'letter-spacing: {r["tracking"]}')
    if r.get("caps"):
        st.append("text-transform: uppercase")
    if r.get("italic"):
        st.append("font-style: italic")
    if r.get("tabular") or r.get("use") == "data":
        st.append("font-variant-numeric: tabular-nums")
    c = r.get("color", "muted" if r.get("muted") else "text")
    st.append(f'color: var(--{color or c})')
    if c == "on-primary" and not color:
        st.append("background: var(--primary); padding: 2px 8px; border-radius: 6px")
    return "; ".join(st)


def pick_row(o, use, fallback_font="ui"):
    return next((r for r in o["scale"] if r.get("use") == use), None) or \
        next((r for r in o["scale"] if r.get("font", "ui") == fallback_font), o["scale"][0])


def style_guide(o, rows, measured, spec, C, pal):
    """The option as a plain-text brief for Claude: fonts, how to load them, CSS for the scale,
    the colors it was checked against, and the rules. Pasted into a prompt or a project's notes,
    it lets Claude set new pages and artifacts in this type."""
    brand = spec.get("brand") or "the brand"
    f = o["fonts"]
    roles = {"display": "--font-display", "ui": "--font-body", "mono": "--font-mono"}
    lines = [f"# {brand} typography: {o['name']}", "",
             f"Use these fonts and this type scale for anything made for {brand}: web pages, artifacts, documents and slides. "
             "Every size, weight and color pairing below passed WCAG 2.2 AA and APCA checks; don't go smaller or lighter.", ""]
    if o.get("why"):
        lines += [o["why"], ""]
    lines += ["## Fonts"]
    google, other = [], []
    for slot in SLOTS:
        if slot not in f:
            continue
        ff, meas = f[slot], measured[f[slot]["family"]]
        lic = F.LICENCES.get(meas["licence"], (meas["licence"] or "licence unknown", ""))[0]
        ws = sorted({int(r.get("weight", 400)) for r in o["scale"] if r.get("font", "ui") == slot} | set(map(int, ff.get("weights", [])))) or [400]
        src = {"google": "Google Fonts", "fontshare": "Fontshare", "file": "local file"}[meas["source"]]
        lines.append(f'- {ff.get("role") or slot.title()}: **{ff["family"]}** ({src}, {lic}), weights {", ".join(map(str, ws))}.'
                     + (f' {ff["use"]}' if ff.get("use") else ""))
        (google if meas["source"] == "google" else other).append((ff["family"], ws, meas))
    lines += ["", "## Loading the fonts"]
    if google:
        q = "&".join("family=" + fam.replace(" ", "+") + ":wght@" + ";".join(map(str, ws)) for fam, ws, _ in google)
        lines += ["Google Fonts (works in Claude artifacts):", "```html",
                  f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?{q}&display=swap">', "```"]
    for fam, ws, meas in other:
        if meas["source"] == "fontshare":
            lines.append(f'{fam} is on Fontshare, not Google Fonts. On a website, load '
                         f'`https://api.fontshare.com/v2/css?f[]={F.slug(fam, "-")}@{",".join(map(str, ws))}&display=swap`. '
                         "In a Claude artifact, other font hosts are blocked, so inline the font files as @font-face data URIs.")
        else:
            lines.append(f"{fam} is a local font file: inline it as an @font-face data URI, or self-host it.")
    lines += ["", "## CSS", "```css", ":root {"]
    for slot in SLOTS:
        if slot in f:
            lines.append(f'  {roles[slot]}: {font_stack(f[slot], measured)};')
    if "display" not in f:
        lines.append(f'  --font-display: var(--font-body);')
    if "mono" not in f:
        lines.append(f'  --font-mono: var(--font-body);')
    lines.append("}")
    body = o.get("body") or {}
    body_r = pick_row(o, "body")
    lines += ["body {", f'  font-family: var(--font-body);', f'  font-size: {body_r["size"]};',
              f'  font-weight: {body_r.get("weight", 400)};', f'  line-height: {body_r.get("line", 1.5)};', "}",
              f'p {{ max-width: {body.get("measure", 66)}ch; margin: 0 0 {body.get("paragraph_spacing", "1em")}; }}']
    for r in o["scale"]:
        cls = re.sub(r"[^a-z0-9]+", "-", r["label"].lower()).strip("-")
        decl = [f'font-family: var({roles.get(r.get("font", "ui"), "--font-body") if r.get("font", "ui") in f else "--font-body"})',
                f'font-size: {r["size"]}', f'font-weight: {r.get("weight", 400)}', f'line-height: {r.get("line", 1.4)}']
        if r.get("tracking"):
            decl.append(f'letter-spacing: {r["tracking"]}')
        if r.get("caps"):
            decl.append("text-transform: uppercase")
        if r.get("tabular") or r.get("use") == "data":
            decl.append("font-variant-numeric: tabular-nums")
        lines.append(f'.type-{cls} {{ {"; ".join(decl)}; }}  /* {r.get("use", "")} */')
    lines += ["```", "", "## Colors these sizes were checked against"]
    for m in MODES:
        c = C[m]
        lines.append(f'- {m.title()} mode: text {c["fg"]["text"]}, secondary text {c["fg"]["muted"]}, page {c["bg"]["page"]}, '
                     f'card {c["bg"]["card"]}, button {c["fill"]["primary"]} with {c["fg"]["on-primary"]} labels.')
    lines.append(f'Palette: {pal["name"]}{"" if pal.get("_source") else " (greyscale: recheck the sizes once the brand colors exist)"}.')
    lines += ["", "## Rules"]
    # smallest size at which the secondary text color passes APCA on every background, both modes
    for w in (400, 600):
        need = max(APCA.min_size(abs(APCA.lc(C[m]["fg"]["muted"], bg)), w) for m in MODES for bg in C[m]["bg"].values())
        if need < apca_mod.NON_TEXT:
            lines.append(f"- Secondary text color only at {math.ceil(need)}px or larger at weight {w}; smaller text uses the main text color.")
    for r in o["scale"]:
        c = r.get("color", "muted" if r.get("muted") else "text")
        if c == "on-primary":
            lines.append(f'- {r["label"]} labels sit on the button color above, in its label color, at {r["size"]} / {r.get("weight", 400)} or larger.')
        elif c != "text":
            lines.append(f'- {r["label"]} text uses the {"secondary text" if c == "muted" else c} color.')
    lines += ["- Use bold for emphasis in reading text, not italics or capitals.",
              "- Set sizes in rem so text follows the reader's browser setting.",
              "- Use font-variant-numeric: tabular-nums wherever figures line up in columns."]
    for fam_slot in ("display",):
        if fam_slot in f and f[fam_slot].get("use"):
            lines.append(f'- {f[fam_slot]["family"]}: {f[fam_slot]["use"]}')
    watches = [r for r in rows if r["status"] == "watch" and r["fix"]]
    if watches:
        lines += ["", "## Known trade-offs"]
        lines += [f'- {r["check"]}: {r["detail"]} Fix: {r["fix"]}' for r in watches]
    return "\n".join(lines)


def option_html(o, rows, measured, spec, samples, guide=""):
    S = samples
    brand = spec.get("wordmark") or spec.get("brand") or "Brand"
    f = o["fonts"]
    disp = f.get("display", f["ui"])
    mono = f.get("mono", f["ui"])
    vars_ = (f'--f-display: {font_stack(disp, measured)}; --f-ui: {font_stack(f["ui"], measured)}; '
             f'--f-mono: {font_stack(mono, measured)};')
    body = o.get("body") or {}
    body_r = pick_row(o, "body")
    h1 = next((r for r in o["scale"] if r.get("use") == "heading"), o["scale"][0])
    h2 = next((r for r in o["scale"] if r.get("use") == "heading" and r is not h1), h1)
    ui_r = pick_row(o, "ui")
    cap_r = pick_row(o, "caption")
    data_r = pick_row(o, "data", "mono" if "mono" in f else "ui")
    bstyle = scale_style(body_r, o, measured) + (f'; letter-spacing: {body["letter_spacing"]}' if body.get("letter_spacing") else "") \
        + (f'; word-spacing: {body["word_spacing"]}' if body.get("word_spacing") else "")
    para_gap = body.get("paragraph_spacing", "1em")
    measure = body.get("measure", 66)
    c = counts(rows)

    cards = []
    for slot in SLOTS:
        if slot not in f or (slot == "display" and f["display"]["family"] == f["ui"]["family"]):
            continue
        ff = f[slot]
        meas = measured[ff["family"]]
        lic = F.LICENCES.get(meas["licence"], (meas["licence"] or "Unknown licence", ""))[0]
        src = {"google": "Google Fonts", "fontshare": "Fontshare", "file": "Local file"}[meas["source"]]
        link = f'<a href="{esc(meas["url"])}">{src}</a>' if meas.get("url") else src
        ax = ", ".join(f'{a["tag"]} {a["min"]:g}–{a["max"]:g}' for a in meas["axes"]) or f'{len(meas["weights"])} weights'
        cards.append(f'''<div class="font-card">
  <div class="eyebrow">{esc(ff.get("role") or slot)}</div>
  <div class="spec" style="font-family:{esc(font_stack(ff, measured))}; font-weight:{esc((ff.get("weights") or [400])[-1])}">{esc(ff["family"])}</div>
  <div class="chars" style="font-family:{esc(font_stack(ff, measured))}">Aa Bb Gg Rr Il1 O0 rn m 0123456789 &amp;@</div>
  <dl class="facts"><dt>Source</dt><dd>{link} · {esc(lic)}</dd><dt>Axes</dt><dd>{esc(ax)}</dd>
  <dt>x-height</dt><dd>{meas["x_height"]:.3f} of size</dd>{f'<dt>Use</dt><dd>{esc(ff["use"])}</dd>' if ff.get("use") else ""}</dl>
</div>''')

    scale_rows = "\n".join(
        f'<div class="srow"><div class="lbl"><b>{esc(r["label"])}</b><span>{esc(f.get(r.get("font", "ui"), f["ui"])["family"])} '
        f'{esc(r["size"])} / {esc(r.get("weight", 400))} · {esc(r.get("line", 1.4))}</span></div>'
        f'<div style="{esc(scale_style(r, o, measured))}">{esc(r.get("sample") or (S["headline"] if r.get("use") == "heading" else S["paragraph"][0]))}</div></div>'
        for r in o["scale"])

    paras = "".join(f'<p style="{esc(bstyle)}; margin: 0 0 {esc(para_gap)}">{esc(p)}</p>' for p in S["paragraph"])
    nav = "".join(f'<span class="{"on" if i == 0 else ""}">{esc(n)}</span>' for i, n in enumerate(S["nav"]))
    t = S["table"]
    table = (f'<table style="font-family: var(--f-ui)"><caption style="{esc(scale_style(cap_r, o, measured))}">{esc(t["caption"])}</caption><thead><tr>'
             + "".join(f'<th style="font-family: var(--f-ui)">{esc(col)}</th>' for col in t["columns"]) + "</tr></thead><tbody>"
             + "".join("<tr>" + "".join(
                 f'<td style="{esc(scale_style(data_r, o, measured)) if i else ""}">{esc(cell)}</td>'
                 for i, cell in enumerate(rr)) + "</tr>" for rr in t["rows"]) + "</tbody></table>")
    bars = S["chart"]["bars"]
    top = max(v for _, v in bars) or 1
    bw = 300 / len(bars)
    svg = "".join(
        f'<rect x="{30 + i * bw + bw * .2:.1f}" y="{20 + 120 * (1 - v / top):.1f}" width="{bw * .6:.1f}" height="{120 * v / top:.1f}" rx="3" style="fill:var(--primary)"/>'
        f'<text x="{30 + i * bw + bw / 2:.1f}" y="160" text-anchor="middle" style="font: 500 12px var(--f-ui); fill: var(--muted)">{esc(k)}</text>'
        f'<text x="{30 + i * bw + bw / 2:.1f}" y="{14 + 120 * (1 - v / top):.1f}" text-anchor="middle" style="font: 600 12px var(--f-mono); font-variant-numeric: tabular-nums; fill: var(--text)">{v:,}</text>'
        for i, (k, v) in enumerate(bars))
    groups = []
    for g in GROUPS:
        gr = [r for r in rows if r["group"] == g]
        if not gr:
            continue
        groups.append(f'<tr class="grp"><th colspan="4">{esc(g)}</th></tr>' + "".join(
            f'<tr><td>{esc(r["check"])}{f"<div class=cap>{esc(r["standard"])}</div>" if r["standard"] else ""}</td>'
            f'<td><span class="badge {r["status"]}">{ {"pass": "Pass", "watch": "Watch", "fail": "Fail", "test": "Test"}[r["status"]] }</span></td>'
            f'<td>{esc(r["detail"])}</td><td class="cap">{esc(r["fix"] or "")}</td></tr>' for r in gr))
    return f'''<section class="option" id="opt-{esc(o["id"])}" style="{esc(vars_)}">
<header class="ohead">
  <div><div class="eyebrow">Option {esc(o["id"]).upper()}{' · <span class="pick">Our pick</span>' if o.get("pick") else ""}</div>
  <h2 style="font-family: var(--f-display)">{esc(o["name"])}</h2>
  {f'<p class="lede">{esc(o["character"])}</p>' if o.get("character") else ""}
  {f'<p>{esc(o["why"])}</p>' if o.get("why") else ""}</div>
  <div class="tally"><span class="badge pass">{c["pass"]} pass</span><span class="badge watch">{c["watch"]} watch</span>
  <span class="badge fail">{c["fail"]} fail</span><span class="badge test">{c["test"]} to test</span></div>
</header>
<div class="guide">
  <button class="copy" type="button" id="copy-{esc(o["id"])}" data-target="guide-{esc(o["id"])}">Copy style guide</button>
  <span class="cap copied" id="copied-{esc(o["id"])}" role="status" aria-live="polite"></span>
  <details><summary>Style guide for Claude: paste it into a prompt or a project</summary>
  <pre id="guide-{esc(o["id"])}" tabindex="0">{esc(guide)}</pre></details>
</div>
<div class="cards">{"".join(cards)}</div>

<h3>Wordmark</h3>
<div class="wordmark">
  <div class="wm-big" style="font-family: var(--f-display); font-weight: {esc(h1.get("weight", 600))}">{esc(brand)}</div>
  <div class="wm-row">
    <div class="wm-tile rev" style="font-family: var(--f-display); font-weight: {esc(h1.get("weight", 600))}">{esc(brand)}</div>
    <div class="wm-tile" style="font-family: var(--f-display); font-weight: {esc(h1.get("weight", 600))}; font-size: 16px">{esc(brand)}</div>
    <div class="wm-tile mono-mark" style="font-family: var(--f-display); font-weight: {esc(h1.get("weight", 600))}">{esc(brand[:1])}</div>
  </div>
  <p class="cap">Large, reversed on the primary color, at 16px (the smallest it should go), and as a single-letter mark.</p>
</div>

<h3>Websites and apps</h3>
<div class="spec-web">
  <div class="topbar" style="font-family: var(--f-ui)"><b style="font-family: var(--f-display)">{esc(brand)}</b><nav>{nav}</nav></div>
  <div class="web-body">
    <h1 style="{esc(scale_style(h1, o, measured))}; margin: 0 0 12px">{esc(S["headline"])}</h1>
    <div style="max-width: {esc(measure)}ch">{paras}</div>
    <div class="btns"><button class="b1" style="{esc(scale_style(ui_r, o, measured, "on-primary"))}">{esc(S["buttons"][0])}</button>
    <button class="b2" style="{esc(scale_style(ui_r, o, measured, "text"))}">{esc(S["buttons"][1])}</button></div>
    <label class="field" style="font-family: var(--f-ui)"><span style="{esc(scale_style(ui_r, o, measured, "text"))}; font-weight: 600">{esc(S["input"]["label"])}</span>
      <input placeholder="{esc(S["input"]["placeholder"])}" style="{esc(scale_style(body_r, o, measured))}">
      <span style="{esc(scale_style(cap_r, o, measured))}">{esc(S["input"]["help"])}</span></label>
  </div>
</div>

<h3>Print and documents</h3>
<div class="print-row">
  <div class="doc">
    <div class="eyebrow" style="font-family: var(--f-mono)">{esc(brand)}</div>
    <div style="font-family: var(--f-display); font-weight: {esc(h1.get("weight", 600))}; font-size: 28px; line-height: 1.15; margin: 6px 0 4px">{esc(S["doc"]["title"])}</div>
    <div style="{esc(scale_style(h2, o, measured))}; font-size: 15px; color: var(--muted)">{esc(S["doc"]["subtitle"])}</div>
    <p style="font-family: var(--f-ui); font-size: 11pt; line-height: {esc(body_r.get("line", 1.5))}; margin: 14px 0">{esc(S["paragraph"][0])}</p>
    <blockquote style="font-family: var(--f-display); font-size: 16pt; line-height: 1.3">“{esc(S["doc"]["quote"])}”</blockquote>
    <p style="font-family: var(--f-ui); font-size: 11pt; line-height: {esc(body_r.get("line", 1.5))}; margin: 14px 0">{esc(S["paragraph"][-1])}</p>
    <div class="cap" style="font-family: var(--f-ui)">{esc(S["doc"]["caption"])} · body at 11pt for print</div>
  </div>
  <div class="bcard">
    <div style="font-family: var(--f-display); font-weight: {esc(h1.get("weight", 600))}; font-size: 20px">{esc(brand)}</div>
    <div><div style="font-family: var(--f-ui); font-weight: 600; font-size: 13px">{esc(S["card"]["name"])}</div>
    <div style="font-family: var(--f-ui); font-size: 11px; color: var(--muted)">{esc(S["card"]["role"])}</div>
    <div style="font-family: var(--f-mono); font-size: 9.5px; margin-top: 8px; font-variant-numeric: tabular-nums">{esc(S["card"]["contact"])}</div></div>
  </div>
</div>

<h3>Data and charts</h3>
<div class="data-row">
  <div class="tbl">{table}</div>
  <figure class="chart"><figcaption style="font-family: var(--f-ui); font-weight: 600">{esc(S["chart"]["title"])}</figcaption>
  <svg viewBox="0 0 360 170" role="img" aria-label="{esc(S["chart"]["title"])}"><line x1="24" y1="140" x2="340" y2="140" style="stroke:var(--line)"/>{svg}</svg></figure>
</div>

<h3>Type scale</h3>
<div class="scale">{scale_rows}</div>

<h3>Readability checks</h3>
<div class="tablewrap"><table class="checks"><thead><tr><th>Check</th><th>Result</th><th>Measured</th><th>Fix</th></tr></thead>
<tbody>{"".join(groups)}</tbody></table></div>
</section>'''


def write_html(spec, pal, results, measured, base, out, distinct=()):
    tpl = (HERE.parent / "references" / "specimen-template.html").read_text()
    C, _ = colors(pal, spec.get("primary"), spec.get("fill"))
    samples = {**DEFAULT_SAMPLES, **(spec.get("samples") or {})}
    brand = spec.get("brand") or "Brand"
    summary = "".join(
        f'<tr><td><a href="#opt-{esc(o["id"])}">{esc(o["id"]).upper()} · {esc(o["name"])}</a>{" <span class=pick>Our pick</span>" if o.get("pick") else ""}</td>'
        f'<td>{esc(" + ".join(dict.fromkeys(f["family"] for f in o["fonts"].values())))}</td>'
        f'<td>{" ".join(f"<span class=\"badge {k}\">{v}</span>" for k, v in counts(results[o["id"]]).items() if v)}</td></tr>'
        for o in spec["options"])
    assumptions = "".join(f"<li>{esc(a)}</li>" for a in spec.get("assumptions") or [])
    links = "".join(f'<a href="#opt-{esc(o["id"])}">Option {esc(o["id"]).upper()}</a>' for o in spec["options"])
    body = f'''<header class="hero">
  <div class="eyebrow">Typography options · {esc(brand)}</div>
  <h1>{esc(spec.get("title") or f"Type for {brand}")}</h1>
  {f'<p class="lede">{esc(spec["brief"])}</p>' if spec.get("brief") else ""}
  <table class="summary"><thead><tr><th>Option</th><th>Fonts</th><th>Checks</th></tr></thead><tbody>{summary}</tbody></table>
  {('<div class="tablewrap"><table class="differ"><thead><tr><th>Pair</th><th>Different enough?</th><th>How they differ</th></tr></thead><tbody>'
    + "".join(f'<tr><td>{esc(r["check"])}</td><td><span class="badge {r["status"]}">{"Yes" if r["status"] == "pass" else "No"}</span></td>'
              f'<td>{esc(r["detail"])}</td></tr>' for r in distinct) + '</tbody></table></div>') if distinct else ""}
  {f'<details><summary>Assumptions</summary><ul>{assumptions}</ul></details>' if assumptions else ""}
  <p class="cap">Colors: {esc(pal["name"])}{"" if pal.get("_source") else " (no palette given, so the checks use greyscale)"}.
  Checks: WCAG 2.2, APCA (apca-w3 {apca_mod.VERSION}, screen text), the British Dyslexia Association Dyslexia Style Guide (2023), and measured letter shapes.</p>
</header>
{"".join(option_html(o, results[o["id"]], measured, spec, samples, style_guide(o, results[o["id"]], measured, spec, C, pal)) for o in spec["options"])}
<footer class="cap">APCA results use the apca-w3 {apca_mod.VERSION} font lookup table (reference font Barlow), interpolated between its 5-Lc rows, with weights rounded down to the 100 step.
Glyph likeness is the shared ink of two letters on one baseline; 80% or more is hard to tell apart. Letter shapes are measured at the regular weight.</footer>'''
    page = (tpl.replace("__TITLE__", esc(spec.get("page_title") or f"{brand} Type"))
               .replace("__FONTS__", google_link(spec))
               .replace("/*__EMBED__*/", embedded(spec, base))
               .replace("/*__TOKENS__*/", tokens(C))
               .replace("__LINKS__", links)
               .replace("__BODY__", body))
    Path(out).write_text(page)


# ---------- brand-builder export ----------

def brand_type(spec, o, measured, base, fonts_dir):
    """Option o as brand-builder's "type" block. Non-Google fonts are copied to fonts_dir and
    listed under "files" so build_brand.py can embed them."""
    out = {"title": spec.get("type_title") or "Type", "lede": o.get("why") or o.get("character") or ""}
    S = {**DEFAULT_SAMPLES, **(spec.get("samples") or {})}
    for slot in SLOTS:
        if slot not in o["fonts"]:
            continue
        f = o["fonts"][slot]
        ws = sorted(set(map(int, f.get("weights", []))) | {int(r.get("weight", 400)) for r in o["scale"] if r.get("font", "ui") == slot}) or [400]
        entry = {"family": f["family"], "weights": ws, "role": f.get("role") or {"display": "Display", "ui": "Interface", "mono": "Code"}[slot],
                 "sample": spec.get("wordmark") or spec.get("brand") if slot == "display" else (S["headline"] if slot == "ui" else "font-variant-numeric: tabular-nums;"),
                 "chars": "Aa Bb Gg Rr Il1 O0 0123456789", "use": f.get("use") or "",
                 "fallback": FALLBACK[measured[f["family"]]["category"]]}
        if f.get("source", "google") != "google":
            if not fonts_dir:
                raise ValueError(f'{f["family"]} isn\'t on Google Fonts: pass --fonts-dir so its files can be copied for brand-builder')
            d = Path(fonts_dir)
            d.mkdir(parents=True, exist_ok=True)
            entry["google"] = False
            entry["files"] = {}
            for w in ws:
                dest = d / f'{F.slug(f["family"], "-")}-{w}.ttf'
                if f.get("source") == "fontshare":
                    dest.write_bytes(F.fontshare_file(f["family"], w, CACHE))
                else:
                    shutil.copyfile(Path(base) / f["file"], dest)
                # relative to the brand spec, which sits next to the fonts folder
                entry["files"][str(w)] = f"{d.name}/{dest.name}"
        out[slot] = entry
    out["scale"] = [{"label": r["label"],
                     "spec": f'{o["fonts"].get(r.get("font", "ui"), o["fonts"]["ui"])["family"]} {r["size"]} / {r.get("weight", 400)}',
                     "font": r.get("font", "ui") if r.get("font", "ui") in o["fonts"] else "ui", "size": r["size"],
                     "weight": int(r.get("weight", 400)), "line": float(r.get("line", 1.4)),
                     **({"muted": True} if r.get("color") == "muted" or r.get("muted") else {}),
                     **({"tabular": True} if r.get("tabular") or r.get("use") == "data" else {}),
                     "sample": r.get("sample") or (S["headline"] if r.get("use") == "heading" else S["paragraph"][0])}
                    for r in o["scale"]]
    return out


# ---------- main ----------

def print_report(spec, pal, results, distinct=()):
    print(f'Type for {spec.get("brand", "the brand")}  (colors: {pal["name"]}{"" if pal.get("_source") else ", greyscale default"})')
    if distinct:
        print("\n== Are the options noticeably different?")
        for r in distinct:
            print(f'    {"ok  " if r["status"] == "pass" else "FAIL"}  {r["check"]}: {r["detail"]}')
            if r["fix"] and r["status"] != "pass":
                print(f'          → {r["fix"]}')
    for o in spec["options"]:
        rows = results[o["id"]]
        c = counts(rows)
        print(f'\n== Option {o["id"]}: {o["name"]}{"  [pick]" if o.get("pick") else ""}  '
              f'({c["pass"]} pass, {c["watch"]} watch, {c["fail"]} fail, {c["test"]} to test)')
        print("   " + " + ".join(f'{s}: {f["family"]}' for s, f in o["fonts"].items()))
        group = None
        for r in rows:
            if r["group"] != group:
                group = r["group"]
                print(f"  {group}")
            mark = {"pass": "ok  ", "watch": "WATCH", "fail": "FAIL", "test": "TEST"}[r["status"]]
            print(f'    {mark:<5} {r["check"]}: {r["detail"]}')
            if r["fix"] and r["status"] != "pass":
                print(f'          → {r["fix"]}')


def main():
    global APCA, CACHE
    ap = argparse.ArgumentParser(description="Check brand typography options and build a specimen page.")
    ap.add_argument("spec", nargs="?", help="type spec JSON (see references/type-spec.md)")
    ap.add_argument("--out", help="write the specimen page here")
    ap.add_argument("--brand-type", metavar="ID", help="print this option as brand-builder's type block")
    ap.add_argument("--fonts-dir", help="with --brand-type: where to copy non-Google font files")
    ap.add_argument("--font", help="measure one font and print the raw facts")
    ap.add_argument("--source", default="google", help="with --font: google or fontshare")
    ap.add_argument("--cache", help=f"font and APCA cache (default {CACHE})")
    args = ap.parse_args()
    if args.cache:
        CACHE = Path(args.cache)
    if args.font:
        m = F.measure({"family": args.font, "source": args.source}, CACHE)
        m["coverage"] = {k: f"{len(v)} missing" if v else "all" for k, v in m["coverage"].items()}
        print(json.dumps(m, indent=2, ensure_ascii=False))
        return 0
    if not args.spec:
        ap.error("give a type spec, or --font")
    try:
        spec, pal, base = load(args.spec)
        APCA = apca_mod.APCA(CACHE)
        C, _ = colors(pal, spec.get("primary"), spec.get("fill"))
        measured = {}
        for o in spec["options"]:
            for f in o["fonts"].values():
                if f["family"] not in measured:
                    measured[f["family"]] = F.measure(f, CACHE, base)
    except (ValueError, LookupError, OSError, KeyError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    results = {o["id"]: check_option(o, measured, spec, C) for o in spec["options"]}
    if args.brand_type:
        o = next((o for o in spec["options"] if o["id"] == args.brand_type), None)
        if not o:
            print(f"error: no option {args.brand_type}", file=sys.stderr)
            return 2
        fails = [r["check"] for r in results[o["id"]] if r["status"] == "fail"]
        if fails:
            print(f"warning: option {o['id']} still fails: {', '.join(fails)}. Fix them before handing it to brand-builder.", file=sys.stderr)
        try:
            print(json.dumps(brand_type(spec, o, measured, base, args.fonts_dir), indent=2, ensure_ascii=False))
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        return 0
    distinct = distinct_rows(spec, measured)
    print_report(spec, pal, results, distinct)
    if args.out:
        write_html(spec, pal, results, measured, base, args.out, distinct)
        print(f"\nWrote {args.out}")
    rows = [r for rs in results.values() for r in rs] + distinct
    return 1 if any(r["status"] == "fail" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
