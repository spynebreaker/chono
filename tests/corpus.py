"""Synthetic test corpus: fake civil records with real-world spelling variants.

All names are invented combinations of common Ecuadorian surnames; no real
records are used. Some files are typed PDFs, others are rasterized to
simulate scans (OCR is applied by the tests that need it).
"""

from __future__ import annotations

import random
from pathlib import Path

from fpdf import FPDF

FIRST = ["José", "María", "Manuel", "Rosa", "Andrés", "Concepción", "Ramón", "Dolores", "Luis", "Carmen"]
# surname -> spelling variants that clerks and OCR produce
SURNAMES = {
    "Villacrés": ["Villacrés", "Villacres", "Billacres", "Villacrez"],
    "Núñez": ["Núñez", "Nuñez", "Nunez"],
    "Güemes": ["Güemes", "Guemes"],
    "Íñiguez": ["Íñiguez", "Iñiguez", "Yñiguez"],
    "Ordóñez": ["Ordóñez", "Ordoñez", "Hordóñez"],
    "Donoso": ["Donoso"],
    "Cevallos": ["Cevallos", "Zeballos", "Ceballos"],
    "Herrera": ["Herrera", "Errera"],
}
KINDS = ["NACIMIENTO", "MATRIMONIO", "DEFUNCIÓN"]


def font_path() -> str:
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/System/Library/Fonts/Supplemental/Arial.ttf",
              r"C:\Windows\Fonts\arial.ttf"]:
        if Path(p).exists():
            return p
    raise FileNotFoundError("no Unicode TTF font found")


def make_record(path: Path, number: int, kind: str, people: list[str]) -> None:
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("u", fname=font_path())
    pdf.set_font("u", size=12)
    lines = ["REGISTRO CIVIL DE GUAYAQUIL", f"PARTIDA DE {kind} No. {number}", "",
             "En la ciudad de Guayaquil se inscribe la presente partida.",
             f"Inscrito: {people[0]}.", f"Padre: {people[1]}.", f"Madre: {people[2]}.",
             f"Testigo: {people[3]}."]
    for line in lines:
        pdf.cell(0, 8, line, new_x="LMARGIN", new_y="NEXT")
    pdf.output(str(path))


def make_corpus(folder: Path, n: int = 50, seed: int = 7) -> dict[str, list[Path]]:
    """Create n typed records; return which files contain each canonical surname."""
    rnd = random.Random(seed)
    folder.mkdir(parents=True, exist_ok=True)
    truth: dict[str, list[Path]] = {s: [] for s in SURNAMES}
    canon = list(SURNAMES)
    for i in range(n):
        people, used = [], set()
        for _ in range(4):
            s = rnd.choice(canon)
            used.add(s)
            people.append(f"{rnd.choice(FIRST)} {rnd.choice(SURNAMES[s])}")
        p = folder / f"acta_{i:03d}.pdf"
        make_record(p, 1000 + i, rnd.choice(KINDS), people)
        for s in used:
            truth[s].append(p)
    return truth


def rasterize(src: Path, dst: Path, dpi: int = 200) -> None:
    """Turn a typed PDF into an image-only PDF, like a scanner would."""
    import pypdfium2 as pdfium
    from PIL import ImageFilter

    img = pdfium.PdfDocument(str(src))[0].render(scale=dpi / 72).to_pil().convert("L")
    img = img.rotate(0.8, fillcolor=255).filter(ImageFilter.GaussianBlur(0.5))
    img.save(str(dst), resolution=dpi)
