"""
Copies the nangate45 platform directory from the OpenROAD-flow-scripts submodule
into src/dv_flow/liborfs_nangate45/share/nangate45/ at build/sdist time.

If the submodule is absent (e.g. installing from PyPI), the copy is skipped;
the bundled share/ directory must have been included in the sdist.
"""
from __future__ import annotations
import shutil
from pathlib import Path
from setuptools.command.build_py import build_py as _build_py
from setuptools.command.sdist import sdist as _sdist


def _project_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    return Path(__file__).resolve().parents[1]


ROOT = _project_root()
SRC  = ROOT.parents[0] / "OpenROAD-flow-scripts" / "flow" / "platforms" / "nangate45"
DST  = ROOT / "src" / "dv_flow" / "liborfs_nangate45" / "share" / "nangate45"


def _copy_platform() -> None:
    if not SRC.is_dir():
        print(f"[build_platform] SKIP: {SRC} not found")
        return
    if DST.exists():
        # Make all entries writable before removal (source may be read-only from git)
        DST.chmod(0o755)
        for f in DST.rglob("*"):
            if f.is_file():
                f.chmod(0o644)
            elif f.is_dir():
                f.chmod(0o755)
        shutil.rmtree(DST)
    shutil.copytree(SRC, DST)
    # Ensure files are writable (source may be read-only from git)
    for f in DST.rglob("*"):
        if f.is_file():
            f.chmod(0o644)
    print(f"[build_platform] Copied nangate45 platform ({_dir_size_mb(DST):.1f} MB) → {DST}")


def _dir_size_mb(path: Path) -> float:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) / 1e6


class BuildPy(_build_py):
    def run(self):
        _copy_platform()
        super().run()


class Sdist(_sdist):
    def run(self):
        _copy_platform()
        super().run()


__all__ = ["BuildPy", "Sdist"]
