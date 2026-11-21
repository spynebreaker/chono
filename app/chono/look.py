"""Chono's look (2026-11 redesign): smooth rounded surfaces, soft shadows and line icons drawn
with Pillow, so the window looks the same, and current, on Windows and macOS.

Tk draws text; everything with curves or shadows is a picture made here at 4x and scaled
down, which Tk alone can't anti-alias. Colors follow Chono's icon: cream paper, charcoal ink
and the copper of the axe-head bookmark.
"""

from __future__ import annotations

import math
import tkinter as tk
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter, ImageTk

BG = "#f6f2eb"           # warm paper
SURFACE = "#ffffff"
SURFACE_HOVER = "#fbf6f1"
INK = "#23272b"
MUTED = "#6b7177"
FAINT = "#9aa0a5"
BORDER = "#e7dfd3"
ACCENT = "#a95632"        # copper, as in the icon
ACCENT_DARK = "#8c4224"
ACCENT_SOFT = "#f6e7dd"
CHARCOAL = "#2c3136"
GOOD = "#3c7a55"

FAMILY = "Segoe UI"
SCALE = 1.0  # screen pixels per design pixel (Windows display scaling)
SS = 4       # supersampling for anti-aliased drawing


def setup(root: tk.Tk) -> None:
    """Pick the font and measure the screen's scaling once, before building any window."""
    from tkinter import font as tkfont

    global FAMILY, SCALE
    have = set(tkfont.families(root))
    for f in ("Segoe UI Variable Text", "Segoe UI", "SF Pro Text", "Helvetica Neue", "Inter",
              "Noto Sans", "DejaVu Sans", "Arial"):
        if f in have:
            FAMILY = f
            break
    try:
        SCALE = max(1.0, root.winfo_fpixels("1i") / 96.0)
    except tk.TclError:
        SCALE = 1.0


def F(size: int, weight: str = "normal") -> tuple:
    if weight == "bold":
        return (FAMILY, size, "bold")
    return (FAMILY, size)


def px(v: float) -> int:
    return int(round(v * SCALE))


def _rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


# --- pictures -------------------------------------------------------------------------------

@lru_cache(maxsize=256)
def _surface(w: int, h: int, r: int, fill: str, bg: str, border: str = "", shadow: int = 0,
             ring: str = "", ring_w: int = 0) -> Image.Image:
    """A rounded rectangle on `bg`, with an optional border, focus ring and soft shadow below.
    w, h, r and shadow are screen pixels."""
    k = SS
    img = Image.new("RGB", (w * k, h * k), _rgb(bg))
    pad = shadow
    if shadow:
        sh = Image.new("L", (w * k, h * k), 0)
        ImageDraw.Draw(sh).rounded_rectangle(
            [pad * k, (pad + shadow // 2) * k, (w - pad) * k, (h - pad // 3) * k], r * k, fill=70)
        sh = sh.filter(ImageFilter.GaussianBlur(shadow * k * 0.6))
        dark = Image.new("RGB", img.size, (90, 70, 50))
        img = Image.composite(dark, img, sh)
    d = ImageDraw.Draw(img)
    box = [pad * k, pad * k, (w - pad) * k - 1, (h - pad - (shadow // 2)) * k - 1] if shadow else \
        [0, 0, w * k - 1, h * k - 1]
    if ring:
        d.rounded_rectangle(box, r * k, fill=_rgb(ring))
        inset = ring_w * k
        box = [box[0] + inset, box[1] + inset, box[2] - inset, box[3] - inset]
        d.rounded_rectangle(box, max(1, r - ring_w) * k, fill=_rgb(fill))
    elif border:
        d.rounded_rectangle(box, r * k, fill=_rgb(fill), outline=_rgb(border), width=max(1, k))
    else:
        d.rounded_rectangle(box, r * k, fill=_rgb(fill))
    return img.resize((w, h), Image.LANCZOS)


def surface(w: int, h: int, r: int, fill: str, bg: str, **kw) -> ImageTk.PhotoImage:
    return ImageTk.PhotoImage(_surface(w, h, r, fill, bg, **kw))


@lru_cache(maxsize=256)
def _icon(name: str, size: int, color: str, bg: str, badge: str = "") -> Image.Image:
    k = SS * 2
    s = size * k
    img = Image.new("RGB", (s, s), _rgb(bg))
    d = ImageDraw.Draw(img)
    if badge:
        d.ellipse([0, 0, s - 1, s - 1], fill=_rgb(badge))
        inner = s * 0.56
        off = (s - inner) / 2
    else:
        inner, off = s, 0
    draw = ICONS.get(name, ICONS["doc"])
    draw(d, off, off, inner, _rgb(color), _rgb(badge or bg))
    return img.resize((size, size), Image.LANCZOS)


def icon(name: str, size: int, color: str = ACCENT, bg: str = SURFACE, badge: str = "") -> ImageTk.PhotoImage:
    return ImageTk.PhotoImage(_icon(name, px(size), color, bg, badge))


def app_logo(size: int) -> ImageTk.PhotoImage | None:
    from pathlib import Path

    try:
        img = Image.open(Path(__file__).with_name("icono.png")).convert("RGBA")
    except OSError:
        return None
    return ImageTk.PhotoImage(img.resize((px(size), px(size)), Image.LANCZOS))


# --- line icons (own drawings; each fills a box of side s at x, y) --------------------------

def _w(s: float) -> int:
    return max(1, int(s * 0.085))


def _page(d, x, y, s, c, bg, fold=True):
    w, h = s * 0.64, s * 0.82
    x0, y0 = x + (s - w) / 2, y + (s - h) / 2
    f = s * 0.2
    lw = _w(s)
    pts = [(x0, y0), (x0 + w - f, y0), (x0 + w, y0 + f), (x0 + w, y0 + h), (x0, y0 + h)]
    d.polygon(pts, fill=bg)
    d.line(pts + [pts[0]], fill=c, width=lw, joint="curve")
    if fold:
        d.line([(x0 + w - f, y0), (x0 + w - f, y0 + f), (x0 + w, y0 + f)], fill=c, width=lw, joint="curve")
    for p in pts:
        d.ellipse([p[0] - lw / 2, p[1] - lw / 2, p[0] + lw / 2, p[1] + lw / 2], fill=c)
    return x0, y0, w, h


def _text_lines(d, x0, y0, w, h, c, n=3, top=0.42):
    lw = _w(w / 0.64)
    for i in range(n):
        yy = y0 + h * (top + i * 0.16)
        x1 = x0 + w * (0.78 if i < n - 1 else 0.55)
        d.line([(x0 + w * 0.22, yy), (x1, yy)], fill=c, width=lw)
        for xx in (x0 + w * 0.22, x1):
            d.ellipse([xx - lw / 2, yy - lw / 2, xx + lw / 2, yy + lw / 2], fill=c)


def i_doc(d, x, y, s, c, bg):
    _page(d, x, y, s, c, bg)


def i_open(d, x, y, s, c, bg):
    lw = _w(s)
    # an open folder with a page coming out
    d.rounded_rectangle([x + s * 0.08, y + s * 0.3, x + s * 0.92, y + s * 0.86], s * 0.08, outline=c, width=lw)
    d.line([(x + s * 0.08, y + s * 0.38), (x + s * 0.08, y + s * 0.22), (x + s * 0.36, y + s * 0.22),
            (x + s * 0.44, y + s * 0.3)], fill=c, width=lw, joint="curve")
    d.line([(x + s * 0.3, y + s * 0.56), (x + s * 0.7, y + s * 0.56)], fill=c, width=lw)
    d.line([(x + s * 0.3, y + s * 0.7), (x + s * 0.58, y + s * 0.7)], fill=c, width=lw)


def i_read(d, x, y, s, c, bg):
    x0, y0, w, h = _page(d, x, y, s, c, bg)
    _text_lines(d, x0, y0, w, h, c)


def i_scan(d, x, y, s, c, bg):
    lw = _w(s)
    d.rounded_rectangle([x + s * 0.08, y + s * 0.42, x + s * 0.92, y + s * 0.8], s * 0.07, outline=c, width=lw)
    d.line([(x + s * 0.22, y + s * 0.42), (x + s * 0.34, y + s * 0.16), (x + s * 0.74, y + s * 0.16)],
           fill=c, width=lw, joint="curve")
    d.line([(x + s * 0.2, y + s * 0.61), (x + s * 0.8, y + s * 0.61)], fill=c, width=lw)
    d.ellipse([x + s * 0.72, y + s * 0.67, x + s * 0.8, y + s * 0.75], fill=c)


def i_search(d, x, y, s, c, bg):
    lw = int(_w(s) * 1.25)
    d.ellipse([x + s * 0.12, y + s * 0.12, x + s * 0.64, y + s * 0.64], outline=c, width=lw)
    d.line([(x + s * 0.57, y + s * 0.57), (x + s * 0.86, y + s * 0.86)], fill=c, width=int(lw * 1.2))
    e = s * 0.86
    d.ellipse([x + e - lw * 0.6, y + e - lw * 0.6, x + e + lw * 0.6, y + e + lw * 0.6], fill=c)


def i_grid(d, x, y, s, c, bg):
    for i in range(2):
        for j in range(2):
            x0, y0 = x + s * (0.12 + i * 0.42), y + s * (0.12 + j * 0.42)
            d.rounded_rectangle([x0, y0, x0 + s * 0.32, y0 + s * 0.32], s * 0.07, outline=c, width=_w(s))


def i_make(d, x, y, s, c, bg):
    x0, y0, w, h = _page(d, x, y, s, c, bg)
    cx, cy, r = x0 + w / 2, y0 + h * 0.6, s * 0.14
    d.line([(cx - r, cy), (cx + r, cy)], fill=c, width=_w(s))
    d.line([(cx, cy - r), (cx, cy + r)], fill=c, width=_w(s))


def i_word(d, x, y, s, c, bg):
    x0, y0, w, h = _page(d, x, y, s, c, bg)
    xs = [x0 + w * k for k in (0.2, 0.35, 0.5, 0.65, 0.8)]
    ys = [y0 + h * k for k in (0.42, 0.74, 0.52, 0.74, 0.42)]
    d.line(list(zip(xs, ys)), fill=c, width=_w(s), joint="curve")


def i_merge(d, x, y, s, c, bg):
    _page(d, x - s * 0.16, y - s * 0.1, s * 0.7, c, bg)
    _page(d, x + s * 0.3, y - s * 0.1, s * 0.7, c, bg)
    lw = _w(s)
    d.line([(x + s * 0.5, y + s * 0.62), (x + s * 0.5, y + s * 0.92)], fill=c, width=lw)
    d.line([(x + s * 0.38, y + s * 0.8), (x + s * 0.5, y + s * 0.92), (x + s * 0.62, y + s * 0.8)],
           fill=c, width=lw, joint="curve")


def i_shrink(d, x, y, s, c, bg):
    lw = _w(s)
    for (ax, ay), (bx, by) in [((0.14, 0.14), (0.4, 0.4)), ((0.86, 0.14), (0.6, 0.4)),
                               ((0.14, 0.86), (0.4, 0.6)), ((0.86, 0.86), (0.6, 0.6))]:
        d.line([(x + s * ax, y + s * ay), (x + s * bx, y + s * by)], fill=c, width=lw)
        hx, hy = x + s * bx, y + s * by
        dx = 0.13 * s * (1 if ax < 0.5 else -1)
        dy = 0.13 * s * (1 if ay < 0.5 else -1)
        d.line([(hx - dx, hy), (hx, hy), (hx, hy - dy)], fill=c, width=lw, joint="curve")


def i_eye(d, x, y, s, c, bg):
    lw = _w(s)
    pts = [(x + s * (0.08 + 0.84 * t / 20), y + s * (0.5 - 0.26 * math.sin(math.pi * t / 20))) for t in range(21)]
    pts2 = [(px_, 2 * (y + s * 0.5) - py_) for px_, py_ in pts]
    d.line(pts, fill=c, width=lw, joint="curve")
    d.line(pts2, fill=c, width=lw, joint="curve")
    d.ellipse([x + s * 0.38, y + s * 0.38, x + s * 0.62, y + s * 0.62], fill=c)


def i_edit(d, x, y, s, c, bg):
    lw = _w(s)
    p = [(x + s * 0.2, y + s * 0.8), (x + s * 0.24, y + s * 0.62), (x + s * 0.64, y + s * 0.22),
         (x + s * 0.78, y + s * 0.36), (x + s * 0.38, y + s * 0.76), (x + s * 0.2, y + s * 0.8)]
    d.line(p, fill=c, width=lw, joint="curve")
    d.line([(x + s * 0.56, y + s * 0.3), (x + s * 0.7, y + s * 0.44)], fill=c, width=lw)


def i_compare(d, x, y, s, c, bg):
    _page(d, x - s * 0.14, y - s * 0.06, s * 0.78, c, bg)
    _page(d, x + s * 0.32, y + s * 0.24, s * 0.78, c, bg)


def i_stack(d, x, y, s, c, bg):
    for i in (2, 1, 0):
        o = s * 0.1 * i
        _page(d, x + o - s * 0.08, y + o - s * 0.08, s * 0.8, c, bg, fold=(i == 0))


def i_lock(d, x, y, s, c, bg):
    lw = _w(s)
    d.rounded_rectangle([x + s * 0.2, y + s * 0.44, x + s * 0.8, y + s * 0.88], s * 0.08, fill=c)
    d.arc([x + s * 0.3, y + s * 0.12, x + s * 0.7, y + s * 0.6], 180, 360, fill=c, width=lw)
    d.line([(x + s * 0.3, y + s * 0.36), (x + s * 0.3, y + s * 0.46)], fill=c, width=lw)
    d.line([(x + s * 0.7, y + s * 0.36), (x + s * 0.7, y + s * 0.46)], fill=c, width=lw)
    d.ellipse([x + s * 0.45, y + s * 0.58, x + s * 0.55, y + s * 0.68], fill=bg)


def i_blackout(d, x, y, s, c, bg):
    x0, y0, w, h = _page(d, x, y, s, c, bg)
    _text_lines(d, x0, y0, w, h, c, n=2, top=0.38)
    d.rectangle([x0 + w * 0.16, y0 + h * 0.68, x0 + w * 0.84, y0 + h * 0.82], fill=c)


def i_sign(d, x, y, s, c, bg):
    lw = _w(s)
    pts = [(x + s * (0.12 + 0.6 * t / 30), y + s * (0.55 - 0.16 * math.sin(t / 30 * 3.6 * math.pi) - 0.05 * t / 30))
           for t in range(31)]
    d.line(pts, fill=c, width=lw, joint="curve")
    d.line([(x + s * 0.12, y + s * 0.82), (x + s * 0.88, y + s * 0.82)], fill=c, width=lw)


def i_print(d, x, y, s, c, bg):
    lw = _w(s)
    d.rectangle([x + s * 0.3, y + s * 0.12, x + s * 0.7, y + s * 0.36], outline=c, width=lw)
    d.rounded_rectangle([x + s * 0.1, y + s * 0.36, x + s * 0.9, y + s * 0.7], s * 0.07, fill=c)
    d.rectangle([x + s * 0.3, y + s * 0.56, x + s * 0.7, y + s * 0.88], fill=bg, outline=c, width=lw)


def i_backup(d, x, y, s, c, bg):
    lw = _w(s)
    d.ellipse([x + s * 0.18, y + s * 0.1, x + s * 0.82, y + s * 0.32], outline=c, width=lw)
    d.line([(x + s * 0.18, y + s * 0.21), (x + s * 0.18, y + s * 0.79)], fill=c, width=lw)
    d.line([(x + s * 0.82, y + s * 0.21), (x + s * 0.82, y + s * 0.79)], fill=c, width=lw)
    d.arc([x + s * 0.18, y + s * 0.68, x + s * 0.82, y + s * 0.9], 0, 180, fill=c, width=lw)
    d.arc([x + s * 0.18, y + s * 0.39, x + s * 0.82, y + s * 0.61], 0, 180, fill=c, width=lw)


def i_back(d, x, y, s, c, bg):
    lw = int(_w(s) * 1.2)
    d.line([(x + s * 0.82, y + s * 0.5), (x + s * 0.2, y + s * 0.5)], fill=c, width=lw)
    d.line([(x + s * 0.45, y + s * 0.24), (x + s * 0.18, y + s * 0.5), (x + s * 0.45, y + s * 0.76)],
           fill=c, width=lw, joint="curve")


def i_folder(d, x, y, s, c, bg):
    lw = _w(s)
    d.line([(x + s * 0.1, y + s * 0.8), (x + s * 0.1, y + s * 0.2), (x + s * 0.4, y + s * 0.2),
            (x + s * 0.48, y + s * 0.3), (x + s * 0.9, y + s * 0.3), (x + s * 0.9, y + s * 0.8),
            (x + s * 0.1, y + s * 0.8)], fill=c, width=lw, joint="curve")


def i_clock(d, x, y, s, c, bg):
    lw = _w(s)
    d.ellipse([x + s * 0.12, y + s * 0.12, x + s * 0.88, y + s * 0.88], outline=c, width=lw)
    d.line([(x + s * 0.5, y + s * 0.28), (x + s * 0.5, y + s * 0.5), (x + s * 0.66, y + s * 0.62)],
           fill=c, width=lw, joint="curve")


def i_chevron(d, x, y, s, c, bg):
    lw = int(_w(s) * 1.2)
    d.line([(x + s * 0.38, y + s * 0.2), (x + s * 0.66, y + s * 0.5), (x + s * 0.38, y + s * 0.8)],
           fill=c, width=lw, joint="curve")


ICONS = {name[2:]: fn for name, fn in dict(globals()).items() if name.startswith("i_")}
ICONS["more"] = i_grid


# --- widgets --------------------------------------------------------------------------------

class _Pressable(tk.Canvas):
    """A canvas that acts as a button: hover, press, keyboard (Tab, Enter, Space)."""

    def __init__(self, parent, w: int, h: int, command, bg: str = "", **kw) -> None:
        super().__init__(parent, width=w, height=h, bg=bg or parent.cget("bg"), highlightthickness=0,
                         cursor="hand2", takefocus=1, **kw)
        self.command, self.w, self.h = command, w, h
        self.hover = self.focused = False
        self.bind("<Enter>", lambda _e: self._set(hover=True))
        self.bind("<Leave>", lambda _e: self._set(hover=False))
        self.bind("<FocusIn>", lambda _e: self._set(focused=True))
        self.bind("<FocusOut>", lambda _e: self._set(focused=False))
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Return>", lambda _e: self.command())
        self.bind("<space>", lambda _e: self.command())

    def _set(self, **state) -> None:
        for k, v in state.items():
            setattr(self, k, v)
        self.paint()

    def paint(self) -> None:  # pragma: no cover - drawn by subclasses
        pass

    def _release(self, e) -> None:
        if 0 <= e.x <= self.w and 0 <= e.y <= self.h:
            self.after(10, self.command)


class Button(_Pressable):
    """A rounded button: primary (copper), secondary (white with a border) or quiet (text)."""

    def __init__(self, parent, text: str, command, kind: str = "primary", icon_name: str = "",
                 size: int = 16, width: int = 0, height: int = 52, bg: str = "") -> None:
        f = F(size, "bold")
        probe = tk.Label(parent, text=text, font=f)
        tw = probe.winfo_reqwidth()
        probe.destroy()
        ic = px(22) if icon_name else 0
        w = width and px(width) or tw + ic + (px(10) if ic else 0) + px(44)
        h = px(height)
        super().__init__(parent, w, h, command, bg=bg)
        self.text, self.kind, self.font, self.icon_name, self.ic = text, kind, f, icon_name, ic
        self.paint()

    def colors(self):
        if self.kind == "primary":
            return (ACCENT_DARK if self.hover else ACCENT), "#ffffff", ""
        if self.kind == "secondary":
            return (SURFACE_HOVER if self.hover else SURFACE), INK, BORDER
        return (ACCENT_SOFT if self.hover else self.cget("bg")), ACCENT, ""

    def paint(self) -> None:
        fill, fg, border = self.colors()
        self.delete("all")
        ring = ACCENT if self.focused and self.kind != "primary" else (CHARCOAL if self.focused else "")
        self._bg = surface(self.w, self.h, self.h // 2, fill, self.cget("bg"), border=border,
                           ring=ring, ring_w=px(2) if ring else 0)
        self.create_image(0, 0, image=self._bg, anchor="nw")
        x = self.w / 2
        if self.icon_name:
            probe_w = self.w - px(44) - self.ic - px(10)
            x0 = (self.w - (self.ic + px(10) + probe_w)) / 2
            self._ic = ImageTk.PhotoImage(_icon(self.icon_name, self.ic, fg, fill))
            self.create_image(x0, self.h / 2, image=self._ic, anchor="w")
            self.create_text(x0 + self.ic + px(10), self.h / 2, text=self.text, font=self.font, fill=fg, anchor="w")
        else:
            self.create_text(x, self.h / 2, text=self.text, font=self.font, fill=fg)


class Tile(_Pressable):
    """A big action: icon in a copper circle, title and a short line, on a white card."""

    def __init__(self, parent, title: str, hint: str, icon_name: str, command,
                 width: int = 300, height: int = 210, compact: bool = False) -> None:
        w, h = px(width), px(height)
        super().__init__(parent, w, h, command)
        self.title, self.hint, self.icon_name, self.compact = title, hint, icon_name, compact
        self.paint()

    def paint(self) -> None:
        self.delete("all")
        sh = px(10)
        fill = SURFACE_HOVER if self.hover else SURFACE
        self._bg = surface(self.w, self.h, px(22), fill, self.cget("bg"), border=BORDER, shadow=sh,
                           ring=ACCENT if self.focused else "", ring_w=px(3) if self.focused else 0)
        self.create_image(0, 0, image=self._bg, anchor="nw")
        inner_w = self.w - 2 * sh - px(48)
        if self.compact:
            isz = 52
            badge = ACCENT if self.hover else ACCENT_SOFT
            color = "#ffffff" if self.hover else ACCENT
            self._ic = ImageTk.PhotoImage(_icon(self.icon_name, px(isz), color, fill, badge))
            cy = (self.h - sh) / 2
            self.create_image(sh + px(20), cy, image=self._ic, anchor="w")
            tx = sh + px(20) + px(isz) + px(16)
            t = self.create_text(tx, 0, text=self.title, font=F(15, "bold"), fill=INK, anchor="nw",
                                 width=self.w - tx - sh - px(14))
            hn = self.create_text(tx, 0, text=self.hint, font=F(12), fill=MUTED, anchor="nw",
                                  width=self.w - tx - sh - px(14))
            tb, hb = self.bbox(t), self.bbox(hn)
            if not self.hint:
                self.delete(hn)
                hb = (0, 0, 0, 0)
            total = (tb[3] - tb[1]) + (px(2) + (hb[3] - hb[1]) if self.hint else 0)
            top = cy - total / 2
            self.coords(t, tx, top)
            self.coords(hn, tx, top + (tb[3] - tb[1]) + px(2))
            return
        isz = 64
        badge = ACCENT if self.hover else ACCENT_SOFT
        color = "#ffffff" if self.hover else ACCENT
        self._ic = ImageTk.PhotoImage(_icon(self.icon_name, px(isz), color, fill, badge))
        x0 = sh + px(24)
        self.create_image(x0, sh + px(24), image=self._ic, anchor="nw")
        y = sh + px(24) + px(isz) + px(16)
        t = self.create_text(x0, y, text=self.title, font=F(17, "bold"), fill=INK, anchor="nw", width=inner_w)
        y = self.bbox(t)[3] + px(4)
        self.create_text(x0, y, text=self.hint, font=F(13), fill=MUTED, anchor="nw", width=inner_w)


class SearchBar(tk.Frame):
    """The big search box: magnifier, a wide entry and a Buscar button, on a white pill."""

    def __init__(self, parent, on_search, placeholder: str, width: int = 920) -> None:
        super().__init__(parent, bg=parent.cget("bg"))
        self.on_search, self.placeholder = on_search, placeholder
        w, h = px(width), px(76)
        self.canvas = tk.Canvas(self, width=w, height=h, bg=parent.cget("bg"), highlightthickness=0)
        self.canvas.pack()
        self.w, self.h = w, h
        self.focused = False
        self._paint()
        self._ic = icon("search", 26, MUTED, SURFACE)
        self.canvas.create_image(px(30), h / 2 - px(3), image=self._ic, anchor="w")
        self.var = tk.StringVar()
        self.entry = tk.Entry(self.canvas, textvariable=self.var, font=F(18), relief="flat", bd=0,
                              bg=SURFACE, fg=INK, insertbackground=INK, highlightthickness=0)
        self.button = Button(self.canvas, "Buscar", self._go, "primary", size=15, height=50, bg=SURFACE)
        bw = self.button.w
        # The button sits clear of the box's rounded end, so its square corners never show.
        self.canvas.create_window(px(70), h / 2 - px(3), window=self.entry, anchor="w",
                                  width=w - px(70) - bw - px(40), height=px(40))
        self.canvas.create_window(w - px(24) - bw, h / 2 - px(3), window=self.button, anchor="w")
        self._show_placeholder()
        self.entry.bind("<FocusIn>", self._focus_in)
        self.entry.bind("<FocusOut>", self._focus_out)
        self.entry.bind("<Return>", lambda _e: self._go())
        self.entry.bind("<Configure>", self._to_start, add="+")
        self.entry.bind("<Map>", self._to_start, add="+")
        self.canvas.bind("<Button-1>", lambda _e: self.entry.focus_set())

    def _paint(self) -> None:
        self.canvas.delete("bg")
        self._bg = surface(self.w, self.h, px(30), SURFACE, self.canvas.cget("bg"),
                           border=BORDER, shadow=px(8),
                           ring=ACCENT if self.focused else "", ring_w=px(2) if self.focused else 0)
        self.canvas.create_image(0, 0, image=self._bg, anchor="nw", tags="bg")
        self.canvas.tag_lower("bg")

    def _show_placeholder(self) -> None:
        if not self.var.get():
            self.entry.config(fg=FAINT)
            self.var.set(self.placeholder)
            self._placeholder = True
            self._to_start()

    def _to_start(self, _e=None) -> None:
        """Show the text from its first letter. Set before the box had its size (macOS), it
        stayed scrolled to its end and looked empty."""
        if getattr(self, "_placeholder", False):
            self.entry.icursor(0)
            self.entry.xview_moveto(0)

    def _focus_in(self, _e=None) -> None:
        self.focused = True
        self._paint()
        if getattr(self, "_placeholder", False):
            self.var.set("")
            self.entry.config(fg=INK)
            self._placeholder = False

    def _focus_out(self, _e=None) -> None:
        self.focused = False
        self._paint()
        self._show_placeholder()

    def text(self) -> str:
        return "" if getattr(self, "_placeholder", False) else self.var.get().strip()

    def set_text(self, text: str) -> None:
        self._placeholder = False
        self.entry.config(fg=INK)
        self.var.set(text)

    def _go(self) -> None:
        t = self.text()
        if t:
            self.on_search(t)
        else:
            self.entry.focus_set()


class Row(_Pressable):
    """A full-width row in a list: icon, title, a muted line, and an action word on the right."""

    def __init__(self, parent, title: str, detail: str, icon_name: str, command, action: str = "Abrir",
                 width: int = 920, height: int = 72, bold_word: str = "") -> None:
        super().__init__(parent, px(width), px(height), command)
        self.title, self.detail, self.icon_name, self.action = title, detail, icon_name, action
        self.paint()

    def paint(self) -> None:
        self.delete("all")
        fill = SURFACE_HOVER if self.hover else SURFACE
        self._bg = surface(self.w, self.h, px(16), fill, self.cget("bg"), border=BORDER,
                           ring=ACCENT if self.focused else "", ring_w=px(2) if self.focused else 0)
        self.create_image(0, 0, image=self._bg, anchor="nw")
        self._ic = ImageTk.PhotoImage(_icon(self.icon_name, px(40), ACCENT, fill, ACCENT_SOFT))
        self.create_image(px(16), self.h / 2, image=self._ic, anchor="w")
        tx = px(72)
        aw = px(120)
        t = self.create_text(tx, 0, text=self.title, font=F(15, "bold"), fill=INK, anchor="nw",
                             width=self.w - tx - aw)
        dn = self.create_text(tx, 0, text=self.detail, font=F(12), fill=MUTED, anchor="nw",
                              width=self.w - tx - aw)
        tb, db = self.bbox(t), self.bbox(dn)
        total = (tb[3] - tb[1]) + (db[3] - db[1]) + px(2)
        top = self.h / 2 - total / 2
        self.coords(t, tx, top)
        self.coords(dn, tx, top + (tb[3] - tb[1]) + px(2))
        self.create_text(self.w - px(48), self.h / 2, text=self.action, font=F(14, "bold"),
                         fill=ACCENT, anchor="e")
        self._ch = ImageTk.PhotoImage(_icon("chevron", px(20), ACCENT, fill))
        self.create_image(self.w - px(20), self.h / 2, image=self._ch, anchor="e")


class Scroll(tk.Frame):
    """A vertically scrolling area; put children in `.inner`. The mouse wheel scrolls it."""

    def __init__(self, parent, height: int = 400) -> None:
        super().__init__(parent, bg=parent.cget("bg"))
        self.canvas = tk.Canvas(self, bg=parent.cget("bg"), highlightthickness=0, height=px(height))
        self.bar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=parent.cget("bg"))
        self.inner.bind("<Configure>", self._fit)
        self._win = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: (self.canvas.itemconfig(self._win, width=e.width), self._fit()))
        self.bind_all("<MouseWheel>", self._wheel, add="+")
        self.bind_all("<Button-4>", lambda _e: self.bar.winfo_ismapped() and self.canvas.yview_scroll(-3, "units"), add="+")
        self.bind_all("<Button-5>", lambda _e: self.bar.winfo_ismapped() and self.canvas.yview_scroll(3, "units"), add="+")

    def _fit(self, _e=None) -> None:
        """Scroll only when the content is taller than the area; the bar shows only then."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        need = self.inner.winfo_reqheight() > self.canvas.winfo_height() + 2
        if need and not self.bar.winfo_ismapped():
            self.bar.pack(side="right", fill="y")
        elif not need and self.bar.winfo_ismapped():
            self.bar.pack_forget()
            self.canvas.yview_moveto(0)

    def _wheel(self, e) -> None:
        if not self.bar.winfo_ismapped():
            return
        if not self.winfo_ismapped():
            return
        step = -1 if e.delta > 0 else 1
        self.canvas.yview_scroll(step * 3, "units")


def title(parent, text: str, size: int = 30) -> tk.Label:
    return tk.Label(parent, text=text, font=F(size, "bold"), fg=INK, bg=parent.cget("bg"))


def label(parent, text: str, size: int = 14, color: str = MUTED, bold: bool = False, wrap: int = 0) -> tk.Label:
    return tk.Label(parent, text=text, font=F(size, "bold" if bold else "normal"), fg=color,
                    bg=parent.cget("bg"), justify="left", wraplength=px(wrap) if wrap else 0)


def section(parent, text: str) -> tk.Label:
    return tk.Label(parent, text=text, font=F(15, "bold"), fg=INK, bg=parent.cget("bg"))
