"""Fetch free fonts and measure them, using only the standard library (plus Pillow, if present, for glyph shapes).

Sources:
  google     Google Fonts, from the google/fonts GitHub repo (METADATA.pb plus the regular font file)
  fontshare  Fontshare (Indian Type Foundry), from its public API and CSS endpoint
  file       a local .ttf or .otf the user supplies, with the licence they name

measure(font) returns the facts the checks need: licence, category, weights and axes, character
coverage, OpenType features, x-height and cap height, figure widths, and (with Pillow) letter
spacing, apertures and how alike confusable letters look.
"""
import base64
import hashlib
import json
import re
import struct
import urllib.parse
import urllib.request
from pathlib import Path

try:
    from PIL import Image, ImageChops, ImageDraw, ImageFont
except ImportError:  # glyph-shape checks are skipped without Pillow
    Image = None

UA = {"User-Agent": "brand-typography/1.0 (+https://github.com/ItsAlwaysRaining/claude-skills)"}
GOOGLE_RAW = "https://raw.githubusercontent.com/google/fonts/main"
FONTSHARE_API = "https://api.fontshare.com/v2"

# What each licence allows, in the page's words. All of these allow commercial use, logos and web embedding.
LICENCES = {
    "OFL": ("SIL Open Font License 1.1", "Free for commercial use, logos, web and print, and embedding. "
            "Can't be sold on its own; modified versions need a new name."),
    "APACHE2": ("Apache License 2.0", "Free for commercial use, logos, web and print, and embedding."),
    "UFL": ("Ubuntu Font Licence 1.0", "Free for commercial use, logos, web and print, and embedding. "
            "Modified versions need a new name."),
    "ITF_FFL": ("ITF Free Font License", "Free for personal and commercial use, logos, web, apps and print. "
                "The font files can't be shared, sold or modified."),
}
GOOGLE_DIRS = {"ofl": "OFL", "apache": "APACHE2", "ufl": "UFL"}
CATEGORIES = {"SANS_SERIF": "sans", "SERIF": "serif", "DISPLAY": "display", "HANDWRITING": "script",
              "MONOSPACE": "mono", "sans": "sans", "serif": "serif", "slab": "serif", "display": "display",
              "script": "script", "handwritten": "script", "mono": "mono"}

# Character sets for the language check. Each set holds the letters a text in those languages actually needs.
CHARSETS = {
    "latin": "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
             "ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÑÒÓÔÕÖØÙÚÛÜÝßàáâãäåæçèéêëìíîïñòóôõöøùúûüýÿ"
             "&@#%‘’“”–—…€£$¢¥",
    "latin-ext": "ĀāĂăĄąĆćČčĎďĐđĒēĖėĘęĚěĞğĢģĪīĮįİıĶķĹĺĻļĽľŁłŃńŅņŇňŐőŒœŔŕŘřŚśŞşŠšŢţŤťŪūŮůŰűŲųŸŹźŻżŽžȘșȚț",
    "vietnamese": "ẠạẢảẤấẦầẨẩẪẫẬậẮắẰằẲẳẴẵẶặẸẹẺẻẼẽẾếỀềỂểỄễỆệỈỉỊịỌọỎỏỐốỒồỔổỖỗỘộỚớỜờỞởỠỡỢợỤụỦủỨứỪừỬửỮữỰựỲỳỴỵỶỷỸỹƠơƯưĐđ",
    "cyrillic": "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюя",
    "cyrillic-ext": "ЂЃЄЅІЇЈЉЊЋЌЎЏђѓєѕіїјљњћќўџҐґ",
    "greek": "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩαβγδεζηθικλμνξοπρσςτυφχψωάέήίόύώ",
}

# Letter groups that readers confuse. Mirror pairs are compared after flipping the first one.
CONFUSABLE = [("I", "l"), ("l", "1"), ("I", "1"), ("O", "0"), ("rn", "m"), ("cl", "d")]
MIRRORS = [("b", "d"), ("p", "q")]


# ---------- fetching ----------

def _get(url, binary=False):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        data = r.read()
    return data if binary else data.decode("utf-8")


def _cached(cache, name, url, binary=True):
    path = Path(cache) / name
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_get(url, binary=True))
    return path.read_bytes() if binary else path.read_text()


def slug(family, sep=""):
    return re.sub(r"[^a-z0-9]+", sep, family.lower()).strip(sep)


def parse_metadata_pb(text):
    """The few fields of a Google Fonts METADATA.pb that the checks use."""
    meta = {"fonts": [], "subsets": re.findall(r'^subsets: "([^"]+)"', text, re.M), "axes": []}
    for key in ("name", "license", "category"):
        m = re.search(rf'^{key}: "([^"]+)"', text, re.M)
        meta[key] = m.group(1) if m else None
    for block in re.findall(r"^fonts \{(.*?)^\}", text, re.M | re.S):
        f = dict(re.findall(r'(\w+): "?([^"\n]+)"?', block))
        meta["fonts"].append({"style": f.get("style"), "weight": int(f.get("weight", 400)), "filename": f.get("filename")})
    for block in re.findall(r"^axes \{(.*?)^\}", text, re.M | re.S):
        a = dict(re.findall(r'(\w+): "?([^"\n]+)"?', block))
        meta["axes"].append({"tag": a["tag"], "min": float(a["min_value"]), "max": float(a["max_value"])})
    return meta


def fetch_google(family, cache):
    s = slug(family)
    meta = None
    for d in GOOGLE_DIRS:
        try:
            text = _cached(cache, f"google/{s}/METADATA.pb", f"{GOOGLE_RAW}/{d}/{s}/METADATA.pb", binary=False)
            meta, folder = parse_metadata_pb(text), d
            break
        except Exception:
            continue
    if meta is None:
        raise LookupError(f'"{family}" isn\'t on Google Fonts (looked for {s} in ofl/, apache/ and ufl/).')
    uprights = [f for f in meta["fonts"] if f["style"] == "normal"] or meta["fonts"]
    regular = min(uprights, key=lambda f: abs(f["weight"] - 400))
    files = {}
    for f in uprights:
        files.setdefault(f["filename"], f["weight"])
    data = _cached(cache, f"google/{s}/{regular['filename']}",
                   f"{GOOGLE_RAW}/{folder}/{s}/{urllib.parse.quote(regular['filename'])}")
    wght = next((a for a in meta["axes"] if a["tag"] == "wght"), None)
    weights = list(range(int(wght["min"]), int(wght["max"]) + 1, 100)) if wght else sorted({f["weight"] for f in uprights})
    return {
        "family": meta["name"] or family, "source": "google",
        "licence": (meta["license"] or GOOGLE_DIRS[folder]).upper(),
        "category": CATEGORIES.get(meta["category"] or "", "sans"), "subsets": meta["subsets"],
        "axes": meta["axes"], "weights": weights, "italic": any(f["style"] == "italic" for f in meta["fonts"]),
        "regular": data, "regular_weight": regular["weight"],
        "url": f"https://fonts.google.com/specimen/{family.replace(' ', '+')}",
    }


def _fontshare_record(family, cache):
    s = slug(family, "-")
    path = Path(cache) / "fontshare" / "fonts.json"
    if not path.exists():
        fonts, page = [], 1
        while True:
            d = json.loads(_get(f"{FONTSHARE_API}/fonts?limit=100&page={page}"))
            fonts += d["fonts"]
            if not d.get("has_more"):
                break
            page += 1
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(fonts))
    for f in json.loads(path.read_text()):
        if f["slug"] == s or f["name"].lower() == family.lower():
            return f
    raise LookupError(f'"{family}" isn\'t on Fontshare (looked for {s}).')


def fontshare_file(family, weight, cache):
    """A Fontshare weight as TTF bytes, from its CSS endpoint."""
    rec = _fontshare_record(family, cache)
    css = _cached(cache, f"fontshare/{rec['slug']}/{weight}.css",
                  f"{FONTSHARE_API}/css?f[]={rec['slug']}@{weight}", binary=False)
    m = re.search(r"url\('([^']+\.ttf)'\)", css)
    if not m:
        raise LookupError(f"Fontshare has no TTF for {family} {weight}.")
    url = ("https:" + m.group(1)) if m.group(1).startswith("//") else m.group(1)
    return _cached(cache, f"fontshare/{rec['slug']}/{weight}.ttf", url)


def fetch_fontshare(family, cache):
    rec = _fontshare_record(family, cache)
    uprights = [st for st in rec["styles"] if not st["is_italic"] and not st["is_variable"]]
    weights = sorted({st["weight"]["weight"] for st in uprights})
    regular = min(weights, key=lambda w: abs(w - 400))
    axes = [{"tag": a["property"], "min": a["range_left"], "max": a["range_right"]} for a in rec.get("axes") or []]
    return {
        "family": rec["name"], "source": "fontshare",
        "licence": (rec.get("license_type") or "").upper(),
        "category": CATEGORIES.get((rec.get("category") or "").lower(), "sans"),
        "languages": rec.get("languages") or "", "axes": axes, "weights": weights,
        "italic": any(st["is_italic"] for st in rec["styles"]),
        "regular": fontshare_file(family, regular, cache), "regular_weight": regular,
        "url": f"https://www.fontshare.com/fonts/{rec['slug']}",
    }


def fetch_file(spec, base):
    path = (Path(base) / spec["file"]).resolve()
    data = path.read_bytes()
    t = Sfnt(data)
    return {
        "family": spec["family"], "source": "file", "path": str(path),
        "licence": (spec.get("licence") or spec.get("license") or "").upper().replace(" ", "_"),
        "category": spec.get("category", "sans"), "axes": t.axes(), "weights": spec.get("available") or t.weights(),
        "italic": False, "regular": data, "regular_weight": t.os2_weight(), "url": spec.get("url"),
    }


def fetch(spec, cache, base="."):
    src = spec.get("source", "google")
    if src == "google":
        return fetch_google(spec["family"], cache)
    if src == "fontshare":
        return fetch_fontshare(spec["family"], cache)
    if src == "file":
        return fetch_file(spec, base)
    raise ValueError(f'Unknown font source "{src}". Use google, fontshare or file.')


def embed_css(spec, cache, base="."):
    """@font-face rules with the font inlined, for fonts that can't load from Google Fonts' stylesheet."""
    rules = []
    for w in spec.get("weights", [400]):
        if spec.get("source") == "fontshare":
            data = fontshare_file(spec["family"], w, cache)
        else:
            data = (Path(base) / spec["file"]).read_bytes()
        b64 = base64.b64encode(data).decode()
        rules.append(f'@font-face {{ font-family: "{spec["family"]}"; font-weight: {w}; font-style: normal; '
                     f'font-display: swap; src: url(data:font/ttf;base64,{b64}) format("truetype"); }}')
        if spec.get("source") == "file":
            break  # one file covers every weight it has
    return "\n".join(rules)


# ---------- reading the font file ----------

class Sfnt:
    """Just enough of a TrueType/OpenType reader for metrics, coverage and feature tags."""

    def __init__(self, data):
        self.data = data
        tag = data[:4]
        if tag == b"ttcf":
            data = data  # first font of a collection
            off = struct.unpack(">I", data[12:16])[0]
        elif tag in (b"\x00\x01\x00\x00", b"OTTO", b"true"):
            off = 0
        else:
            raise ValueError("Not a TTF or OTF file (WOFF and WOFF2 aren't supported).")
        n = struct.unpack(">H", data[off + 4:off + 6])[0]
        self.tables = {}
        for i in range(n):
            rec = data[off + 12 + 16 * i: off + 28 + 16 * i]
            t, _, o, ln = struct.unpack(">4sIII", rec)
            self.tables[t.decode("latin-1")] = (o, ln)

    def table(self, tag):
        if tag not in self.tables:
            return None
        o, ln = self.tables[tag]
        return self.data[o:o + ln]

    def upm(self):
        return struct.unpack(">H", self.table("head")[18:20])[0]

    def os2(self):
        t = self.table("OS/2")
        if not t:
            return {}
        v = struct.unpack(">H", t[:2])[0]
        out = {"version": v, "weight": struct.unpack(">H", t[4:6])[0], "fsType": struct.unpack(">H", t[8:10])[0]}
        if v >= 2 and len(t) >= 90:
            out["xHeight"], out["capHeight"] = struct.unpack(">hh", t[86:90])
        return out

    def os2_weight(self):
        return self.os2().get("weight", 400)

    def weights(self):
        ax = next((a for a in self.axes() if a["tag"] == "wght"), None)
        return list(range(int(ax["min"]), int(ax["max"]) + 1, 100)) if ax else [self.os2_weight()]

    def axes(self):
        t = self.table("fvar")
        if not t:
            return []
        off, _, count, size = struct.unpack(">HHHH", t[4:12])
        out = []
        for i in range(count):
            tag, mn, _, mx = struct.unpack(">4siii", t[off + i * size: off + i * size + 16])
            out.append({"tag": tag.decode(), "min": mn / 65536, "max": mx / 65536})
        return out

    def cmap(self):
        """{codepoint: glyph id} from the best Unicode subtable (format 4 or 12)."""
        t = self.table("cmap")
        n = struct.unpack(">H", t[2:4])[0]
        subs = []
        for i in range(n):
            pid, eid, off = struct.unpack(">HHI", t[4 + 8 * i: 12 + 8 * i])
            fmt = struct.unpack(">H", t[off:off + 2])[0]
            if (pid, eid) in ((3, 10), (0, 4), (0, 6)) and fmt == 12:
                subs.append((0, off, fmt))
            elif (pid, eid) in ((3, 1), (0, 3), (0, 1), (0, 0)) and fmt == 4:
                subs.append((1, off, fmt))
        _, off, fmt = min(subs)
        out = {}
        if fmt == 12:
            ngroups = struct.unpack(">I", t[off + 12: off + 16])[0]
            for g in range(ngroups):
                s, e, gid = struct.unpack(">III", t[off + 16 + 12 * g: off + 28 + 12 * g])
                for c in range(s, e + 1):
                    out[c] = gid + c - s
            return out
        seg2 = struct.unpack(">H", t[off + 6: off + 8])[0]
        ends = off + 14
        starts = ends + seg2 + 2
        deltas = starts + seg2
        ranges = deltas + seg2
        for i in range(seg2 // 2):
            end = struct.unpack(">H", t[ends + 2 * i: ends + 2 * i + 2])[0]
            start = struct.unpack(">H", t[starts + 2 * i: starts + 2 * i + 2])[0]
            delta = struct.unpack(">h", t[deltas + 2 * i: deltas + 2 * i + 2])[0]
            ro = struct.unpack(">H", t[ranges + 2 * i: ranges + 2 * i + 2])[0]
            for c in range(start, end + 1):
                if c == 0xFFFF:
                    continue
                if ro == 0:
                    gid = (c + delta) & 0xFFFF
                else:
                    p = ranges + 2 * i + ro + 2 * (c - start)
                    gid = struct.unpack(">H", t[p:p + 2])[0]
                    gid = (gid + delta) & 0xFFFF if gid else 0
                if gid:
                    out[c] = gid
        return out

    def advances(self):
        hhea, hmtx = self.table("hhea"), self.table("hmtx")
        n = struct.unpack(">H", hhea[34:36])[0]
        adv = [struct.unpack(">H", hmtx[4 * i: 4 * i + 2])[0] for i in range(n)]
        return adv

    def features(self):
        tags = set()
        for name in ("GSUB", "GPOS"):
            t = self.table(name)
            if not t:
                continue
            off = struct.unpack(">H", t[6:8])[0]
            n = struct.unpack(">H", t[off:off + 2])[0]
            for i in range(n):
                tags.add(t[off + 2 + 6 * i: off + 6 + 6 * i].decode("latin-1"))
        return sorted(tags)

    def name(self, nid):
        t = self.table("name")
        if not t:
            return ""
        count, soff = struct.unpack(">HH", t[2:6])
        for i in range(count):
            pid, eid, lid, n, ln, o = struct.unpack(">HHHHHH", t[6 + 12 * i: 18 + 12 * i])
            if n != nid:
                continue
            raw = t[soff + o: soff + o + ln]
            if pid in (0, 3):
                return raw.decode("utf-16-be", "replace")
            return raw.decode("latin-1")
        return ""


# ---------- glyph shapes (Pillow) ----------

PX = 96  # render size for shape comparisons


def _render(font, text, flip=False):
    """Ink of `text` on a shared baseline, as a 1-bit image cropped to its own width."""
    asc, desc = font.getmetrics()
    w = int(font.getlength(text)) + PX
    img = Image.new("L", (w, asc + desc + 8), 0)
    ImageDraw.Draw(img).text((PX // 2, 4), text, font=font, fill=255)
    bbox = img.getbbox()
    if not bbox:
        return None
    img = img.crop((bbox[0], 0, bbox[2], img.height)).point(lambda v: 255 if v > 127 else 0)
    return img.transpose(Image.FLIP_LEFT_RIGHT) if flip else img


def likeness(font, a, b, flip=False):
    """How alike two glyphs (or letter pairs) look: shared ink over all ink, with both
    centred on a shared baseline. 1.0 is identical."""
    ia, ib = _render(font, a, flip), _render(font, b)
    if ia is None or ib is None:
        return 0.0
    w = max(ia.width, ib.width)

    def pad(im):
        c = Image.new("L", (w, im.height), 0)
        c.paste(im, ((w - im.width) // 2, 0))
        return c
    ia, ib = pad(ia), pad(ib)
    inter = ImageChops.multiply(ia, ib).histogram()[255]
    union = ImageChops.lighter(ia, ib).histogram()[255]
    return inter / union if union else 0.0


def aperture(font, ch):
    """How open a letter's mouth is: the largest gap down the right side of `c` or `e`,
    as a share of the letter's height."""
    img = _render(font, ch)
    if img is None:
        return None
    bbox = img.getbbox()
    top, bottom = bbox[1], bbox[3]
    x = img.width - 1 - max(1, img.width // 12)
    col = [img.getpixel((x, y)) for y in range(top, bottom)]
    best = run = 0
    for v in col:
        run = run + 1 if v == 0 else 0
        best = max(best, run)
    return best / (bottom - top)


def spacing(font):
    """Average side space between lowercase letters, as a share of their average ink width,
    and the word space as a multiple of that letter space (both BDA measures)."""
    gaps, inks = [], []
    for ch in "abcdefghijklmnopqrstuvwxyz":
        img = _render(font, ch)
        if img is None:
            continue
        gaps.append(font.getlength(ch) - img.width)
        inks.append(img.width)
    gap, ink = sum(gaps) / len(gaps), sum(inks) / len(inks)
    return {"letter": gap / ink, "word": font.getlength(" ") / gap if gap > 0 else None, "ink_em": ink / PX, "gap_em": gap / PX}


PROFILE_WORD = "hamburgefonstiv"


def profile(font):
    """What makes a face look like itself at a glance, measured on the regular weight:
    width (average advance per letter, in em), weight (share of ink inside the letters' box),
    stroke contrast (thickest vertical stroke of o over its thinnest horizontal one) and
    the opening of c. Two fonts that differ on none of these read as the same font."""
    width = font.getlength(PROFILE_WORD) / len(PROFILE_WORD) / PX
    img = _render(font, PROFILE_WORD)
    bbox = img.getbbox()
    box = img.crop(bbox)
    weight = box.histogram()[255] / (box.width * box.height)
    o = _render(font, "o")
    ob = o.getbbox()
    o = o.crop(ob)
    mid_y, mid_x = o.height // 2, o.width // 2
    row = [o.getpixel((x, mid_y)) for x in range(o.width)]
    col = [o.getpixel((mid_x, y)) for y in range(o.height)]

    def first_run(px):
        n = 0
        for v in px:
            if v:
                n += 1
            elif n:
                break
        return n
    vert, horiz = first_run(row), first_run(col)
    return {"width": round(width, 3), "weight": round(weight, 3),
            "contrast": round(vert / horiz, 2) if horiz else None, "aperture": round(aperture(font, "c") or 0, 2)}


def measure(spec, cache, base="."):
    f = fetch(spec, cache, base)
    t = Sfnt(f["regular"])
    upm, os2 = t.upm(), t.os2()
    cmap = t.cmap()
    adv = t.advances()
    digits = [adv[min(cmap.get(ord(d), 0), len(adv) - 1)] for d in "0123456789"] if all(ord(d) in cmap for d in "0123456789") else []
    xh, cap = os2.get("xHeight"), os2.get("capHeight")
    out = {
        "family": f["family"], "source": f["source"], "licence": f["licence"], "category": f["category"],
        "weights": f["weights"], "axes": f["axes"], "italic": f["italic"], "url": f.get("url"),
        "fsType": os2.get("fsType", 0), "licence_text": t.name(13)[:300], "licence_url": t.name(14),
        "coverage": {k: [c for c in v if ord(c) not in cmap] for k, v in CHARSETS.items()},
        "features": t.features(), "tabular_default": bool(digits) and len(set(digits)) == 1,
        "x_height": round(xh / upm, 3) if xh else None, "cap_height": round(cap / upm, 3) if cap else None,
        "sha1": hashlib.sha1(f["regular"]).hexdigest()[:10],
    }
    if Image is None:
        out["shapes"] = None
        return out
    import io
    font = ImageFont.truetype(io.BytesIO(f["regular"]), PX)
    # measure variable fonts at their text setting: regular weight, 16px optical size
    try:
        values = []
        for ax, meta in zip(font.get_variation_axes(), t.axes()):
            pick = {"wght": 400, "opsz": 16}.get(meta["tag"], ax["default"])
            values.append(min(max(pick, ax["minimum"]), ax["maximum"]))
        if values:
            font.set_variation_by_axes(values)
    except Exception:
        pass  # static font, or Pillow built without variation support: the default instance is fine
    if not out["x_height"]:
        x, h = font.getbbox("x"), font.getbbox("H")
        out["x_height"] = round((x[3] - x[1]) / PX, 3)
        out["cap_height"] = round((h[3] - h[1]) / PX, 3)
    out["shapes"] = {
        "confusable": [{"a": a, "b": b, "likeness": round(likeness(font, a, b), 2)} for a, b in CONFUSABLE],
        "mirrors": [{"a": a, "b": b, "likeness": round(likeness(font, a, b, flip=True), 2)} for a, b in MIRRORS],
        "aperture": {ch: round(aperture(font, ch) or 0, 2) for ch in "ce"},
        "spacing": {k: (round(v, 3) if v is not None else None) for k, v in spacing(font).items()},
        "profile": profile(font),
    }
    return out
