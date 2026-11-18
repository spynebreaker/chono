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


def read_scanned(src: str, languages: str = "spa") -> Path:
    """Make a scanned PDF or image searchable. Returns the new file."""
    s = Path(src)
    out = ocr_output_name(s)
    cmd = [_python(), "-m", "ocrmypdf", "-l", languages, "--deskew", "--rotate-pages",
           "--output-type", "pdf", "--skip-text"]
    if s.suffix.lower() in {".jpg", ".jpeg", ".png", ".tif", ".tiff"}:
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
