"""
orfs.Route — Detailed routing + fill cell insertion (2 substeps).

5_2: detail_route.tcl → 5_2_route.odb
5_3: fillcell.tcl     → 5_3_fillcell.odb  (copied → 5_route.odb + 5_route.sdc)
"""
import os
import shutil
from dv_flow.mgr import TaskDataResult
from .orfs_util import (
    get_scripts_dir, get_platform_dir, extract_design_config, get_odb_path,
    build_env, run_openroad, emit_odb_fileset, stage_link_inputs, get_upstream_results,
)
from .orfs_log_parser import parse_log

_SUBSTEPS = [
    ("5_2_route",    "detail_route"),
    ("5_3_fillcell", "fillcell"),
]


async def Route(ctxt, input) -> TaskDataResult:
    p = input.params
    scripts_dir  = get_scripts_dir(p.flow_home)
    platform_dir = get_platform_dir(input)
    design_cfg   = extract_design_config(input)
    input_odb    = get_odb_path(input)

    stage_overrides = {"INPUT_ODB": input_odb}
    if p.detailed_route_args:
        stage_overrides["DETAILED_ROUTE_ARGS"] = p.detailed_route_args

    env = build_env(platform_dir, design_cfg, stage_overrides,
                    input.rundir, scripts_dir)

    # Symlink all upstream results files into this stage's RESULTS_DIR
    upstream_results = get_upstream_results(input)
    if upstream_results:
        import glob as _glob
        for f in _glob.glob(os.path.join(upstream_results, "*")):
            stage_link_inputs(env, f)

    markers = []

    for stage_id, tcl_name in _SUBSTEPS:
        logname = f"{stage_id}.log"
        status = await run_openroad(
            ctxt, env,
            os.path.join(scripts_dir, f"{tcl_name}.tcl"),
            stage_id, logname,
        )
        markers.extend(parse_log(os.path.join(input.rundir, "logs", logname)))
        if status:
            return TaskDataResult(status=status, output=[], markers=markers)
        env["INPUT_ODB"] = os.path.join(env["RESULTS_DIR"], f"{stage_id}.odb")

    results_dir = env["RESULTS_DIR"]
    src_odb = os.path.join(results_dir, "5_3_fillcell.odb")
    dst_odb = os.path.join(results_dir, "5_route.odb")
    if os.path.isfile(src_odb):
        shutil.copy2(src_odb, dst_odb)
    # Create 5_route.sdc for Finish (copy of GRT SDC)
    for sdc_candidate in ("5_1_grt.sdc", "4_cts.sdc"):
        sdc_src = os.path.join(results_dir, sdc_candidate)
        if os.path.isfile(sdc_src):
            dst_sdc = os.path.join(results_dir, "5_route.sdc")
            if not os.path.exists(dst_sdc):
                shutil.copy2(sdc_src, dst_sdc)
            break

    output = [emit_odb_fileset(input.rundir, "5_route.odb", input.name)]
    return TaskDataResult(status=0, output=output, changed=True, markers=markers)
