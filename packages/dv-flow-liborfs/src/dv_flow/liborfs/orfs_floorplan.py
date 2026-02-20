"""
orfs_floorplan.py — orfs.Floorplan task (4 substeps).

2_1: floorplan.tcl       → 2_1_floorplan.odb
2_2: macro_place.tcl     → 2_2_floorplan_macro.odb
2_3: tapcell.tcl         → 2_3_floorplan_tapcell.odb
2_4: pdn.tcl             → 2_4_floorplan_pdn.odb  (copied → 2_floorplan.odb)
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
    ("2_1_floorplan",         "floorplan"),
    ("2_2_floorplan_macro",   "macro_place"),
    ("2_3_floorplan_tapcell", "tapcell"),
    ("2_4_floorplan_pdn",     "pdn"),
]


async def Floorplan(ctxt, input) -> TaskDataResult:
    p = input.params
    scripts_dir  = get_scripts_dir(p.flow_home)
    platform_dir = get_platform_dir(input)
    design_cfg   = extract_design_config(input)
    input_odb    = get_odb_path(input)

    stage_overrides = {"INPUT_ODB": input_odb}
    if p.core_utilization:
        stage_overrides["CORE_UTILIZATION"]  = str(p.core_utilization)
    if p.core_aspect_ratio:
        stage_overrides["CORE_ASPECT_RATIO"] = p.core_aspect_ratio
    if p.core_margin:
        stage_overrides["CORE_MARGIN"]       = p.core_margin
    if p.die_area:
        stage_overrides["DIE_AREA"]          = p.die_area
    if p.core_area:
        stage_overrides["CORE_AREA"]         = p.core_area
    if p.pdn_tcl:
        stage_overrides["PDN_TCL"]           = p.pdn_tcl

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
        # Chain: pass output ODB of this substep as input to next
        env["INPUT_ODB"] = os.path.join(env["RESULTS_DIR"], f"{stage_id}.odb")

    # Canonical output name
    src_odb = os.path.join(env["RESULTS_DIR"], "2_4_floorplan_pdn.odb")
    dst_odb = os.path.join(env["RESULTS_DIR"], "2_floorplan.odb")
    if os.path.isfile(src_odb):
        shutil.copy2(src_odb, dst_odb)
    # Create canonical SDC for next stage (2_floorplan.sdc = 2_1_floorplan.sdc)
    src_sdc = os.path.join(env["RESULTS_DIR"], "2_1_floorplan.sdc")
    dst_sdc = os.path.join(env["RESULTS_DIR"], "2_floorplan.sdc")
    if os.path.isfile(src_sdc) and not os.path.exists(dst_sdc):
        shutil.copy2(src_sdc, dst_sdc)

    output = [emit_odb_fileset(input.rundir, "2_floorplan.odb", input.name)]
    return TaskDataResult(status=0, output=output, changed=True, markers=markers)
