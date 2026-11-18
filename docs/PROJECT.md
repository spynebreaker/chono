# Project: Chono, our own PDF app (Acrobat replacement)

Status: in development (November 2026). Repo: https://github.com/spynebreaker/chono (public, AGPL-3.0). Components verified and tested on 2026-11-18 (Linux sandbox, Goreguzzler Windows 11, Uryu macOS). Waiting for sample PDFs from Dad.

---

## 1. Why

- Dad (80, genealogy hobby) pays a monthly Adobe Acrobat subscription. It is expensive and he keeps running into features and "permissions" he cannot use.
- Goal: a simple, free PDF app that covers everything he really does, with no subscription.
- Second goal: a learning project and a public portfolio piece, in the same spirit as the game development work (understand how software is built by building it).

## 2. Ground rules

- **No copied code.** We study Acrobat only by observing its behavior and by reading the public PDF standard (ISO 32000). We never decompile or copy Adobe code.
- **Open source, public repo, license AGPL-3.0.** The app is for Dad and for us; if it is ever shared, it is shared for free, never sold. Because the code is open, GPL and AGPL components are allowed (Ghostscript, MuPDF, PyMuPDF). Anyone who receives or improves it must keep it open.
- **Each component stays a separate piece** (the "quimera" design), so any one can be swapped later.
- **Own name and look.** Nothing that imitates Adobe branding.
- Keep a `THIRD_PARTY.md` with every component, its license and its notice. Mark which ones are GPL/AGPL.

## 3. Approach: a "quimera"

One simple interface; each button calls the best tool for that job.

| Feature | Component | License | Tested 2026-11-18 |
|---|---|---|---|
| View, zoom, search, comments, page edits, merge, split, reorder | **PdfCraft** (storytold/pdfcraft, v0.21.1, Rust, self-declared alpha) | MIT/Apache (640 crates, all permissive) | Official v0.21.1 builds (Windows x64 portable, macOS universal, SHA256 verified): text, combine, info, render OK on both. Full Spanish UI. Has an MCP channel to drive and screenshot the app. |
| Fallback viewer | PDF.js (6.5) | Apache | XFA test OK |
| XFA forms (the documents that "need Acrobat") | PdfCraft XFA renderer, PDF.js (`enableXfa: true`) as fallback | MIT/Apache, Apache | Our own dynamic XFA test form: both replaced the "Please wait" page and showed the fields. Real government forms with scripts still untested. |
| OCR of typed/printed records | **OCRmyPDF 17 + Tesseract 5 (spa)**, output `--output-type pdf` | MPL, Apache (deps include fpdf2 and img2pdf, LGPL) | Linux, Windows and Mac: 8 of 9 accented surnames exact, 3 to 5 s/page; only ü was read as ú (Güemes as Gúemes), which the accent-insensitive search covers. Tesseract also ships `spa_old` (old Spanish), worth testing on old records. |
| PDF/A output (optional) | OCRmyPDF + Ghostscript | AGPL | Works on Windows and Mac with Ghostscript 10.08 from conda-forge (PDF/A-2b confirmed). The official Windows gs installer hung in silent mode; use the conda-forge build. |
| OCR of handwritten records | **Kraken 7.1** (multilingual base models, 2026) | Apache | Not tested yet (heavy install). Evaluate in Phase 2 with Dad's real handwritten pages. |
| Convert to Word | **pdf2docx** (uses PyMuPDF) | MIT + AGPL | Clean editable paragraphs on Linux, Windows and Mac. On Windows it needs the Microsoft Visual C++ Redistributable (PyMuPDF DLL error without it). LibreOffice put the text into 10 frames with text boxes: rejected. |
| Digital signatures (timestamp, long-term validation) | pyHanko | MIT | Signed and validated (cryptographically sound) on Linux, Windows and Mac. |
| PDF/A validation (optional) | veraPDF | MPL or GPL | Not needed unless Dad archives to PDF/A. |
| Cross-file surname search | Own index: SQLite FTS5, accent-insensitive (Núñez = Nunez), plus fuzzy/phonetic matching for spelling variants (Villacres, Villacrés, Billacres) | Public domain (SQLite) | To build in Phase 2. |

Rejected after testing:
- **PdfCraft built-in OCR** for Spanish: the CLI only supports English; it turned "José Núñez Peña" into "Jos? N??ez Pe?a" and dropped a full line. Use Tesseract instead.
- **LibreOffice** for PDF to Word (text boxes, not editable text).
- **qpdf** as a separate tool: PdfCraft already merges, splits and repairs. Keep only as a fallback.
- **Stirling-PDF**: open core (MIT core plus proprietary modules), a server app, more than Dad needs.

## 4. Users and requirements

**Primary user: Dad.**
- Big buttons, few options, Spanish interface, large fonts.
- Works offline on his computer: **Windows** (Dad). Also must run on **Mac** (us).
- Must open every PDF he uses today without errors.

**Genealogy features (to confirm with him):**
- Search a surname across many records at once, ignoring accents and spelling variants.
- OCR scanned birth, marriage and death records (typed and handwritten) so the text is searchable.
- Mark names, dates and places; build an index of surnames per document.
- Merge records into one file per family; print.

## 5. Phases

### Phase 0: Discovery (2 to 3 days)
- Get the PDFs that "ask for Acrobat" and a screenshot of any error message.
- Classify the problem: XFA form, digital signature, protected PDF, or just habit.
- Ask how many of his records are handwritten vs typed.
- List what Dad actually does each week with Acrobat.

### Phase 1: Core viewer (3 to 5 days)
- PdfCraft as the base; open, zoom, search, thumbnails, print.
- Run his real files through PdfCraft and PDF.js; keep PDF.js only if PdfCraft fails.
- Confirm his XFA files open.

### Phase 2: His daily tools (1 to 2 weeks)
- Highlights, notes, merge, split, reorder pages (PdfCraft).
- OCR button "Leer acta escaneada" (OCRmyPDF + Tesseract spa).
- Handwriting test with Kraken on his real pages.
- Cross-file surname search (own index).

### Phase 3: Extras (1 week, only what he needs)
- Convert to Word (pdf2docx).
- Signatures, if he signs documents (pyHanko).
- Surname / place index for genealogy.

### Phase 4: Delivery (1 week)
- Installer for his computer. Tested approach: one conda-forge environment (micromamba) with Python 3.12, Tesseract and Ghostscript, plus pip packages; it installed in under a minute on both Windows and Mac without Homebrew or admin installers. On Windows also install the Visual C++ Redistributable. Still the hardest part, more than the UI.
- A one-page guide with screenshots, in Spanish.
- Remote updates, so he never has to do anything technical.

**Total: about 3 to 5 weeks** to a version Dad can use every day.

## 5b. Test machines

- **Goreguzzler** (Windows 11, x64, Python 3.12, winget, 167 GB free): main test box, same OS as Dad. Reached from Uryu with `~/infra/bin/gz`.
- **Uryu** (macOS 26.6, Apple Silicon, 32 GB free, no Homebrew yet): Mac test box. Low disk: avoid building Rust there; use release binaries.
- Windows installer is the priority (Dad); Mac build is secondary.

## 5c. Test results 2026-11-18

- Test kit and reports: `~/lab/pdf-dad/mac/` on Uryu and `C:\agent\pdf-dad\` on Goreguzzler (`test_all.py`, `report.txt`, `work/`).
- Windows (Goreguzzler): all OK after adding VC++ Redistributable and conda-forge Ghostscript.
- Mac (Uryu): all OK; test env takes 1.6 GB.
- Same on all three systems: PdfCraft built-in OCR rejects Spanish (`unsupported language "es"`).

## 5d. Built on 2026-11-18 (before Dad's files)

- Public repo with AGPL-3.0, README, THIRD_PARTY.md, CLAUDE.md (clean-room rules), CI on Linux, Windows and Mac.
- Surname search (`app/chono/search.py`): SQLite FTS5 index, accent-insensitive, Spanish phonetic key (b/v, c/s/z, ll/y, silent h) and near-miss matching for OCR errors. 50-record synthetic test corpus; every spelling variant found.
- Five-button Spanish window (`app/chono/launcher.py`): Abrir, Leer acta escaneada, Buscar apellido, Unir actas, Imprimir. Checked on the Goreguzzler screen.
- Windows installer (`installer/windows/install.ps1`): no admin rights, about 2.5 minutes, self-test included (real OCR round trip). Install and uninstall cycle passed on Goreguzzler; all 7 tests pass in the installed environment.
- Handwriting test: see `docs/handwriting-test.md`. Kraken beats Tesseract 2 to 3 times on cursive, but runs only on Linux/Mac.
- Name: **Chono** (chosen 2026-11-18), after the Chono people of Guayaquil. Repo: spynebreaker/chono.

## 5e. Phase 0, first real file (2026-11-18)

- File: a 7-page scan of an 1820 handwritten military roll (archive stamp from the Archivo Historico del Guayas). Made with Acrobat's image-to-PDF tool: plain JPEG pages, no text layer, no forms, no protection. It does not need Acrobat; PdfCraft opens it fine.
- Tesseract `spa`: unusable on this hand (almost no correct words).
- Kraken 7.1 + PP-OCRv6 small: most names and streets readable on page 1 (Mayans, Blanco, Escaso, Sepeda exact; Alcoser read as Alcosen). About 50 s per page on CPU. Faded or stained pages come out much worse.
- With the phonetic search, "Alcocer" finds "Alcosen", "Cepeda" finds "Sepeda" and "Zopeda", "Rodriguez" finds "Rodrigues". Archival abbreviations ("Rodrig.s", "Fran.co") are not expanded yet.
- Conclusion: handwriting OCR (Kraken) is the core feature for Dad, not Tesseract. Next: run Kraken for Windows (WSL or a Uryu service), add an abbreviation dictionary, and an image clean-up step for faded pages.

## 6. Learning track (parallel, optional)

Build our own PDF engine from scratch, without libraries, like an emulator:
1. Read the file structure (objects, cross-reference table, streams).
2. Decompress streams and parse content operators.
3. Draw simple pages (lines, rectangles, basic text with standard fonts).
4. Add embedded fonts, images, then annotations.

Compare every page we draw against PDF.js and PdfCraft output as the reference. Over time this engine can replace the library inside the app.

Reference: the ArtCraft projects (October 2026) used the same method: clean-room rule written in the agent instructions, automated tests on every change, a corpus of real files to compare against, and an MCP channel so the AI can drive and screenshot the app.

## 7. Costs

- Software: $0 (all open source).
- Build: our time with Claude.
- Savings: Dad's Acrobat subscription. Verified: on an "annual plan, paid monthly", cancelling after the first 14 days costs 50% of the remaining contract. Check his plan type and wait for the year to end if it is annual.

## 8. Risks

- **Complex XFA forms with scripts** may still fail in both viewers. Fallback: free Acrobat Reader only for those rare files.
- **PdfCraft is alpha** and changes fast. Pin a version; PDF.js is the fallback viewer.
- **Handwritten old records**: open-source handwriting recognition is far weaker than OCR on printed text. Results on his real pages decide whether it is worth it.
- **Installer**: bundling Python + Tesseract for Mac or Windows is real work.
- **Certified signatures from government systems** may need extra validation work.

## 9. Open questions

1. ~~Mac or Windows?~~ Answered: Dad on Windows, us on Mac.
2. Which files fail today, and what message appears?
3. What does he do with PDFs every week?
4. Does he need to sign documents?
5. How many of his records are handwritten?
6. Does he need Word conversion or PDF/A at all?

## 10. Next step

Get 2 or 3 of the PDFs that "need Acrobat" from Dad, a photo of the error message, and 2 or 3 scanned records (one handwritten if possible), and run Phase 0.
