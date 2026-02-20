# Task Reference

This page describes every task provided by the `orfs` DV-Flow package.

---

## Task: DesignConfig

`orfs.DesignConfig` collects RTL (Verilog/SystemVerilog) and SDC FileSets from
upstream tasks, resolves their absolute paths, and emits an `orfs.DesignConfig`
DataItem consumed by all downstream stage tasks.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `design_name` | str | `""` | Top-level design name (`DESIGN_NAME`) |
| `design_nickname` | str | `""` | Short nickname for result directories (defaults to `design_name`) |
| `clock_period_ps` | int | `0` | Clock period in picoseconds (`ABC_CLOCK_PERIOD_IN_PS`) |
| `blocks` | list | `[]` | Hierarchical sub-block names (`BLOCKS`) |
| `verilog_defines` | list | `[]` | Preprocessor defines (`VERILOG_DEFINES`) |
| `synth_hierarchical` | bool | `false` | Enable hierarchical synthesis (`SYNTH_HIERARCHICAL`) |
| `num_cores` | int | `0` | CPU cores for parallel steps; 0 = autodetect (`NUM_CORES`) |

### Consumes

* `verilogSource` FileSet
* `systemVerilogSource` FileSet
* `sdc` FileSet

### Produces

* `orfs.DesignConfig` DataItem (plus pass-through of all input FileSets)

### Example

```yaml
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
    design_name: gcd
    clock_period_ps: 1100
```

---

## Task: Synth

`orfs.Synth` runs RTL synthesis through three Yosys/OpenROAD sub-steps:

1. `synth_canonicalize.tcl` → `1_1_yosys_canonicalize.rtlil`
2. `synth.tcl` → `1_2_yosys.v` + `1_2_yosys.sdc`
3. `synth_odb.tcl` → `1_synth.odb` + `1_synth.sdc`

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `flow_home` | str | `""` | Path to ORFS scripts dir; empty = use bundled or `ORFS_FLOW_HOME` |
| `synth_args` | str | `""` | Extra Yosys synthesis arguments (`SYNTH_ARGS`) |
| `synth_gut` | bool | `false` | Replace all cell internals with wires (`SYNTH_GUT`) |
| `synth_memory_max_bits` | int | `4096` | Max bits for memory synthesis (`SYNTH_MEMORY_MAX_BITS`) |

### Consumes

* `orfsOpenRoadPlatform` FileSet (from platform task)
* `orfs.DesignConfig` DataItem

### Produces

* `orfsODB` FileSet pointing to `results/1_synth.odb`

### Example

```yaml
- name: synth
  uses: orfs.Synth
  needs: [pdk, design]
  with:
    synth_args: "-flatten"
```

---

## Task: Floorplan

`orfs.Floorplan` executes four sub-steps: floorplan init, macro placement,
tap cell insertion, and power distribution network (PDN) generation.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `flow_home` | str | `""` | Path to ORFS scripts dir |
| `core_utilization` | int | `0` | Target core utilization 0–100 (`CORE_UTILIZATION`); 0 = platform default |
| `core_aspect_ratio` | str | `""` | Core height/width ratio (`CORE_ASPECT_RATIO`) |
| `core_margin` | str | `""` | Core margin in microns (`CORE_MARGIN`) |
| `die_area` | str | `""` | Explicit die area `"x0 y0 x1 y1"` in μm (`DIE_AREA`) |
| `core_area` | str | `""` | Explicit core area `"x0 y0 x1 y1"` in μm (`CORE_AREA`) |
| `pdn_tcl` | str | `""` | Override PDN TCL script; empty = platform default |

### Example

```yaml
- name: floorplan
  uses: orfs.Floorplan
  needs: [pdk, design, synth]
  with:
    core_utilization: 45
```

---

## Task: Place

`orfs.Place` runs five placement sub-steps: global place (skip IO), IO pin
placement, refined global placement, timing-driven resizing, and detailed
(legalized) placement.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `flow_home` | str | `""` | Path to ORFS scripts dir |
| `place_density` | str | `""` | Placement density 0–1 (`PLACE_DENSITY`); empty = platform default |
| `place_density_lb_addon` | str | `""` | Placement density lower-bound add-on |
| `global_placement_args` | str | `""` | Extra global placement arguments |

### Example

```yaml
- name: place
  uses: orfs.Place
  needs: [pdk, design, floorplan]
  with:
    place_density: "0.60"
```

---

## Task: CTS

`orfs.CTS` inserts and optimizes the clock tree.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `flow_home` | str | `""` | Path to ORFS scripts dir |
| `cts_cluster_size` | int | `0` | CTS cluster size; 0 = platform default |
| `cts_cluster_diameter` | int | `0` | CTS cluster diameter |
| `cts_buf_distance` | int | `0` | Buffer insertion distance |
| `cts_args` | str | `""` | Additional CTS arguments |

### Example

```yaml
- name: cts
  uses: orfs.CTS
  needs: [pdk, design, place]
```

---

## Task: GlobalRoute

`orfs.GlobalRoute` performs global routing with congestion analysis.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `flow_home` | str | `""` | Path to ORFS scripts dir |
| `routing_layer_adjustment` | str | `""` | Layer capacity adjustment 0–1 |
| `tns_end_percent` | int | `100` | Percentage of violating endpoints to fix |
| `min_routing_layer` | str | `""` | Minimum routing layer name |
| `max_routing_layer` | str | `""` | Maximum routing layer name |

### Example

```yaml
- name: grt
  uses: orfs.GlobalRoute
  needs: [pdk, design, cts]
  with:
    tns_end_percent: 100
```

---

## Task: Route

`orfs.Route` runs detailed routing (TritonRoute) followed by filler cell insertion.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `flow_home` | str | `""` | Path to ORFS scripts dir |
| `detailed_route_args` | str | `""` | Extra TritonRoute arguments |

### Example

```yaml
- name: route
  uses: orfs.Route
  needs: [pdk, design, grt]
```

---

## Task: Finish

`orfs.Finish` inserts metal density fill, runs the final timing/power/area
report, and writes metrics to `logs/6_report.json`.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `flow_home` | str | `""` | Path to ORFS scripts dir |

### Produces

* `orfsODB` FileSet pointing to `results/6_1_fill.odb`
* `orfsMetrics` FileSet pointing to `logs/6_report.json`

### Example

```yaml
- name: finish
  uses: orfs.Finish
  needs: [pdk, design, route]
```

---

## Task: MetricsCheck

`orfs.MetricsCheck` reads the `orfsMetrics` JSON file produced by `orfs.Finish`
and asserts configurable pass/fail thresholds.  It emits error markers for any
threshold violation so `dfm run` returns a non-zero exit code.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `wns_threshold` | str | `"0.0"` | WNS must be ≥ this value (ns); `0.0` requires timing closure |
| `max_drc` | int | `0` | Maximum allowed DRC violations; `0` requires clean DRC |
| `max_area_um2` | str | `"0.0"` | Maximum die area in μm²; `0.0` = no check |

### Consumes

* `orfsMetrics` FileSet

### Example

```yaml
- name: check
  uses: orfs.MetricsCheck
  needs: [finish]
  with:
    wns_threshold: 0.0
    max_drc: 0
```

---

## Task: GDS

`orfs.GDS` streams out a GDS file from the final ODB using KLayout.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `flow_home` | str | `""` | Path to ORFS scripts dir |
| `klayout_tech_file` | str | `""` | Override KLayout tech file; empty = platform default |

---

## Task: DRC

`orfs.DRC` runs a Design Rule Check on the GDS output using KLayout.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `flow_home` | str | `""` | Path to ORFS scripts dir |
| `drc_rules_file` | str | `""` | Override DRC rules file; empty = platform default |
