"""
orfs.GDS — GDS streaming via KLayout.
"""
import os
from dv_flow.mgr import FileSet, TaskDataResult
from .orfs_util import (
    get_scripts_dir, get_platform_dir, extract_design_config, get_odb_path,
    build_env,
)
from .orfs_log_parser import parse_log


async def GDS(ctxt, input) -> TaskDataResult:
    p = input.params
    scripts_dir  = get_scripts_dir(p.flow_home)
    platform_dir = get_platform_dir(input)
    design_cfg   = extract_design_config(input)
    input_odb    = get_odb_path(input)

    stage_overrides = {"INPUT_ODB": input_odb}
    if p.klayout_tech_file:
        stage_overrides["KLAYOUT_TECH_FILE"] = p.klayout_tech_file

    env = build_env(platform_dir, design_cfg, stage_overrides,
                    input.rundir, scripts_dir)

    logname = "6_gds.log"
    klayout_script = os.path.join(scripts_dir, "klayout.sh")
    status = await ctxt.exec(
        [env.get("KLAYOUT_EXE", "klayout"), "-zz",
         "-r", os.path.join(scripts_dir, "klayout.tcl")],
        logfile=logname, env=env,
    )
    markers = parse_log(os.path.join(input.rundir, "logs", logname))

    design_name = design_cfg.design_name
    gds_file = f"{design_name}.gds"
    output = [FileSet(
        src=input.name,
        filetype="orfsGDS",
        basedir=os.path.join(input.rundir, "results"),
        files=[gds_file],
    )]
    return TaskDataResult(status=status, output=output,
                          changed=(status == 0), markers=markers)
