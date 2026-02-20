"""
orfs.Place — Placement stage (5 substeps).

3_1: global_place_skip_io.tcl → 3_1_place_gp_skip_io.odb
3_2: io_placement.tcl          → 3_2_place_iop.odb
3_3: global_place.tcl          → 3_3_place_gp.odb
3_4: resize.tcl                → 3_4_place_resized.odb
3_5: detail_place.tcl          → 3_5_place_dp.odb  (copied → 3_place.odb + 3_place.sdc)
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
    ("3_1_place_gp_skip_io", "global_place_skip_io"),
    ("3_2_place_iop",         "io_placement"),
    ("3_3_place_gp",          "global_place"),
    ("3_4_place_resized",     "resize"),
    ("3_5_place_dp",          "detail_place"),
]


async def Place(ctxt, input) -> TaskDataResult:
    p = input.params
    scripts_dir  = get_scripts_dir(p.flow_home)
    platform_dir = get_platform_dir(input)
    design_cfg   = extract_design_config(input)
    input_odb    = get_odb_path(input)

    stage_overrides = {"INPUT_ODB": input_odb}
    if p.place_density:
        stage_overrides["PLACE_DENSITY"]          = str(p.place_density)
    if p.place_density_lb_addon:
        stage_overrides["PLACE_DENSITY_LB_ADDON"] = str(p.place_density_lb_addon)
    if p.global_placement_args:
        stage_overrides["GLOBAL_PLACEMENT_ARGS"]  = p.global_placement_args

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
    src_odb = os.path.join(results_dir, "3_5_place_dp.odb")
    dst_odb = os.path.join(results_dir, "3_place.odb")
    if os.path.isfile(src_odb):
        shutil.copy2(src_odb, dst_odb)
    # Create 3_place.sdc for CTS (copy of the floorplan SDC)
    for sdc_candidate in ("2_floorplan.sdc", "2_1_floorplan.sdc", "1_synth.sdc"):
        sdc_src = os.path.join(results_dir, sdc_candidate)
        if os.path.isfile(sdc_src):
            dst_sdc = os.path.join(results_dir, "3_place.sdc")
            if not os.path.exists(dst_sdc):
                shutil.copy2(sdc_src, dst_sdc)
            break

    output = [emit_odb_fileset(input.rundir, "3_place.odb", input.name)]
    return TaskDataResult(status=0, output=output, changed=True, markers=markers)
