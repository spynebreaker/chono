"""Open the PDF given on the command line with Chono (used by Windows "Open with")."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from chono.launcher import main  # noqa: E402

main()
