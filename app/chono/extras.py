"""The "more" tools: corrected transcriptions, notes and highlights, smaller copies,
reading a whole folder, and backups. No UI code here, so it can be tested.
External programs (scanner, speech) stay in tools.py."""

from __future__ import annotations

import io
import json
import os
import shutil
import time
from pathlib import Path

from . import tools

# ---------------------------------------------------------------- corrections

SIDECAR_SUFFIX = ".chono.json"


def sidecar(pdf: Path | str) -> Path:
    """The file next to a PDF that keeps its corrected text and its notes."""
    p = Path(pdf)
    return p.with_name(p.name + SIDECAR_SUFFIX)


def load_sidecar(pdf: Path | str) -> dict:
    try:
        data = json.loads(sidecar(pdf).read_text("utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _hide(path: Path) -> None:
    """Keep the side file out of sight in the folder of records (Windows)."""
    if tools.SYSTEM == "Windows":
        try:
            import ctypes

            ctypes.windll.kernel32.SetFileAttributesW(str(path), 0x02)  # FILE_ATTRIBUTE_HIDDEN
        except Exception:
            pass


def _write_sidecar(pdf: Path | str, data: dict) -> None:
    side = sidecar(pdf)
    if side.exists() and tools.SYSTEM == "Windows":
        # a hidden file can't be replaced by name on Windows; clear the attribute first
        try:
            import ctypes

            ctypes.windll.kernel32.SetFileAttributesW(str(side), 0x80)
        except Exception:
            pass
    tmp = side.with_name(side.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), "utf-8")
    os.replace(tmp, side)
    _hide(side)


def corrected_pages(pdf: Path | str) -> dict[int, str]:
    """Page number (1-based) to the text the user corrected."""
    raw = load_sidecar(pdf).get("pages", {})
    out = {}
    for k, v in raw.items():
        try:
            out[int(k)] = str(v)
        except (TypeError, ValueError):
            continue
    return out


def save_correction(pdf: Path | str, page: int, text: str) -> None:
    data = load_sidecar(pdf)
    data.setdefault("pages", {})[str(page)] = text
    _write_sidecar(pdf, data)


def page_texts(pdf: Path | str) -> list[str]:
    """The text of each page: the user's correction when there is one."""
    from .search import extract_pages

    texts = [t.replace("\r\n", "\n").replace("\r", "\n") for t in extract_pages(Path(pdf))]
    for page, text in corrected_pages(pdf).items():
        if 1 <= page <= len(texts):
            texts[page - 1] = text
    return texts


def export_transcription(pdf: Path | str, out: Path | str) -> Path:
    """All pages' text (corrected where corrected) in one Word file."""
    import docx

    d = docx.Document()
    d.add_heading(Path(pdf).stem, level=1)
    for i, t in enumerate(page_texts(pdf), 1):
        d.add_heading(f"Página {i}", level=2)
        for line in t.splitlines():
            d.add_paragraph(line)
    d.save(str(out))
    return Path(out)


# ---------------------------------------------------------- notes, highlights


class CannotMark(Exception):
    """The file must not be changed here (a signed or scripted form)."""


def _check_markable(pdf) -> None:
    form = pdf.Root.get("/AcroForm")
    if form is not None and "/XFA" in form:
        raise CannotMark("form")
    if form is not None:
        for f in form.get("/Fields", []):
            if f.get("/FT") == "/Sig" and "/V" in f:
                raise CannotMark("signed")


def _save_in_place(pdf, path: Path) -> None:
    tmp = path.with_name(path.stem + ".chono-tmp.pdf")
    pdf.save(tmp)
    pdf.close()
    os.replace(tmp, path)


YELLOW = [1.0, 0.92, 0.23]


def add_highlight(path: Path | str, page: int, rect: tuple[float, float, float, float]) -> None:
    """Yellow highlight over rect (x0, y0, x1, y1 in PDF points) on page (1-based)."""
    import pikepdf

    path = Path(path)
    x0, y0, x1, y1 = min(rect[0], rect[2]), min(rect[1], rect[3]), max(rect[0], rect[2]), max(rect[1], rect[3])
    if x1 - x0 < 1 or y1 - y0 < 1:
        return
    pdf = pikepdf.open(path)
    try:
        _check_markable(pdf)
        pg = pdf.pages[page - 1]
        w, h = x1 - x0, y1 - y0
        ap = pdf.make_stream(
            f"/GS0 gs {YELLOW[0]} {YELLOW[1]} {YELLOW[2]} rg 0 0 {w:.2f} {h:.2f} re f".encode(),
            Type=pikepdf.Name.XObject, Subtype=pikepdf.Name.Form, BBox=[0, 0, w, h],
            Resources=pikepdf.Dictionary(ExtGState=pikepdf.Dictionary(
                GS0=pikepdf.Dictionary(BM=pikepdf.Name.Multiply, CA=0.45, ca=0.45))))
        annot = pdf.make_indirect(pikepdf.Dictionary(
            Type=pikepdf.Name.Annot, Subtype=pikepdf.Name.Highlight,
            Rect=[x0, y0, x1, y1], QuadPoints=[x0, y1, x1, y1, x0, y0, x1, y0],
            C=YELLOW, CA=0.45, F=4, T=pikepdf.String("Chono"),
            AP=pikepdf.Dictionary(N=ap)))
        pg.obj.Annots = pdf.make_indirect(pikepdf.Array(list(pg.obj.get("/Annots", [])) + [annot]))
    except Exception:
        pdf.close()
        raise
    _save_in_place(pdf, path)


def add_note(path: Path | str, page: int, text: str) -> None:
    """A note (sticky note) at the top left of page (1-based), also kept for search."""
    import pikepdf

    path = Path(path)
    text = text.strip()
    if not text:
        return
    pdf = pikepdf.open(path)
    try:
        _check_markable(pdf)
        pg = pdf.pages[page - 1]
        llx, lly, urx, ury = [float(v) for v in pg.mediabox]
        n = len([a for a in pg.obj.get("/Annots", []) if a.get("/Subtype") == "/Text"])
        x, y = llx + 12 + 26 * (n % 10), ury - 36
        annot = pdf.make_indirect(pikepdf.Dictionary(
            Type=pikepdf.Name.Annot, Subtype=pikepdf.Name.Text, Rect=[x, y, x + 22, y + 22],
            Contents=pikepdf.String(text), T=pikepdf.String("Chono"), C=YELLOW, Name=pikepdf.Name.Comment,
            F=4, M=pikepdf.String(time.strftime("D:%Y%m%d%H%M%S"))))
        pg.obj.Annots = pdf.make_indirect(pikepdf.Array(list(pg.obj.get("/Annots", [])) + [annot]))
    except Exception:
        pdf.close()
        raise
    _save_in_place(pdf, path)
    data = load_sidecar(path)
    data.setdefault("notes", {}).setdefault(str(page), []).append(text)
    _write_sidecar(path, data)


def notes(path: Path | str) -> dict[int, list[str]]:
    """The notes on each page (1-based), read from the PDF itself."""
    import pikepdf

    out: dict[int, list[str]] = {}
    with pikepdf.open(path) as pdf:
        for i, pg in enumerate(pdf.pages, 1):
            for a in pg.obj.get("/Annots", []):
                if a.get("/Subtype") == "/Text" and "/Contents" in a:
                    out.setdefault(i, []).append(str(a.Contents))
    return out


# --------------------------------------------------------------- smaller copy

SMALL_SIDE = 1700  # longest side of a page picture, in pixels (about 150 dpi on a letter page)
SMALL_QUALITY = 60


def smaller_name(src: Path) -> Path:
    return src.with_name(f"{src.stem} (para enviar).pdf")


def make_smaller(src: Path | str) -> Path | None:
    """A copy with its pictures made lighter, to send by email or WhatsApp.

    Text, hidden OCR text, forms and notes are kept as they are; only large
    pictures are shrunk and saved as JPEG. Returns None when that would not
    make the file at least 10% smaller.
    """
    import pikepdf
    from PIL import Image
    from pikepdf import PdfImage

    src = Path(src)
    out = smaller_name(src)
    with pikepdf.open(src) as pdf:
        done = set()
        shrunk = 0
        for page in pdf.pages:
            images = page.get_images() if hasattr(page, "get_images") else page.images
            for _name, raw in images.items():
                if raw.objgen in done:
                    continue
                done.add(raw.objgen)
                try:
                    if "/SMask" in raw or "/Mask" in raw or raw.get("/ImageMask", False):
                        continue
                    img = PdfImage(raw).as_pil_image()
                except Exception:
                    continue
                if max(img.size) <= SMALL_SIDE and raw.get("/Filter") == "/DCTDecode":
                    continue
                if img.mode not in ("L", "RGB"):
                    img = img.convert("RGB")
                scale = min(1.0, SMALL_SIDE / max(img.size))
                if scale < 1.0:
                    img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.LANCZOS)
                buf = io.BytesIO()
                img.save(buf, "JPEG", quality=SMALL_QUALITY, optimize=True)
                data = buf.getvalue()
                if len(data) >= len(raw.read_raw_bytes()):
                    continue
                raw.write(data, filter=pikepdf.Name.DCTDecode)
                shrunk += 1
                raw.Width, raw.Height = img.width, img.height
                raw.ColorSpace = pikepdf.Name.DeviceGray if img.mode == "L" else pikepdf.Name.DeviceRGB
                raw.BitsPerComponent = 8
                for k in ("/DecodeParms", "/Decode"):
                    if k in raw:
                        del raw[k]
        if not shrunk:  # no picture to make lighter: the file is as small as it gets here
            return None
        pdf.remove_unreferenced_resources()
        pdf.save(out, compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)
    if out.stat().st_size > 0.9 * src.stat().st_size:
        out.unlink()
        return None
    return out


# -------------------------------------------------------- a whole folder at once


def pending_scans(folder: Path | str) -> list[Path]:
    """Scanned records in the folder that have no readable text yet and no
    "(con texto)" copy beside them, plus photos of pages with no PDF made from them."""
    from .search import extract_pages

    folder = Path(folder)
    out = []
    for f in sorted(folder.rglob("*")):
        if not f.is_file() or f.name.endswith(SIDECAR_SUFFIX):
            continue
        suffix = f.suffix.lower()
        if suffix != ".pdf" and suffix not in tools.PHOTO_TYPES:
            continue
        if "(con texto)" in f.stem or "(para enviar)" in f.stem:
            continue
        if tools.ocr_output_name(f).exists():
            continue
        if suffix == ".pdf":
            try:
                if any(t.strip() for t in extract_pages(f)):
                    continue
            except Exception:
                continue
        out.append(f)
    return out


def read_folder(files: list[Path], progress=None) -> tuple[list[Path], list[Path]]:
    """Read every file; progress(done, total, name). Returns (made, failed)."""
    made, failed = [], []
    for n, f in enumerate(files):
        if progress:
            progress(n, len(files), f.name)
        try:
            made.append(tools.read_scanned(str(f)))
        except Exception:
            failed.append(f)
    if progress:
        progress(len(files), len(files), "")
    return made, failed


# --------------------------------------------------------------------- backup

BACKUP_EVERY_DAYS = 7


def backup(src: Path | str, dst: Path | str, extra: list[Path] | None = None, progress=None) -> dict:
    """Copy the records folder into dst/<folder name>, and extra files into dst/Chono.

    Only new or changed files are copied. Nothing is ever deleted in dst, so a
    record deleted by mistake at home is still in the backup.
    """
    src, dst = Path(src), Path(dst)
    if dst.resolve().is_relative_to(src.resolve()):
        raise ValueError("the backup can't go inside the folder it copies")
    target = dst / src.name
    files = [f for f in src.rglob("*") if f.is_file() and not f.name.endswith(".chono-tmp.pdf")]
    copied = same = 0
    jobs = [(f, target / f.relative_to(src)) for f in files] + [(f, dst / "Chono" / f.name) for f in (extra or []) if f.is_file()]
    for n, (f, to) in enumerate(jobs):
        if progress:
            progress(n, len(jobs))
        st = f.stat()
        if to.exists():
            t = to.stat()
            if t.st_size == st.st_size and t.st_mtime >= st.st_mtime - 2:  # FAT keeps 2 s steps
                same += 1
                continue
        to.parent.mkdir(parents=True, exist_ok=True)
        tmp = to.with_name(to.name + ".copiando")
        if to.exists() and tools.SYSTEM == "Windows":
            try:
                import ctypes

                ctypes.windll.kernel32.SetFileAttributesW(str(to), 0x80)
            except Exception:
                pass
        shutil.copy2(f, tmp)
        os.replace(tmp, to)
        copied += 1
    return {"copied": copied, "unchanged": same, "folder": str(target)}


def backup_due(last: float | None, now: float | None = None) -> bool:
    now = time.time() if now is None else now
    return last is None or now - last >= BACKUP_EVERY_DAYS * 86400
