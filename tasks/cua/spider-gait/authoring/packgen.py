"""Small, dependency-free drawing/PDF/XLSX helpers for the materials pack.

The build host has no PIL, matplotlib, reportlab or openpyxl, so this module
writes PNG (zlib), PDF (base-14 text plus embedded raster) and XLSX (minimal
OOXML) by hand. Authoring-only; nothing here ships inside the task images.
"""
import struct
import zlib

import numpy as np


# --------------------------------------------------------------------------
# 5x7 bitmap font (digits, capitals, and the punctuation used on drawings)
# --------------------------------------------------------------------------
GLYPHS = {
    " ": ["00000"] * 7,
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01111"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
    "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "11011", "10001"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    ".": ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
    ",": ["00000", "00000", "00000", "00000", "00110", "00100", "01000"],
    "-": ["00000", "00000", "00000", "01110", "00000", "00000", "00000"],
    "+": ["00000", "00100", "00100", "11111", "00100", "00100", "00000"],
    "=": ["00000", "00000", "11111", "00000", "11111", "00000", "00000"],
    "/": ["00001", "00010", "00010", "00100", "01000", "01000", "10000"],
    "(": ["00010", "00100", "01000", "01000", "01000", "00100", "00010"],
    ")": ["01000", "00100", "00010", "00010", "00010", "00100", "01000"],
    ":": ["00000", "01100", "01100", "00000", "01100", "01100", "00000"],
    "%": ["11001", "11010", "00100", "00100", "01000", "10110", "00110"],
    "?": ["01110", "10001", "00001", "00010", "00100", "00000", "00100"],
    ">": ["01000", "00100", "00010", "00001", "00010", "00100", "01000"],
    "<": ["00010", "00100", "01000", "10000", "01000", "00100", "00010"],
    "*": ["00000", "10101", "01110", "11111", "01110", "10101", "00000"],
}


class Canvas:
    """RGB canvas with 3x supersampling; coordinates are pixels, y down."""

    def __init__(self, width, height, background=(255, 255, 255), scale=3):
        self.w, self.h, self.s = int(width), int(height), int(scale)
        self.buf = np.empty((self.h * self.s, self.w * self.s, 3), dtype=np.float32)
        self.buf[:] = np.asarray(background, dtype=np.float32)

    def _plot(self, x, y, color):
        xi, yi = int(round(x * self.s)), int(round(y * self.s))
        r = self.s // 2 + 1
        if 0 <= yi < self.buf.shape[0] and 0 <= xi < self.buf.shape[1]:
            self.buf[max(0, yi - r):yi + r + 1, max(0, xi - r):xi + r + 1] = color

    def line(self, x0, y0, x1, y1, color=(0, 0, 0), width=1.0):
        steps = max(2, int(max(abs(x1 - x0), abs(y1 - y0)) * self.s * 1.5))
        for i in range(steps + 1):
            t = i / steps
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            r = int(width * self.s)
            if r <= 1:
                self._plot(x, y, color)
            else:
                for dx in range(-r, r + 1):
                    for dy in range(-r, r + 1):
                        self._plot(x + dx / self.s, y + dy / self.s, color)

    def dashed(self, x0, y0, x1, y1, color=(120, 120, 120), dash=8, gap=6):
        length = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
        if length == 0:
            return
        pos = 0.0
        while pos < length:
            end = min(pos + dash, length)
            self.line(x0 + (x1 - x0) * pos / length, y0 + (y1 - y0) * pos / length,
                      x0 + (x1 - x0) * end / length, y0 + (y1 - y0) * end / length, color)
            pos += dash + gap

    def circle(self, cx, cy, r, color=(0, 0, 0), fill=None, width=1.0):
        n = max(24, int(r * 6))
        if fill is not None:
            ys, xs = np.mgrid[-r:r:1 / self.s, -r:r:1 / self.s] if r > 1 else (None, None)
            if ys is not None:
                yy = np.round((cy + ys) * self.s).astype(int)
                xx = np.round((cx + xs) * self.s).astype(int)
                mask = (xx >= 0) & (xx < self.buf.shape[1]) & (yy >= 0) & (yy < self.buf.shape[0]) & (xs ** 2 + ys ** 2 <= r * r)
                self.buf[yy[mask], xx[mask]] = np.asarray(fill, dtype=np.float32)
        pts = [(cx + r * np.cos(2 * np.pi * i / n), cy + r * np.sin(2 * np.pi * i / n)) for i in range(n + 1)]
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            self.line(ax, ay, bx, by, color, width)

    def rect(self, x0, y0, x1, y1, color=(0, 0, 0), fill=None, width=1.0):
        if fill is not None:
            ya, yb = sorted((int(y0 * self.s), int(y1 * self.s)))
            xa, xb = sorted((int(x0 * self.s), int(x1 * self.s)))
            ya, yb = max(0, ya), min(self.buf.shape[0], yb)
            xa, xb = max(0, xa), min(self.buf.shape[1], xb)
            self.buf[ya:yb, xa:xb] = np.asarray(fill, dtype=np.float32)
        self.line(x0, y0, x1, y0, color, width)
        self.line(x1, y0, x1, y1, color, width)
        self.line(x1, y1, x0, y1, color, width)
        self.line(x0, y1, x0, y0, color, width)

    def text(self, x, y, value, scale=2, color=(0, 0, 0), spacing=1):
        """Draw text with the 5x7 font; y is the top of the glyph box."""
        cx = x
        for ch in str(value).upper():
            g = GLYPHS.get(ch, GLYPHS["?"])
            for row, bits in enumerate(g):
                for col, bit in enumerate(bits):
                    if bit == "1":
                        for dy in range(scale):
                            for dx in range(scale):
                                px = cx + (col * scale + dx) / 1.0
                                py = y + (row * scale + dy) / 1.0
                                yi = int(round(py * self.s))
                                xi = int(round(px * self.s))
                                if 0 <= yi < self.buf.shape[0] and 0 <= xi < self.buf.shape[1]:
                                    self.buf[yi, xi] = color
            cx += (5 + spacing) * scale
        return cx

    def text_width(self, value, scale=2, spacing=1):
        return len(str(value)) * (5 + spacing) * scale

    def text_center(self, cx, y, value, scale=2, color=(0, 0, 0)):
        self.text(cx - self.text_width(value, scale) / 2, y, value, scale, color)

    def png(self):
        s = self.s
        img = self.buf.reshape(self.h, s, self.w, s, 3).mean(axis=(1, 3))
        data = np.clip(img, 0, 255).astype(np.uint8)
        return encode_png(data)


def encode_png(rgb):
    h, w, _ = rgb.shape
    raw = b"".join(b"\x00" + rgb[y].tobytes() for y in range(h))

    def chunk(tag, payload):
        return (struct.pack(">I", len(payload)) + tag + payload
                + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


# --------------------------------------------------------------------------
# minimal PDF writer (base-14 Helvetica, vector lines, embedded PNG raster)
# --------------------------------------------------------------------------
class PDF:
    def __init__(self, width, height):
        self.w, self.h = width, height
        self.pages = []          # list of content streams
        self.images = []         # list of (name, rgb array)
        self._ops = []

    def _esc(self, text):
        return (str(text).replace("\\", r"\\").replace("(", r"\(")
                .replace(")", r"\)"))

    def text(self, x, y, value, size=10, bold=False):
        font = "F2" if bold else "F1"
        self._ops.append(f"BT /{font} {size} Tf {x:.2f} {self.h - y:.2f} Td ({self._esc(value)}) Tj ET")

    def line(self, x0, y0, x1, y1, width=0.6):
        self._ops.append(f"{width} w {x0:.2f} {self.h - y0:.2f} m {x1:.2f} {self.h - y1:.2f} l S")

    def rect(self, x0, y0, x1, y1, fill=None, stroke=(0, 0, 0), width=0.6):
        if fill is not None:
            self._ops.append(f"{fill[0]} {fill[1]} {fill[2]} rg "
                             f"{x0:.2f} {self.h - y1:.2f} {x1 - x0:.2f} {y1 - y0:.2f} re f")
        self._ops.append(f"{stroke[0]} {stroke[1]} {stroke[2]} RG {width} w "
                         f"{x0:.2f} {self.h - y1:.2f} {x1 - x0:.2f} {y1 - y0:.2f} re S")

    def image(self, name, x, y, w, h):
        self._ops.append(f"q {w:.2f} 0 0 {h:.2f} {x:.2f} {self.h - y - h:.2f} cm /{name} Do Q")

    def add_image(self, name, rgb):
        self.images.append((name, rgb))

    def new_page(self):
        if self._ops:
            self.pages.append("\n".join(self._ops))
        self._ops = []

    def save(self, path):
        self.new_page()
        pages = len(self.pages)
        image_objs = {name: 3 + 2 * pages + i for i, (name, _) in enumerate(self.images)}
        font_num = 3 + 2 * pages + len(self.images)
        xobjects = " ".join(f"/{n} {o} 0 R" for n, o in image_objs.items())
        objs = []          # object body at index i has PDF object number i + 1
        objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
        kids = " ".join(f"{3 + 2 * i} 0 R" for i in range(pages))
        objs.append(f"<< /Type /Pages /Kids [{kids}] /Count {pages} >>".encode())
        for i, stream in enumerate(self.pages):
            objs.append((f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.w} {self.h}] "
                         f"/Resources << /Font << /F1 {font_num} 0 R /F2 {font_num + 1} 0 R >> "
                         f"/XObject << {xobjects} >> >> /Contents {4 + 2 * i} 0 R >>").encode())
            data = stream.encode("latin-1")
            objs.append(b"<< /Length " + str(len(data)).encode() + b" >>\nstream\n" + data + b"\nendstream")
        for name, rgb in self.images:
            h, w, _ = rgb.shape
            raw = b"".join(b"\x00" + rgb[y].tobytes() for y in range(h))
            payload = zlib.compress(raw, 9)
            objs.append((f"<< /Type /XObject /Subtype /Image /Width {w} /Height {h} "
                         f"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode "
                         f"/Length {len(payload)} >>\nstream\n").encode() + payload + b"\nendstream")
        objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")

        out = bytearray(b"%PDF-1.4\n")
        offsets = []
        for i, body in enumerate(objs):
            offsets.append(len(out))
            out += f"{i + 1} 0 obj\n".encode() + body + b"\nendobj\n"
        xref = len(out)
        out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
        for off in offsets:
            out += f"{off:010d} 00000 n \n".encode()
        out += (f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n"
                f"{xref}\n%%EOF\n").encode()
        with open(path, "wb") as fh:
            fh.write(out)


# --------------------------------------------------------------------------
# minimal XLSX writer (inline strings; one worksheet is enough)
# --------------------------------------------------------------------------
def write_xlsx(path, sheet_name, rows, col_widths=None):
    def esc(value):
        return (str(value).replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;"))

    xml_rows = []
    for r, row in enumerate(rows, start=1):
        cells = []
        for c, value in enumerate(row, start=1):
            ref = f"{chr(64 + c)}{r}"
            if isinstance(value, (int, float)):
                cells.append(f'<c r="{ref}"><v>{value}</v></c>')
            else:
                cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{esc(value)}</t></is></c>')
        xml_rows.append(f'<row r="{r}">' + "".join(cells) + "</row>")
    cols = ""
    if col_widths:
        cols = "<cols>" + "".join(
            f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>'
            for i, w in enumerate(col_widths, start=1)) + "</cols>"
    sheet = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             f'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
             f'{cols}<sheetData>' + "".join(xml_rows) + "</sheetData></worksheet>")
    files = {
        "[Content_Types].xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '</Types>'),
        "_rels/.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>'),
        "xl/workbook.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f'<sheets><sheet name="{esc(sheet_name)}" sheetId="1" r:id="rId1"/></sheets></workbook>'),
        "xl/_rels/workbook.xml.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '</Relationships>'),
        "xl/worksheets/sheet1.xml": sheet,
    }
    with zlib_zip(path) as zf:
        for name, data in files.items():
            zf.writestr(name, data)


class zlib_zip:
    """Tiny wrapper so write_xlsx reads clearly."""
    def __init__(self, path):
        import zipfile
        self.path = path
        self.zf = None

    def __enter__(self):
        import zipfile
        self.zf = zipfile.ZipFile(self.path, "w", zipfile.ZIP_DEFLATED)
        return self.zf

    def __exit__(self, *exc):
        self.zf.close()
        return False
