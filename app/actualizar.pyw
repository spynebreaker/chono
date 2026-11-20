"""Daily quiet update check, started by a scheduled task (Windows) or a LaunchAgent (Mac).
Updates Chono when nothing of it is open; opens no window."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from chono.update import quiet_check  # noqa: E402

quiet_check()
