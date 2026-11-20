"""Automatic updates.

At most once a day, Chono asks GitHub for the VERSION on the main branch. When it is newer than
the installed one, Chono says so, closes, and a small PowerShell script (update.ps1, copied out of
the app folder first, since the installer replaces that folder; on a Mac, update.sh, which the
installer puts next to the app folder) waits for it to close, runs the
installer of the new version over the installed one (what is already installed is skipped), and
opens Chono again. Without internet, or on a computer where Chono is not installed (a source
checkout), nothing happens.

Dad mostly opens PDFs straight from Windows (Chono is the default PDF app), which never shows
Chono's window, so the installers also add a daily quiet check (app/actualizar.pyw, run by a
scheduled task on Windows and a LaunchAgent on a Mac). It updates only when no Chono or PdfCraft
window is open, and opens nothing afterwards.
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
    if sys.platform == "darwin":
        try:
            return subprocess.run(["pgrep", "-x", "pdfcraft"], capture_output=True, timeout=10).returncode == 0
        except Exception:
            return True
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


def chono_window_running() -> bool:
    """Whether Chono's own window (or another Chono program) is open, besides this process."""
    if sys.platform == "darwin":
        try:
            out = subprocess.run(["pgrep", "-f", "-m chono$"], capture_output=True, text=True, timeout=10).stdout
        except Exception:
            return True
        return any(int(p) != os.getpid() for p in out.split())
    if sys.platform != "win32":
        return False
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq pythonw.exe", "/NH"],
            capture_output=True, text=True, timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).stdout
    except Exception:
        return True
    return out.lower().count("pythonw.exe") > 1  # this check runs in pythonw too


def updater_command(root: Path, version: str, pid: int, relaunch: bool = True) -> list[str]:
    if sys.platform == "darwin":
        cmd = ["/bin/bash", str(root / "update.sh"), "--root", str(root), "--version", version, "--wait-pid", str(pid)]
        return cmd if relaunch else cmd + ["--no-launch"]
    script = root / "update.ps1"
    cmd = [
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), "-Root", str(root), "-Version", version, "-WaitPid", str(pid),
    ]
    return cmd if relaunch else cmd + ["-NoLaunch"]


def start(root: Path, version: str, relaunch: bool = True) -> bool:
    """Copy the updater out of the app folder and start it, detached; Chono must close next."""
    if sys.platform == "darwin":
        # update.sh is put next to app/ by the installer (installer/mac/update.sh)
        if not (root / "update.sh").is_file():
            return False
        try:
            subprocess.Popen(updater_command(root, version, os.getpid(), relaunch), cwd=str(root), start_new_session=True,
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            return False
        return True
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
            subprocess.Popen(updater_command(root, version, os.getpid(), relaunch), cwd=str(root), creationflags=flags | extra,
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


def quiet_check() -> str | None:
    """The daily quiet check (app/actualizar.pyw): update when nothing of Chono is open, without
    asking and without opening anything. Returns the version started, or None."""
    import json

    from .search import default_db

    cfg_path = default_db().with_name("config.json")
    try:
        config = json.loads(cfg_path.read_text("utf-8"))
        config = config if isinstance(config, dict) else {}
    except Exception:
        config = {}
    if chono_window_running():
        return None  # Chono's own window checks by itself; never update under it
    version = check(config)
    try:
        cfg_path.write_text(json.dumps(config, ensure_ascii=False), "utf-8")
    except OSError:
        pass
    root = install_root()
    if version and root is not None and start(root, version, relaunch=False):
        return version
    return None
