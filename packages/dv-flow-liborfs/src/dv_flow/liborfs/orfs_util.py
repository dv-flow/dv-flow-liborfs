"""
orfs_util.py — Core utilities for dv-flow-liborfs task implementations.

Public API:
  get_scripts_dir(flow_home)       → str
  get_platform_dir(input)          → str
  extract_design_config(input)     → DesignConfigData
  get_odb_path(input)              → str
  parse_platform_config(pdir)      → dict
  load_defaults(scripts_dir)       → dict
  build_env(...)                   → dict
  run_openroad(ctxt, env, tcl, stage_id, logname) → int
  run_yosys(ctxt, env, tcl, logname)              → int
  emit_odb_fileset(rundir, odb_name, src_name)    → FileSet
"""
import dataclasses as dc
import glob as _glob
import logging
import os
import re
import yaml
from typing import Dict, List

from dv_flow.mgr import FileSet

_log = logging.getLogger("orfs_util")

# ── Script directory resolution ──────────────────────────────────────────────

def get_scripts_dir(flow_home: str = "") -> str:
    """Return path to the ORFS scripts directory.

    Priority:
      1. flow_home parameter (explicit override)
      2. ORFS_FLOW_HOME environment variable
      3. Bundled share/scripts/ installed with the package
    """
    if flow_home:
        return flow_home
    env_home = os.environ.get("ORFS_FLOW_HOME", "")
    if env_home:
        return env_home
    bundled = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "share", "scripts")
    if os.path.isdir(bundled):
        return bundled
    raise RuntimeError(
        "ORFS scripts not found. Set ORFS_FLOW_HOME env var or install "
        "dv-flow-liborfs from source with the OpenROAD-flow-scripts submodule."
    )

# ── Input extraction helpers ──────────────────────────────────────────────────

def get_platform_dir(input) -> str:
    """Extract basedir from the orfsOpenRoadPlatform FileSet in input.inputs."""
    for item in input.inputs:
        if getattr(item, 'type', None) == "std.FileSet" and \
                getattr(item, 'filetype', None) == "orfsOpenRoadPlatform":
            return item.basedir
    raise ValueError(
        "No orfsOpenRoadPlatform FileSet in task inputs. "
        "Add 'needs: [pdk]' with an orfs.<platform>.Platform task."
    )


def get_odb_path(input) -> str:
    """Extract the .odb file path from the orfsODB FileSet in input.inputs."""
    for item in input.inputs:
        if getattr(item, 'type', None) == "std.FileSet" and \
                getattr(item, 'filetype', None) == "orfsODB":
            if item.files:
                return os.path.join(item.basedir, item.files[0])
            raise ValueError("orfsODB FileSet is empty.")
    raise ValueError(
        "No orfsODB FileSet in task inputs. "
        "Add the upstream stage task to 'needs:'."
    )

# ── Design config extraction ──────────────────────────────────────────────────

@dc.dataclass
class DesignConfigData:
    """Structured design configuration resolved from input DataItems/FileSets."""
    design_name: str = ""
    design_nickname: str = ""
    clock_period_ps: int = 0
    verilog_files: List[str] = dc.field(default_factory=list)
    sdc_file: str = ""
    blocks: List[str] = dc.field(default_factory=list)
    verilog_defines: List[str] = dc.field(default_factory=list)
    synth_hierarchical: bool = False
    num_cores: int = 0


def extract_design_config(input) -> DesignConfigData:
    """Build a DesignConfigData from the consumed orfs.DesignConfig DataItem.

    File paths (verilog_files, sdc_file) are resolved by the DesignConfig
    task and stored in the DataItem, so we just read them here.
    """
    cfg = DesignConfigData()
    for item in input.inputs:
        if getattr(item, 'type', None) == "orfs.DesignConfig":
            cfg.design_name        = item.design_name
            cfg.design_nickname    = item.design_nickname or item.design_name
            cfg.clock_period_ps    = int(item.clock_period_ps)
            cfg.blocks             = list(item.blocks or [])
            cfg.verilog_defines    = list(item.verilog_defines or [])
            cfg.synth_hierarchical = bool(item.synth_hierarchical)
            cfg.num_cores          = int(item.num_cores)
            cfg.verilog_files      = list(item.verilog_files or [])
            cfg.sdc_file           = item.sdc_file or ""
            break
    return cfg

# ── Platform config.mk parser ─────────────────────────────────────────────────

def parse_platform_config(platform_dir: str) -> Dict[str, str]:
    """Parse <platform_dir>/config.mk and resolve values relative to platform_dir.

    Handles patterns used by all ORFS platform config.mk files:
      - VAR = value / VAR := value / VAR ?= value
      - $(PLATFORM_DIR)/path  substitution
      - $(sort $(wildcard ...)) and $(wildcard ...)  glob expansion
      - Multi-line values joined with backslash continuation
      - Unknown $(VAR) references are replaced with empty string
    """
    config_mk = os.path.join(platform_dir, "config.mk")
    if not os.path.isfile(config_mk):
        _log.warning("config.mk not found at %s — platform vars will be absent", config_mk)
        return {}

    result: Dict[str, str] = {"PLATFORM_DIR": platform_dir}

    def _resolve(val: str) -> str:
        val = val.replace("$(PLATFORM_DIR)", platform_dir)

        def _expand_wildcard(m):
            pattern = m.group(1).replace("$(PLATFORM_DIR)", platform_dir)
            return " ".join(sorted(_glob.glob(pattern)))

        val = re.sub(r'\$\(sort\s+\$\(wildcard\s+([^)]+)\)\)', _expand_wildcard, val)
        val = re.sub(r'\$\(wildcard\s+([^)]+)\)', _expand_wildcard, val)

        def _replace_var(m):
            return result.get(m.group(1), "")

        val = re.sub(r'\$\(([^)]+)\)', _replace_var, val)
        return val.strip()

    with open(config_mk) as f:
        raw = f.read()

    raw = re.sub(r'\\\n\s*', ' ', raw)   # join continuation lines

    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        m = re.match(r'^(?:export\s+)?([A-Z_][A-Z0-9_]*)\s*(?:\?=|:=|=)\s*(.*)', line)
        if m:
            var, val = m.group(1), m.group(2).strip()
            result[var] = _resolve(val)

    return result

# ── Default variable loader ────────────────────────────────────────────────────

def load_defaults(scripts_dir: str) -> Dict[str, str]:
    """Load ORFS variable defaults from variables.yaml.

    Returns a dict of {VAR_NAME: str(default)} for all vars that have a
    non-None, non-empty default.
    """
    yaml_path = os.path.join(scripts_dir, "variables.yaml")
    if not os.path.isfile(yaml_path):
        _log.warning("variables.yaml not found at %s", yaml_path)
        return {}
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    defaults: Dict[str, str] = {}
    for var_name, info in data.items():
        if isinstance(info, dict) and "default" in info:
            val = info["default"]
            if val is not None and str(val).strip():
                defaults[var_name] = str(val)
    return defaults

# ── Environment construction ───────────────────────────────────────────────────

def build_env(
    platform_dir: str,
    design_cfg: DesignConfigData,
    stage_overrides: Dict[str, str],
    rundir: str,
    scripts_dir: str,
    *,
    results_subdir: str = "results",
    log_subdir: str = "logs",
    reports_subdir: str = "reports",
    objects_subdir: str = "objects",
) -> Dict[str, str]:
    """Construct the full ORFS environment dict for a stage task.

    Layer order (later wins):
      1. os.environ (tool PATH, etc.)
      2. variables.yaml defaults
      3. Platform config.mk resolved values
      4. Design-level params (DesignConfigData)
      5. Stage-specific overrides (from task with: params)
      6. Directory vars (RESULTS_DIR, LOG_DIR, REPORTS_DIR, OBJECTS_DIR)
      7. Tool paths (OPENROAD_EXE, YOSYS_EXE, KLAYOUT_EXE — only if not set)
    """
    env = dict(os.environ)

    env.update(load_defaults(scripts_dir))
    env.update(parse_platform_config(platform_dir))

    # Design-level
    if design_cfg.design_name:
        env["DESIGN_NAME"] = design_cfg.design_name
    if design_cfg.design_nickname:
        env["DESIGN_NICKNAME"] = design_cfg.design_nickname
    if design_cfg.clock_period_ps:
        env["ABC_CLOCK_PERIOD_IN_PS"] = str(design_cfg.clock_period_ps)
    if design_cfg.verilog_files:
        env["VERILOG_FILES"] = " ".join(design_cfg.verilog_files)
    if design_cfg.sdc_file:
        env["SDC_FILE"] = design_cfg.sdc_file
    if design_cfg.blocks:
        env["BLOCKS"] = " ".join(design_cfg.blocks)
    if design_cfg.verilog_defines:
        env["VERILOG_DEFINES"] = " ".join(design_cfg.verilog_defines)
    if design_cfg.synth_hierarchical:
        env["SYNTH_HIERARCHICAL"] = "1"
    if design_cfg.num_cores:
        env["NUM_CORES"] = str(design_cfg.num_cores)

    # Stage-specific overrides (skip zero/empty values that mean "use default")
    for k, v in stage_overrides.items():
        sv = str(v) if v is not None else ""
        if sv and sv != "0" and sv != "0.0":
            env[k] = sv

    # Directory vars
    env["RESULTS_DIR"] = os.path.join(rundir, results_subdir)
    env["LOG_DIR"]     = os.path.join(rundir, log_subdir)
    env["REPORTS_DIR"] = os.path.join(rundir, reports_subdir)
    env["OBJECTS_DIR"] = os.path.join(rundir, objects_subdir)
    env["SCRIPTS_DIR"] = scripts_dir
    # FLOW_HOME = parent of scripts_dir (contains platforms/common, util, etc.)
    env["FLOW_HOME"]   = os.path.dirname(scripts_dir)

    # Tool defaults
    env.setdefault("OPENROAD_EXE", "openroad")
    env.setdefault("YOSYS_EXE",    "yosys")
    env.setdefault("KLAYOUT_EXE",  "klayout")
    import sys
    env.setdefault("PYTHON_EXE", sys.executable)
    # Disable commercial-tool-dependent checks by default
    env.setdefault("LEC_CHECK", "0")
    env.setdefault("EQUIVALENCE_CHECK", "0")
    # Force-disable LEC/equivalence checks (require Kepler/JasperGold; not in open-source flow)
    env["LEC_CHECK"] = env.get("LEC_CHECK", "0")
    if env.get("LEC_CHECK") == "1" and not env.get("KEPLER_FORMAL_EXE", ""):
        env["LEC_CHECK"] = "0"
    if env.get("EQUIVALENCE_CHECK") == "1" and not env.get("JASPER_EXE", ""):
        env["EQUIVALENCE_CHECK"] = "0"
    # Force headless mode: suppress OpenROAD GUI (no Qt display needed for batch flow)
    env["DISPLAY"] = ""
    # Remove the incorrect offscreen hint we set previously
    env.pop("QT_QPA_PLATFORM", None)

    return env

# ── Stage handoff helpers ──────────────────────────────────────────────────────

def get_upstream_results(input) -> str:
    """Return the RESULTS_DIR of the upstream task (from the orfsODB FileSet basedir)."""
    for item in input.inputs:
        if getattr(item, 'type', None) == "std.FileSet" and \
                getattr(item, 'filetype', None) == "orfsODB":
            return item.basedir
    return ""


def stage_link_inputs(env: dict, *src_files: str) -> None:
    """Symlink upstream stage output files into the current stage's RESULTS_DIR.

    ORFS TCL scripts reference files by basename relative to RESULTS_DIR.
    Each DFM task has its own RESULTS_DIR, so we symlink upstream files in
    before running any script.  Using symlinks avoids copying large ODB files.

    Args:
        env:       environment dict with RESULTS_DIR set
        *src_files: absolute paths to files to link into RESULTS_DIR
    """
    results_dir = env["RESULTS_DIR"]
    os.makedirs(results_dir, exist_ok=True)
    for src in src_files:
        if src and os.path.isfile(src):
            dst = os.path.join(results_dir, os.path.basename(src))
            if not os.path.exists(dst):
                os.symlink(src, dst)


# ── Tool runner helpers ──────────────────────────────────────────────────────

async def run_openroad(ctxt, env: dict, tcl_script: str,
                       stage_id: str, logname: str) -> int:
    """Run openroad -no_splash <tcl_script> -metrics <log_dir>/<stage_id>.json"""
    for d in (env["LOG_DIR"], env["RESULTS_DIR"],
              env["REPORTS_DIR"], env["OBJECTS_DIR"]):
        os.makedirs(d, exist_ok=True)
    metrics_file = os.path.join(env["LOG_DIR"], f"{stage_id}.json")
    cmd = [
        env["OPENROAD_EXE"],
        "-no_splash",
        "-exit",
        tcl_script,
        "-metrics", metrics_file,
    ]
    return await ctxt.exec(cmd, logfile=logname, env=env)


async def run_yosys(ctxt, env: dict, tcl_script: str, logname: str) -> int:
    """Run yosys -c <tcl_script>"""
    for d in (env["LOG_DIR"], env["RESULTS_DIR"],
              env["REPORTS_DIR"], env["OBJECTS_DIR"]):
        os.makedirs(d, exist_ok=True)
    return await ctxt.exec([env["YOSYS_EXE"], "-c", tcl_script],
                           logfile=logname, env=env)

# ── Output helpers ─────────────────────────────────────────────────────────────

def emit_odb_fileset(rundir: str, odb_name: str, src_name: str) -> FileSet:
    """Create an orfsODB FileSet pointing to <rundir>/results/<odb_name>."""
    return FileSet(
        src=src_name,
        filetype="orfsODB",
        basedir=os.path.join(rundir, "results"),
        files=[odb_name],
    )
