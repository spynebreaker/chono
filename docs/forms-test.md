# Fillable forms test (2026-11-18)

Engine: PdfCraft 0.21.1 CLI (`pdfcraft-cli run --script`), macOS (Uryu). Forms are public government PDFs, downloaded fresh; they are not committed. Script: `bench/forms_test.py`.

## Forms

| Form | Kind | Fields | Result |
|---|---|---|---|
| IRS 1040, W-9, W-4, 4868, 8822 | AcroForm + static XFA copy | 17 to 199 | Filled (text with accents, check boxes), saved, values in the AcroForm fields and in the XFA data, rendered correctly |
| USCIS I-90, I-130 | Same, encrypted (owner password, restrictions) | 195, 450 | Filled and saved. Rendering to an image is refused by the restrictions (the viewer itself shows it) |
| IRCC IMM 5707 (Family information) | Dynamic XFA only ("Please wait" in other viewers), encrypted | 0 AcroForm fields; PdfCraft lays out 3 pages, 91 fields | Laid out, filled, saved, XFA data updated |
| IRCC IMM 5257 (Visitor visa) | Dynamic XFA, encrypted, signed (usage rights) | PdfCraft lays out 5 pages, 174 fields (text, lists, radios, signature) | A full rewrite is refused to keep the signature; an incremental save works. Name and list choice saved in the XFA data and shown on the page. Max length enforced (UCI field, 10 characters) |

## Forms without fields

- IRS W-9 page 1 turned into a 200 dpi scan: `form_detect_fields` found 23 fields (15 text, 8 check boxes), the same count as the original form.
- Fill & Sign (`fill_sign_add`): typed text, a check mark and today's date placed on the scan, then baked into the page; the text is extractable.
- Digital signature (`sign_document`) with a self-made .p12: pyHanko reports intact, valid, covering the whole file (not trusted, as expected for a self-made certificate). An Ecuadorian electronic signature (.p12) should be trusted the same way.

## SRI (Ecuador)

No public fillable PDF forms found. Declarations and requests (including the IVA refund for older adults) are web forms inside "SRI en Línea" behind a login, and the downloadable formats are Excel files. Nothing for Chono to do there beyond printing or saving receipts.

## Opened in Adobe Acrobat Reader (Goreguzzler, Windows 11, Reader 26.003)

Reader was installed only as a reference viewer, to observe how it shows the files (clean-room rules: observe documents, never Adobe code).

- IRS 1040 filled by PdfCraft: Reader shows the typed name in the fields.
- IRCC IMM 5257 and IMM 5707 filled by PdfCraft: Reader lays out the dynamic XFA form and shows the saved values (name, list choice). No "Please wait" page and no error.
- Both IRCC forms show Reader's bar "Please fill out the following form. You cannot save data typed into this form." The original forms carry Adobe usage rights (`/Perms /UR3`, the signature that lets Reader save form data); PdfCraft drops it when it saves (it keeps `/DocMDP`). So after Chono fills an IRCC form, Reader can still show and print it, but someone using Reader could not save further typing. Chono itself can keep editing. A changed document would lose those rights anyway, since the usage-rights signature only covers the original bytes.
- Reader's first-run license, "make Reader your default" and promotion dialogs had to be dismissed; Windows' default PDF app stayed Microsoft Edge.

## PdfCraft window on Windows (Goreguzzler, 2026-11-18)

Driven through PdfCraft's UI control channel (`pdfcraft --control FILE`, `pdfcraft-cli ui`).

- IRCC IMM 5257 (blank original) opens and lays out in the window. Clicking the Family name field and typing "Núñez Peña" works; File > Save writes it (read back with the CLI: `FamilyName = Núñez Peña`).
- The Validate button does not work: the JavaScript console shows `ReferenceError: globValidatePressed is not defined`. The IRCC form keeps shared variables in an XFA script object that PdfCraft does not provide yet, so its own checks (and the barcode page it makes) do not run. Adobe Reader is still needed for that step, or the form has to be checked by eye.
- A bar says "At least one signature is invalid" on the untouched original. PdfCraft reports that IRCC's certifying signature was followed by changes it does not allow and that the signer is not in its trusted list. Adobe Reader showed no such warning on the same file, so this looks like a PdfCraft false alarm, but it would worry Dad. Chono should explain it or hide it for these forms.
- Interface language: Preferences > General > Interface language is "Auto" (follows Windows, which is English on Goreguzzler). Setting it to Spanish (`ui set key=language value=es`) turns the menus into Spanish (Abrir, Archivo, Edición, Ver, Firmar...). The installer should set this.

## Fixing Validate in PdfCraft (2026-11-18)

Why it fails: the IRCC form keeps shared code under `<variables>`: 9 script objects (`validateForm`, `BC`, `LOV`...) and 3 named text values (`globValidatePressed`, `globFirstField`, `globShowErrorMessageFlag`). XFA 3.3 (chapter 10) lets the form's scripts use both by name. PdfCraft 0.21.1 reads neither.

Upstream state (checked before writing code, as PdfCraft's house rules ask):
- Script objects: PR #4948, open, not merged (performance concerns on large objects).
- Named text values: tracked in issue #5009, claimed on Nov 14 by another contributor on top of #4948.
- Still missing after both, and needed by IMM 5257: `nodes.append` / `nodes.remove` (the red-border highlighting), `createNode` and `loadXML` on the datasets (the dropdown lists, loaded at open), choice-list methods, and drawing barcodes. Issue #5009 lists the first three as planned but not started; barcodes are not tracked.
- The false "signature is invalid" bar on IRCC forms is issue #2759, already open with a fix in progress.

What we did: on top of PR #4948, named values now become small script objects with a `value` member; a write records an effect and the engine keeps the value for the rest of the session (Adobe's behaviour), so a click's change reaches the next click. Patch: `patches/pdfcraft-xfa-chono.patch` (tests: a new engine test, and 758 of 765 engine tests pass; the 7 failures need OCR models not installed in the build box). On the real IMM 5257 the Validate click now gets past `globValidatePressed` and runs deep into the checks (`validateCompletedForm` > `validateFirstSection` > `validateUCI`), then stops at `nodes.remove` in the colouring code. At open, `initLOV` still fails on the datasets methods.

### Progress (2026-11-18, later)

Our patched PdfCraft (`patches/pdfcraft-xfa-chono.patch`, on top of PR #4948) now runs the real IMM 5257 with no script errors at open and a Validate click that completes:
- Named `<variables>` values, kept between events.
- A data store under `xfa.datasets` (`createNode`, `nodes.append`, `loadXML`, `resolveNode(s)`, attributes), kept while the form is open: the form loads its 500 KiB of value lists at open.
- Choice-list methods (`clearItems`, `addItem`, `deleteItem`, `getDisplayItem`, `getSaveItem`, `boundItem`, `length`, `selectedIndex`), recorded as list overrides that are drawn and saved.
- `<bindItems>` from that data: Place of birth 262 countries, Country 243, Province 14 (all empty before).
- `getDeltas()` (empty), rich-text captions answering `#text`, property and node lists accepting `remove`/`append`/`insert`.
- Tests: new engine and JS tests; JS 218/218, XFA 317/317, engine all but the 7 OCR-model tests.
- Still missing: on an incomplete form Validate marks the missing fields with red borders, which PdfCraft computes but does not draw yet (property writes last for the script only); the barcode page; a Windows build.

## Not tested yet

- Calculated fields in the window (none of the tested forms has them).
