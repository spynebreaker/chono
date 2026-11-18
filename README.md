# Chono

*Named after the Chonos, the people who lived on the hill where Guayaquil was founded, long before the Spanish city.*

A free, open-source PDF app in Spanish, built for an 80-year-old genealogist who was paying for Adobe Acrobat. Big buttons, few options, no subscription.

**Español:** Una aplicación de PDF gratuita y de código abierto, en español, con botones grandes. Abre PDF, lee actas escaneadas (OCR), busca apellidos en todas las actas a la vez (aunque estén escritos con o sin tilde, o con otra ortografía), une actas en un solo archivo e imprime.

## What it does

| Button | What happens |
|---|---|
| Abrir un PDF | Opens the file in [PdfCraft](https://github.com/storytold/pdfcraft), including XFA forms |
| Leer acta escaneada | Runs OCR (Tesseract, Spanish) so the scan becomes searchable; saves `name (con texto).pdf` |
| Buscar apellido | Searches every PDF in the records folder; finds `Núñez` from `Nunez`, and `Villacrés` from `Billacres` or `Villacrez` |
| Unir actas | Merges several records into one file per family |
| Imprimir | Sends a PDF to the printer |

## How it is built

The app is a thin Spanish interface over mature open-source tools. Each button calls the best tool for that job. See [docs/PROJECT.md](docs/PROJECT.md) for the plan, the test results and why each component was chosen.

## Install (Windows, no administrator rights)

```powershell
powershell -ExecutionPolicy Bypass -File installer\windows\install.ps1
```

Everything goes under `%LOCALAPPDATA%\Chono`. Remove it with `installer\windows\uninstall.ps1`.

## Develop and test

```bash
python -m pip install -r installer/requirements.txt pytest
python -m pytest tests
```

The tests build a synthetic corpus of 50 fake civil records with real-world spelling variants. No real records are stored in this repository.

## Clean-room rule

This project never copies, decompiles or studies Adobe code. Behavior comes from the public PDF standard (ISO 32000) and from observing how documents behave. See [CLAUDE.md](CLAUDE.md).

## License

AGPL-3.0. Third-party components and their licenses are listed in [THIRD_PARTY.md](THIRD_PARTY.md).
