"""
orfs.Synth — RTL synthesis (3 substeps).

Substep 1: yosys -c synth_canonicalize.tcl  → 1_1_yosys_canonicalize.rtlil
Substep 2: yosys -c synth.tcl              → 1_2_yosys.v  +  1_2_yosys.sdc
Substep 3: openroad synth_odb.tcl          → 1_synth.odb  +  1_synth.sdc
"""
import os
from dv_flow.mgr import TaskDataResult
from .orfs_util import (
    get_scripts_dir, get_platform_dir, extract_design_config,
    build_env, run_openroad, run_yosys, emit_odb_fileset,
)
from .orfs_log_parser import parse_log


async def Synth(ctxt, input) -> TaskDataResult:
    p = input.params
    scripts_dir  = get_scripts_dir(p.flow_home)
    platform_dir = get_platform_dir(input)
    design_cfg   = extract_design_config(input)

    stage_overrides = {}
    if p.synth_args:
        stage_overrides["SYNTH_ARGS"] = p.synth_args
    if p.synth_gut:
        stage_overrides["SYNTH_GUT"] = "1"
    if p.synth_memory_max_bits and p.synth_memory_max_bits != 4096:
        stage_overrides["SYNTH_MEMORY_MAX_BITS"] = str(p.synth_memory_max_bits)

    env = build_env(platform_dir, design_cfg, stage_overrides,
                    input.rundir, scripts_dir)

    markers = []

    # Substep 1: canonicalize
    log1 = "1_1_synth_canonicalize.log"
    status = await run_yosys(ctxt, env,
                             os.path.join(scripts_dir, "synth_canonicalize.tcl"),
                             log1)
    markers.extend(parse_log(os.path.join(input.rundir, "logs", log1)))
    if status:
        return TaskDataResult(status=status, output=[], markers=markers)

    # Substep 2: synthesis
    log2 = "1_2_synth.log"
    status = await run_yosys(ctxt, env,
                             os.path.join(scripts_dir, "synth.tcl"),
                             log2)
    markers.extend(parse_log(os.path.join(input.rundir, "logs", log2)))
    if status:
        return TaskDataResult(status=status, output=[], markers=markers)

    # Substep 3: convert to ODB
    # synth_odb.tcl expects 1_2_yosys.sdc in RESULTS_DIR (same as SDC_FILE)
    import shutil
    results_dir = env["RESULTS_DIR"]
    sdc_src = os.path.join(results_dir, "1_synth.sdc")
    sdc_dst = os.path.join(results_dir, "1_2_yosys.sdc")
    if os.path.isfile(sdc_src) and not os.path.isfile(sdc_dst):
        shutil.copy2(sdc_src, sdc_dst)
    elif design_cfg.sdc_file and not os.path.isfile(sdc_dst):
        shutil.copy2(design_cfg.sdc_file, sdc_dst)
    # synth_odb.tcl will overwrite 1_synth.sdc — ensure it's writable
    if os.path.isfile(sdc_src):
        os.chmod(sdc_src, 0o644)
    if os.path.isfile(sdc_dst):
        os.chmod(sdc_dst, 0o644)
    log3 = "1_3_synth_odb.log"
    status = await run_openroad(ctxt, env,
                                os.path.join(scripts_dir, "synth_odb.tcl"),
                                "1_3_synth_odb", log3)
    markers.extend(parse_log(os.path.join(input.rundir, "logs", log3)))

    output = [emit_odb_fileset(input.rundir, "1_synth.odb", input.name)]
    return TaskDataResult(status=status, output=output,
                          changed=(status == 0), markers=markers)
