"""Invisible text layer for pages read by the handwriting engine.

Kraken writes ALTO XML: one box per word, in image pixels. Here those words
become hidden text placed over the page picture, so the PDF can be searched
and copied like any scanned record that went through OCR.
"""

from __future__ import annotations

import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Word:
    x: float
    y: float
    w: float
    h: float
    text: str


def clean_text(s: str) -> str:
    """NFC form, no stray combining marks, only characters Helvetica can hold."""
    s = unicodedata.normalize("NFC", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.encode("latin-1", "ignore").decode("latin-1").strip()


def alto_words(path: Path) -> tuple[list[Word], float, float]:
    """Words and page size (pixels) from an ALTO file."""
    root = ET.parse(path).getroot()
    page = next(e for e in root.iter() if e.tag.endswith("}Page") or e.tag == "Page")
    words = []
    for e in root.iter():
        if not (e.tag.endswith("}String") or e.tag == "String"):
            continue
        t = clean_text(e.get("CONTENT", ""))
        if t:
            words.append(Word(float(e.get("HPOS", 0)), float(e.get("VPOS", 0)),
                              float(e.get("WIDTH", 0)), float(e.get("HEIGHT", 0)), t))
    return words, float(page.get("WIDTH")), float(page.get("HEIGHT"))


def overlay_pdf(words: list[Word], img_w: float, img_h: float,
                page_w: float, page_h: float, dst: Path) -> Path:
    """One-page PDF with the words as invisible text, sized like the page."""
    from fpdf import FPDF

    sx, sy = page_w / img_w, page_h / img_h
    pdf = FPDF(unit="pt", format=(page_w, page_h))
    pdf.set_auto_page_break(False)
    pdf.set_margins(0, 0, 0)
    pdf.add_page()
    pdf.text_mode = "INVISIBLE"
    for w in words:
        size = max(1.0, w.h * sy * 0.8)
        pdf.set_font("helvetica", size=size)
        natural = pdf.get_string_width(w.text)
        if natural <= 0:
            continue
        pdf.set_stretching(max(10.0, min(1000.0, 100.0 * w.w * sx / natural)))
        # trailing space so text extraction keeps words apart
        pdf.text(w.x * sx, (w.y + w.h * 0.8) * sy, w.text + " ")
    pdf.output(str(dst))
    return dst
