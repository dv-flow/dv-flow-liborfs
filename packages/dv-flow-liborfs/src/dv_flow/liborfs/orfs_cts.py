"""
orfs.CTS — Clock tree synthesis (1 substep).

4_1: cts.tcl → 4_1_cts.odb + 4_cts.sdc (copied → 4_cts.odb)
"""
import os
import shutil
from dv_flow.mgr import TaskDataResult
from .orfs_util import (
    get_scripts_dir, get_platform_dir, extract_design_config, get_odb_path,
    build_env, run_openroad, emit_odb_fileset, stage_link_inputs, get_upstream_results,
)
from .orfs_log_parser import parse_log


async def CTS(ctxt, input) -> TaskDataResult:
    p = input.params
    scripts_dir  = get_scripts_dir(p.flow_home)
    platform_dir = get_platform_dir(input)
    design_cfg   = extract_design_config(input)
    input_odb    = get_odb_path(input)

    stage_overrides = {"INPUT_ODB": input_odb}
    if p.cts_cluster_size:
        stage_overrides["CTS_CLUSTER_SIZE"]     = str(p.cts_cluster_size)
    if p.cts_cluster_diameter:
        stage_overrides["CTS_CLUSTER_DIAMETER"] = str(p.cts_cluster_diameter)
    if p.cts_buf_distance:
        stage_overrides["CTS_BUF_DISTANCE"]     = str(p.cts_buf_distance)
    if p.cts_args:
        stage_overrides["CTS_ARGS"]             = p.cts_args

    env = build_env(platform_dir, design_cfg, stage_overrides,
                    input.rundir, scripts_dir)

    # Symlink all upstream results files into this stage's RESULTS_DIR
    upstream_results = get_upstream_results(input)
    if upstream_results:
        import glob as _glob
        for f in _glob.glob(os.path.join(upstream_results, "*")):
            stage_link_inputs(env, f)

    logname = "4_1_cts.log"
    status = await run_openroad(
        ctxt, env,
        os.path.join(scripts_dir, "cts.tcl"),
        "4_1_cts", logname,
    )
    markers = parse_log(os.path.join(input.rundir, "logs", logname))
    if status:
        return TaskDataResult(status=status, output=[], markers=markers)

    results_dir = env["RESULTS_DIR"]
    src_odb = os.path.join(results_dir, "4_1_cts.odb")
    dst_odb = os.path.join(results_dir, "4_cts.odb")
    if os.path.isfile(src_odb):
        shutil.copy2(src_odb, dst_odb)

    output = [emit_odb_fileset(input.rundir, "4_cts.odb", input.name)]
    return TaskDataResult(status=0, output=output, changed=True, markers=markers)
