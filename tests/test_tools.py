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
