"""Actions behind the five buttons. No UI code here, so it can be tested."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

SYSTEM = platform.system()  # "Windows", "Darwin", "Linux"


def install_root() -> Path:
    """Folder that holds the bundled tools (set by the installer)."""
    env = os.environ.get("CHONO_HOME")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2]


def _find(names: list[str], *subdirs: str) -> str | None:
    root = install_root()
    for sub in subdirs:
        for n in names:
            for p in (root / sub).glob(f"**/{n}"):
                if p.is_file():
                    return str(p)
    for n in names:
        found = shutil.which(n)
        if found:
            return found
    return None


def pdfcraft_gui() -> str | None:
    if SYSTEM == "Darwin":
        app = Path("/Applications/PdfCraft.app")
        if app.exists():
            return str(app)
    return _find(["pdfcraft.exe", "pdfcraft"], "pdfcraft")


def pdfcraft_cli() -> str | None:
    return _find(["pdfcraft-cli.exe", "pdfcraft-cli"], "pdfcraft")


def tool_env() -> dict:
    """Environment with the bundled Tesseract/Ghostscript first on PATH."""
    env = dict(os.environ)
    root = install_root()
    extra = [root / "env" / "Library" / "bin", root / "env" / "Scripts", root / "env" / "bin", root / "env"]
    env["PATH"] = os.pathsep.join(str(p) for p in extra if p.exists()) + os.pathsep + env.get("PATH", "")
    tessdata = root / "tessdata"
    if tessdata.exists():
        env["TESSDATA_PREFIX"] = str(tessdata)
    return env


def open_pdf(path: str) -> None:
    gui = pdfcraft_gui()
    if gui and SYSTEM == "Darwin" and gui.endswith(".app"):
        subprocess.Popen(["open", "-a", gui, path])
    elif gui:
        subprocess.Popen([gui, path])
    elif SYSTEM == "Windows":
        os.startfile(path)  # type: ignore[attr-defined]
    elif SYSTEM == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def ocr_output_name(src: Path) -> Path:
    return src.with_name(f"{src.stem} (con texto).pdf")


PHOTO_TYPES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".heic", ".webp"}


def clean_photo(src: Path, dst: Path) -> Path:
    """Prepare a phone photo of a page for OCR.

    Finds the page in the picture, straightens it, and evens out shadows
    from a lamp or a window. Tested on a simulated photo of a 1930s phone
    directory: words recovered went from 70% to 81%. Hard black and white
    thresholding made it worse (60%), so the result stays grayscale.
    """
    import cv2
    import numpy as np

    img = cv2.imread(str(src))
    if img is None:
        raise ValueError(f"cannot read image {src}")
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(cv2.GaussianBlur(g, (9, 9), 0), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        c = max(contours, key=cv2.contourArea)
        quad = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)
        # only flatten when the page clearly fills most of the picture
        if len(quad) == 4 and cv2.contourArea(quad) > 0.3 * g.size:
            p = quad.reshape(4, 2).astype(np.float32)
            s, d = p.sum(1), np.diff(p, axis=1).ravel()
            tl, br, tr, bl = p[s.argmin()], p[s.argmax()], p[d.argmin()], p[d.argmax()]
            w = int(max(np.linalg.norm(tr - tl), np.linalg.norm(br - bl)))
            h = int(max(np.linalg.norm(bl - tl), np.linalg.norm(br - tr)))
            m = cv2.getPerspectiveTransform(np.float32([tl, tr, br, bl]),
                                            np.float32([[0, 0], [w, 0], [w, h], [0, h]]))
            g = cv2.warpPerspective(g, m, (w, h))
    background = cv2.morphologyEx(g, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31)))
    cv2.imwrite(str(dst), cv2.divide(g, background, scale=255))
    return dst


# Tesseract word confidence on test pages: print 82 to 93, handwriting 30 to 71.
HANDWRITING_CONFIDENCE = 75


def kraken_exe() -> str | None:
    """Handwriting engine (Kraken), installed in its own environment."""
    env = os.environ.get("CHONO_KRAKEN")
    if env:
        return env
    root = install_root() / "kraken"
    for p in (root / "Scripts" / "kraken.exe", root / "bin" / "kraken"):
        if p.is_file():
            return str(p)
    return None


def kraken_model() -> str | None:
    env = os.environ.get("CHONO_KRAKEN_MODEL")
    if env:
        return env
    p = install_root() / "models" / "small.safetensors"
    return str(p) if p.is_file() else None


def handwriting_ready() -> bool:
    return bool(kraken_exe() and kraken_model())


def page_confidence(image: Path) -> tuple[float, int]:
    """Mean Tesseract word confidence (0 to 100) and number of words."""
    import csv
    import io

    env = tool_env()
    exe = shutil.which("tesseract", path=env["PATH"]) or "tesseract"
    r = subprocess.run([exe, str(image), "-", "-l", "spa", "--psm", "3", "tsv"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, **_hidden())
    conf = []
    for row in csv.DictReader(io.StringIO(r.stdout), delimiter="\t", quoting=csv.QUOTE_NONE):
        try:
            c = float(row.get("conf") or -1)
        except ValueError:
            continue
        if c >= 0 and (row.get("text") or "").strip():
            conf.append(c)
    return (sum(conf) / len(conf) if conf else 0.0), len(conf)


def looks_handwritten(mean: float, words: int) -> bool:
    return words >= 3 and mean < HANDWRITING_CONFIDENCE


def run_kraken(pairs: list[tuple[Path, Path]], progress=None) -> None:
    """Read handwritten page images, writing one ALTO file per image.

    All pages go in one call so the model loads once. progress(done, total)
    is called as each page finishes.
    """
    cmd = [kraken_exe(), "-a"]
    for img, xml in pairs:
        cmd += ["-i", str(img), str(xml)]
    cmd += ["segment", "-bl", "ocr", "-m", kraken_model()]
    env = tool_env()
    env["PYTHONUTF8"] = "1"  # Windows console otherwise crashes on Kraken's check marks
    env["PYTHONIOENCODING"] = "utf-8"
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                         encoding="utf-8", errors="replace", env=env, **_hidden())
    done, tail = 0, []
    for line in p.stdout:
        tail = (tail + [line])[-20:]
        if "Writing recognition results" in line:
            done += 1
            if progress:
                progress(min(done, len(pairs)), len(pairs))
    if p.wait() != 0:
        raise RuntimeError("kraken failed: " + "".join(tail))


def _photo_to_pdf(png: Path, dst: Path) -> Path:
    import img2pdf

    layout = img2pdf.get_fixed_dpi_layout_fun((300, 300))
    dst.write_bytes(img2pdf.convert(str(png), layout_fun=layout))
    return dst


def _handwriting_pass(source: Path, out: Path, tmp: Path, progress=None) -> list[int]:
    """Re-read pages Tesseract struggled with using Kraken. Returns those pages."""
    import pikepdf
    import pypdfium2 as pdfium

    from .textlayer import alto_words, overlay_pdf

    doc = pdfium.PdfDocument(str(source))
    low, sizes = [], {}
    try:
        for i in range(len(doc)):
            page = doc[i]
            if page.get_textpage().get_text_range().strip():
                continue  # already has real text
            img = tmp / f"p{i}.png"
            page.render(scale=300 / 72, grayscale=True).to_pil().save(img)
            sizes[i] = page.get_size()
            if looks_handwritten(*page_confidence(img)):
                low.append(i)
    finally:
        doc.close()
    if not low:
        return []
    if progress:
        progress(0, len(low))
    pairs = [(tmp / f"p{i}.png", tmp / f"p{i}.xml") for i in low]
    run_kraken(pairs, progress)
    replaced, keep = [], []
    with pikepdf.open(source) as src, pikepdf.open(out, allow_overwriting_input=True) as dst:
        for i, (_, xml) in zip(low, pairs):
            if not xml.exists():
                continue  # Kraken skipped this page: keep the Tesseract text
            words, iw, ih = alto_words(xml)
            ov = pikepdf.open(overlay_pdf(words, iw, ih, *sizes[i], tmp / f"o{i}.pdf"))
            keep.append(ov)
            dst.pages[i] = src.pages[i]
            dst.pages[i].add_overlay(ov.pages[0])
            replaced.append(i)
        dst.save(out)
    for ov in keep:
        ov.close()
    return replaced


def read_scanned(src: str, languages: str = "spa", progress=None) -> Path:
    """Make a scanned PDF or a phone photo searchable. Returns the new file.

    Printed pages are read by Tesseract. Pages where Tesseract is unsure
    (handwriting) are read again by Kraken when it is installed; that takes
    about a minute per page, and progress(done, total) reports it.
    """
    import tempfile

    s = Path(src)
    out = ocr_output_name(s)
    cmd = [_python(), "-m", "ocrmypdf", "-l", languages, "--deskew", "--rotate-pages",
           "--output-type", "pdf", "--skip-text"]
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        if s.suffix.lower() in PHOTO_TYPES:
            s = _photo_to_pdf(clean_photo(s, tmp / "pagina.png"), tmp / "pagina.pdf")
        subprocess.run(cmd + [str(s), str(out)], check=True, env=tool_env(), capture_output=True, **_hidden())
        if handwriting_ready():
            _handwriting_pass(s, out, tmp, progress)
    return out


def _hidden() -> dict:
    """On Windows, run console tools without flashing black windows.

    The app runs under pythonw.exe (no console). Starting python.exe with
    CREATE_NO_WINDOW gives it a hidden console that Tesseract and
    Ghostscript then inherit.
    """
    if SYSTEM != "Windows":
        return {}
    return {"creationflags": 0x08000000}  # CREATE_NO_WINDOW


def _python() -> str:
    exe = sys.executable
    if SYSTEM == "Windows" and exe.lower().endswith("pythonw.exe"):
        exe = exe[:-len("pythonw.exe")] + "python.exe"
    return exe


def merge(files: list[str], out: str) -> Path:
    cli = pdfcraft_cli()
    if cli:
        subprocess.run([cli, "combine", *files, "--out", out], check=True, capture_output=True, **_hidden())
    else:  # fallback without PdfCraft
        import pikepdf

        pdf = pikepdf.new()
        for f in files:
            with pikepdf.open(f) as src:
                pdf.pages.extend(src.pages)
        pdf.save(out)
    return Path(out)


def print_pdf(path: str) -> None:
    if SYSTEM == "Windows":
        os.startfile(path, "print")  # type: ignore[attr-defined]
    else:
        subprocess.run(["lp", path], check=True)
