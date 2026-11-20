"""Stand-in for coremltools where it can't be installed (Windows), used only by Chono's
kraken_run.py. Kraken imports these names when it loads; they are needed only to read or
write Core ML files, which Chono never does. Using any of them raises ValueError, which
Kraken treats as "this loader doesn't fit" and moves on to the safetensors loader."""

__version__ = "0+chono.stub"


class Unavailable:
    def __init__(self, *args, **kwargs):
        raise ValueError("Core ML is not available on this computer")
