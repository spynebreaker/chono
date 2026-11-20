"""Automatic updates: version comparison, the daily check, the installed-folder detection and
the updater command. Nothing here touches the network."""

from pathlib import Path

from chono import update


def test_versions_compare_as_numbers():
    assert update.newer("0.10.0", "0.9.9")
    assert update.newer("1.0", "0.9")
    assert not update.newer("0.2.0", "0.2.0")
    assert not update.newer("0.1.0", "0.2.0")
    assert update.newer("0.1.0", None), "an install without a version is updated once"
    assert not update.newer(None, "0.1.0"), "no answer from the internet: nothing happens"


def test_the_check_runs_at_most_once_a_day():
    assert update.due({}, now=1_000_000)
    assert not update.due({"update_checked": 1_000_000}, now=1_000_000 + 3600)
    assert update.due({"update_checked": 1_000_000}, now=1_000_000 + 25 * 3600)
    assert update.due({"update_checked": 2_000_000}, now=1_000_000), "a clock set back checks again"
    assert update.due({"update_checked": "nonsense"}, now=1_000_000)


def test_a_source_checkout_is_not_an_install(monkeypatch):
    assert update.install_root() is None
    config = {}
    monkeypatch.setattr(update, "latest_version", lambda timeout=5.0: "99.0.0")
    assert update.check(config) is None
    assert config == {}, "nothing was checked"


def test_installed_version_is_read_and_checked(tmp_path: Path):
    (tmp_path / "VERSION").write_text("﻿0.3.1\n", encoding="utf-8")
    assert update.installed_version(tmp_path) == "0.3.1"
    (tmp_path / "VERSION").write_text("<html>", encoding="utf-8")
    assert update.installed_version(tmp_path) is None


def test_check_offers_a_newer_version_unless_pdfcraft_is_open(tmp_path: Path, monkeypatch):
    for d in ("env", "app"):
        (tmp_path / d).mkdir()
    (tmp_path / "VERSION").write_text("0.1.0", encoding="utf-8")
    monkeypatch.setattr(update, "install_root", lambda: tmp_path)
    monkeypatch.setattr(update, "latest_version", lambda timeout=5.0: "0.2.0")
    monkeypatch.setattr(update, "pdfcraft_running", lambda: False)
    config = {}
    assert update.check(config) == "0.2.0"
    assert config["update_checked"] > 0
    assert update.check(config) is None, "already checked today"
    monkeypatch.setattr(update, "pdfcraft_running", lambda: True)
    assert update.check({}) is None, "PdfCraft's files can't be replaced while it is open"
    monkeypatch.setattr(update, "latest_version", lambda timeout=5.0: None)
    offline = {}
    assert update.check(offline) is None and "update_checked" not in offline, "offline: try again next time"


def test_updater_command_runs_the_copied_script(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(update.sys, "platform", "win32")
    cmd = update.updater_command(tmp_path, "0.2.0", 1234)
    assert cmd[0] == "powershell.exe"
    assert str(tmp_path / "update.ps1") in cmd
    assert cmd[cmd.index("-Version") + 1] == "0.2.0" and cmd[cmd.index("-WaitPid") + 1] == "1234"
    assert Path(update.__file__).with_name("update.ps1").is_file(), "the updater ships with the app"


def test_on_a_mac_the_updater_is_the_shell_script_next_to_the_app(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(update.sys, "platform", "darwin")
    cmd = update.updater_command(tmp_path, "0.4.0", 77)
    assert cmd[:2] == ["/bin/bash", str(tmp_path / "update.sh")]
    assert cmd[cmd.index("--version") + 1] == "0.4.0" and cmd[cmd.index("--wait-pid") + 1] == "77"
    assert cmd[cmd.index("--root") + 1] == str(tmp_path)
    repo = Path(update.__file__).resolve().parents[2]
    assert (repo / "installer" / "mac" / "update.sh").is_file(), "the Mac updater ships with the installer"


def test_the_quiet_daily_check_opens_nothing_afterwards(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(update.sys, "platform", "win32")
    assert update.updater_command(tmp_path, "0.5.0", 1, relaunch=False)[-1] == "-NoLaunch"
    assert "-NoLaunch" not in update.updater_command(tmp_path, "0.5.0", 1)
    monkeypatch.setattr(update.sys, "platform", "darwin")
    assert update.updater_command(tmp_path, "0.5.0", 1, relaunch=False)[-1] == "--no-launch"
    script = (Path(update.__file__).with_name("update.ps1")).read_text("utf-8")
    assert "[switch]$NoLaunch" in script and "-not $NoLaunch" in script


def test_the_quiet_check_never_updates_under_an_open_chono(monkeypatch):
    monkeypatch.setattr(update, "chono_window_running", lambda: True)
    started = []
    monkeypatch.setattr(update, "start", lambda *a, **k: started.append(a) or True)
    assert update.quiet_check() is None and not started
