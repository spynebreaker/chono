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

## Not tested yet

- Form scripts (calculations, Validate buttons) in the PdfCraft window; none of the IRS forms has calculated fields.
- The PdfCraft window itself on Windows with these forms (only the engine was tested).
