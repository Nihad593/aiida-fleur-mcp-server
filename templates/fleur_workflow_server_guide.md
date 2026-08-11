# FLEUR Workflow Server Guide

This MCP server generates Python scripts for the/Users/abuawwad/Desktop/aiida-fleur-mcp/server.py main `aiida-fleur`
workflows instead of producing only one narrow calculation template.

## What It Generates

- SCF scripts
- EOS scripts
- relax scripts
- band structure scripts
- DOS scripts
- MAE scripts
- spin-spiral and DMI scripts
- magnetic film setup scripts
- plotting scripts using `plot_fleur`

## Magnetic Helper

The generated scripts include a small helper that can inject common
`inpxml_changes` for:

- `collinear`
- `noncollinear`
- `spin_spiral`

This is a good starting point, but realistic magnetic studies still often need
workflow-specific `wf_parameters` and manual refinement.

## Recommended Usage

1. Call `list_fleur_workflows`.
2. Generate the workflow script you need.
3. Edit the produced dictionaries if you want more precise FLEUR settings.
4. Run the script with your configured AiiDA profile.
