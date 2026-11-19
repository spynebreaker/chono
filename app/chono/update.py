"""Automatic updates.

At most once a day, Chono asks GitHub for the VERSION on the main branch. When it is newer than
the installed one, Chono says so, closes, and a small PowerShell script (update.ps1, copied out of
the app folder first, since the installer replaces that folder) waits for it to close, runs the
installer of the new version over the installed one (what is already installed is skipped), and
opens Chono again. Without internet, or on a computer where Chono is not installed (a source
checkout), nothing happens.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = "spynebreaker/chono"
VERSION_URL = f"https://raw.githubusercontent.com/{REPO}/main/VERSION"
CHECK_EVERY = 24 * 3600
_VERSION = re.compile(r"^\d+(\.\d+){0,3}$")


def install_root() -> Path | None:
    """The installed Chono folder (holding VERSION, env and app), or None when running from a
    source checkout."""
    root = Path(__file__).resolve().parents[2]
    if (root / "VERSION").is_file() and (root / "env").is_dir() and (root / "app").is_dir():
        return root
    return None


def parse(v: str) -> tuple[int, ...]:
    return tuple(int(p) for p in v.strip().split("."))


def installed_version(root: Path) -> str | None:
    try:
        v = (root / "VERSION").read_text(encoding="utf-8-sig").strip()
    except OSError:
        return None
    return v if _VERSION.match(v) else None


def latest_version(timeout: float = 5.0) -> str | None:
    """The VERSION on GitHub's main branch; None without internet or for anything unexpected."""
    try:
        req = urllib.request.Request(VERSION_URL, headers={"User-Agent": "Chono"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            v = r.read(64).decode("utf-8", "replace").strip()
    except Exception:
        return None
    return v if _VERSION.match(v) else None


def newer(latest: str | None, installed: str | None) -> bool:
    if not latest:
        return False
    if not installed:
        return True
    return parse(latest) > parse(installed)


def due(config: dict, now: float | None = None) -> bool:
    now = time.time() if now is None else now
    try:
        last = float(config.get("update_checked", 0))
    except (TypeError, ValueError):
        last = 0.0
    return now - last >= CHECK_EVERY or now < last


def pdfcraft_running() -> bool:
    """Whether a PdfCraft window is open: its files can't be replaced then."""
    if sys.platform != "win32":
        return False
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq pdfcraft.exe", "/NH"],
            capture_output=True, text=True, timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).stdout
    except Exception:
        return True  # unsure: don't update this time
    return "pdfcraft.exe" in out.lower()


def updater_command(root: Path, version: str, pid: int) -> list[str]:
    script = root / "update.ps1"
    return [
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), "-Root", str(root), "-Version", version, "-WaitPid", str(pid),
    ]


def start(root: Path, version: str) -> bool:
    """Copy the updater out of the app folder and start it, detached; Chono must close next."""
    try:
        shutil.copyfile(Path(__file__).with_name("update.ps1"), root / "update.ps1")
    except OSError:
        return False
    # Hidden, with a console of its own: PowerShell started without one (DETACHED_PROCESS)
    # exits at once, doing nothing.
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    # Out of any job Chono runs in (a launcher's job ends its children with it), when allowed.
    breakaway = getattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB", 0)
    for extra in (breakaway, 0):
        try:
            subprocess.Popen(updater_command(root, version, os.getpid()), cwd=str(root), creationflags=flags | extra,
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except OSError:
            continue
    return False


def check(config: dict) -> str | None:
    """The version to update to now, or None. Records the check in `config` (the caller saves it)."""
    root = install_root()
    if root is None or not due(config):
        return None
    latest = latest_version()
    if latest is None:
        return None  # no internet: try again next time
    config["update_checked"] = time.time()
    if newer(latest, installed_version(root)) and not pdfcraft_running():
        return latest
    return None
