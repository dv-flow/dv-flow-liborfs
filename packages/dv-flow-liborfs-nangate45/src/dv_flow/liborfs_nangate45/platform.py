import os
from dv_flow.mgr import FileSet, TaskDataResult


async def Platform(ctxt, input) -> TaskDataResult:
    platform_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "share", "nangate45"
    )
    if not os.path.isdir(platform_dir):
        ctxt.error(
            f"nangate45 platform directory not found at {platform_dir}. "
            "Re-install dv-flow-liborfs-nangate45 from source with the "
            "OpenROAD-flow-scripts submodule checked out."
        )
        return TaskDataResult(status=1, output=[], markers=[])

    fs = FileSet(
        src=input.name,
        filetype="orfsOpenRoadPlatform",
        basedir=platform_dir,
        files=[],
    )
    return TaskDataResult(output=[fs], status=0, changed=False)
