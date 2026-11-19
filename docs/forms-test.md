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
- Still missing: a Windows build.

### Red borders (2026-11-18, night)

- A script that paints a field's border edge by edge (or takes the border out) now records a border override, saved in the file and drawn on the widget. Radio buttons inside a group take theirs too.
- Real IMM 5257, empty form, Validate click: 54 fields marked red ("232, 6, 6"), 1 marked "incorrect" ("231, 6, 6"), 11 reset to white; 44 widget names on the page carry the red border. Checked by rendering page 1 of the saved file: the required fields show red frames, as in Reader.
- New engine test `xfa_scripts_paint_and_clear_a_field_border` (fails without the fix for radio buttons).

### Barcodes and a complete form (2026-11-19)

- PDF417 barcode fields are drawn as bars (vendored MIT `pdf417` crate), with the form's module sizes. A rendered symbol decodes back to its text with zxing-cpp (automation test `a_pdf417_field_is_drawn_as_bars`).
- Before a save or print the form's `preSave`/`prePrint` scripts run; `<manifest>` lists, `.dataNode` paths and `xfa.data.saveXML()` work; choosing a radio button runs its click script (it clears the red mark).
- Real IMM 5257, filled with synthetic test answers by a script that fills whatever Validate marks: after 4 rounds Validate says the form is complete (`Validated: Yes`), the barcode page appears (page 6), and saving fills the 5 barcodes with the answers (`IMM5257_06-2018_1|01||SAMPLE|...`). All 5 decode with zxing-cpp from PdfCraft's own rendering.
- Not checked: that IRCC's systems accept our barcodes (only an independent reader was used), and Adobe's exact checksum (`CRCNum` is computed over our data XML, which is not byte-for-byte Adobe's).

### IMM 5257: the last two red fields (2026-11-19)

- After a full Validate, "Previous countries of residence" (Country_2, Status_2) stayed red even when filled. Cause: a script's `mandatory = "error"` lasted for that script only, so when the field was filled its own check (which clears the mark only on a required field) saw it as optional and left the red. PdfCraft now keeps `mandatory` for the form's later events, stored with the form's other script changes (`/Mandatory`). Engine test `a_field_a_script_made_required_stays_required`.
- Same form: the values of subforms marked `<bind match="none"/>` were written to the data under an extra node of their own name (`Fragment1`); by XFA 3.3 such a subform adds no data level, and the form's own data agrees. Fixed (`a_subform_bound_to_no_data_adds_no_data_level`), so the saved data now matches the form's structure.
- With both, IMM 5257 filled by the test script ends with 0 red fields and `Validated: Yes` (before: 2 red), and the form now also asks for the dates of a previous country and rejects an alias equal to the full name, as it should.

### 18 more forms: IRS and IRCC (2026-11-19)

Tested with a script that opens each form, presses its Validate or Check button, fills every field with synthetic values (accents included), saves (incrementally, as Chono does) and reopens.

| Form | Kind | Result |
|---|---|---|
| IRS 1040-X, Schedule 1, Schedule C, Schedule SE, 2848, 4506-T, 8821, 8962, 9465, W-7 | static XFA (2848 and 1040-X with scripts) | All values kept after save and reopen |
| IRCC IMM 1294, 1295, 5710 (study and work permits) | dynamic, signed | Validate and Clear Form work; save keeps the signature intact |
| IRCC IMM 5406, 5532, 5562, 5669 | dynamic | Validate works, values kept |
| IRCC IMM 5476 (use of a representative) | static | Values kept |

Fixed on the way (private commit e23a114e): a bare `parent` in scripts (IMM 5562), rich-text data values emptied on reopening (IMM 5476), saving after a script removed a page (IMM 5406, my build 3 regression), `xfa.resolveNode("xfa.datasets")` (IMM 5710 Clear Form).

Not bugs: IRS 2848's Check Form stops at a reference to `Table_Line1`, an object the form doesn't have (any viewer stops there). On IMM 1294/1295/5710 some test values are cleared on reopening by the form's own opening scripts, because the test answers contradict each other (a province with a country other than Canada or the US); real answers aren't affected.

### Windows build (2026-11-19)

- Built from Linux with the MinGW toolchain (x86_64-pc-windows-gnu), no Microsoft SDK needed. Ubuntu's MinGW lacks 9 newer user32 functions (window DPI behaviour); a small extra import library supplies them at link time. The programs need only Windows' own DLLs.
- Kept on the `pdfcraft-build` branch of this repository (`pdfcraft-chono-windows-x64.zip`, now build 2, see the branch README); the installer downloads it, checks the hash, and puts it over the official portable build with `CHONO_PATCHED.txt`.
- Tested on Goreguzzler (Windows 11) in the real window, Spanish interface: IMM 5257 opens, the dropdowns are full, Validate on the empty form marks 53 fields red and sets "Validated: No", Save keeps it. Page 1 rendered: 0 red pixels before, 5,071 after.

## Not tested yet

- Calculated fields in the window (none of the tested forms has them).

### IMM 5707 (Family information), 2026-11-19

Second IRCC form, 91 fields (55 text, 12 lists, 7 radio groups, 16 buttons).

- Found two bugs, both fixed in the patch, each with an engine test that failed before the fix:
  - On open, SectionB's layout script stopped with "cannot convert null": `this.resolveNode("SectionB._Child")` (a `_name` step, the instance manager, inside a path) found nothing (`xfa_resolve_node_from_an_object_by_its_own_name`).
  - Validate stopped with "not a callable function": the form names the missing field from a label with `draw.value.resolveNode("#exData")`, and a label's `value` read as plain text instead of its value element (`xfa_draw_value_is_its_value_element`).
- After the fix: opens with 0 script errors; Validate on the empty form shows the form's own message, "The following field must have a value: APPLICANT, Family name (as shown on passport/travel document)". IMM 5257 still validates and draws its barcodes.

### IMM 5409 and IMM 5645: static forms (2026-11-19)

- IMM 5409 (Statutory Declaration of Common-Law Union) and IMM 5645 (Family Information, visitors/students/workers) are static XFA forms: fixed pages, no `/NeedsRendering`. They open with no errors, and fields fill, save and print.
- Stock PdfCraft runs no XFA script on static forms (its parity notes say scripts run on forms it lays out). So IMM 5409's Validate did nothing, and IMM 5645's checkboxes didn't untick each other (Visitor/Worker/Student/Other, Yes/No).
- Chono build 3 of PdfCraft (`pdfcraft-0.21.1-chono3`, private commit ff578450) runs them. The script engine maps each template object to the AcroForm field of the same name (page-master fields by the name without the root and page-set steps), marks push buttons that have click scripts, runs a check box's click script after it changes, and writes what the scripts change back to the fields: hidden or shown (widget flags), read-only, border colour and width, then redraws them.
- Local check on the real files: IMM 5409 Validate shows "The following field must have a value: Country"; IMM 5645 clears Worker when Visitor is ticked. The scripts that run on opening only write empty values, so nothing visible changes.
- Engine test with a synthetic form: `static_xfa_forms_run_their_scripts_on_their_own_fields`.
- `needs_form_reader` sends static scripted forms to the other reader only when the installed PdfCraft is older than build 3 (`pdfcraft_build()` reads the tag in `CHONO_PATCHED.txt`).
- Choosing a radio button on a static form runs that button's click script too (private commit dbc681d6; the button is the group's field in the same place as the widget that is on). IMM 5409's radio groups have no scripts of their own, so this is for other forms.
