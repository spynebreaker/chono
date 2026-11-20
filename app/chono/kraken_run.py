"""Starts Kraken's command line inside Kraken's own Python environment (not Chono's).

Kraken tries its model loaders in order and the first one, for Core ML models, needs
coremltools. coremltools has no Windows build: pip installs an empty package there, the
import fails and Kraken stops before trying the safetensors loader that Chono's model needs.
When coremltools can't be imported, the Core ML loader is left out, and a stand-in
(coreml_stub/) provides the names Kraken imports at start (only Core ML reading and writing
use them).
Usage: python kraken_run.py <kraken arguments>
"""

import importlib.metadata as metadata
import sys

def _coreml_importable() -> bool:
    try:
        import coremltools  # noqa: F401
    except Exception:
        return False
    return True


if not _coreml_importable():
    from pathlib import Path

    sys.modules.pop("coremltools", None)  # a failed import of the empty package
    sys.path.insert(0, str(Path(__file__).resolve().with_name("coreml_stub")))
    _entry_points = metadata.entry_points

    def entry_points(**params):
        found = _entry_points(**params)
        if params.get("group") == "kraken.loaders":
            return metadata.EntryPoints(e for e in found if e.name != "coreml")
        return found

    metadata.entry_points = entry_points

if __name__ == "__main__":
    from kraken.kraken import cli

    sys.argv[0] = "kraken"
    sys.exit(cli())
