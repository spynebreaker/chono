"""The tools of "Más cosas". All files are synthetic (tests/corpus.py)."""

import datetime
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from chono import more  # noqa: E402
from corpus import make_record, rasterize  # noqa: E402

pymupdf = pytest.importorskip("pymupdf")

PEOPLE = ["José Villacrés Núñez", "Manuel Villacrés", "Rosa Núñez Ordóñez", "Ramón Cevallos"]


@pytest.fixture
def record(tmp_path: Path) -> Path:
    p = tmp_path / "acta 12.pdf"
    make_record(p, 12, "NACIMIENTO", PEOPLE)
    return p


def text_of(p: Path, password: str | None = None) -> str:
    with pymupdf.open(str(p)) as d:
        if password:
            d.authenticate(password)
        return "".join(page.get_text() for page in d)


def test_new_files_go_next_to_the_original_and_never_overwrite(record: Path):
    a = more.new_name(record, "con clave")
    assert a.name == "acta 12 (con clave).pdf" and a.parent == record.parent
    a.write_bytes(b"x")
    assert more.new_name(record, "con clave").name == "acta 12 (con clave 2).pdf"


def test_a_password_locks_the_copy_and_takes_it_off_again(record: Path):
    locked = more.add_password(record, "abuelo1918")
    assert more.is_protected(locked) and not more.is_protected(record)
    with pytest.raises(more.ChonoError):
        more.remove_password(locked, "otra")
    opened = more.remove_password(locked, "abuelo1918")
    assert "Villacrés" in text_of(opened)


def test_blacked_out_words_are_gone_from_the_file_not_only_covered(record: Path):
    out, n = more.black_out(record, ["Rosa Núñez Ordóñez"])
    assert n == 1
    text = text_of(out)
    assert "Rosa" not in text and "Ordóñez" not in text
    assert "José Villacrés Núñez" in text, "the rest stays"
    assert "Rosa" in text_of(record), "the original is untouched"


def test_black_out_on_a_scan_without_text_says_to_read_it_first(record: Path, tmp_path: Path):
    scan = tmp_path / "escaneo.pdf"
    rasterize(record, scan)
    with pytest.raises(more.ChonoError, match="Leer acta"):
        more.black_out(scan, ["Rosa"])


def test_a_pdf_turns_into_an_editable_word_file(record: Path):
    import docx

    out = more.to_word(record)
    assert out.suffix == ".docx"
    words = " ".join(p.text for p in docx.Document(str(out)).paragraphs)
    assert "Villacrés" in words and "PARTIDA DE NACIMIENTO" in words


def test_compare_marks_what_changed_between_two_versions(tmp_path: Path):
    old, new = tmp_path / "v1.pdf", tmp_path / "v2.pdf"
    make_record(old, 12, "NACIMIENTO", PEOPLE)
    make_record(new, 12, "NACIMIENTO", [PEOPLE[0], "Manuel Villacrez", PEOPLE[2], PEOPLE[3]])
    out, n = more.compare(old, new)
    assert n == 1
    with pymupdf.open(str(out)) as d:
        annots = [(a.type[1], a.info["content"]) for page in d for a in page.annots()]
    marked = [a for a in annots if a[0] == "Highlight"]
    notes = [c for t, c in annots if t == "Text"]
    assert len(marked) == 1 and notes == ["Antes decía: Villacrés."]
    _same, zero = more.compare(old, old)
    assert zero == 0


def test_corrected_text_replaces_the_old_words_on_the_page(record: Path):
    out, n = more.replace_text(record, "Ramón Cevallos", "Ramón Zeballos")
    assert n == 1
    text = text_of(out)
    assert "Zeballos" in text and "Cevallos" not in text
    with pytest.raises(more.ChonoError):
        more.replace_text(record, "no existe", "x")


def make_p12(path: Path, password: str) -> None:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Persona de Prueba")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now)
            .not_valid_after(now + datetime.timedelta(days=30))
            .add_extension(x509.KeyUsage(True, True, False, False, False, False, False, False, False), True)
            .sign(key, hashes.SHA256()))
    path.write_bytes(pkcs12.serialize_key_and_certificates(
        b"prueba", key, cert, None, serialization.BestAvailableEncryption(password.encode())))


def test_a_signed_copy_carries_a_valid_untouched_signature(record: Path, tmp_path: Path):
    p12 = tmp_path / "firma.p12"
    make_p12(p12, "1234")
    with pytest.raises(more.ChonoError, match="clave de la firma"):
        more.sign(record, p12, "mala")
    out = more.sign(record, p12, "1234", reason="Copia fiel")
    assert more.signature_status(out) == [("Common Name: Persona de Prueba", True)]
    assert more.signature_status(record) == []


@pytest.mark.skipif(not more.libreoffice(), reason="LibreOffice not installed")
def test_a_word_document_becomes_a_pdf(tmp_path: Path):
    import docx

    d = docx.Document()
    d.add_paragraph("Carta para la familia Villacrés Núñez")
    src = tmp_path / "carta.docx"
    d.save(str(src))
    out = more.make_pdf(src)
    assert out.name == "carta (PDF).pdf"
    assert "Villacrés Núñez" in text_of(out)


def test_a_picture_becomes_a_pdf_and_a_pdf_is_left_alone(record: Path, tmp_path: Path):
    png = tmp_path / "foto.png"
    with pymupdf.open(str(record)) as d:
        d[0].get_pixmap(dpi=60).save(str(png))
    out = more.make_pdf(png)
    with pymupdf.open(str(out)) as d:
        assert d.page_count == 1
    with pytest.raises(more.ChonoError):
        more.make_pdf(record)
