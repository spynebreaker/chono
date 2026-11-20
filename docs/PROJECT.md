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
| XFA forms (the documents that "need Acrobat") | PdfCraft XFA renderer, PDF.js (`enableXfa: true`) as fallback | MIT/Apache, Apache | Real IRCC dynamic XFA forms (IMM 5707, IMM 5257) laid out, filled and saved by PdfCraft, see 5j. Form scripts in the window still untested. |
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
- Conclusion: handwriting OCR (Kraken) is the core feature for Dad, not Tesseract. Next: add an abbreviation dictionary and an image clean-up step for faded pages.
- Kraken on native Windows (2026-11-18, Goreguzzler): installs with plain pip in a Python 3.12 venv (CPU torch<=2.14 from the PyTorch CPU index, then kraken 7.1.1), about 5 minutes, about 1.1 GB, no admin rights and no WSL. Output on the test page is identical to the Mac. About 100 s per page including model load. Gotcha: on Windows it crashes with a 'charmap' codec error unless PYTHONUTF8=1 and PYTHONIOENCODING=utf-8 are set. Decision: Kraken runs on Dad's own PC, installed by the Chono installer.

## 5e2. Second real file (2026-11-18)

- A 50-page typeset book about the Protestant cemetery of Guayaquil (InDesign export, real text, no forms, no protection). Nothing in it needs Acrobat.
- Found a search bug: about 300 words were split at line ends with soft hyphens (PDFium returns U+FFFE), so "Coronel" and "iglesia" were missed on some pages. Fixed with `join_hyphens()` in the index; plain hyphens are joined only between lowercase letters.

## 5f. Photos of printed directories (2026-11-18)

- Dad works mostly from photos of printed sources (phone and city directories). Test on a 1932 phone directory page turned into a fake phone photo: see `docs/print-photo-test.md`.
- Raw photo 70% of words; after page flattening and shadow removal 81% (with tessdata_best). Black and white thresholding hurts. Kraken is worse than Tesseract on print.
- Added `clean_photo()` before OCR for every image file, plus a test. Tesseract for print, Kraken for handwriting, chosen automatically by confidence: done, see 5g.

## 5g. Handwriting built in (2026-11-18)

- "Leer acta escaneada" now picks the engine per page. Tesseract reads every page first; pages with no text whose mean Tesseract word confidence is under 75 go to Kraken in one batch (model loads once). Measured confidence: print 82 to 93, handwriting fonts 65 to 71, Dad's 1820 roll 30 to 35.
- Kraken writes ALTO (one box per word); `app/chono/textlayer.py` turns it into an invisible text layer over the original page image, so search, copy and the surname index work the same as for print.
- Phone photos are cleaned, then wrapped into a 300 dpi PDF (img2pdf) before OCR.
- The window shows "Leyendo letra a mano: página N de M" while Kraken works.
- Windows installer adds Kraken 7.1.1 + CPU PyTorch in `kraken\` and the model in `models\` (SHA256 checked); `-NoHandwriting` skips it. Full install on Goreguzzler: 7.3 minutes; all 11 tests pass in the installed environment, including a real Kraken run. Same on Uryu.
- End to end on Uryu: a cursive baptism page went to Kraken by itself (14 s), a phone directory photo stayed with Tesseract (4 s); search found Villacrés, Núñez, and Guayaquil (read as "Iuayaquil", found as near miss).
- Known limits: a page that OCRmyPDF rotated is re-read by Kraken from the original orientation; Kraken can't be cancelled from the window yet.

## 5h. Third real file: 1952 Guayaquil phone directory (2026-11-18)

- 173 pages of phone photos of the open book (two pages per photo, a hand in the frame). Acrobat Paper Capture had already added a hidden text layer, of poor quality.
- On page 72 (88 test words: names, streets, businesses): Acrobat 39 (44%); Tesseract on the raw photo 64; after shadow removal 78 to 80 (89 to 91%), even with the small `spa` model.
- The old pipeline would have kept Acrobat's text (`--skip-text`). Now `read_scanned()` treats every page that is a big picture with only invisible text as a scan: it strips the old hidden layer, evens out shadows (no perspective change, so positions match), runs Tesseract in parallel, and puts its own hidden text over the untouched picture. Pages with visible typed text (books made in InDesign, even over a background photo) are left alone. OCRmyPDF is no longer in this path.
- Speed in the sandbox (2 cores, small model): about 4 s per page; file size unchanged.
- Full book: 173 pages in 11.5 minutes in the sandbox, no errors. Search across the whole book, pages found with an exact match, Acrobat vs Chono: Aguirre 16 vs 77, Gomez 4 vs 54, Rocafuerte 12 vs 46, Arosemena 2 vs 20, Febres Cordero 3 vs 14, Villacres 0 vs 4.
- The first handwriting rule (mean Tesseract confidence under 75) would have sent all 173 print pages to Kraken (about 3 hours, worse text): noisy print scores 46 to 70. New rule counts words of 3+ letters that Tesseract is sure of (85+): print 22% to 96% (11 to 235 words), the 1820 roll 0% to 6%, cursive test fonts 19% to 29% (3 to 9 words). Handwriting if under 15%, or under 10 sure words and under 40%. A page with ink but almost no real words (faint page 3 of the roll, where Kraken still reads 49 words) also goes to Kraken. On 25 sampled directory pages none go to Kraken; 7 of 7 roll pages do.
- Lost from OCRmyPDF: automatic page rotation and deskew. Tesseract copes with small tilts; sideways photos are a known gap.

## 5i. Fourth and fifth real files (2026-11-18)

- "El legendario Barrio Orellana": 115-page InDesign book. 108 pages with typed text stay byte-for-byte the same text; the 7 picture-only pages get OCR (12 s). A photo page gets some junk hidden text (harmless, but adds noise).
- "Pío López Lara": 196-page Canon scan with an Acrobat Paper Capture layer. Acrobat did well on the clean book pages, badly on newspaper clippings; Chono re-read all 196 pages in 8.3 minutes. Search gains are small here (Alarcón 4 to 8 pages, Olmedo 6 to 8, Guayaquil 110 to 114).
- Search fixes found with these files: near misses on short names matched common words ("Icaza" matched "casa" on 73 pages), now short keys must share the first letter; and sound-alike hits now show the matching word in the snippet (the 1952 directory spells it "Ycaza").

## 5j. Fillable forms (2026-11-18)

- Tested PdfCraft's form engine on IRS (1040, W-9, W-4, 4868, 8822), USCIS (I-90, I-130) and IRCC (IMM 5707, IMM 5257) forms: all filled and saved, including the dynamic XFA IRCC forms that other free viewers show as "Please wait". Values land in the XFA data too, so Adobe's viewers should show them. Scanned forms: automatic field detection found all 23 W-9 fields; Fill & Sign and digital signing work. SRI has no public fillable PDFs (web forms behind login). Checked in Adobe Reader as a reference viewer: filled values show in IRS and IRCC forms; IRCC forms lose Adobe's usage rights when saved, so Reader shows them read-only for further typing. In the PdfCraft window on Windows, typing and saving work and the menus can be set to Spanish, but IRCC's Validate button fails (missing XFA script variables) and a false "signature is invalid" bar shows on the original IRCC form. Fixing it upstream: named `<variables>` values patched on top of PdfCraft PR #4948 (`patches/`), which gets Validate further; the rest (node methods, datasets, barcodes) is planned upstream, not started. Details: `docs/forms-test.md`.

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

## 5k. More tools (2026-11-19)

Main window: Abrir un PDF, Leer acta escaneada, Escanear acta, Buscar apellido, Más cosas. The rest is under "Más cosas", so the first screen stays at five buttons.

- Escanear acta: with the scanner (Windows' own scanner support, WIA: the scanner's window opens, one page at a time, "¿Escanea otra página?") or with phone photos (several at once, in order). The pages are cleaned, read, and saved in the records folder as "Escaneo <date> <time>.pdf".
- Ver y corregir el texto: the page on the left, its text on the right. Corrections are kept in a hidden side file (`<name>.pdf.chono.json`) and search uses them. Also: Resaltar (drag over the page), Agregar nota (a PDF note, also searchable), Leer en voz alta (Windows voices, a Spanish one when installed, a bit slow), Pasar a Word. Forms and signed files are not marked, to avoid damaging them.
- Leer todas las actas: reads every scanned record in the folder that has no text and no "(con texto)" copy.
- Achicar para enviar: a lighter copy, "(para enviar)", with pictures at about 150 dpi; text, forms and notes kept. Says so when the file is already small.
- Copia de seguridad: copies the records folder and Chono's search index to a disk or cloud folder chosen once. Only new or changed files are copied and nothing is deleted there. Done again automatically once a week when the disk is connected.
- Government forms with a usage-rights seal (IRCC): before opening, Chono says the "signature not valid" bar that may appear is normal (once per file).
- With Chono's patched PdfCraft installed (marked by `CHONO_PATCHED.txt` next to it), scripted forms open in it directly; the "other reader" question is only for an unpatched PdfCraft.

## Automatic updates (2026-11-19)

- Chono checks, at most once a day and only when installed (not from a source checkout), the `VERSION` file on the main branch of github.com/spynebreaker/chono (5 s timeout; silent without internet).
- When it is newer than the installed `VERSION`, Chono says so in one message, copies `app/chono/update.ps1` to the install folder, starts it and closes. The updater waits for Chono to close, runs the installer of the new version over the installed one (already-installed parts are skipped; the handwriting engine only if it was installed), logs to `update.log` and opens Chono again.
- No update while PdfCraft is open (its files can't be replaced then).
- **Releasing:** a change reaches dad only when `VERSION` is raised. Raise it only after the change is tested on Windows.

## Symbols in forms (2026-11-19)

Our PdfCraft build embeds Noto Sans Symbols 2 and Liberation Sans (OFL-1.1, from craft-fonts) through `CRAFT_FONTS_DIR`, with a trimmed manifest of those two faces only (+1.8 MB). Characters of a form's text that the standard fonts lack (► ✓ √ ☐) are drawn from them instead of `?`.

## macOS version (2026-11-20)

- Install: `curl -fsSL .../get.sh | bash` (README). No admin rights, no paid certificate: curl leaves no quarantine flag and every binary is ad hoc signed.
- Layout under `~/Library/Application Support/Chono`: micromamba env (Python 3.12, Tk, Tesseract, Ghostscript), tessdata_best spa/spa_old/eng plus osd, Kraken venv with the medium model, `pdfcraft/` (universal, from the `pdfcraft-macos` release, checksum pinned in `install.sh`), `app/`, `update.sh`. Package caches are removed after install (saves about 0.8 GB). About 2.2 GB in all, 1 GB without handwriting.
- `~/Applications/Chono.app` is registered as an alternate PDF viewer: Finder "Open With > Chono" opens the PDF in PdfCraft through Tk's OpenDocument event (the Chono window also opens).
- Updates: Chono starts `update.sh` (same flow as Windows), which reruns the installer over the same folder and opens Chono again.
- CI: `pdfcraft-macos.yml` builds both architectures on `macos-latest`, merges with lipo, strips, signs ad hoc and uploads the zip to the release (a branch can't hold files over 100 MB). A rebuild changes the zip, so its new `.sha256` must be put in `install.sh` in the same change.
- Tested on Uryu (macOS 26.6, Apple silicon), 2026-11-20: install and self-test, all 37 tests with the real tools (none skipped), handwriting on a public baptism record (19 s, readable), Finder Open With launching PdfCraft with the file, updater 0.3.1 to 0.3.2, uninstall. Not tested yet: an Intel Mac and a clean user account.

## More tools and a new look (2026-11-20)

Under "Más cosas" (grouped: Hacer y convertir, Revisar y corregir, Proteger y firmar, Imprimir y guardar). Each tool writes a new file next to the original, never changes it. Code: `app/chono/more.py`; tests: `tests/test_more.py`.

- Hacer PDF de un archivo: pictures through the photo path; Word, Excel, PowerPoint, text, HTML and others through LibreOffice headless (own profile, so it works while LibreOffice is open). Dad's PC has about 2,600 Word files and no Office, so the installers add LibreOffice 26.8.3 (about 1 GB; `-NoOffice` / `--no-office` skip it; not fatal if the download fails). On Windows it is the MSI unpacked with `msiexec /a` (no admin) and offered in "Open with" for Office files.
- Pasar a Word: pdf2docx. A scan without text first needs "Leer acta escaneada".
- Poner o quitar clave: pikepdf, AES-256.
- Tachar datos: PyMuPDF redaction; the words leave the file, and on scans the picture under them is blacked out too. Metadata cleared.
- Comparar dos versiones: word-level diff; added or changed words highlighted in the new version, removed words in a note ("Antes decía: ...").
- Firmar: pyHanko with a .p12/.pfx (for example the Ecuadorian electronic signature); the file is asked for once.
- Corregir texto impreso: the old words are removed and the new ones written in their place with a standard font (Helvetica, Times or Courier, by the original's style) at about the same size and color. Not perfect for unusual fonts.

New look (`app/chono/ui.py`): warm paper background, white rounded cards with a drawn icon (same on Windows and Mac, no font icons), bold title and a short hint; hover and keyboard focus; Más cosas in four columns (fits dad's 2560x1080 screen and a 1440x900 Mac).

Tested 2026-11-20: all 51 tests on dad's PC (Windows 11, real tools, none skipped) and on Uryu (macOS 26), the new screens on Windows (Goreguzzler) and Linux. Released as 0.4.0.

Handwriting on Windows had never worked: coremltools has no Windows build, and Kraken both tries a Core ML loader first and imports coremltools names for its line finder. Fixed with `kraken_run.py` (skips that loader and puts `coreml_stub/` on the path when coremltools can't load) and `installer/models/blla.safetensors` (Kraken's line finder converted with `ketos convert`). A public 1918 baptism record now reads in 73 s on dad's PC.

The Windows installer's self-test also stopped when the updater logged its output (Windows PowerShell turns stderr into errors there); it now checks exit codes only.
