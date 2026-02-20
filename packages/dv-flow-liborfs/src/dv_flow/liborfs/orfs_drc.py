"""
orfs.DRC — Design Rule Check via KLayout.
"""
import os
from dv_flow.mgr import TaskDataResult
from .orfs_util import (
    get_scripts_dir, get_platform_dir, extract_design_config,
    build_env,
)
from .orfs_log_parser import parse_log


async def DRC(ctxt, input) -> TaskDataResult:
    p = input.params
    scripts_dir  = get_scripts_dir(p.flow_home)
    platform_dir = get_platform_dir(input)
    design_cfg   = extract_design_config(input)

    # Get GDS path from orfsGDS FileSet
    gds_file = None
    for item in input.inputs:
        if getattr(item, 'type', None) == "std.FileSet" and \
                getattr(item, 'filetype', None) == "orfsGDS":
            if item.files:
                gds_file = os.path.join(item.basedir, item.files[0])

    stage_overrides = {}
    if gds_file:
        stage_overrides["GDS_FILE"] = gds_file
    if p.drc_rules_file:
        stage_overrides["DRC_RULES_FILE"] = p.drc_rules_file

    env = build_env(platform_dir, design_cfg, stage_overrides,
                    input.rundir, scripts_dir)

    logname = "6_drc.log"
    # KLayout DRC uses the platform's drc/<rules>.lydrc script
    drc_script = os.path.join(scripts_dir, "klayout", "drc",
                               env.get("DRC_RULES_FILE", ""))
    if not os.path.isfile(drc_script):
        # Fall back to platform DRC directory
        drc_script = os.path.join(platform_dir, "drc",
                                   os.listdir(os.path.join(platform_dir, "drc"))[0]
                                   if os.path.isdir(os.path.join(platform_dir, "drc")) else "")

    status = await ctxt.exec(
        [env.get("KLAYOUT_EXE", "klayout"), "-b",
         "-r", drc_script,
         "-rd", f"input={gds_file or ''}",
         "-rd", f"report={os.path.join(input.rundir, 'reports', 'drc.xml')}"],
        logfile=logname, env=env,
    )
    markers = parse_log(os.path.join(input.rundir, "logs", logname))

    return TaskDataResult(status=status, output=[], markers=markers)
