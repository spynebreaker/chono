"""Keep a stuck PdfCraft from swallowing Dad's opens on Windows.

On Dad's PC PdfCraft sometimes stalls while starting: the process lives on with no window,
holds the single-instance socket, and every later double click is handed to it, so nothing
opens. Before opening, Chono ends PdfCraft processes that have been up a while with no
visible window (or a window that stopped answering); after opening it waits for the file's
window and, if it never shows, cleans up and tries once more.

The decisions take plain data so they can be tested on any system; only the probes use
the Windows API.
"""

from __future__ import annotations

import re
import subprocess
import time
from dataclasses import dataclass, field
from typing import Callable

STALE_AFTER_S = 45  # a PdfCraft this old with no window is stuck, not starting
WAIT_S = 25  # how long to wait for the opened file's window
HUNG_RECHECK_S = 4  # a window must stay hung this long before it counts


@dataclass
class Proc:
    pid: int
    age: float  # seconds since it started
    titles: list[str] = field(default_factory=list)  # visible windows with a PdfCraft title
    hung: bool = False  # a visible PdfCraft window stopped answering


def is_stuck(p: Proc, stale_after: float = STALE_AFTER_S) -> bool:
    if p.hung:
        return True
    return not p.titles and p.age >= stale_after


def shows(procs: list[Proc], path: str) -> bool:
    name = re.split(r"[\\/]", path)[-1].lower()
    return any(name in t.lower() for p in procs if not p.hung for t in p.titles)


def stuck_pids(
    probe: Callable[[], list[Proc]],
    sleep: Callable[[float], None] = time.sleep,
    stale_after: float = STALE_AFTER_S,
) -> list[int]:
    """Processes that are stuck now and still stuck a few seconds later."""
    first = {p.pid for p in probe() if is_stuck(p, stale_after)}
    if not first:
        return []
    sleep(HUNG_RECHECK_S)
    return [p.pid for p in probe() if p.pid in first and is_stuck(p, stale_after)]


def wait_for(
    path: str,
    probe: Callable[[], list[Proc]],
    timeout: float = WAIT_S,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> bool:
    end = clock() + timeout
    while True:
        if shows(probe(), path):
            return True
        if clock() >= end:
            return False
        sleep(0.5)


def open_watched(
    path: str,
    launch: Callable[[], None],
    probe: Callable[[], list[Proc]],
    kill: Callable[[list[int]], None],
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> bool:
    """Open path, clearing stuck PdfCraft before and, once, after a failed try."""
    stuck = stuck_pids(probe, sleep)
    if stuck:
        kill(stuck)
    for attempt in range(2):
        launch()
        if wait_for(path, probe, sleep=sleep, clock=clock):
            return True
        if attempt == 0:
            # the launch went nowhere: anything without a window now is stuck
            kill(stuck_pids(probe, sleep, stale_after=0))
    return False


# Windows probes ----------------------------------------------------------------------------

NO_WINDOW = 0x08000000  # CREATE_NO_WINDOW


def _pids() -> list[int]:
    out = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq pdfcraft.exe", "/FO", "CSV", "/NH"],
        capture_output=True, text=True, creationflags=NO_WINDOW,
    ).stdout
    pids = []
    for line in out.splitlines():
        cells = [c.strip('"') for c in line.split('","')]
        if len(cells) > 1 and cells[1].isdigit():
            pids.append(int(cells[1]))
    return pids


def _age(pid: int) -> float:
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    h = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return 0.0
    try:
        times = [wintypes.FILETIME() for _ in range(4)]
        if not k32.GetProcessTimes(h, *[ctypes.byref(t) for t in times]):
            return 0.0
        now = wintypes.FILETIME()
        k32.GetSystemTimeAsFileTime(ctypes.byref(now))

        def ticks(t: wintypes.FILETIME) -> int:
            return (t.dwHighDateTime << 32) | t.dwLowDateTime

        return max(0.0, (ticks(now) - ticks(times[0])) / 1e7)
    finally:
        k32.CloseHandle(h)


def probe() -> list[Proc]:
    import ctypes
    from ctypes import wintypes

    u32 = ctypes.windll.user32  # type: ignore[attr-defined]
    procs = {pid: Proc(pid, _age(pid)) for pid in _pids()}
    if not procs:
        return []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def each(hwnd, _lparam):
        pid = wintypes.DWORD()
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        p = procs.get(pid.value)
        if p and u32.IsWindowVisible(hwnd):
            buf = ctypes.create_unicode_buffer(512)
            u32.GetWindowTextW(hwnd, buf, 512)
            if buf.value.endswith("PdfCraft"):
                p.titles.append(buf.value)
                if u32.IsHungAppWindow(hwnd):
                    p.hung = True
        return True

    u32.EnumWindows(each, 0)
    return list(procs.values())


def kill(pids: list[int]) -> None:
    for pid in pids:
        subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, creationflags=NO_WINDOW)
