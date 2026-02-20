import os
import shutil
import subprocess
import sys
import pytest


def _tools_available():
    """Return True if OPENROAD_EXE and YOSYS_EXE are set or on PATH."""
    openroad = os.environ.get('OPENROAD_EXE') or shutil.which('openroad')
    yosys = os.environ.get('YOSYS_EXE') or shutil.which('yosys')
    return bool(openroad and yosys)


_SKIP = pytest.mark.skipif(
    not _tools_available(),
    reason="OPENROAD_EXE and YOSYS_EXE must be set (or openroad/yosys on PATH)"
)

_GCD_DATA_DIR = os.path.join(
    os.path.dirname(__file__), '..', '..', 'tests', 'gcd_nangate45'
)


@_SKIP
def test_gcd_finish(tmpdir):
    """Run the GCD flow through the Finish stage; assert exit-0 and metrics file."""
    # Copy the test data to tmpdir so the flow runs in an isolated directory
    src_dir = os.path.abspath(_GCD_DATA_DIR)
    for item in os.listdir(src_dir):
        s = os.path.join(src_dir, item)
        d = os.path.join(str(tmpdir), item)
        if os.path.isdir(s):
            shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)

    cmd = [sys.executable, '-m', 'dv_flow.mgr', 'run', 'finish']
    result = subprocess.run(cmd, cwd=str(tmpdir))

    assert result.returncode == 0, "dfm run finish exited with non-zero status"

    metrics_file = os.path.join(
        str(tmpdir), 'rundir', 'gcd_nangate45.finish', 'results', '6_report.json'
    )
    assert os.path.isfile(metrics_file), \
        "Expected metrics file not found: %s" % metrics_file
