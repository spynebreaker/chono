"""Chono's look: colors, type and the big clickable cards with simple drawn icons.

Plain Tk only (no extra packages). Icons are drawn with lines and shapes so they look the
same on Windows and macOS, whatever fonts are installed.
"""

from __future__ import annotations

import tkinter as tk

BG = "#f3efe7"        # warm paper
CARD = "#ffffff"
CARD_HOVER = "#eaf3f6"
CARD_PRESS = "#d5e8ee"
BORDER = "#ddd6c8"
INK = "#1d2a33"
MUTED = "#5d6870"
ACCENT = "#1f6f8b"     # deep teal-blue
ACCENT_SOFT = "#d9ebf1"
WARN = "#a14a2b"

FAMILY = "Segoe UI"


def pick_family(root: tk.Misc) -> str:
    from tkinter import font as tkfont

    global FAMILY
    have = set(tkfont.families(root))
    for f in ("Segoe UI", "SF Pro Text", "Helvetica Neue", "Arial", "DejaVu Sans", "Liberation Sans"):
        if f in have:
            FAMILY = f
            return f
    FAMILY = "TkDefaultFont"
    return FAMILY


def F(size: int, bold: bool = False) -> tuple:
    return (FAMILY, size, "bold") if bold else (FAMILY, size)


def _round_rect(c: tk.Canvas, x0, y0, x1, y1, r, **kw):
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1, x1 - r, y1,
           x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return c.create_polygon(pts, smooth=True, **kw)


# icons: each draws inside a box of side s at (x, y) ------------------------------------------

def _doc(c, x, y, s, col, fill=CARD):
    w, h, f = s * 0.62, s * 0.8, s * 0.2
    x0, y0 = x + (s - w) / 2, y + (s - h) / 2
    c.create_polygon(x0, y0, x0 + w - f, y0, x0 + w, y0 + f, x0 + w, y0 + h, x0, y0 + h,
                     outline=col, fill=fill, width=2.5, joinstyle="round")
    c.create_line(x0 + w - f, y0, x0 + w - f, y0 + f, x0 + w, y0 + f, fill=col, width=2.5)
    return x0, y0, w, h


def _lines(c, x0, y0, w, h, col, n=3, start=0.38):
    for i in range(n):
        yy = y0 + h * (start + i * 0.17)
        c.create_line(x0 + w * 0.2, yy, x0 + w * (0.8 if i < n - 1 else 0.55), yy, fill=col, width=2.5,
                      capstyle="round")


def icon_open(c, x, y, s, col):
    x0, y0, w, h = _doc(c, x, y, s, col)
    c.create_polygon(x0 + w * 0.38, y0 + h * 0.4, x0 + w * 0.38, y0 + h * 0.75, x0 + w * 0.7, y0 + h * 0.575,
                     fill=col, outline=col)


def icon_read(c, x, y, s, col):
    x0, y0, w, h = _doc(c, x, y, s, col)
    _lines(c, x0, y0, w, h, col)


def icon_scan(c, x, y, s, col):
    c.create_rectangle(x + s * 0.12, y + s * 0.42, x + s * 0.88, y + s * 0.78, outline=col, width=2.5)
    c.create_line(x + s * 0.22, y + s * 0.42, x + s * 0.32, y + s * 0.18, x + s * 0.72, y + s * 0.18,
                  fill=col, width=2.5, joinstyle="round")
    c.create_line(x + s * 0.22, y + s * 0.6, x + s * 0.78, y + s * 0.6, fill=col, width=2.5, capstyle="round")


def icon_search(c, x, y, s, col):
    c.create_oval(x + s * 0.16, y + s * 0.16, x + s * 0.62, y + s * 0.62, outline=col, width=3)
    c.create_line(x + s * 0.56, y + s * 0.56, x + s * 0.84, y + s * 0.84, fill=col, width=4, capstyle="round")


def icon_more(c, x, y, s, col):
    for i in range(3):
        cx = x + s * (0.26 + i * 0.24)
        c.create_oval(cx - s * 0.07, y + s * 0.43, cx + s * 0.07, y + s * 0.57, fill=col, outline=col)


def icon_make(c, x, y, s, col):
    x0, y0, w, h = _doc(c, x, y, s, col)
    cx, cy, r = x0 + w / 2, y0 + h * 0.58, s * 0.13
    c.create_line(cx - r, cy, cx + r, cy, fill=col, width=3, capstyle="round")
    c.create_line(cx, cy - r, cx, cy + r, fill=col, width=3, capstyle="round")


def icon_word(c, x, y, s, col):
    x0, y0, w, h = _doc(c, x, y, s, col)
    xs = [x0 + w * k for k in (0.18, 0.33, 0.5, 0.67, 0.82)]
    c.create_line(xs[0], y0 + h * 0.4, xs[1], y0 + h * 0.75, xs[2], y0 + h * 0.5, xs[3], y0 + h * 0.75,
                  xs[4], y0 + h * 0.4, fill=col, width=2.5, joinstyle="round", capstyle="round")


def icon_lock(c, x, y, s, col):
    c.create_rectangle(x + s * 0.24, y + s * 0.45, x + s * 0.76, y + s * 0.84, outline=col, fill=col, width=2)
    c.create_arc(x + s * 0.32, y + s * 0.16, x + s * 0.68, y + s * 0.62, start=0, extent=180, style="arc",
                 outline=col, width=3)
    c.create_line(x + s * 0.32, y + s * 0.39, x + s * 0.32, y + s * 0.46, fill=col, width=3)
    c.create_line(x + s * 0.68, y + s * 0.39, x + s * 0.68, y + s * 0.46, fill=col, width=3)
    c.create_oval(x + s * 0.46, y + s * 0.58, x + s * 0.54, y + s * 0.66, fill=CARD, outline=CARD)


def icon_blackout(c, x, y, s, col):
    x0, y0, w, h = _doc(c, x, y, s, col)
    _lines(c, x0, y0, w, h, col, n=3, start=0.3)
    c.create_rectangle(x0 + w * 0.15, y0 + h * 0.55, x0 + w * 0.85, y0 + h * 0.7, fill=INK, outline=INK)


def icon_compare(c, x, y, s, col):
    _doc(c, x - s * 0.13, y - s * 0.05, s * 0.8, col)
    _doc(c, x + s * 0.3, y + s * 0.22, s * 0.8, col)


def icon_sign(c, x, y, s, col):
    c.create_line(x + s * 0.12, y + s * 0.62, x + s * 0.24, y + s * 0.42, x + s * 0.34, y + s * 0.66,
                  x + s * 0.48, y + s * 0.36, x + s * 0.56, y + s * 0.64, x + s * 0.7, y + s * 0.5,
                  fill=col, width=2.5, smooth=True, capstyle="round")
    c.create_line(x + s * 0.12, y + s * 0.8, x + s * 0.88, y + s * 0.8, fill=col, width=2.5, capstyle="round")


def icon_edit(c, x, y, s, col):
    c.create_polygon(x + s * 0.2, y + s * 0.8, x + s * 0.24, y + s * 0.62, x + s * 0.66, y + s * 0.2,
                     x + s * 0.8, y + s * 0.34, x + s * 0.38, y + s * 0.76, outline=col, fill=CARD, width=2.5,
                     joinstyle="round")
    c.create_line(x + s * 0.58, y + s * 0.28, x + s * 0.72, y + s * 0.42, fill=col, width=2.5)


def icon_eye(c, x, y, s, col):
    c.create_oval(x + s * 0.1, y + s * 0.3, x + s * 0.9, y + s * 0.7, outline=col, width=2.5)
    c.create_oval(x + s * 0.38, y + s * 0.38, x + s * 0.62, y + s * 0.62, fill=col, outline=col)


def icon_stack(c, x, y, s, col):
    for i in range(3):
        d = s * 0.1 * i
        c.create_rectangle(x + s * 0.2 + d, y + s * 0.18 + d, x + s * 0.62 + d, y + s * 0.6 + d,
                           outline=col, fill=CARD, width=2.5)


def icon_shrink(c, x, y, s, col):
    c.create_rectangle(x + s * 0.1, y + s * 0.1, x + s * 0.9, y + s * 0.9, outline=col, width=2, dash=(4, 3))
    c.create_rectangle(x + s * 0.3, y + s * 0.3, x + s * 0.7, y + s * 0.7, outline=col, fill=col, width=2.5)


def icon_merge(c, x, y, s, col):
    _doc(c, x - s * 0.18, y - s * 0.12, s * 0.62, col)
    _doc(c, x + s * 0.18, y - s * 0.12, s * 0.62, col)
    c.create_line(x + s * 0.5, y + s * 0.56, x + s * 0.5, y + s * 0.92, fill=col, width=3, arrow="last",
                  arrowshape=(9, 11, 5))


def icon_print(c, x, y, s, col):
    c.create_rectangle(x + s * 0.3, y + s * 0.14, x + s * 0.7, y + s * 0.38, outline=col, width=2.5)
    c.create_rectangle(x + s * 0.12, y + s * 0.38, x + s * 0.88, y + s * 0.68, outline=col, fill=col, width=2.5)
    c.create_rectangle(x + s * 0.3, y + s * 0.56, x + s * 0.7, y + s * 0.86, outline=col, fill=CARD, width=2.5)


def icon_backup(c, x, y, s, col):
    c.create_oval(x + s * 0.18, y + s * 0.14, x + s * 0.82, y + s * 0.34, outline=col, width=2.5)
    c.create_line(x + s * 0.18, y + s * 0.24, x + s * 0.18, y + s * 0.76, fill=col, width=2.5)
    c.create_line(x + s * 0.82, y + s * 0.24, x + s * 0.82, y + s * 0.76, fill=col, width=2.5)
    c.create_arc(x + s * 0.18, y + s * 0.66, x + s * 0.82, y + s * 0.86, start=180, extent=180,
                 style="arc", outline=col, width=2.5)
    c.create_arc(x + s * 0.18, y + s * 0.42, x + s * 0.82, y + s * 0.62, start=180, extent=180,
                 style="arc", outline=col, width=2.5)


ICONS = {name[5:]: fn for name, fn in globals().items() if name.startswith("icon_")}


class Card(tk.Canvas):
    """A big rounded card: icon, title and a short line under it. The whole card is the button,
    and it also works with the keyboard (Tab to it, Enter or Space)."""

    def __init__(self, parent, title: str, hint: str, command, icon: str = "read",
                 width: int = 520, height: int = 92, title_size: int = 19) -> None:
        bg = parent.cget("bg")
        super().__init__(parent, width=width, height=height, bg=bg, highlightthickness=0,
                         cursor="hand2", takefocus=1)
        self.command = command
        self.w, self.h = width, height
        self.shadow = _round_rect(self, 3, 5, width - 1, height - 1, 18, fill=BORDER, outline="")
        self.body = _round_rect(self, 1, 1, width - 4, height - 5, 18, fill=CARD, outline=BORDER)
        s = height * 0.62
        ix, iy = 18, (height - 5 - s) / 2
        self.badge = self.create_oval(ix - 4, iy - 4, ix + s + 4, iy + s + 4, fill=ACCENT_SOFT, outline="")
        ICONS.get(icon, icon_read)(self, ix + s * 0.14, iy + s * 0.14, s * 0.72, ACCENT)
        tx = ix + s + 22
        wrap = width - tx - 16
        # title (may take two lines) with the hint right under it, centered as a block
        t = self.create_text(tx, 0, text=title, anchor="nw", font=F(title_size, True), fill=INK, width=wrap)
        items = [t]
        bottom = self.bbox(t)[3]
        if hint:
            hn = self.create_text(tx, bottom + 2, text=hint, anchor="nw", font=F(max(12, title_size - 6)),
                                  fill=MUTED, width=wrap)
            items.append(hn)
            bottom = self.bbox(hn)[3]
        top = self.bbox(t)[1]
        dy = ((height - 5) - (bottom - top)) / 2 - top
        for it in items:
            self.move(it, 0, dy)
        self.bind("<Enter>", lambda _e: self._paint(CARD_HOVER))
        self.bind("<Leave>", lambda _e: self._paint(CARD))
        self.bind("<ButtonPress-1>", lambda _e: self._paint(CARD_PRESS))
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<FocusIn>", lambda _e: self.itemconfig(self.body, outline=ACCENT, width=3))
        self.bind("<FocusOut>", lambda _e: self.itemconfig(self.body, outline=BORDER, width=1))
        self.bind("<Return>", lambda _e: self.command())
        self.bind("<space>", lambda _e: self.command())

    def _paint(self, color: str) -> None:
        self.itemconfig(self.body, fill=color)

    def _release(self, e) -> None:
        inside = 0 <= e.x <= self.w and 0 <= e.y <= self.h
        self._paint(CARD_HOVER if inside else CARD)
        if inside:
            self.after(10, self.command)


def link(parent, text: str, command, size: int = 14) -> tk.Label:
    """A quiet text button (Cerrar, Cancelar, Cambiar carpeta)."""
    lab = tk.Label(parent, text=text, font=F(size, True), fg=ACCENT, bg=parent.cget("bg"), cursor="hand2",
                   padx=14, pady=8)
    lab.bind("<Button-1>", lambda _e: command())
    lab.bind("<Enter>", lambda _e: lab.config(bg=ACCENT_SOFT))
    lab.bind("<Leave>", lambda _e: lab.config(bg=parent.cget("bg")))
    return lab


def header(parent, title: str, subtitle: str = "") -> None:
    tk.Label(parent, text=title, font=F(28, True), fg=INK, bg=parent.cget("bg")).pack(anchor="w", padx=28,
                                                                                      pady=(22, 0))
    if subtitle:
        tk.Label(parent, text=subtitle, font=F(14), fg=MUTED, bg=parent.cget("bg")).pack(anchor="w", padx=28,
                                                                                         pady=(0, 10))


def section(parent, text: str) -> tk.Label:
    return tk.Label(parent, text=text.upper(), font=F(12, True), fg=MUTED, bg=parent.cget("bg"))
