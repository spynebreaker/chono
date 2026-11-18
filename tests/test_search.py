import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from corpus import SURNAMES, make_corpus, rasterize  # noqa: E402
from chono.phonetic import fold, phon  # noqa: E402
from chono.search import Index  # noqa: E402


def test_fold_and_phonetic_keys():
    assert fold("Núñez") == "nunez"
    assert phon("Villacrés") == phon("Billacres") == phon("Villacrez")
    assert phon("Cevallos") == phon("Zeballos") == phon("Ceballos")
    assert phon("Herrera") == phon("Errera")
    assert phon("Íñiguez") == phon("Yñiguez")
    assert phon("Donoso") != phon("Núñez")


@pytest.fixture(scope="module")
def corpus(tmp_path_factory):
    folder = tmp_path_factory.mktemp("actas")
    truth = make_corpus(folder, n=50)
    return folder, truth


def test_every_variant_found(corpus, tmp_path):
    folder, truth = corpus
    idx = Index(tmp_path / "i.sqlite")
    stats = idx.update(folder)
    assert stats["indexed"] == 50
    for canon, files in truth.items():
        found = {Path(h.path).name for h in idx.search(canon)}
        expected = {p.name for p in files}
        missing = expected - found
        assert not missing, f"{canon}: missing {sorted(missing)}"


def test_accentless_query(corpus, tmp_path):
    folder, truth = corpus
    idx = Index(tmp_path / "i.sqlite")
    idx.update(folder)
    a = {h.path for h in idx.search("Nunez")}
    b = {h.path for h in idx.search("Núñez")}
    assert a == b and a


def test_incremental_update(corpus, tmp_path):
    folder, _ = corpus
    idx = Index(tmp_path / "i.sqlite")
    idx.update(folder)
    again = idx.update(folder)
    assert again["indexed"] == 0 and again["unchanged"] == 50


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract not installed")
def test_scanned_record_after_ocr(corpus, tmp_path):
    folder, truth = corpus
    src = sorted(truth["Güemes"])[0]
    scan = tmp_path / "scan" / "escaneada.pdf"
    scan.parent.mkdir()
    rasterize(src, scan)
    idx = Index(tmp_path / "i.sqlite")
    assert idx.update(scan.parent)["needs_ocr"], "image-only PDF must be flagged"
    out = scan.with_name("escaneada_texto.pdf")
    subprocess.run([sys.executable, "-m", "ocrmypdf", "-q", "-l", "spa", "--output-type", "pdf",
                    str(scan), str(out)], check=True)
    scan.unlink()
    idx.update(scan.parent)
    assert any(Path(h.path).name == out.name for h in idx.search("Güemes"))
