# FLEUR Workflow MCP Server

This repository is an MCP server for generating runnable `aiida-fleur` Python
scripts for the main FLEUR workflows.

## Supported Workflows

- `scf`
- `eos`
- `relax`
- `band`
- `dos`
- `mae`
- `ssdisp`
- `dmi`
- `corehole`
- `init_cls`
- `create_magnetic`

The generated scripts are meant to be practical starting points for:

- self-consistent calculations
- DOS and band structure calculations
- structure relaxations and EOS scans
- magnetic anisotropy and spin-spiral studies
- DMI workflows
- magnetic film setup
- quick plotting with `plot_fleur`
- AiiDA supercomputer and code setup guides

## Main MCP Tools

### `list_fleur_workflows`

Lists the supported workflows, their `WorkflowFactory(...)` entry points, and
the corresponding official documentation pages.

### `generate_fleur_workflow_script`

Creates a runnable Python script for a selected `aiida-fleur` workflow.

Useful inputs include:

- `workflow`
- `material`
- `structure_file`
- `inpgen_code`
- `fleur_code`
- `workflow_parameters`
- `calc_parameters`
- `scf_workflow_parameters`
- `magnetism`
- `plot_results`

### `generate_fleur_plot_script`

Creates a small plotting script that calls `plot_fleur` on one or more node
PKs or UUIDs.

### `execute_fleur_workflow_script`

Runs a generated workflow script with:

```bash
verdi run <script_path>
```

### `list_aiida_processes`

Lists recent AiiDA processes.

### `check_aiida_process`

Shows the status and report of a selected AiiDA process.

### `inspect_aiida_outputs`

Loads a selected AiiDA process and summarizes its outputs, output nodes, and
basic workflow result information.

### `generate_aiida_setup_guide`

Creates a Markdown setup procedure for:

- `verdi computer setup`
- `verdi computer configure`
- `verdi computer test`
- `verdi code create` for `inpgen`
- `verdi code create` for `fleur`

Useful inputs include:

- `system_preset` such as `jureca`, `juwels-cluster`, `juwels-booster`, or `jupiter`
- `computer_label`
- `hostname`
- `scheduler`
- `work_dir`
- `mpirun_command`
- `prepend_text`
- `inpgen_executable_path`
- `fleur_executable_path`

If required setup fields are missing, the server now reports which ones are
still needed.

### `setup_aiida_computer_and_codes`

Creates the AiiDA computer and registers the `inpgen` and `fleur` codes with
the local `verdi` command.

Behavior:

- if required fields are missing, the tool asks for them
- if `apply=false`, it returns a preview and setup guide
- if `apply=true`, it runs the setup locally

Important inputs:

- `system_preset`
- `computer_label`
- `hostname`
- `ssh_username` for SSH-based machines
- `inpgen_executable_path`
- `fleur_executable_path`
- `verdi_command`
- `apply`
- `replace_existing`

## Requirements

- Python 3.10+
- `mcp`
- `aiida-core`
- `aiida-fleur`
- `ase`
- configured AiiDA profile
- configured `inpgen` and `fleur` code nodes

## Run

```bash
python3 -m pip install mcp
python3 /absolute/path/to/server.py
```

## Notes

- The server now focuses on generating workflow scripts, not raw `inp.xml`
  files.
- It can also generate an AiiDA setup guide for a remote supercomputer and the
  `inpgen`/`fleur` codes you want to register there.
- Magnetic setup is provided as a helper for common `inpxml_changes`, but many
  real magnetic calculations still require workflow-specific tuning.
- For advanced input details, use the official `aiida-fleur` workflow docs
  linked by `list_fleur_workflows`.
