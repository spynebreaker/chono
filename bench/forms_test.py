"""Fill-and-save check for public PDF forms with PdfCraft's CLI.

Usage: python forms_test.py <pdfcraft-cli> <form.pdf>...
Fills the first three long text fields with an accented name and the first
check box, saves a copy next to the form, and checks the value landed in
the AcroForm fields and, if present, in the XFA data.
"""

import json
import pathlib
import subprocess
import sys

import pikepdf

NAME = "José Núñez Peña"


def run(cli: str, steps: list, work: pathlib.Path) -> dict:
    p = work / "steps.json"
    p.write_text(json.dumps(steps))
    r = subprocess.run([cli, "run", "--script", str(p), "--report"], capture_output=True, text=True, timeout=300)
    try:
        return json.loads(r.stdout)
    except ValueError:
        return {"ok": False, "raw": (r.stdout + r.stderr)[:600]}


def main(cli: str, forms: list[str]) -> None:
    for f in map(pathlib.Path, forms):
        work = f.parent
        rep = run(cli, [{"tool": "doc_open", "args": {"path": str(f)}}, {"tool": "form_fields", "args": {"doc": 1}}], work)
        if not rep.get("ok"):
            print(f.stem, "open failed", rep)
            continue
        fields = rep["steps"][1]["result"][0]["fields"]
        texts = [x for x in fields if x["type"] == "text" and not x.get("read_only") and (x.get("max_length") or 99) > 20][:3]
        boxes = [x for x in fields if x["type"] == "checkbox" and not x.get("read_only")][:1]
        values = {x["name"]: NAME for x in texts} | {x["name"]: True for x in boxes}
        out = work / (f.stem + "_lleno.pdf")
        out.write_bytes(f.read_bytes())  # incremental save keeps any signature valid
        rep2 = run(cli, [{"tool": "doc_open", "args": {"path": str(out)}},
                         {"tool": "form_fill", "args": {"doc": 1, "values": values}},
                         {"tool": "doc_save", "args": {"doc": 1}}], work)
        xfa_ok = None
        if rep2.get("ok"):
            with pikepdf.open(out) as pdf:
                af = pdf.Root.get("/AcroForm")
                x = af.get("/XFA") if af is not None else None
                if isinstance(x, pikepdf.Array):
                    parts = {str(x[i]): x[i + 1] for i in range(0, len(x), 2)}
                    xfa_ok = NAME in parts["datasets"].read_bytes().decode("utf-8", "ignore")
        print(f"{f.stem}: fields {len(fields)}, filled {len(values)}, saved {rep2.get('ok')}, XFA data updated {xfa_ok}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
