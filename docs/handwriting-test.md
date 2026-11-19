# Handwriting OCR: first test (2026-11-18)

## Why a proxy test

The open datasets closest to Dad's records (19th-century Latin American manuscripts, for example the Chilean Araucanía letters) publish only transcriptions; the page images may not be redistributed. Until Dad sends real handwritten records, the test renders a six-line Spanish baptism entry in three cursive fonts (Google Fonts, OFL/Apache), slightly rotated and blurred, and measures character error rate (CER) against the exact text.

Script: `bench/handwriting_proxy.py`. Ran on Uryu (macOS, Apple Silicon).

## Results

| Font | Tesseract `spa` | Tesseract `spa_old` | Kraken 7.1 + PP-OCRv6 small |
|---|---|---|---|
| Cedarville Cursive | 16.9% CER | 26.8% | **6.3%** |
| Dawning of a New Day | 26.4% | 31.5% | **10.6%** |
| Homemade Apple | 29.1% | 33.1% | **13.0%** |

Surnames found (out of 7: Núñez, Peña, Villacrés, Íñiguez, Cañar, Muñoz, Ordóñez), Kraken, ignoring accents: 5, 6 and 4. Tesseract `spa`: 2, 1 and 4.

## Conclusions

- Kraken is 2 to 3 times more accurate than Tesseract on cursive. `spa_old` is worse than `spa` here (it targets old print, not handwriting).
- Kraken writes accents as separate combining marks; text must be NFC-normalized before exact comparison. The search index already folds accents, so it is unaffected.
- Kraken officially supports Linux and macOS, but it installs and runs natively on Windows 11 with pip (tested 2026-11-18, same output as Mac). Set PYTHONUTF8=1 and PYTHONIOENCODING=utf-8 or it crashes on a console encoding error. No WSL needed.
- A cursive font is far cleaner than a 1920s clerk's hand. Real error rates will be higher; the model card reports 5% CER on its Spanish manuscript test set.
- Model: PP-OCRv6 small multilingual base model, Apache-2.0, Zenodo record 21788405 (13 MB).

## Models and speed (2026-11-19)

Same proxy test (3 cursive fonts, CER, 7 surnames each), Kraken 7.1.1 on Uryu:

| Model | Licence | CER per font | Surnames | 
|---|---|---|---|
| PP-OCRv6 tiny (Zenodo 21788403) | Apache-2.0 | 8.3% 15.4% 16.1% | 1/21 |
| PP-OCRv6 small (in use) | Apache-2.0 | 6.3% 10.6% 13.0% | 7/21 |
| PP-OCRv6 medium (Zenodo 21788410, 64 MB) | Apache-2.0 | 3.5% 10.2% 10.6% | 9/21 |
| McCATMuS (Zenodo 13788177, 16th to 21st c.) | CC-BY-4.0 | 16.5% 27.2% 24.4% | 0/21 |

No Spanish-only Kraken model for 19th and 20th century hands was found; the medieval ones (CATMuS Medieval, TRIDIS) do not fit civil records.

Speed on Goreguzzler (6 logical cores), one dense A4 page at 300 dpi (40 handwritten lines):

| Run | Time |
|---|---|
| Segmentation only | 43 s |
| Small model, default threads | 75 s |
| Small model, `--threads 6` | 53 s |
| Small model, `--threads 6 -B 64` | 60 s (batch size does not help) |
| Medium model, default threads | 143 s |
| Medium model, `--threads 6` | 100 s |

The same page takes 11 s (small) and 15 s (medium) on Uryu. Chono now passes `--threads <cores>` (about 30% faster on Windows). Switching to medium would cut errors but double the time per page.
