# Third-party components

The app's own code is AGPL-3.0. It installs and calls these components, each under its own license. Components marked **copyleft** require that the combined work stays open source, which this project already is.

| Component | Used for | License | Copyleft |
|---|---|---|---|
| [PdfCraft](https://github.com/storytold/pdfcraft) 0.21.1 | Viewer, XFA forms, merge, split | MIT or Apache-2.0 | |
| PdfCraft OCR models (ocrs) | Not used for Spanish (English only) | CC-BY-SA-4.0 | weak |
| [OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF) 17 | OCR pipeline | MPL-2.0 | weak |
| [Tesseract](https://github.com/tesseract-ocr/tesseract) 5 | OCR engine | Apache-2.0 | |
| tessdata_best / tessdata models (spa, spa_old, eng, osd) | OCR language models | Apache-2.0 | |
| Leptonica | Image library used by Tesseract | BSD-2-Clause style | |
| [Ghostscript](https://www.ghostscript.com/) 10 | PDF/A output | AGPL-3.0 | **yes** |
| [pikepdf](https://github.com/pikepdf/pikepdf) | PDF repair and merge fallback | MPL-2.0 | weak |
| [pypdfium2](https://github.com/pypdfium2-team/pypdfium2) / PDFium | Text extraction for search | BSD-3-Clause / Apache-2.0 | |
| [fpdf2](https://github.com/py-pdf/fpdf2) | OCR text layer (via OCRmyPDF), test corpus | LGPL-3.0 | weak |
| img2pdf | Image to PDF (via OCRmyPDF) | LGPL-3.0 | weak |
| [pdf2docx](https://github.com/ArtifexSoftware/pdf2docx) | PDF to Word | MIT | |
| [PyMuPDF](https://github.com/pymupdf/PyMuPDF) / MuPDF | Used by pdf2docx | AGPL-3.0 | **yes** |
| python-docx | Word files | MIT | |
| [pyHanko](https://github.com/MatthiasValvekens/pyHanko) | Digital signatures | MIT | |
| Python, Tk | Runtime and window | PSF / Tcl-Tk (BSD-style) | |
| [micromamba](https://github.com/mamba-org/mamba) + conda-forge packages | Installer | BSD-3-Clause; each package keeps its license | |
| SQLite (FTS5) | Search index | Public domain | |
| [Kraken](https://github.com/mittagessen/kraken) 7.1 (benchmark only, not bundled yet) | Handwriting recognition test | Apache-2.0 | |
| PP-OCRv6 small multilingual model (Zenodo 21788405) | Handwriting model for Kraken | Apache-2.0 | |
| Cedarville Cursive, Dawning of a New Day, Homemade Apple (Google Fonts, downloaded by the benchmark) | Handwriting proxy test images | OFL-1.1 / Apache-2.0 | |

Full license texts ship inside each installed package. Checked on 2026-11-18 from installed package metadata and the PdfCraft `deny.toml` (no copyleft crates in its 640 dependencies).
