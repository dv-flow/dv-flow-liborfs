"""
orfs.Finish — Density fill + final report (2 substeps).

6_1:     density_fill.tcl → 6_1_fill.odb
6_report: final_report.tcl → metrics in LOG_DIR/6_report.json

Emits:
  - orfsODB FileSet pointing to results/6_1_fill.odb
  - orfsMetrics FileSet pointing to logs/ (for orfs.MetricsCheck)
"""
import os
from dv_flow.mgr import FileSet, TaskDataResult
from .orfs_util import (
    get_scripts_dir, get_platform_dir, extract_design_config, get_odb_path,
    build_env, run_openroad, emit_odb_fileset, stage_link_inputs, get_upstream_results,
)
from .orfs_log_parser import parse_log


async def Finish(ctxt, input) -> TaskDataResult:
    p = input.params
    scripts_dir  = get_scripts_dir(p.flow_home)
    platform_dir = get_platform_dir(input)
    design_cfg   = extract_design_config(input)
    input_odb    = get_odb_path(input)

    env = build_env(platform_dir, design_cfg, {"INPUT_ODB": input_odb},
                    input.rundir, scripts_dir)

    # Symlink all upstream results files into this stage's RESULTS_DIR
    upstream_results = get_upstream_results(input)
    if upstream_results:
        import glob as _glob
        for f in _glob.glob(os.path.join(upstream_results, "*")):
            stage_link_inputs(env, f)

    markers = []

    # Substep 6_1: density fill
    log1 = "6_1_fill.log"
    status = await run_openroad(
        ctxt, env,
        os.path.join(scripts_dir, "density_fill.tcl"),
        "6_1_fill", log1,
    )
    markers.extend(parse_log(os.path.join(input.rundir, "logs", log1)))
    if status:
        return TaskDataResult(status=status, output=[], markers=markers)

    env["INPUT_ODB"] = os.path.join(env["RESULTS_DIR"], "6_1_fill.odb")
    # Create 6_1_fill.sdc for final_report.tcl (copy of upstream SDC)
    import shutil as _shutil
    for sdc_candidate in ("5_route.sdc", "5_1_grt.sdc", "4_cts.sdc"):
        sdc_src = os.path.join(env["RESULTS_DIR"], sdc_candidate)
        if os.path.isfile(sdc_src):
            dst_sdc = os.path.join(env["RESULTS_DIR"], "6_1_fill.sdc")
            if not os.path.exists(dst_sdc):
                _shutil.copy2(sdc_src, dst_sdc)
            break

    # Substep 6_report: final timing/power/area report
    log2 = "6_report.log"
    status = await run_openroad(
        ctxt, env,
        os.path.join(scripts_dir, "final_report.tcl"),
        "6_report", log2,
    )
    markers.extend(parse_log(os.path.join(input.rundir, "logs", log2)))

    output = [
        emit_odb_fileset(input.rundir, "6_1_fill.odb", input.name),
        # Metrics FileSet: basedir=logs/, file=6_report.json
        FileSet(
            src=input.name,
            filetype="orfsMetrics",
            basedir=os.path.join(input.rundir, "logs"),
            files=["6_report.json"],
        ),
    ]
    return TaskDataResult(status=status, output=output,
                          changed=(status == 0), markers=markers)
