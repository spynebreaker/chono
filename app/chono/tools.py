"""Actions behind the five buttons. No UI code here, so it can be tested."""

from __future__ import annotations

import os
import platform
import re
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
    """Chono's own PdfCraft first; on a Mac without it, an installed PdfCraft.app."""
    found = _find(["pdfcraft.exe", "pdfcraft"], "pdfcraft")
    if found or SYSTEM != "Darwin":
        return found
    app = Path("/Applications/PdfCraft.app")
    return str(app) if app.exists() else None


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


def open_file(path: str) -> None:
    """Open any file (a Word file, say) with the program the computer uses for it."""
    if SYSTEM == "Windows":
        os.startfile(path)  # type: ignore[attr-defined]
    elif SYSTEM == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


# Form scripts stock PdfCraft can't run. Dynamic XFA forms (Canada's IRCC forms, for one) keep
# shared code and named values under <variables>; their Validate buttons stop with a
# ReferenceError in PdfCraft 0.21.1. Chono's installer bundles PdfCraft with
# patches/pdfcraft-xfa-chono.patch applied and marks it with this file; then they run in it.
SCRIPTED_FORMS_NEED_READER = True
PATCHED_MARK = "CHONO_PATCHED.txt"


# First Chono build of PdfCraft that runs the scripts of static XFA forms.
STATIC_SCRIPTS_BUILD = 3


def pdfcraft_build() -> int:
    """The Chono build number of the installed PdfCraft (0 when it is the stock one).

    The mark file's first line is the build tag, such as "pdfcraft-0.21.1-chono3".
    """
    gui = pdfcraft_gui()
    if not gui:
        return 0
    mark = Path(gui).parent / PATCHED_MARK
    try:
        first = mark.read_text(encoding="utf-8", errors="replace").splitlines()[0]
    except (OSError, IndexError):
        return 0
    m = re.search(r"-chono(\d+)\s*$", first.strip())
    return int(m.group(1)) if m else 1


def pdfcraft_patched() -> bool:
    return pdfcraft_build() > 0
# Largest XFA template read to look for <variables>.
MAX_TEMPLATE_BYTES = 16 << 20


def needs_form_reader(path: str) -> bool:
    """True for a form whose own buttons (such as Validate) need code PdfCraft can't run.

    Two cases. A dynamic XFA form (it says /NeedsRendering, and PdfCraft lays it out) whose
    scripts keep shared code under <variables>: stock PdfCraft 0.21.1 can't run those, Chono's
    patched build can. A static XFA form (fixed pages, no /NeedsRendering) with scripts:
    stock PdfCraft and Chono builds before STATIC_SCRIPTS_BUILD run none of its scripts
    (Canada's IMM 5409 and IMM 5645 are such forms).
    """
    try:
        import pikepdf

        with pikepdf.open(path) as pdf:
            form = pdf.Root.get("/AcroForm")
            xfa = form.get("/XFA") if form is not None else None
            if not isinstance(xfa, pikepdf.Array):
                return False
            dynamic = bool(pdf.Root.get("/NeedsRendering", False))
            for i in range(0, len(xfa) - 1, 2):
                if str(xfa[i]) != "template":
                    continue
                stream = xfa[i + 1]
                if int(stream.get("/Length", 0)) > MAX_TEMPLATE_BYTES:
                    return False
                t = stream.read_bytes()[:MAX_TEMPLATE_BYTES]
                if not dynamic:
                    if pdfcraft_build() >= STATIC_SCRIPTS_BUILD:
                        return False
                    return re.search(rb"<event\b[^>]*>\s*<script\b[^>]*>\s*[^<\s]", t) is not None
                if not SCRIPTED_FORMS_NEED_READER or pdfcraft_patched():
                    return False
                return re.search(rb"<variables\b[^>]*>.*?<(script|text|integer|decimal|boolean)\s[^>]*name=", t, re.S) is not None
    except Exception:  # an unreadable file is opened as usual
        return False
    return False


def government_form_signature(path: str) -> bool:
    """A scripted form that carries a usage-rights seal (Canada's IRCC forms do).

    Filling it changes the document after the seal, so viewers may show a bar saying
    the signature is not valid. The form still works; Chono says so before opening it.
    """
    try:
        import pikepdf

        with pikepdf.open(path) as pdf:
            form = pdf.Root.get("/AcroForm")
            if form is None or "/XFA" not in form:
                return False
            perms = pdf.Root.get("/Perms")
            if perms is not None and ("/UR3" in perms or "/UR" in perms or "/DocMDP" in perms):
                return True
            return any(f.get("/FT") == "/Sig" and "/V" in f for f in form.get("/Fields", []))
    except Exception:
        return False


def form_reader() -> str | None:
    """The free reader installed on Windows, used only for forms that need it."""
    if SYSTEM != "Windows":
        return None
    for base in (os.environ.get("ProgramFiles", r"C:\Program Files"), os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")):
        for rel in (r"Adobe\Acrobat DC\Acrobat\Acrobat.exe", r"Adobe\Acrobat Reader DC\Reader\AcroRd32.exe"):
            p = Path(base) / rel
            if p.is_file():
                return str(p)
    return None


def open_in_form_reader(path: str) -> bool:
    exe = form_reader()
    if not exe:
        return False
    subprocess.Popen([exe, path])
    return True


def ocr_output_name(src: Path) -> Path:
    return src.with_name(f"{src.stem} (con texto).pdf")


PHOTO_TYPES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".heic", ".webp"}


def clean_photo(src: Path, dst: Path, flatten: bool = True) -> Path:
    """Prepare a phone photo of a page for OCR.

    Finds the page in the picture, straightens it, and evens out shadows
    from a lamp or a window. Tested on a simulated photo of a 1930s phone
    directory: words recovered went from 70% to 81%. Hard black and white
    thresholding made it worse (60%), so the result stays grayscale.
    With flatten=False the picture keeps its exact geometry (only shadows
    are evened out), so word positions still match the original image.
    """
    import cv2
    import numpy as np

    img = cv2.imread(str(src))
    if img is None:
        raise ValueError(f"cannot read image {src}")
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(cv2.GaussianBlur(g, (9, 9), 0), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if flatten and contours:
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


# How to tell handwriting from print, measured on real pages: count words of
# 3 or more letters that Tesseract reads with confidence 85 or more.
#   print (1952 phone directory, typed records): 22% to 96% of words, 11 to 235 words
#   handwriting (1820 roll): 0% to 6%; cursive test fonts: 19% to 29%, 3 to 9 words
# Mean confidence alone failed: noisy print pages score 46 to 70, like handwriting.
SURE_CONFIDENCE = 85


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
    for name in ("medium.safetensors", "small.safetensors"):  # small: installs before 0.3.1
        p = install_root() / "models" / name
        if p.is_file():
            return str(p)
    return None


def handwriting_ready() -> bool:
    return bool(kraken_exe() and kraken_model())


def tesseract_words(image: Path, languages: str = "spa"):
    """Words with boxes (image pixels) and confidence, as Tesseract reads them."""
    import csv
    import io

    from .textlayer import Word

    env = tool_env()
    exe = shutil.which("tesseract", path=env["PATH"]) or "tesseract"
    r = subprocess.run([exe, str(image), "-", "-l", languages, "--psm", "3", "tsv"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, **_hidden())
    words = []
    for row in csv.DictReader(io.StringIO(r.stdout), delimiter="\t", quoting=csv.QUOTE_NONE):
        try:
            c = float(row.get("conf") or -1)
            text = (row.get("text") or "").strip()
            if c < 0 or not text:
                continue
            words.append(Word(float(row["left"]), float(row["top"]), float(row["width"]),
                              float(row["height"]), text, c))
        except (ValueError, KeyError, TypeError):
            continue
    return words


_REAL_WORD = re.compile(r"[^\W\d_]{3,}[.,;:]?")


def looks_handwritten(words) -> bool:
    """True when Tesseract is sure of very few real words on the page."""
    real = [w for w in words if _REAL_WORD.fullmatch(w.text)]
    if len(real) < 3:
        # ink Tesseract can't make words of (faint handwriting), but not a blank page
        return len(words) >= 5
    sure = sum(w.conf >= SURE_CONFIDENCE for w in real)
    share = sure / len(real)
    return share < 0.15 or (sure < 10 and share < 0.4)


def kraken_threads() -> list[str]:
    """Use every core: on Windows Kraken otherwise reads a page about 30% slower."""
    return ["--threads", str(max(1, os.cpu_count() or 1))]


def run_kraken(pairs: list[tuple[Path, Path]], progress=None) -> None:
    """Read handwritten page images, writing one ALTO file per image.

    All pages go in one call so the model loads once. progress(done, total)
    is called as each page finishes.
    """
    cmd = [kraken_exe(), *kraken_threads(), "-a"]
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


def _page_kind(page) -> str:
    """'text' (real typed text), 'scan' (picture, maybe with an old OCR layer)
    or 'other'. Old OCR layers (Acrobat Paper Capture, OCRmyPDF, Chono) are
    invisible text over a picture that fills the page."""
    import pypdfium2.raw as raw

    w, h = page.get_size()
    big_image, visible_text = False, False
    for o in page.get_objects(max_depth=4):
        if o.type == raw.FPDF_PAGEOBJ_IMAGE:
            l, b, r, t = o.get_bounds()
            big_image |= (r - l) * (t - b) >= 0.6 * w * h
        elif o.type == raw.FPDF_PAGEOBJ_TEXT:
            visible_text |= raw.FPDFTextObj_GetTextRenderMode(o.raw) != raw.FPDF_TEXTRENDERMODE_INVISIBLE
    if visible_text:
        return "text"
    return "scan" if big_image else "other"


def _strip_text(pdf, page) -> None:
    """Remove the old hidden OCR text from a scanned page, keep the picture."""
    import pikepdf

    def text_only_form(name) -> bool:
        xobj = page.obj.get("/Resources", {}).get("/XObject", {}).get(name)
        if xobj is None or xobj.get("/Subtype") != "/Form":
            return False
        ops = {str(o.operator) for o in pikepdf.parse_content_stream(xobj)}
        return "BT" in ops and not ops & {"Do", "BI", "re", "m", "f", "S", "sh"}

    out, in_text = [], False
    for op in pikepdf.parse_content_stream(page):
        name = str(op.operator)
        if name == "BT":
            in_text = True
        elif name == "ET":
            in_text = False
        elif not in_text and not (name == "Do" and text_only_form(op.operands[0])):
            out.append(op)
    page.obj.Contents = pdf.make_stream(pikepdf.unparse_content_stream(out))


def _ocr_page(i: int, page_png: Path, clean_png: Path, languages: str):
    import cv2

    clean_photo(page_png, clean_png, flatten=False)
    words = tesseract_words(clean_png, languages)
    h, w = cv2.imread(str(page_png), cv2.IMREAD_GRAYSCALE).shape
    return i, words, w, h


def read_scanned(src: str, languages: str = "spa", progress=None) -> Path:
    """Make a scanned PDF or a phone photo searchable. Returns the new file.

    Every page that is a picture gets read again, even if Acrobat already
    added text, because that old text is often poor (on a 1952 phone
    directory, Acrobat got 44% of the words, Chono 89%). The picture itself
    is kept as it was. Pages with real typed text are left alone.
    Printed pages are read by Tesseract. Pages where Tesseract is unsure
    (handwriting) are read again by Kraken when it is installed; that takes
    about a minute per page. progress(stage, done, total) reports both,
    with stage "print" or "hand".
    """
    import tempfile
    from concurrent.futures import ThreadPoolExecutor

    import pikepdf
    import pypdfium2 as pdfium

    from .textlayer import alto_words, overlay_pdf

    s = Path(src)
    out = ocr_output_name(s)
    say = progress or (lambda *a: None)
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        if s.suffix.lower() in PHOTO_TYPES:
            s = _photo_to_pdf(clean_photo(s, tmp / "pagina.png"), tmp / "pagina.pdf")
        pdf = pikepdf.open(s)
        doc = pdfium.PdfDocument(str(s))
        scans, sizes = [], {}
        for i in range(len(doc)):
            kind = _page_kind(doc[i])
            if kind == "text":
                continue
            sizes[i] = doc[i].get_size()
            scans.append(i)
        doc.close()
        for i in scans:
            _strip_text(pdf, pdf.pages[i])
        clean_src = tmp / "sin_texto.pdf"
        pdf.save(clean_src)
        doc = pdfium.PdfDocument(str(clean_src))
        for i in scans:
            doc[i].render(scale=300 / 72, grayscale=True).to_pil().save(tmp / f"p{i}.png")
        doc.close()

        say("print", 0, len(scans))
        results, done = {}, 0
        workers = max(1, (os.cpu_count() or 2) - 1)
        with ThreadPoolExecutor(workers) as ex:
            jobs = [ex.submit(_ocr_page, i, tmp / f"p{i}.png", tmp / f"c{i}.png", languages) for i in scans]
            for job in jobs:
                i, words, w, h = job.result()
                results[i] = (words, w, h, looks_handwritten(words))
                done += 1
                say("print", done, len(scans))

        hand = [i for i in scans if results[i][3]] if handwriting_ready() else []
        if hand:
            say("hand", 0, len(hand))
            pairs = [(tmp / f"p{i}.png", tmp / f"p{i}.xml") for i in hand]
            run_kraken(pairs, lambda d, n: say("hand", d, n))
            for i, (_, xml) in zip(hand, pairs):
                if xml.exists():
                    words, w, h = alto_words(xml)
                    results[i] = (words, w, h, True)

        keep = []
        for i in scans:
            words, w, h, _ = results[i]
            if not words:
                continue
            ov = pikepdf.open(overlay_pdf(words, w, h, *sizes[i], tmp / f"o{i}.pdf"))
            keep.append(ov)
            pdf.pages[i].add_overlay(ov.pages[0])
        pdf.save(out)
        pdf.close()
        for ov in keep:
            ov.close()
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


def photos_to_pdf(photos: list[str], out: Path) -> Path:
    """Several photos or scanned pictures of pages, cleaned and in order, as one PDF."""
    import tempfile

    import img2pdf

    with tempfile.TemporaryDirectory() as t:
        pages = [str(clean_photo(Path(p), Path(t) / f"p{i}.png")) for i, p in enumerate(photos)]
        layout = img2pdf.get_fixed_dpi_layout_fun((300, 300))
        out.write_bytes(img2pdf.convert(pages, layout_fun=layout))
    return out


class NoScanner(Exception):
    """No scanner is connected, or Windows has no driver for it."""


# Windows Image Acquisition (WIA), part of Windows: shows the scanner's own window and
# saves what it scans. Exit code 2 when there is no scanner, 3 when the user cancels.
_WIA_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
try {
  $d = New-Object -ComObject WIA.CommonDialog
  $img = $d.ShowAcquireImage(1, 1, 65536, '{B96B3CAE-0728-11D3-9D7B-0000F81EF32E}', $false, $true, $false)
} catch {
  if ($_.Exception.Message -match '0x80210015|WIA_S_NO_DEVICE_AVAILABLE') { exit 2 }
  exit 4
}
if ($null -eq $img) { exit 3 }
$img.SaveFile($env:CHONO_SCAN_OUT)
exit 0
"""


def scan_page(dst: Path) -> Path | None:
    """Scan one page with the scanner (Windows). None when the user cancels."""
    if SYSTEM != "Windows":
        raise NoScanner("only on Windows")
    if dst.exists():
        dst.unlink()
    env = dict(os.environ)
    env["CHONO_SCAN_OUT"] = str(dst)
    r = subprocess.run(["powershell", "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass", "-Command", _WIA_SCRIPT],
                       env=env, capture_output=True, **_hidden())
    if r.returncode == 2:
        raise NoScanner("no scanner")
    if r.returncode == 3:
        return None
    if r.returncode != 0 or not dst.exists():
        raise NoScanner(f"scanner error {r.returncode}")
    return dst


# Speech: Windows' own voices (System.Speech), a Spanish one when installed, a bit slower
# than normal. The text comes through a file, so no character can break the command.
_SPEAK_SCRIPT = r"""
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$v = $s.GetInstalledVoices() | Where-Object { $_.Enabled -and $_.VoiceInfo.Culture.Name -like 'es*' } | Select-Object -First 1
if ($v) { $s.SelectVoice($v.VoiceInfo.Name) }
$s.Rate = -2
$s.Speak([IO.File]::ReadAllText($env:CHONO_SPEAK_FILE, [Text.Encoding]::UTF8))
"""


def speak(text: str):
    """Read text aloud. Returns the running process (stop it with stop_speaking), or None."""
    import tempfile

    text = " ".join(text.split())
    if not text:
        return None
    if SYSTEM == "Windows":
        f = Path(tempfile.gettempdir()) / "chono-voz.txt"
        f.write_text(text, "utf-8")
        env = dict(os.environ)
        env["CHONO_SPEAK_FILE"] = str(f)
        return subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", _SPEAK_SCRIPT],
                                env=env, **_hidden())
    if SYSTEM == "Darwin":
        return subprocess.Popen(["say", "-r", "160", text])
    exe = shutil.which("espeak-ng") or shutil.which("espeak")
    return subprocess.Popen([exe, "-v", "es", "-s", "140", text]) if exe else None


def stop_speaking(proc) -> None:
    if proc is not None and proc.poll() is None:
        proc.kill()
        try:
            proc.wait(5)
        except subprocess.TimeoutExpired:
            pass
