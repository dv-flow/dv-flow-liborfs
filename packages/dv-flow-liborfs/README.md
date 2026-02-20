# dv-flow-liborfs

DV Flow task library that wraps each stage of the [OpenROAD](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts) RTL-to-GDSII flow as cacheable, composable DFM (DV Flow Manager) tasks.

Each stage — synthesis, floorplan, placement, CTS, routing, and sign-off — is a separate task node. DFM caches task outputs by input hash, so only changed stages re-run.

---

## Prerequisites

| Tool | Environment variable |
|------|---------------------|
| [OpenROAD](https://openroad.readthedocs.io) binary | `OPENROAD_EXE` |
| [Yosys](https://yosyshq.net/yosys/) binary | `YOSYS_EXE` |
| Platform/PDK package | _(installed via pip, see below)_ |

---

## Installation

```bash
pip install dv-flow-liborfs dv-flow-liborfs-nangate45
```

Replace `dv-flow-liborfs-nangate45` with the platform package for your target PDK (see [Platform Packages](#platform-packages) below).

---

## Quick-start Example

```yaml
# yaml-language-server: $schema=https://dv-flow.github.io/flow.dv.schema.json
package:
  name: my_design

  imports:
  - name: orfs
  - name: orfs.nangate45       # platform-specific PDK package

  tasks:
  - name: pdk
    uses: orfs.nangate45.Platform

  - name: rtl
    uses: std.FileSet
    with:
      type: verilogSource
      include: "src/*.v"

  - name: sdc
    uses: std.FileSet
    with:
      type: sdc
      include: "src/constraints.sdc"

  - name: design
    uses: orfs.DesignConfig
    needs: [rtl, sdc]
    with:
      design_name: my_design
      clock_period_ps: 1000

  - name: synth
    uses: orfs.Synth
    needs: [pdk, design]

  - name: floorplan
    uses: orfs.Floorplan
    needs: [pdk, design, synth]
    with:
      core_utilization: 45

  - name: place
    uses: orfs.Place
    needs: [pdk, design, floorplan]

  - name: cts
    uses: orfs.CTS
    needs: [pdk, design, place]

  - name: grt
    uses: orfs.GlobalRoute
    needs: [pdk, design, cts]

  - name: route
    uses: orfs.Route
    needs: [pdk, design, grt]

  - name: finish
    uses: orfs.Finish
    needs: [pdk, design, route]
```

Run to the finish stage:

```bash
OPENROAD_EXE=/path/to/openroad YOSYS_EXE=/path/to/yosys dfm run finish
```

---

## Task Reference

| Name | Description | Key Parameters |
|------|-------------|----------------|
| `orfs.DesignConfig` | Declares design identity; collects RTL/SDC FileSets and resolves absolute paths | `design_name`, `clock_period_ps`, `verilog_defines`, `synth_hierarchical`, `num_cores` |
| `orfs.Synth` | RTL synthesis (Yosys 3-step: canonicalize → synth → synth_odb) | `flow_home`, `synth_args`, `synth_gut`, `synth_memory_max_bits` |
| `orfs.Floorplan` | Floorplan init, macro place, tapcell, PDN (4 substeps) | `core_utilization`, `core_aspect_ratio`, `core_margin`, `die_area`, `core_area`, `pdn_tcl` |
| `orfs.Place` | Global and detailed placement, timing-driven resizing (5 substeps) | `place_density`, `place_density_lb_addon`, `global_placement_args` |
| `orfs.CTS` | Clock tree synthesis | `cts_cluster_size`, `cts_cluster_diameter`, `cts_buf_distance`, `cts_args` |
| `orfs.GlobalRoute` | Global routing with congestion analysis | `routing_layer_adjustment`, `tns_end_percent`, `min_routing_layer`, `max_routing_layer` |
| `orfs.Route` | Detailed routing (TritonRoute) + filler cell insertion | `detailed_route_args` |
| `orfs.Finish` | Density fill, final timing/power report, JSON metrics | `flow_home` |
| `orfs.MetricsCheck` | Assert pass/fail thresholds against `6_report.json` metrics | `wns_threshold`, `max_drc`, `max_area_um2` |
| `orfs.GDS` | GDS streaming via KLayout | `klayout_tech_file` |
| `orfs.DRC` | Design Rule Check via KLayout | `drc_rules_file` |

---

## How Caching Works

DFM computes a content hash over each task's parameters and all upstream outputs. If a task's hash matches a previously completed run, DFM skips re-execution and replays the cached outputs. Changing a parameter (e.g., `core_utilization`) invalidates only that stage and all downstream stages — synthesis is not re-run.

---

## Platform Packages

Technology-specific files (LEF/LIB/RC tables, PDN config, etc.) are shipped in separate packages so the core library stays PDK-neutral.

| Package | PDK |
|---------|-----|
| `dv-flow-liborfs-nangate45` | NanGate 45 nm open PDK |

A platform package registers the `orfs.<pdk>.Platform` task that emits an `orfsOpenRoadPlatform` FileSet consumed by every stage task.

---

## Running the GCD Example

```bash
cd examples/gcd_nangate45
OPENROAD_EXE=/path/to/openroad YOSYS_EXE=/path/to/yosys dfm run finish
```

See [examples/gcd_nangate45/README.md](examples/gcd_nangate45/README.md) for details.
