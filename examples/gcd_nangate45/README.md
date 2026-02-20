# GCD NanGate45 Example

A complete RTL-to-GDS example for the GCD (Greatest Common Divisor) design
using the NanGate 45 nm open PDK.

## Prerequisites

* `dv-flow-liborfs` and `dv-flow-liborfs-nangate45` installed
* OpenROAD binary accessible (set `OPENROAD_EXE`)
* Yosys binary accessible (set `YOSYS_EXE`)

## How to Run

```bash
cd examples/gcd_nangate45

# Run the full RTL-to-GDS flow through the Finish stage
OPENROAD_EXE=/path/to/openroad YOSYS_EXE=/path/to/yosys dfm run finish

# Optionally run the metrics check as well
OPENROAD_EXE=/path/to/openroad YOSYS_EXE=/path/to/yosys dfm run check
```

## What Happens

1. **Synthesis** — Yosys synthesises `src/gcd.v` against the NanGate45 standard-cell library.
2. **Floorplan** — OpenROAD initialises the die/core area at 45 % utilisation.
3. **Place** — Global and detailed placement, plus timing-driven resizing.
4. **CTS** — Clock tree synthesis.
5. **Global Route** — FastRoute global routing.
6. **Route** — TritonRoute detailed routing + filler cells.
7. **Finish** — Metal density fill, final timing/power/area report (`6_report.json`).

Results land in `rundir/` (created in the current directory by `dfm`).
