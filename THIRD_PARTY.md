# Third-party components

The app's own code is AGPL-3.0. It installs and calls these components, each under its own license. Components marked **copyleft** require that the combined work stays open source, which this project already is.

| Component | Used for | License | Copyleft |
|---|---|---|---|
| [PdfCraft](https://github.com/storytold/pdfcraft) 0.21.1 | Viewer, XFA forms, merge, split | MIT or Apache-2.0 | |
| [pdf417](https://crates.io/crates/pdf417) 0.2.1 (vendored in our PdfCraft patch) and [awint_core](https://crates.io/crates/awint_core) 0.11 | Draws PDF417 barcodes on XFA forms (IRCC) | MIT; MIT or Apache-2.0 | |
| [Noto Sans Symbols 2](https://github.com/google/fonts/tree/47d54ca1ebb14fd864695f1d39dc734f39017c33/ofl/notosanssymbols2) and [Liberation Sans](https://github.com/liberationfonts/liberation-fonts) Regular, from [craft-fonts](https://github.com/storytold/craft-fonts) cc9269cd | Embedded in our PdfCraft build to draw the symbols forms use (► ✓ √) | OFL-1.1 | weak (font only) |
| PdfCraft OCR models (ocrs) | Not used for Spanish (English only) | CC-BY-SA-4.0 | weak |
| [OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF) 17 | PDF/A output and installer self-test (Chono now runs Tesseract itself) | MPL-2.0 | weak |
| [Tesseract](https://github.com/tesseract-ocr/tesseract) 5 | OCR engine | Apache-2.0 | |
| tessdata_best / tessdata models (spa, spa_old, eng, osd) | OCR language models | Apache-2.0 | |
| Leptonica | Image library used by Tesseract | BSD-2-Clause style | |
| [Ghostscript](https://www.ghostscript.com/) 10 | PDF/A output | AGPL-3.0 | **yes** |
| [pikepdf](https://github.com/pikepdf/pikepdf) | PDF repair and merge fallback | MPL-2.0 | weak |
| [pypdfium2](https://github.com/pypdfium2-team/pypdfium2) / PDFium | Text extraction for search | BSD-3-Clause / Apache-2.0 | |
| [fpdf2](https://github.com/py-pdf/fpdf2) | Hidden OCR text layer, test corpus | LGPL-3.0 | weak |
| img2pdf | Image to PDF for phone photos | LGPL-3.0 | weak |
| [pdf2docx](https://github.com/ArtifexSoftware/pdf2docx) | PDF to Word | MIT | |
| [PyMuPDF](https://github.com/pymupdf/PyMuPDF) / MuPDF | Used by pdf2docx | AGPL-3.0 | **yes** |
| python-docx | Word files | MIT | |
| [OpenCV](https://github.com/opencv/opencv) (opencv-python-headless) | Straighten phone photos and remove shadows before OCR | Apache-2.0 | |
| [pyHanko](https://github.com/MatthiasValvekens/pyHanko) | Digital signatures | MIT | |
| Python, Tk | Runtime and window | PSF / Tcl-Tk (BSD-style) | |
| [micromamba](https://github.com/mamba-org/mamba) + conda-forge packages | Installer | BSD-3-Clause; each package keeps its license | |
| SQLite (FTS5) | Search index | Public domain | |
| [Kraken](https://github.com/mittagessen/kraken) 7.1.1 (own environment, `installer/kraken-requirements.txt`) | Handwriting recognition | Apache-2.0 | |
| [PyTorch](https://github.com/pytorch/pytorch) 2.14 CPU, torchvision 0.29 | Runs the handwriting model | BSD-3-Clause (PyTorch notice lists Apache-2.0, MIT, BSL-1.0 parts) | |
| Lightning, torchmetrics, scikit-image, scikit-learn, SciPy, NumPy, Shapely, lxml, pyarrow, coremltools, rich, and their small dependencies | Pulled in by Kraken | Apache-2.0, BSD, MIT, PSF; certifi and tqdm MPL-2.0 (weak) | weak |
| PP-OCRv6 small multilingual model (Zenodo 21788405) | Handwriting model for Kraken | Apache-2.0 | |
| Cedarville Cursive, Dawning of a New Day, Homemade Apple (Google Fonts, downloaded by the benchmark) | Handwriting proxy test images | OFL-1.1 / Apache-2.0 | |

Full license texts ship inside each installed package. Checked on 2026-11-18 from installed package metadata and the PdfCraft `deny.toml` (no copyleft crates in its 640 dependencies).

## Patches to third-party code

| Patch | Applies to | License of the patched code |
|---|---|---|
| `patches/pdfcraft-xfa-chono.patch` | PdfCraft, on top of its PR #4948: XFA `<variables>` named values and manifests, script data under `xfa.datasets`, choice lists, validation borders, preSave/prePrint scripts, PDF417 barcodes (includes the vendored pdf417 crate, MIT) | MIT/Apache-2.0 (PdfCraft); the patch is offered under the same terms |
