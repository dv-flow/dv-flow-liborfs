"""
orfs.MetricsCheck — Assert thresholds against ORFS flow metrics.

Reads the orfsMetrics JSON file produced by orfs.Finish and emits
error markers for any configured threshold violation.
"""
import json
import os
from dv_flow.mgr import TaskDataResult, TaskMarker, TaskMarkerLoc, SeverityE


async def MetricsCheck(ctxt, input) -> TaskDataResult:
    p = input.params
    markers = []

    # Locate metrics file from the orfsMetrics FileSet
    metrics_file = None
    for item in input.inputs:
        if getattr(item, 'type', None) == "std.FileSet" and \
                getattr(item, 'filetype', None) == "orfsMetrics":
            if item.files:
                metrics_file = os.path.join(item.basedir, item.files[0])
            break

    if not metrics_file or not os.path.isfile(metrics_file):
        markers.append(TaskMarker(
            severity=SeverityE.Error,
            msg="No metrics file found (orfsMetrics FileSet missing or empty). "
                "Ensure orfs.Finish ran successfully.",
        ))
        return TaskDataResult(status=1, output=[], markers=markers)

    with open(metrics_file) as f:
        m = json.load(f)

    status = 0
    # WNS check (setup timing slack — should be >= threshold)
    wns = m.get("timing__setup__ws", None)
    if wns is not None and p.wns_threshold is not None:
        if float(wns) < float(p.wns_threshold):
            markers.append(TaskMarker(
                severity=SeverityE.Error,
                msg=f"Timing not closed: WNS {wns:.3f} ns < threshold "
                    f"{p.wns_threshold:.3f} ns",
            ))
            status = 1

    # DRC violation count
    drc = m.get("design__violations", None)
    if drc is not None and p.max_drc is not None:
        if int(drc) > int(p.max_drc):
            markers.append(TaskMarker(
                severity=SeverityE.Error,
                msg=f"DRC violations {drc} exceed max_drc limit {p.max_drc}",
            ))
            status = 1

    # Die area check
    area = m.get("design__die__area", None)
    if area is not None and p.max_area_um2 and float(p.max_area_um2) > 0:
        if float(area) > float(p.max_area_um2):
            markers.append(TaskMarker(
                severity=SeverityE.Error,
                msg=f"Die area {area:.0f} um² exceeds limit {p.max_area_um2:.0f} um²",
            ))
            status = 1

    return TaskDataResult(status=status, output=[], markers=markers)
