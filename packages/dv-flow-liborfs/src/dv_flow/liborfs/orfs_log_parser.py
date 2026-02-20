"""
orfs_log_parser.py — Parse OpenROAD/Yosys log files into TaskMarker objects.
"""
import re
from dv_flow.mgr import TaskMarker, TaskMarkerLoc, SeverityE

# OpenROAD structured message patterns: [ERROR ORD-123] / [WARNING ORD-123]
_STRUCTURED = [
    (SeverityE.Error,   re.compile(r'\[ERROR\s+[A-Z]+-\d+\]\s*(.*)')),
    (SeverityE.Warning, re.compile(r'\[WARNING\s+[A-Z]+-\d+\]\s*(.*)')),
]
# Fallback bare prefixes
_BARE = [
    (SeverityE.Error,   re.compile(r'^Error:\s*(.*)')),
    (SeverityE.Warning, re.compile(r'^Warning:\s*(.*)')),
    # Yosys
    (SeverityE.Error,   re.compile(r'^ERROR:\s*(.*)')),
    (SeverityE.Warning, re.compile(r'^Warning:\s*(.*)')),
]
_ALL_PATTERNS = _STRUCTURED + _BARE


def parse_log(log_path: str, notify=None):
    """Parse an OpenROAD/Yosys log file.

    For each ERROR or WARNING line, creates a TaskMarker and optionally calls
    notify(marker). Returns a list of all markers found.
    """
    markers = []
    try:
        with open(log_path) as f:
            for lineno, line in enumerate(f, 1):
                for severity, pat in _ALL_PATTERNS:
                    m = pat.search(line)
                    if m:
                        mk = TaskMarker(
                            severity=severity,
                            msg=m.group(1).strip(),
                            loc=TaskMarkerLoc(file=log_path, line=lineno),
                        )
                        markers.append(mk)
                        if notify:
                            notify(mk)
                        break  # only first matching pattern per line
    except OSError:
        pass
    return markers
