# Log Analysis with std.Agent

This example runs the full GCD RTL-to-GDS flow and then uses `std.Agent` to
read the OpenROAD metrics JSON and produce a human-readable summary report.

## What is std.Agent?

`std.Agent` is a DV-Flow standard-library task that invokes an AI coding
assistant (GitHub Copilot CLI or OpenAI Codex CLI) inside the DFM run
environment.  The agent receives your `user_prompt` plus all upstream FileSets
as context and can read files, write files, and return new FileSets as outputs.

## Prerequisites

* `dv-flow-liborfs` and `dv-flow-liborfs-nangate45` installed
* OpenROAD binary accessible (set `OPENROAD_EXE`)
* Yosys binary accessible (set `YOSYS_EXE`)
* GitHub Copilot CLI **or** OpenAI Codex CLI authenticated in your shell
  * Copilot CLI: `gh auth login` then `gh extension install github/gh-copilot`
  * Codex CLI: `export OPENAI_API_KEY=...`

## How to Run

```bash
cd examples/log_analysis

# Run the full flow and then the AI log-analysis step
OPENROAD_EXE=/path/to/openroad YOSYS_EXE=/path/to/yosys dfm run analyze
```

The agent will write a `flow_summary.txt` file to the `analyze` task run
directory and print a concise summary of timing, power, area, and DRC results.
