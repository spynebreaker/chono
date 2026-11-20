"""The extra tools behind "Más cosas": make a PDF from any file, password, black out words,
to Word, compare two versions, digital signature and correcting printed text.

No UI code here, so everything can be tested. Every tool writes a new file next to the
original and never changes the original. Errors meant for the user are ChonoError with a
short Spanish message.
"""

from __future__ import annotations

import difflib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import tools

IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif", ".heic", ".webp"}
OFFICE_TYPES = {".doc", ".docx", ".odt", ".rtf", ".txt", ".html", ".htm", ".xls", ".xlsx",
                ".ods", ".csv", ".ppt", ".pptx", ".odp", ".wpd", ".pages"}


class ChonoError(Exception):
    """A problem to show to the user as it is (plain Spanish)."""


def new_name(src: Path | str, label: str, ext: str = ".pdf") -> Path:
    """'acta.pdf' -> 'acta (label).pdf' in the same folder, never overwriting a file."""
    src = Path(src)
    base = src.with_suffix("").name
    for n in range(1, 1000):
        tail = f" ({label})" if n == 1 else f" ({label} {n})"
        p = src.with_name(f"{base}{tail}{ext}")
        if not p.exists():
            return p
    raise ChonoError("Hay demasiadas copias con ese nombre en la carpeta.")


def _open(src: Path | str, password: str | None = None):
    import pymupdf

    try:
        doc = pymupdf.open(str(src))
    except Exception:
        raise ChonoError("No se pudo abrir el PDF. Puede estar dañado.")
    if doc.needs_pass:
        if not password or not doc.authenticate(password):
            doc.close()
            raise ChonoError("Ese PDF tiene clave. Quítele la clave primero.")
    return doc


def has_text(src: Path | str) -> bool:
    with _open(src) as doc:
        return any(page.get_text().strip() for page in doc)


# 1. make a PDF from a file ----------------------------------------------------------------

def libreoffice() -> str | None:
    """LibreOffice's command line: Chono's own copy first, then one installed on the computer."""
    env = os.environ.get("CHONO_SOFFICE")
    if env:
        return env
    root = tools.install_root() / "libreoffice"
    for p in (root / "program" / "soffice.com", root / "program" / "soffice.exe",
              root / "LibreOffice.app" / "Contents" / "MacOS" / "soffice"):
        if p.is_file():
            return str(p)
    for p in (Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"),
              Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "LibreOffice" / "program" / "soffice.com"):
        if p.is_file():
            return str(p)
    return shutil.which("soffice") or shutil.which("libreoffice")


def open_document(path: Path | str) -> None:
    """Open a result: PDFs in PdfCraft, Word and other documents in Chono's LibreOffice
    (the computer may have no program for them), anything else as the computer decides."""
    path = str(path)
    office = libreoffice()
    if path.lower().endswith(".pdf") or not office or Path(path).suffix.lower() not in OFFICE_TYPES:
        tools.open_file(path)
        return
    app = Path(office)
    if app.name == "soffice.com":  # the window program, not the console one
        app = app.with_name("soffice.exe")
    for p in app.parents:
        if p.suffix == ".app":  # macOS: open the bundle so it shows in the Dock
            subprocess.Popen(["open", "-a", str(p), path])
            return
    subprocess.Popen([str(app), path], **tools._hidden())


def make_pdf(src: Path | str) -> Path:
    """A PDF of a document, spreadsheet, presentation, text or picture."""
    src = Path(src)
    ext = src.suffix.lower()
    if ext == ".pdf":
        raise ChonoError("Ese archivo ya es un PDF.")
    out = new_name(src, "PDF")
    if ext in IMAGE_TYPES:
        return tools.photos_to_pdf([str(src)], out)
    office = libreoffice()
    if not office:
        raise ChonoError("Falta el programa para convertir documentos. Vuelva a instalar Chono.")
    with tempfile.TemporaryDirectory() as tmp:
        # a separate profile: works even while LibreOffice is open on its own
        profile = Path(tmp, "profile").as_uri()
        cmd = [office, f"-env:UserInstallation={profile}", "--headless", "--norestore",
               "--convert-to", "pdf", "--outdir", tmp, str(src)]
        try:
            subprocess.run(cmd, capture_output=True, timeout=300, **tools._hidden())
        except subprocess.TimeoutExpired:
            raise ChonoError("El documento tardó demasiado en convertirse.")
        made = Path(tmp, src.with_suffix(".pdf").name)
        if not made.is_file() or made.stat().st_size == 0:
            raise ChonoError("No se pudo convertir ese archivo a PDF.")
        shutil.move(str(made), out)
    return out


# 2. password ------------------------------------------------------------------------------

def add_password(src: Path | str, password: str) -> Path:
    import pikepdf

    if not password:
        raise ChonoError("Escriba una clave.")
    out = new_name(src, "con clave")
    try:
        with pikepdf.open(str(src)) as pdf:
            pdf.save(str(out), encryption=pikepdf.Encryption(owner=password, user=password, R=6))
    except pikepdf.PasswordError:
        raise ChonoError("Ese PDF ya tiene clave.")
    return out


def remove_password(src: Path | str, password: str) -> Path:
    import pikepdf

    out = new_name(src, "sin clave")
    try:
        with pikepdf.open(str(src), password=password) as pdf:
            pdf.save(str(out))
    except pikepdf.PasswordError:
        raise ChonoError("La clave no es correcta.")
    return out


def is_protected(src: Path | str) -> bool:
    import pikepdf

    try:
        with pikepdf.open(str(src)):
            return False
    except pikepdf.PasswordError:
        return True


# 3. black out words for good ----------------------------------------------------------------

def _find_all(doc, text: str):
    """(page, rectangles) for every place the words appear, ignoring upper/lower case."""
    for page in doc:
        rects = page.search_for(text)
        if rects:
            yield page, rects


def black_out(src: Path | str, words: list[str]) -> tuple[Path, int]:
    """A copy where the words are removed from the file (not only covered) and drawn black.
    Returns the copy and how many places were blacked out."""
    import pymupdf

    words = [w.strip() for w in words if w.strip()]
    if not words:
        raise ChonoError("Escriba lo que quiere tachar.")
    with _open(src) as doc:
        if not any(page.get_text().strip() for page in doc):
            raise ChonoError("Este PDF es una foto sin texto. Primero use \"Leer acta escaneada\".")
        count = 0
        for w in words:
            for page, rects in _find_all(doc, w):
                for r in rects:
                    page.add_redact_annot(r, fill=(0, 0, 0))
                    count += 1
        if not count:
            raise ChonoError("No se encontró ese texto en el PDF.")
        for page in doc:
            # also the picture under the words (scans), not only the hidden text layer
            page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_PIXELS)
        doc.set_metadata({})
        out = new_name(src, "tachado")
        doc.save(str(out), garbage=4, deflate=True)
    return out, count


# 4. to Word -------------------------------------------------------------------------------------

def to_word(src: Path | str) -> Path:
    from pdf2docx import Converter

    if not has_text(src):
        raise ChonoError("Este PDF es una foto sin texto. Primero use \"Leer acta escaneada\".")
    out = new_name(src, "Word", ".docx")
    import logging

    logging.getLogger("pdf2docx").setLevel(logging.ERROR)
    cv = Converter(str(src))
    try:
        cv.convert(str(out), multi_processing=False)
    except Exception:
        out.unlink(missing_ok=True)
        raise ChonoError("No se pudo pasar este PDF a Word.")
    finally:
        cv.close()
    return out


# 5. compare two versions -------------------------------------------------------------------------

def _words(doc):
    """Every word with its page and box, in reading order."""
    for page in doc:
        for x0, y0, x1, y1, text, *_ in page.get_text("words", sort=True):
            yield page.number, (x0, y0, x1, y1), text


def compare(old: Path | str, new: Path | str) -> tuple[Path, int]:
    """A copy of the new version with what changed marked: added or changed words in yellow,
    and a note where words were taken out. Returns the copy and the number of changes."""
    import pymupdf

    with _open(old) as a, _open(new) as b:
        wa = list(_words(a))
        wb = list(_words(b))
        if not wa or not wb:
            raise ChonoError("Uno de los PDFs es una foto sin texto. Primero use \"Leer acta escaneada\".")
        sm = difflib.SequenceMatcher(None, [w[2] for w in wa], [w[2] for w in wb], autojunk=False)
        changes = 0
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                continue
            changes += 1
            if j2 > j1:  # added or changed words: highlight them in the new version
                for pno, box, _t in wb[j1:j2]:
                    b[pno].add_highlight_annot(pymupdf.Rect(box))
            if i2 > i1:  # words that were in the old version only: a note next to the spot
                gone = " ".join(w[2] for w in wa[i1:i2])
                pno, box, _t = wb[min(j1, len(wb) - 1)]
                note = b[pno].add_text_annot(pymupdf.Point(box[0], box[1]), f"Antes decía: {gone}")
                note.set_info(title="Chono")
                note.update()
        out = new_name(new, "cambios")
        b.save(str(out))
    return out, changes


# 6. digital signature -------------------------------------------------------------------------------

def sign(src: Path | str, certificate: Path | str, password: str, reason: str = "") -> Path:
    """Sign with a .p12/.pfx electronic signature (for example the one from the Registro Civil)."""
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko.sign import signers

    try:
        signer = signers.SimpleSigner.load_pkcs12(str(certificate), passphrase=password.encode())
    except Exception:
        signer = None
    if signer is None:
        raise ChonoError("No se pudo abrir la firma. Revise la clave de la firma.")
    if is_protected(src):
        raise ChonoError("Ese PDF tiene clave. Quítele la clave primero.")
    out = new_name(src, "firmado")
    meta = signers.PdfSignatureMetadata(field_name="FirmaChono", reason=reason or None)
    with open(src, "rb") as f_in:
        w = IncrementalPdfFileWriter(f_in, strict=False)
        with open(out, "wb") as f_out:
            signers.sign_pdf(w, meta, signer=signer, output=f_out)
    return out


def signature_status(src: Path | str) -> list[tuple[str, bool]]:
    """(signer name, untouched since signing) for each signature in the file."""
    from pyhanko.pdf_utils.reader import PdfFileReader
    from pyhanko.sign.validation import validate_pdf_signature

    result = []
    with open(src, "rb") as f:
        r = PdfFileReader(f, strict=False)
        for s in r.embedded_signatures:
            st = validate_pdf_signature(s)
            name = s.signer_cert.subject.human_friendly if s.signer_cert else "?"
            result.append((name, bool(st.intact and st.valid)))
    return result


# 7. correct printed text ------------------------------------------------------------------------

def _font_for(span_font: str) -> str:
    f = span_font.lower()
    if "courier" in f or "mono" in f:
        return "cour"
    if "times" in f or "serif" in f and "sans" not in f or "roman" in f:
        return "tiro"
    return "helv"


def _original_font(doc, page, span_font: str, text: str):
    """The PDF's own font for a span, as (font buffer, Font), when it is embedded and has every
    letter of the new text. Embedded fonts are often cut down to the letters the page used, so a
    new letter may be missing; then None and a standard font is used."""
    import pymupdf

    def bare(name: str) -> str:  # "ABCDEF+Garamond-Bold" -> "garamondbold"
        return "".join(c for c in name.split("+", 1)[-1].lower() if c.isalnum())

    want = bare(span_font)
    # the exact name first, so a regular span doesn't take the bold font of the same family
    fonts = sorted(page.get_fonts(full=True), key=lambda f: (bare(f[3]) != want, len(f[3])))
    for xref, ext, _type, basefont, *_ in fonts:
        have = bare(basefont)
        if not want or not (have.startswith(want) or want.startswith(have)) or ext in ("n/a", ""):
            continue
        try:
            buf = doc.extract_font(xref)[3]
            font = pymupdf.Font(fontbuffer=buf)
        except Exception:
            return None
        if buf and all(ch.isspace() or font.has_glyph(ord(ch)) for ch in text):
            return buf, font
        return None
    return None


def replace_text(src: Path | str, old: str, new: str) -> tuple[Path, int]:
    """A copy where every 'old' is taken out of the page and 'new' is written in its place,
    about the same size. Returns the copy and how many places changed."""
    import pymupdf

    old = old.strip()
    if not old:
        raise ChonoError("Escriba el texto que quiere cambiar.")
    with _open(src) as doc:
        count = 0
        for page in doc:
            rects = page.search_for(old)
            if not rects:
                continue
            spans = [s for b in page.get_text("dict")["blocks"] for l in b.get("lines", [])
                     for s in l["spans"]]
            todo = []
            for r in rects:
                span = next((s for s in spans if pymupdf.Rect(s["bbox"]).intersects(r)), None)
                size = span["size"] if span else max(6.0, r.height * 0.8)
                font = _font_for(span["font"]) if span else "helv"
                own = _original_font(doc, page, span["font"], new) if span and new else None
                color = span["color"] if span else 0
                rgb = tuple(((color >> k) & 255) / 255 for k in (16, 8, 0))
                todo.append((r, size, font, own, rgb))
                page.add_redact_annot(r, fill=(1, 1, 1))
            page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE)
            for n, (r, size, font, own, rgb) in enumerate(todo):
                if not new:
                    continue
                if own:
                    font = f"ChonoF{n}"
                    page.insert_font(fontname=font, fontbuffer=own[0])
                    width = own[1].text_length(new, fontsize=size)
                else:
                    width = pymupdf.get_text_length(new, fontname=font, fontsize=size)
                # shrink the type until the new words fit where the old ones were
                if width > r.width * 1.6:
                    size = size * r.width * 1.6 / width
                origin = pymupdf.Point(r.x0, r.y1 - (r.height - size) / 2 - size * 0.2)
                page.insert_text(origin, new, fontsize=size, fontname=font, color=rgb)
            count += len(todo)
        if not count:
            raise ChonoError("No se encontró ese texto en el PDF.")
        out = new_name(src, "corregido")
        doc.save(str(out), garbage=3, deflate=True)
    return out, count
