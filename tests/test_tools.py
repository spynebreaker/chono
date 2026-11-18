import shutil
import sys
from pathlib import Path

import pypdfium2 as pdfium
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from corpus import make_record, rasterize  # noqa: E402
from chono import tools  # noqa: E402


def test_merge(tmp_path):
    a, b = tmp_path / "a.pdf", tmp_path / "b.pdf"
    make_record(a, 1, "NACIMIENTO", ["Ana Núñez", "Luis Núñez", "Rosa Peña", "José Mora"])
    make_record(b, 2, "MATRIMONIO", ["Ana Núñez", "Juan Cevallos", "Rosa Peña", "José Mora"])
    out = tools.merge([str(a), str(b)], str(tmp_path / "familia.pdf"))
    assert len(pdfium.PdfDocument(str(out))) == 2


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract not installed")
def test_read_scanned(tmp_path):
    typed = tmp_path / "t.pdf"
    make_record(typed, 7, "DEFUNCIÓN", ["Ramón Ordóñez", "Pedro Ordóñez", "Dolores Báez", "Luis Mora"])
    scan = tmp_path / "Acta 7.pdf"
    rasterize(typed, scan)
    out = tools.read_scanned(str(scan))
    assert out.name == "Acta 7 (con texto).pdf"
    text = pdfium.PdfDocument(str(out))[0].get_textpage().get_text_range()
    assert "Ordóñez" in text


def _fake_phone_photo(src_pdf, dst_jpg):
    """Tilted page on a dark table with a shadow, like a phone picture."""
    import cv2
    import numpy as np

    page = np.array(pdfium.PdfDocument(str(src_pdf))[0].render(scale=3).to_pil().convert("RGB"))[:, :, ::-1]
    pad = cv2.copyMakeBorder(page, 150, 150, 150, 150, cv2.BORDER_CONSTANT, value=(60, 55, 50))
    h, w = pad.shape[:2]
    m = cv2.getPerspectiveTransform(np.float32([[0, 0], [w, 0], [w, h], [0, h]]),
                                    np.float32([[80, 40], [w - 30, 120], [w - 110, h - 20], [20, h - 100]]))
    photo = cv2.warpPerspective(pad, m, (w, h), borderValue=(60, 55, 50))
    xx = np.mgrid[0:h, 0:w][1]
    photo = np.clip(photo * (0.55 + 0.45 * xx / w)[..., None], 0, 255).astype(np.uint8)
    cv2.imwrite(str(dst_jpg), photo, [cv2.IMWRITE_JPEG_QUALITY, 80])


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract not installed")
def test_read_phone_photo(tmp_path):
    typed = tmp_path / "t.pdf"
    make_record(typed, 9, "MATRIMONIO", ["Rosa Villacrés", "Juan Cevallos", "Carmen Núñez", "Luis Herrera"])
    photo = tmp_path / "foto.jpg"
    _fake_phone_photo(typed, photo)
    out = tools.read_scanned(str(photo))
    text = pdfium.PdfDocument(str(out))[0].get_textpage().get_text_range()
    assert "Cevallos" in text and "Herrera" in text


ALTO = """<?xml version="1.0" encoding="UTF-8"?>
<alto xmlns="http://www.loc.gov/standards/alto/ns-v4#"><Layout>
<Page WIDTH="{w}" HEIGHT="{h}"><PrintSpace><TextBlock><TextLine>
<String CONTENT="Bauticé" HPOS="300" VPOS="400" WIDTH="260" HEIGHT="60" WC="0.9"/>
<String CONTENT="a" HPOS="580" VPOS="400" WIDTH="30" HEIGHT="60" WC="0.9"/>
<String CONTENT="Josefa" HPOS="630" VPOS="400" WIDTH="200" HEIGHT="60" WC="0.9"/>
<String CONTENT="Villacrés" HPOS="850" VPOS="400" WIDTH="280" HEIGHT="60" WC="0.9"/>
<String CONTENT="Nun̂ez" HPOS="1150" VPOS="400" WIDTH="220" HEIGHT="60" WC="0.9"/>
</TextLine></TextBlock></PrintSpace></Page></Layout></alto>"""


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract not installed")
def test_handwritten_page_goes_to_kraken(tmp_path, monkeypatch):
    """A page Tesseract is unsure about gets Kraken's words instead."""
    from PIL import Image

    from chono.search import Index

    typed = tmp_path / "t.pdf"
    make_record(typed, 3, "BAUTIZO", ["Josefa Villacrés", "Pedro Villacrés", "Ana Peña", "Luis Mora"])
    folder = tmp_path / "actas"
    folder.mkdir()
    scan = folder / "Acta 3.pdf"
    rasterize(typed, scan)

    def fake_kraken(pairs, progress=None):
        for img, xml in pairs:
            w, h = Image.open(img).size
            xml.write_text(ALTO.format(w=w, h=h), "utf-8")
        progress and progress(len(pairs), len(pairs))

    calls = []
    monkeypatch.setattr(tools, "handwriting_ready", lambda: True)
    monkeypatch.setattr(tools, "page_confidence", lambda img: (40.0, 30))
    monkeypatch.setattr(tools, "run_kraken", fake_kraken)
    out = tools.read_scanned(str(scan), progress=lambda d, t: calls.append((d, t)))
    text = pdfium.PdfDocument(str(out))[0].get_textpage().get_text_range()
    assert "Josefa Villacrés Nunez" in " ".join(text.split())
    assert "REGISTRO" not in text  # Tesseract's text on that page was replaced
    assert calls[0] == (0, 1) and calls[-1] == (1, 1)

    scan.unlink()  # keep only the OCR result in the folder
    idx = Index(tmp_path / "i.sqlite")
    idx.update(folder)
    assert any(h.page == 1 for h in idx.search("Villacres"))


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract not installed")
def test_printed_page_is_confident(tmp_path):
    typed = tmp_path / "t.pdf"
    make_record(typed, 4, "NACIMIENTO", ["Ana Núñez", "Luis Núñez", "Rosa Peña", "José Mora"])
    img = tmp_path / "p.png"
    pdfium.PdfDocument(str(typed))[0].render(scale=200 / 72).to_pil().save(img)
    assert not tools.looks_handwritten(*tools.page_confidence(img))


@pytest.mark.skipif(not tools.handwriting_ready(), reason="Kraken not installed")
def test_real_kraken(tmp_path, monkeypatch):
    """Runs only where Kraken is installed (set CHONO_KRAKEN and CHONO_KRAKEN_MODEL)."""
    typed = tmp_path / "t.pdf"
    make_record(typed, 5, "BAUTIZO", ["Rosa Cevallos", "Juan Cevallos", "Carmen Herrera", "Luis Donoso"])
    scan = tmp_path / "Acta 5.pdf"
    rasterize(typed, scan)
    monkeypatch.setattr(tools, "page_confidence", lambda img: (40.0, 30))
    out = tools.read_scanned(str(scan))
    text = pdfium.PdfDocument(str(out))[0].get_textpage().get_text_range()
    assert "REGISTRO" not in text.upper() or "GUAYAQUIL" in text.upper()
    assert any(s in text for s in ("Cevallos", "Herrera", "Donoso"))
