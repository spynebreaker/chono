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
- Kraken only supports Linux and macOS. For Dad's Windows PC the options are: run it under WSL, or run it on our Mac (Uryu) as a small service the app calls when online. Decide after testing his real pages.
- A cursive font is far cleaner than a 1920s clerk's hand. Real error rates will be higher; the model card reports 5% CER on its Spanish manuscript test set.
- Model: PP-OCRv6 small multilingual base model, Apache-2.0, Zenodo record 21788405 (13 MB).
