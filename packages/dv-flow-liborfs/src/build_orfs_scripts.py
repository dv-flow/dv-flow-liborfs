"""
Copies ORFS TCL/Python scripts from the OpenROAD-flow-scripts submodule into
src/dv_flow/liborfs/share/scripts/ at build/sdist time.

If the submodule is absent (e.g. installing from PyPI), the copy is skipped
gracefully; tasks fall back to the ORFS_FLOW_HOME env var at runtime.
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
# Source: OpenROAD-flow-scripts submodule (sibling of this package dir)
FLOW_SRC    = ROOT.parents[0] / "OpenROAD-flow-scripts" / "flow"
SCRIPTS_SRC = FLOW_SRC / "scripts"
UTIL_SRC    = FLOW_SRC / "util"
COMMON_SRC  = FLOW_SRC / "platforms" / "common"
# Destination: bundled inside the installed package
SHARE_DST   = ROOT / "src" / "dv_flow" / "liborfs" / "share"
SCRIPTS_DST = SHARE_DST / "scripts"
UTIL_DST    = SHARE_DST / "util"
COMMON_DST  = SHARE_DST / "platforms" / "common"

COPY_EXTS  = {".tcl", ".sh", ".py", ".yaml", ".v", ".script"}
UTIL_FILES = ["genElapsedTime.py", "genMetrics.py", "def2stream.py"]


def _copy_scripts() -> None:
    if not SCRIPTS_SRC.is_dir():
        print(f"[build_orfs_scripts] SKIP: {SCRIPTS_SRC} not found "
              "(tasks will require ORFS_FLOW_HOME at runtime)")
        return
    SCRIPTS_DST.mkdir(parents=True, exist_ok=True)
    count = 0
    for f in SCRIPTS_SRC.iterdir():
        if f.is_file() and f.suffix in COPY_EXTS:
            dst = SCRIPTS_DST / f.name
            if dst.exists():
                dst.chmod(0o755)
            shutil.copy2(f, dst)
            # Make scripts executable; others read-only for user
            dst.chmod(0o755 if f.suffix in {".sh", ".py"} else 0o644)
            count += 1
    print(f"[build_orfs_scripts] Copied {count} scripts → {SCRIPTS_DST}")

    UTIL_DST.mkdir(parents=True, exist_ok=True)
    for name in UTIL_FILES:
        src = UTIL_SRC / name
        if src.is_file():
            dst = UTIL_DST / name
            if dst.exists():
                dst.chmod(0o644)
            shutil.copy2(src, dst)
            dst.chmod(0o644)
    print(f"[build_orfs_scripts] Copied util files → {UTIL_DST}")

    # Copy platforms/common/ (e.g. lcu_kogge_stone.v for Yosys)
    if COMMON_SRC.is_dir():
        COMMON_DST.mkdir(parents=True, exist_ok=True)
        for f in COMMON_SRC.iterdir():
            if f.is_file():
                dst = COMMON_DST / f.name
                if dst.exists():
                    dst.chmod(0o644)
                shutil.copy2(f, dst)
                dst.chmod(0o644)
        print(f"[build_orfs_scripts] Copied platforms/common → {COMMON_DST}")


class BuildPy(_build_py):
    def run(self):
        _copy_scripts()
        super().run()


class Sdist(_sdist):
    def run(self):
        _copy_scripts()
        super().run()


__all__ = ["BuildPy", "Sdist"]
