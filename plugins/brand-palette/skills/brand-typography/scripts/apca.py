"""APCA lightness contrast (Lc) and its minimum font sizes, read from the published apca-w3 package.

APCA is copyright Myndex Research and licensed to the W3C for WCAG web content only, so this repo
doesn't copy its code or tables. This module downloads apca-w3 0.1.9 from unpkg once, checks the
file against the package's published SHA-256, and reads the constants (SA98G) and the font lookup
table (fontMatrixAscend) from it. Use the results for screen text, which is what APCA covers.
"""
import base64
import hashlib
import math
import re
import urllib.request
from pathlib import Path

VERSION = "0.1.9"
URL = f"https://unpkg.com/apca-w3@{VERSION}/src/apca-w3.js"
SHA256 = "eYBjNWTMV0mq1gjxY60aAVr1f1c3Ka8uoIEDRFiref4="  # unpkg integrity for src/apca-w3.js
NON_TEXT, PROHIBITED = 777, 999


class APCA:
    def __init__(self, cache):
        path = Path(cache) / "apca" / f"apca-w3-{VERSION}.js"
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            req = urllib.request.Request(URL, headers={"User-Agent": "brand-typography/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                path.write_bytes(r.read())
        src = path.read_bytes()
        if base64.b64encode(hashlib.sha256(src).digest()).decode() != SHA256:
            path.unlink()
            raise RuntimeError(f"apca-w3 {VERSION} didn't match its published checksum. Run again to re-download.")
        js = src.decode()
        block = re.search(r"const SA98G = \{(.*?)\n\s*\};", js, re.S).group(1)
        self.k = {m.group(1): float(m.group(2)) for m in re.finditer(r"(\w+):\s*([\d.]+)\s*,", block)}
        table = re.search(r"const fontMatrixAscend = \[(.*?)\n\s*\];", js, re.S).group(1)
        rows = re.findall(r"\[([^\[\]]+)\]", table)
        self.weights = [int(x) for x in rows[0].split(",")[1:]]
        self.table = [[float(x) for x in r.split(",")] for r in rows[1:]]

    def y(self, hex_):
        h = hex_.lstrip("#")
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
        k = self.k
        return k["sRco"] * r ** k["mainTRC"] + k["sGco"] * g ** k["mainTRC"] + k["sBco"] * b ** k["mainTRC"]

    def lc(self, text_hex, bg_hex):
        """Signed Lc: positive for dark text on light, negative for light text on dark."""
        k = self.k
        ty, by = self.y(text_hex), self.y(bg_hex)
        ty = ty if ty > k["blkThrs"] else ty + (k["blkThrs"] - ty) ** k["blkClmp"]
        by = by if by > k["blkThrs"] else by + (k["blkThrs"] - by) ** k["blkClmp"]
        if abs(by - ty) < k["deltaYmin"]:
            return 0.0
        if by > ty:
            sapc = (by ** k["normBG"] - ty ** k["normTXT"]) * k["scaleBoW"]
            return 0.0 if sapc < k["loClip"] else (sapc - k["loBoWoffset"]) * 100
        sapc = (by ** k["revBG"] - ty ** k["revTXT"]) * k["scaleWoB"]
        return 0.0 if sapc > -k["loClip"] else (sapc + k["loWoBoffset"]) * 100

    def min_size(self, lc, weight):
        """Smallest font size in px APCA allows at this contrast and weight. Like apca-w3's
        fontLookupAPCA, sizes are interpolated between the table's 5-Lc rows; the weight is
        rounded down to its 100 step so the answer is never too generous.
        Returns NON_TEXT (777) or PROHIBITED (999) when no text size works."""
        lc = min(abs(lc), self.table[-1][0])
        col = 1 + self.weights.index(max(100, min(900, int(weight) // 100 * 100)))
        lo = next((r for r in reversed(self.table) if r[0] <= lc), None)
        if lo is None:
            return PROHIBITED
        hi = next((r for r in self.table if r[0] > lc), None)
        if hi is None or lo[col] >= NON_TEXT or hi[col] >= NON_TEXT:
            return lo[col]
        return round(lo[col] + (hi[col] - lo[col]) * (lc - lo[0]) / (hi[0] - lo[0]), 2)


def round_lc(lc):
    return int(math.floor(abs(lc) + 0.5))
