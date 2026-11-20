"""The installers' package list must parse, and pick one version of each package per system."""
from pathlib import Path

import pytest

packaging = pytest.importorskip("packaging.requirements")

REQ = Path(__file__).resolve().parents[1] / "installer" / "requirements.txt"
SYSTEMS = {
    "windows": {"sys_platform": "win32", "platform_machine": "AMD64"},
    "mac": {"sys_platform": "darwin", "platform_machine": "arm64"},
    "intel mac": {"sys_platform": "darwin", "platform_machine": "x86_64"},
    "linux": {"sys_platform": "linux", "platform_machine": "x86_64"},
}


def test_every_line_parses_and_each_system_gets_one_version_per_package():
    reqs = [packaging.Requirement(line.strip()) for line in REQ.read_text().splitlines()
            if line.strip() and not line.startswith("#")]
    for name, env in SYSTEMS.items():
        chosen = [r.name.lower() for r in reqs if r.marker is None or r.marker.evaluate(env)]
        assert len(chosen) == len(set(chosen)), f"{name}: a package listed twice"
        assert "pikepdf" in chosen and "ocrmypdf" in chosen, name
