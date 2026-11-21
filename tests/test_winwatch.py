import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from chono.winwatch import Proc, is_stuck, open_watched, shows, stuck_pids  # noqa: E402


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += s


def test_stuck_rules():
    assert is_stuck(Proc(1, 120))  # old and windowless
    assert not is_stuck(Proc(1, 5))  # still starting
    assert not is_stuck(Proc(1, 120, ["a.pdf - PdfCraft"]))
    assert is_stuck(Proc(1, 120, ["a.pdf - PdfCraft"], hung=True))


def test_shows_file_name_only_in_live_windows():
    assert shows([Proc(1, 3, ["Carta.pdf - PdfCraft"])], r"C:\x\carta.pdf")
    assert not shows([Proc(1, 3, ["Carta.pdf - PdfCraft"], hung=True)], r"C:\x\carta.pdf")
    assert not shows([Proc(1, 3, [])], r"C:\x\carta.pdf")


def test_brief_hang_is_not_stuck():
    states = iter([[Proc(1, 100, ["a - PdfCraft"], hung=True)], [Proc(1, 104, ["a - PdfCraft"])]])
    assert stuck_pids(lambda: next(states), sleep=lambda s: None) == []


def test_stuck_instance_is_cleared_before_opening():
    clock = Clock()
    world = {"procs": [Proc(7, 600)]}
    killed, launched = [], []

    def kill(pids):
        killed.extend(pids)
        world["procs"] = [p for p in world["procs"] if p.pid not in pids]

    def launch():
        launched.append(1)
        world["procs"].append(Proc(9, 1, ["f.pdf - PdfCraft"]))

    assert open_watched("f.pdf", launch, lambda: list(world["procs"]), kill, clock.sleep, clock)
    assert killed == [7] and len(launched) == 1


def test_launch_that_never_shows_is_retried_once():
    clock = Clock()
    world = {"procs": [], "n": 0}
    killed = []

    def launch():
        world["n"] += 1
        world["procs"].append(Proc(world["n"], 0, [] if world["n"] == 1 else ["f.pdf - PdfCraft"]))

    def kill(pids):
        killed.extend(pids)
        world["procs"] = [p for p in world["procs"] if p.pid not in pids]

    assert open_watched("f.pdf", launch, lambda: list(world["procs"]), kill, clock.sleep, clock)
    assert killed == [1] and world["n"] == 2


def test_gives_up_after_two_tries():
    clock = Clock()
    n = []
    assert not open_watched("f.pdf", lambda: n.append(1), lambda: [], lambda p: None, clock.sleep, clock)
    assert len(n) == 2


def test_viewer_titles_old_and_new():
    from chono.winwatch import is_viewer_title

    assert is_viewer_title("carta.pdf - Chono")
    assert is_viewer_title("carta.pdf — PdfCraft")
    assert is_viewer_title("Chono")  # the viewer with nothing open
    assert not is_viewer_title("carta.pdf - Notepad")
