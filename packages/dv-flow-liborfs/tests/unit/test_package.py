import pytest
from dv_flow.mgr import PackageLoader
import dv_flow.liborfs  # noqa: F401 — triggers package registration


def _load_orfs_pkg():
    loader = PackageLoader()
    root = loader.load_rgy('orfs')
    return root.pkg_m['orfs']


def test_orfs_package_loads():
    """The 'orfs' package can be loaded via PackageLoader."""
    pkg = _load_orfs_pkg()
    assert pkg is not None
    assert pkg.name == 'orfs'


def test_design_config_registered():
    """orfs.DesignConfig task type is registered in the package registry."""
    pkg = _load_orfs_pkg()
    assert 'orfs.DesignConfig' in pkg.task_m


def test_synth_registered():
    """orfs.Synth task type is registered in the package registry."""
    pkg = _load_orfs_pkg()
    assert 'orfs.Synth' in pkg.task_m
