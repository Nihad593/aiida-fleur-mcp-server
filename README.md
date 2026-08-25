# FLEUR Workflow MCP Server

> [!IMPORTANT]
> **Author:** Nihad Abuawwad  
> **Purpose:** A practical MCP server for `aiida-fleur` users who want help with
> workflow learning, supercomputer setup, script generation, execution, and output inspection.

## Quick Navigation

| Open | Description |
| --- | --- |
| [User Guide](docs/USER_GUIDE.md) | End-user documentation with examples and workflow paths |
| [Workflow Server Guide](templates/fleur_workflow_server_guide.md) | Template-style server guide for workflow generation |
| [Setup Server Guide](templates/fleur_setup_server_guide.md) | Template-style setup guide for computers and codes |

> [!TIP]
> Best opening questions for a new user:
> `What does this server do?`
> `List the functions of this server`
> `Explain the scf workflow`
> `Show me how to set up JURECA`

## Overview

This server is designed to support the full `aiida-fleur` lifecycle, from first
questions to running and checking workflows.

| Stage | What the server helps with |
| --- | --- |
| Learn | Explain what each workflow does, when to use it, and how it works |
| Setup | Guide users through AiiDA computer and code configuration |
| Generate | Create exact workflow and submission scripts |
| Run | Execute generated scripts with `verdi run` |
| Monitor | Check process status and reports |
| Inspect | Summarize outputs, result nodes, and workflow results |
| Plot | Generate plotting helpers for `plot_fleur` |

## What Users Can Ask

> [!NOTE]
> The server is built to answer practical user requests, not only developer-facing questions.

- `What does this server do?`
- `List the functions of this server`
- `Explain the eos workflow`
- `Give me a submission script for a DOS calculation`
- `Show me how to set up JURECA`
- `Set up the AiiDA computer and codes for JUPITER`
- `Run this workflow script`
- `Check process 12345`
- `Inspect the outputs of process 12345`

## Main Features

### 1. Overview And Discovery

| Tool | Purpose |
| --- | --- |
| `get_server_overview` | Short description of the server and what it supports |
| `describe_server_functions` | Friendly list of server capabilities grouped by topic |
| `get_client_usage_policy` | Recommended client behavior for concise, focused interaction |

### 2. Workflow Learning

| Tool | Purpose |
| --- | --- |
| `list_fleur_workflows` | Show supported workflows |
| `explain_fleur_workflow` | Teach what a workflow does, when to use it, and how it works |

Supported workflows:

`scf`, `eos`, `relax`, `band`, `dos`, `mae`, `ssdisp`, `dmi`, `corehole`, `init_cls`, `create_magnetic`

> [!TIP]
> Workflow explanations are written for learning. They cover:
> what the workflow does, when to use it, how it runs, important inputs, and expected outputs.

### 3. Script Generation

| Tool | Purpose |
| --- | --- |
| `generate_fleur_workflow_script` | Build a workflow script for `aiida-fleur` |
| `generate_fleur_submission_script` | Build an annotated submission-ready script with comments |

Generated scripts can include notes for:

- editable configuration
- structure loading
- workflow parameters
- scheduler and resource options
- magnetic helper logic
- builder construction
- `submit` usage
- `run_get_node` usage

### 4. Supercomputer And Code Setup

| Tool | Purpose |
| --- | --- |
| `generate_aiida_setup_guide` | Step-by-step setup guide for a target machine |
| `setup_aiida_computer_and_codes` | Render concrete AiiDA computer/code setup commands |

Supported setup topics include:

- AiiDA computers
- `inpgen` codes
- `fleur` codes
- CPU and GPU examples
- module-based setups
- Spack-based setups

Current presets:

- `jureca`
- `juwels-cluster`
- `juwels-booster`
- `jupiter`

The documentation also explains how to adapt the same setup logic for users
outside Forschungszentrum Juelich and outside FZJ systems.

> [!IMPORTANT]
> Setup guides use generalized placeholders such as `<project>` and `<user>`
> so users can safely adapt them to their own account.

### 5. Run, Monitor, And Inspect

| Tool | Purpose |
| --- | --- |
| `execute_fleur_workflow_script` | Run a generated script through `verdi run` |
| `list_aiida_processes` | Show recent AiiDA processes |
| `check_aiida_process` | Inspect process state and report information |
| `inspect_aiida_outputs` | Summarize outputs and result nodes |

### 6. Plotting

| Tool | Purpose |
| --- | --- |
| `generate_fleur_plot_script` | Create helper scripts for plotting workflow results with `plot_fleur` |

## Internal Documentation Resources

The server also exposes internal MCP resources:

- `fleur://docs/overview`
- `fleur://docs/workflow_guide`
- `fleur://docs/setup_guide`
- `fleur://docs/client_policy`

## Recommended User Journey

> [!TIP]
> A good experience is to move in this order: learn, setup, generate, run, inspect.

### New User Path

1. Read the overview.
2. Ask what the server functions are.
3. Ask for a workflow explanation.
4. Ask for a setup guide for the target machine.
5. Generate a submission script.
6. Run the workflow.
7. Monitor and inspect the outputs.

### Experienced User Path

1. Request a workflow script or submission script directly.
2. Run it.
3. Check the process.
4. Inspect outputs.

## Example Questions

### Setup

- `Show me how to set up JURECA for aiida-fleur`
- `Explain how to register inpgen and fleur on JUPITER`
- `Generate a setup guide for JUWELS Cluster`
- `Show me how to adapt this setup for my university cluster`
- `I am outside FZJ, how should I configure my computer and codes?`

### Workflow Learning

- `Explain the relax workflow`
- `What is the difference between band and dos workflows?`
- `When should I use create_magnetic?`

### Script Generation

- `Generate a submission script for an SCF workflow for Fe`
- `Generate a DOS workflow script for Ni`
- `Give me an annotated EOS submission script`

### Execution And Outputs

- `Run this workflow script`
- `List recent AiiDA processes`
- `Check process 12345`
- `Inspect outputs for process 12345`

## Requirements

> [!NOTE]
> Running workflows requires a configured AiiDA profile and registered `inpgen` and `fleur` codes.

- Python 3.10+
- `mcp`
- `aiida-core`
- `aiida-fleur`
- `ase`
- a configured AiiDA profile
- configured `inpgen` and `fleur` code nodes for workflow execution

## Running The Server

> [!WARNING]
> On many macOS/Homebrew Python installations, a virtual environment is the safest way to install `mcp`.

```bash
cd /absolute/path/to/aiida-fleur-mcp
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install mcp
python3 server.py
```

To start it later:

```bash
cd /absolute/path/to/aiida-fleur-mcp
source .venv/bin/activate
python3 server.py
```

## Files

| File | Purpose |
| --- | --- |
| `server.py` | Main MCP server implementation |
| `README.md` | Project overview |
| `docs/USER_GUIDE.md` | Full end-user guide |
| `templates/fleur_workflow_server_guide.md` | Workflow help resource |
| `templates/fleur_setup_server_guide.md` | Setup help resource |

## Notes

- The server focuses on `aiida-fleur` workflow automation, not manual
  `inp.xml` editing.
- The setup application tool changes local AiiDA configuration, so users should
  review the preview before applying changes.
- FZJ machines are provided as strong examples, but the same setup ideas also
  apply to other SLURM, PBS, and LSF-based clusters.
- The client usage policy is advisory. The server can recommend a style of use,
  but cannot technically force a client to hide reasoning or disable other
  tools.
- Advanced magnetic calculations still require workflow-specific scientific
  tuning.

## Full Guide

For a more complete, step-by-step guide, see:

- [USER_GUIDE.md](/Users/abuawwad/Desktop/aiida-fleur-mcp/docs/USER_GUIDE.md)
