# AiiDA-FLEUR EOS MCP Server

This repository is an MCP server focused only on `aiida-fleur` equation-of-state workflows.

It helps an MCP client such as Claude generate:

- reusable AiiDA builder inputs for `WorkflowFactory("fleur.eos")`
- optional runnable Python scripts that submit the EOS workflow
- basic monitoring commands for the submitted AiiDA process

## Prerequisites

- Python 3.10+
- AiiDA with a configured profile
- `aiida-fleur` installed
- configured AiiDA codes for `inpgen` and `fleur`

## Main MCP Tools

### `generate_fleur_eos_inputs`

Returns a reusable AiiDA builder block for `fleur.eos`.

Required inputs:

- `material`
- `structure_file`

Optional inputs:

- `inpgen_code`
- `fleur_code`
- `points`
- `step`
- `guess`
- `fleur_runmax`
- `itmax_per_run`
- `density_converged`
- `num_machines`
- `num_mpiprocs_per_machine`
- `max_wallclock_seconds`
- `queue_name`

### `generate_fleur_eos_script`

Creates a runnable Python script for the same EOS workflow.

### `execute_calculation`

Runs a generated script with:

```bash
verdi run <script_path>
```

### `check_calculation_status`

Shows the status of recent processes or one selected process.

## Important Files

```text
aiida-mcp/
├── server.py
├── templates/
│   ├── fleur_eos_inputs_template.py
│   ├── fleur_eos_script_template.py
│   ├── fleur_eos_workflow_template.py
│   └── fleur_workflow_guide.md
└── prompts/
    └── aiida_fleur_eos.md
```

## Running The Server

```bash
python3 -m pip install mcp
python3 /absolute/path/to/server.py
```

Or register it with Claude Code:

```bash
claude mcp add --scope user python3 /absolute/path/to/server.py
```

## How It Connects To AiiDA

The generated code builds:

```python
WorkflowFactory("fleur.eos").get_builder()
```

and fills:

```python
builder.structure
builder.wf_parameters
builder.scf.wf_parameters
builder.scf.options
builder.scf.inpgen
builder.scf.fleur
```

You can then use the returned builder with:

```python
from aiida.engine import submit
process = submit(builder)
```
