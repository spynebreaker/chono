import os
import shutil
import sys
import time
from pathlib import Path

import pikepdf
import pypdfium2 as pdfium
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from corpus import make_record, rasterize  # noqa: E402
from chono import extras, tools  # noqa: E402
from chono.search import Index  # noqa: E402


def _record(folder: Path, name: str = "Acta 1.pdf") -> Path:
    p = folder / name
    make_record(p, 1, "NACIMIENTO", ["Ana Núñez", "Luis Núñez", "Rosa Peña", "José Mora"])
    return p


def test_a_correction_is_kept_and_found_by_search(tmp_path):
    folder = tmp_path / "Actas"
    folder.mkdir()
    pdf = _record(folder)
    idx = Index(tmp_path / "i.sqlite")
    idx.update(folder)
    assert not idx.search("Villacrés")
    assert "\r" not in extras.page_texts(pdf)[0]
    extras.save_correction(pdf, 1, "Acta de nacimiento de Rosa Villacrés")
    assert extras.page_texts(pdf)[0] == "Acta de nacimiento de Rosa Villacrés"
    idx.update(folder)  # the side file changed: the record is read again
    assert idx.search("Villacrés")
    idx.close()


def test_transcription_goes_to_word(tmp_path):
    import docx

    pdf = _record(tmp_path)
    extras.save_correction(pdf, 1, "Rosa Villacrés\nsegunda línea")
    out = extras.export_transcription(pdf, tmp_path / "t.docx")
    text = "\n".join(p.text for p in docx.Document(str(out)).paragraphs)
    assert "Rosa Villacrés" in text and "segunda línea" in text


def test_highlight_and_note_are_saved_in_the_pdf_and_the_note_is_searchable(tmp_path):
    folder = tmp_path / "Actas"
    folder.mkdir()
    pdf = _record(folder)
    extras.add_highlight(pdf, 1, (72, 600, 300, 620))
    extras.add_note(pdf, 1, "Bisabuela de Juan, ver libro 3")
    with pikepdf.open(pdf) as p:
        kinds = [str(a.Subtype) for a in p.pages[0].Annots]
    assert kinds == ["/Highlight", "/Text"]
    assert extras.notes(pdf) == {1: ["Bisabuela de Juan, ver libro 3"]}
    assert pdfium.PdfDocument(str(pdf))[0].get_textpage().get_text_range()  # still opens with its text
    idx = Index(tmp_path / "i.sqlite")
    idx.update(folder)
    assert idx.search("Bisabuela")
    idx.close()


def test_a_scripted_form_is_not_marked(tmp_path):
    pdf = _record(tmp_path)
    with pikepdf.open(pdf, allow_overwriting_input=True) as p:
        p.Root.AcroForm = pikepdf.Dictionary(Fields=[], XFA=pikepdf.Array())
        p.save(pdf)
    before = pdf.read_bytes()
    with pytest.raises(extras.CannotMark):
        extras.add_note(pdf, 1, "nota")
    assert pdf.read_bytes() == before


def test_smaller_copy_shrinks_a_scan_and_keeps_its_text(tmp_path):
    typed = _record(tmp_path, "t.pdf")
    scan = tmp_path / "Acta.pdf"
    rasterize(typed, scan, dpi=300)
    out = extras.make_smaller(scan)
    assert out is not None and out.name == "Acta (para enviar).pdf"
    assert out.stat().st_size < 0.9 * scan.stat().st_size
    assert len(pdfium.PdfDocument(str(out))) == 1
    # a file that is already small comes back as None
    assert extras.make_smaller(typed) is None


def test_pending_scans_lists_only_records_without_text(tmp_path):
    typed = _record(tmp_path, "Escrita.pdf")
    scan = tmp_path / "Escaneada.pdf"
    rasterize(typed, scan)
    done = tmp_path / "Hecha.pdf"
    rasterize(typed, done)
    tools.ocr_output_name(done).write_bytes(typed.read_bytes())
    (tmp_path / "foto.jpg").write_bytes(b"x")
    names = [p.name for p in extras.pending_scans(tmp_path)]
    assert names == ["Escaneada.pdf", "foto.jpg"]


def test_backup_copies_new_and_changed_files_and_never_deletes(tmp_path):
    src, dst = tmp_path / "Actas", tmp_path / "USB"
    src.mkdir()
    (src / "sub").mkdir()
    (src / "a.pdf").write_bytes(b"a")
    (src / "sub" / "b.pdf").write_bytes(b"b")
    db = tmp_path / "indice.sqlite"
    db.write_bytes(b"db")
    r = extras.backup(src, dst, [db])
    assert r["copied"] == 3
    assert (dst / "Actas" / "sub" / "b.pdf").read_bytes() == b"b"
    assert (dst / "Chono" / "indice.sqlite").exists()
    assert extras.backup(src, dst, [db])["copied"] == 0
    time.sleep(0.01)
    (src / "a.pdf").write_bytes(b"aa")
    os.utime(src / "a.pdf", (time.time() + 10, time.time() + 10))
    (src / "sub" / "b.pdf").unlink()
    assert extras.backup(src, dst, [db])["copied"] == 1
    assert (dst / "Actas" / "a.pdf").read_bytes() == b"aa"
    assert (dst / "Actas" / "sub" / "b.pdf").exists(), "nothing is deleted in the backup"
    with pytest.raises(ValueError):
        extras.backup(src, src / "copia")


def test_backup_is_due_weekly():
    assert extras.backup_due(None)
    assert not extras.backup_due(1000.0, 1000.0 + 86400)
    assert extras.backup_due(1000.0, 1000.0 + 7 * 86400)


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract not installed")
def test_several_photos_become_one_searchable_record(tmp_path):
    from test_tools import _fake_phone_photo

    photos = []
    for n, person in enumerate(["Rosa Villacrés", "Carmen Herrera"]):
        typed = tmp_path / f"t{n}.pdf"
        make_record(typed, n, "MATRIMONIO", [person, "Juan Cevallos", "Ana Mora", "Luis Peña"])
        photos.append(str(tmp_path / f"f{n}.jpg"))
        _fake_phone_photo(typed, photos[-1])
    pdf = tools.photos_to_pdf(photos, tmp_path / "Escaneo.pdf")
    out = tools.read_scanned(str(pdf))
    doc = pdfium.PdfDocument(str(out))
    assert len(doc) == 2
    assert "Herrera" in doc[1].get_textpage().get_text_range()
