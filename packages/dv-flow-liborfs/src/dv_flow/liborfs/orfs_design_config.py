"""
orfs.DesignConfig task implementation.

Consumes verilogSource / systemVerilogSource / sdc FileSets.
Resolves file paths and emits an orfs.DesignConfig DataItem carrying
design_name, clock_period, resolved verilog_files, sdc_file, etc.
"""
import os
from dv_flow.mgr import TaskDataResult


async def DesignConfig(ctxt, input) -> TaskDataResult:
    p = input.params

    # Resolve verilog files and SDC from consumed FileSets
    verilog_files = []
    sdc_file = ""
    for item in input.inputs:
        if getattr(item, 'type', None) == "std.FileSet":
            ft = getattr(item, 'filetype', None)
            if ft in ("verilogSource", "systemVerilogSource"):
                for fn in (item.files or []):
                    verilog_files.append(os.path.join(item.basedir, fn))
            elif ft == "sdc" and item.files:
                sdc_file = os.path.join(item.basedir, item.files[0])

    di = ctxt.mkDataItem(
        "orfs.DesignConfig",
        design_name        = p.design_name,
        design_nickname    = p.design_nickname or p.design_name,
        clock_period_ps    = int(p.clock_period_ps),
        blocks             = list(p.blocks or []),
        verilog_defines    = list(p.verilog_defines or []),
        synth_hierarchical = bool(p.synth_hierarchical),
        num_cores          = int(p.num_cores),
        verilog_files      = verilog_files,
        sdc_file           = sdc_file,
    )

    return TaskDataResult(output=[di], status=0, changed=True)
