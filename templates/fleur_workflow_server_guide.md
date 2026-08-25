# FLEUR Workflow Server Guide

This MCP server generates Python scripts for the main `aiida-fleur`
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
- workflow explanations for teaching users what each workflow does

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
2. Call `explain_fleur_workflow` for the workflow you want to learn.
3. Generate the workflow script you need.
4. Edit the produced dictionaries if you want more precise FLEUR settings.
5. Run the script with your configured AiiDA profile.
