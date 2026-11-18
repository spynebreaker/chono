# Handwriting proxy test: render a Spanish civil-record text in cursive fonts,
# then measure character error rate (CER) for Tesseract (spa, spa_old) and Kraken.
import subprocess, sys, os, unicodedata  # run from a folder holding the .ttf fonts
from PIL import Image, ImageDraw, ImageFont, ImageFilter
LINES = ["En la parroquia de San Alejo de Guayaquil,",
         "a los veinte días del mes de junio de mil",
         "novecientos cuarenta, yo el párroco bauticé",
         "a José Núñez Peña, hijo legítimo de Ramón",
         "Núñez Villacrés y de María Íñiguez Cañar.",
         "Padrinos: Andrés Muñoz y Dolores Ordóñez."]
TRUTH = "\n".join(LINES)
def cer(ref, hyp):
    a, b = " ".join(ref.split()), " ".join(hyp.split())
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j-1] + 1, prev[j-1] + (ca != cb)))
        prev = cur
    return prev[-1] / max(1, len(a))
def surnames(hyp):
    want = ["Núñez", "Peña", "Villacrés", "Íñiguez", "Cañar", "Muñoz", "Ordóñez"]
    return sum(w in hyp for w in want), len(want)
res = []
for font in sorted(f for f in os.listdir(".") if f.endswith(".ttf")):
    F = ImageFont.truetype(font, 44)
    img = Image.new("L", (1700, 110 * len(LINES) + 80), 255)
    d = ImageDraw.Draw(img)
    for i, l in enumerate(LINES): d.text((60, 40 + i * 110), l, font=F, fill=30)
    img = img.rotate(0.7, fillcolor=255).filter(ImageFilter.GaussianBlur(0.7))
    png = font[:-4] + ".png"; img.save(png, dpi=(300, 300))
    for lang in ["spa", "spa_old"]:
        out = subprocess.run(["../env/bin/tesseract", png, "-", "-l", lang, "--psm", "6"], capture_output=True, text=True).stdout
        res.append((font[:-4], "tesseract " + lang, cer(TRUTH, out), surnames(out)))
    p = subprocess.run(["../kenv/bin/kraken", "-i", png, png + ".k.txt", "segment", "-bl", "ocr", "-m", "../kmodels/small.safetensors"], capture_output=True, text=True)
    out = open(png + ".k.txt").read() if os.path.exists(png + ".k.txt") else ""
    out = unicodedata.normalize("NFC", out)  # kraken emits decomposed accents
    res.append((font[:-4], "kraken small", cer(TRUTH, out) if out else 1.0, surnames(out)))
    if not out: print("kraken error:", p.stderr[-300:])
for r in res: print(f"{r[0]:24} {r[1]:18} CER {r[2]*100:5.1f}%  surnames {r[3][0]}/{r[3][1]}")
