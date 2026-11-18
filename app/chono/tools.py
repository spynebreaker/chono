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


def read_scanned(src: str, languages: str = "spa") -> Path:
    """Make a scanned PDF or a phone photo searchable. Returns the new file."""
    import tempfile

    s = Path(src)
    out = ocr_output_name(s)
    cmd = [_python(), "-m", "ocrmypdf", "-l", languages, "--deskew", "--rotate-pages",
           "--output-type", "pdf", "--skip-text"]
    with tempfile.TemporaryDirectory() as tmp:
        if s.suffix.lower() in PHOTO_TYPES:
            s = clean_photo(s, Path(tmp) / "pagina.png")
            cmd += ["--image-dpi", "300"]
        subprocess.run(cmd + [str(s), str(out)], check=True, env=tool_env(), capture_output=True, **_hidden())
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
