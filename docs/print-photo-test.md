# Photos of printed pages (phone directories): test (2026-11-18)

Dad mostly works from photographs of printed sources such as old phone and city directories.

## Sample

One page of a 1932 Valencia (Spain) phone directory, "Lista de profesiones", from the Internet Archive item `guitelval_1936` (dense two-column print, ads, small type). The page was turned into a fake phone photo: upscaled to phone resolution, placed on a dark table, tilted in perspective, lit unevenly from one side, slightly blurred, saved as JPEG.

Score: share of the words that Tesseract reads on the clean scan that are also found in the photo result.

## Results

| Input | Tesseract `spa` (standard) | Tesseract `spa` (tessdata_best) |
|---|---|---|
| Raw phone photo | 69.9% | 69.9% |
| **Cleaned photo** (page found, flattened, shadow removed) | 77.9% | **81.0%** |
| Cleaned + black and white threshold | 59.5% | 60.7% |

- Kraken on the cleaned photo: 68.1%. For print, Tesseract is better; for handwriting, Kraken is better (see `handwriting-test.md`).
- Page layout mode: automatic (`--psm 3`) or `--psm 1` work best; single-column mode (`--psm 4`) loses entries.

## What changed in the app

- `tools.clean_photo()` runs before OCR on every image file (JPG, PNG, TIFF, HEIC, WebP): find the page, flatten it, divide by the estimated background to remove shadows, keep grayscale.
- The installer already ships `tessdata_best` for Spanish.
- New test `test_read_phone_photo` builds a fake phone photo from the synthetic corpus and checks the surnames come back.

## Next

- Choose the engine automatically: Tesseract first; if its confidence is low (handwriting), run Kraken.
- Split directory entries into name / address / phone so the surname search can show them as a list.
