# FLEUR Workflow MCP Server User Guide

> [!IMPORTANT]
> **Author:** Nihad Abuawwad  
> This guide is for end users who want to learn, set up, run, and inspect
> `aiida-fleur` workflows through the MCP server.

## Welcome

> [!TIP]
> The main user path is simple:
> **learn workflows -> set up computers and codes -> generate scripts -> run -> inspect results**

This guide explains how to use the FLEUR Workflow MCP Server from the point of
view of an end user.

## 1. What This Server Is For

This server is a helper layer around `aiida-fleur`. It does not replace AiiDA
or FLEUR. Instead, it helps the user work with them more easily and more
confidently.

### Main capabilities

| Area | What the server provides |
| --- | --- |
| Learning | Workflow explanations and function overviews |
| Setup | AiiDA computer and code setup guides |
| Script generation | Runnable and annotated workflow scripts |
| Execution | `verdi run` execution helpers |
| Monitoring | Process state and report inspection |
| Outputs | Output summaries and plotting helpers |

## 2. Main User Tasks

### Learn A Workflow

Use:

- `list_fleur_workflows`
- `explain_fleur_workflow`

This is useful when the user wants to know:

- what `scf` does
- when `eos` should be used
- how `relax` differs from `scf`
- what `mae`, `dmi`, or `ssdisp` are for

### Set Up A Supercomputer

Use:

- `generate_aiida_setup_guide`
- `setup_aiida_computer_and_codes`

This is useful when the user wants to configure:

- an AiiDA computer
- `inpgen`
- `fleur`
- CPU or GPU versions
- module-based or Spack-based installations

### Generate A Submission Script

Use:

- `generate_fleur_submission_script`

This is useful when the user wants an exact runnable script plus comments that
explain each block.

### Run And Inspect Calculations

Use:

- `execute_fleur_workflow_script`
- `list_aiida_processes`
- `check_aiida_process`
- `inspect_aiida_outputs`

## 3. Supported Workflows

> [!NOTE]
> The server supports both common workflows and more specialized magnetic and spectroscopy workflows.

The server currently supports:

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

## 4. Example User Flows

### Flow A: Learn First

1. Ask for the server overview.
2. Ask for the list of workflows.
3. Ask the server to explain one workflow.
4. Ask for a submission script.

Example:

```text
Explain the eos workflow
Generate a submission script for an eos workflow for Fe
```

### Flow B: Setup First

1. Ask for a setup guide for a machine like JURECA or JUPITER.
2. Read the step-by-step instructions.
3. Apply the setup with real machine-specific values.

Example:

```text
Show me how to set up JURECA
Generate a setup guide for JUPITER
```

### Flow C: Run And Monitor

1. Generate a submission script.
2. Execute the script.
3. Check the created process.
4. Inspect outputs.

Example:

```text
Run this workflow script
Check process 12345
Inspect outputs for process 12345
```

## 5. Supercomputer Support

The server includes presets for:

- `jureca`
- `juwels-cluster`
- `juwels-booster`
- `jupiter`

These presets help the user learn:

- login hostname
- scheduler type
- transport type
- work directory patterns
- module discovery
- code registration examples

> [!IMPORTANT]
> Setup examples use placeholders such as `<project>`, `<user>`,
> `<absolute_path_to_inpgen>`, and `<absolute_path_to_fleur_or_fleur_MPI>` so the
> documentation stays general and safe to reuse.

## 6. Submission Scripts

The generated submission scripts are designed to be teachable.

They include commented blocks for:

- configuration
- structure loading
- scheduler options
- magnetic settings
- builder setup
- submission mode
- run mode

> [!TIP]
> This means the scripts are useful both as runnable files and as learning material.

## 7. Execution And Results

The server can help with:

- running scripts using `verdi run`
- listing processes
- checking reports
- inspecting outputs
- preparing plotting scripts

This lets the user go beyond setup and generation into real workflow handling.

## 8. Limitations

> [!WARNING]
> The server helps with workflow usage and setup, but it does not replace scientific judgment.

- Advanced calculations still require users to choose sensible parameters.
- The client usage policy is only a recommendation; it cannot force a client to
  hide chain-of-thought or disable other tools.

## 9. Running The Server

```bash
cd /absolute/path/to/aiida-fleur-mcp
source .venv/bin/activate
python3 server.py
```

## 10. Best Starting Questions

If the user is new, these are good first questions:

- `What does this server do?`
- `List the functions of this server`
- `Explain the scf workflow`
- `Show me how to set up JURECA`
- `Generate a submission script for a DOS calculation`
- `How do I run and monitor the workflow?`
