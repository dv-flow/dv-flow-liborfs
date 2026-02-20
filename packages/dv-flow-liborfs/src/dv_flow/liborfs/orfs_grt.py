"""
orfs.GlobalRoute — Global routing (1 substep).

5_1: global_route.tcl → 5_1_grt.odb + 5_1_grt.sdc
"""
import os
from dv_flow.mgr import TaskDataResult
from .orfs_util import (
    get_scripts_dir, get_platform_dir, extract_design_config, get_odb_path,
    build_env, run_openroad, emit_odb_fileset, stage_link_inputs, get_upstream_results,
)
from .orfs_log_parser import parse_log


async def GlobalRoute(ctxt, input) -> TaskDataResult:
    p = input.params
    scripts_dir  = get_scripts_dir(p.flow_home)
    platform_dir = get_platform_dir(input)
    design_cfg   = extract_design_config(input)
    input_odb    = get_odb_path(input)

    stage_overrides = {"INPUT_ODB": input_odb}
    if p.routing_layer_adjustment:
        stage_overrides["ROUTING_LAYER_ADJUSTMENT"] = str(p.routing_layer_adjustment)
    if p.tns_end_percent != 100:
        stage_overrides["TNS_END_PERCENT"]          = str(p.tns_end_percent)
    if p.min_routing_layer:
        stage_overrides["MIN_ROUTING_LAYER"]        = p.min_routing_layer
    if p.max_routing_layer:
        stage_overrides["MAX_ROUTING_LAYER"]        = p.max_routing_layer

    env = build_env(platform_dir, design_cfg, stage_overrides,
                    input.rundir, scripts_dir)

    # Symlink all upstream results files into this stage's RESULTS_DIR
    upstream_results = get_upstream_results(input)
    if upstream_results:
        import glob as _glob
        for f in _glob.glob(os.path.join(upstream_results, "*")):
            stage_link_inputs(env, f)

    logname = "5_1_grt.log"
    status = await run_openroad(
        ctxt, env,
        os.path.join(scripts_dir, "global_route.tcl"),
        "5_1_grt", logname,
    )
    markers = parse_log(os.path.join(input.rundir, "logs", logname))

    output = [emit_odb_fileset(input.rundir, "5_1_grt.odb", input.name)]
    return TaskDataResult(status=status, output=output,
                          changed=(status == 0), markers=markers)
