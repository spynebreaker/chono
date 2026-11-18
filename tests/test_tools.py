import shutil
import sys
from pathlib import Path

import pypdfium2 as pdfium
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from corpus import make_record, rasterize  # noqa: E402
from pdfdad import tools  # noqa: E402


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
