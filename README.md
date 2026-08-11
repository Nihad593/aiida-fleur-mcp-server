# FLEUR Workflow MCP Server

This repository provides an MCP server for `aiida-fleur` setup, workflow
generation, execution, monitoring, and output inspection.

It is designed to help with three main areas:

- setup of supercomputers, AiiDA computers, and `inpgen`/`fleur` codes
- generation of runnable `aiida-fleur` workflow scripts
- execution, monitoring, and inspection of AiiDA/FLEUR calculations

## Functions

When a user asks what the server does, the server can describe its functions in
this order:

- setup of supercomputers and AiiDA codes
- system-specific setup presets such as `jureca`, `juwels-cluster`,
  `juwels-booster`, and `jupiter`
- interactive setup support for missing required information
- local AiiDA setup execution with `verdi`
- setup documentation generation
- workflow input/script generation
- supported workflow listing
- magnetic workflow helpers
- workflow execution with `verdi run`
- AiiDA process listing and monitoring
- output and result inspection
- plotting support

## Supported Workflows

The server can generate scripts for these `aiida-fleur` workflows:

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

## Main MCP Tools

### Discovery

- `describe_server_functions`
  Returns the server functions as a clean bullet list.

- `list_fleur_workflows`
  Lists supported workflows, their `WorkflowFactory(...)` entry points, and the
  official documentation links.

### Workflow Generation

- `generate_fleur_workflow_script`
  Generates a runnable Python script for a selected `aiida-fleur` workflow.

Useful inputs include:

- `workflow`
- `material`
- `structure_file`
- `inpgen_code`
- `fleur_code`
- `workflow_parameters`
- `calc_parameters`
- `scf_workflow_parameters`
- `final_scf_workflow_parameters`
- `magnetism`
- `plot_results`

### Plotting

- `generate_fleur_plot_script`
  Generates a plotting script that uses `plot_fleur` on one or more node PKs or
  UUIDs.

### Run And Monitor

- `execute_fleur_workflow_script`
  Runs a generated workflow script with:

```bash
verdi run <script_path>
```

- `list_aiida_processes`
  Lists recent AiiDA processes.

- `check_aiida_process`
  Shows the current status and the report of an AiiDA process by PK or UUID.

- `inspect_aiida_outputs`
  Loads an AiiDA process and summarizes its outputs, output nodes, and basic
  workflow result information.

### Supercomputer And Code Setup

- `generate_aiida_setup_guide`
  Writes a Markdown setup procedure for a remote machine and for registering
  `inpgen` and `fleur`.

- `setup_aiida_computer_and_codes`
  Uses local `verdi` commands to create/configure/test the AiiDA computer and
  register the `inpgen` and `fleur` codes.

Behavior:

- if required fields are missing, the tool asks for them
- if `apply=false`, it returns a preview and setup guide
- if `apply=true`, it runs the setup locally

## Supercomputer Presets

The server currently includes named presets for:

- `jureca`
- `juwels-cluster`
- `juwels-booster`
- `jupiter`

These presets provide machine-specific defaults for:

- login hostname
- scheduler
- transport
- setup notes
- module discovery hints
- links to official system documentation

## Requirements

- Python 3.10+
- `mcp`
- `aiida-core`
- `aiida-fleur`
- `ase`
- a configured AiiDA profile
- configured `inpgen` and `fleur` code nodes for workflow execution

## Running The Server

Because many macOS/Homebrew Python installations are externally managed, a
virtual environment is the recommended way to run the server.

```bash
cd /absolute/path/to/aiida-fleur-mcp
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install mcp
python3 server.py
```

To start it again later:

```bash
cd /absolute/path/to/aiida-fleur-mcp
source .venv/bin/activate
python3 server.py
```

## Notes

- The server focuses on `aiida-fleur` workflow automation, not raw manual
  `inp.xml` authoring.
- Execution and monitoring features rely on your local AiiDA environment and
  `verdi` being available.
- Setup application with `setup_aiida_computer_and_codes` changes your local
  AiiDA configuration, so review the preview before running with `apply=true`.
- The magnetic helper is meant as a practical starting point. Advanced magnetic
  studies still need workflow-specific tuning.
- For workflow-specific scientific input details, use the official
  `aiida-fleur` documentation linked by `list_fleur_workflows`.
