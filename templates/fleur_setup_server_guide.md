# FLEUR Setup Server Guide

This MCP server can now generate an AiiDA setup procedure for a remote
supercomputer and the `inpgen` and `fleur` codes you want to use there.

## What It Produces

The `generate_aiida_setup_guide` tool writes a Markdown guide with ready-to-run
commands for:

- `verdi computer setup`
- `verdi computer configure`
- `verdi computer test`
- `verdi code create` for `fleur.inpgen`
- `verdi code create` for `fleur.fleur`

The `setup_aiida_computer_and_codes` tool can go one step further:

- it checks whether required setup information is missing
- it asks for the missing fields through an `input_required` tool result
- it can run the local `verdi` commands when called with `apply=true`

## Typical Inputs

- `computer_label`
- `hostname`
- `scheduler`
- `work_dir`
- `mpirun_command`
- `prepend_text`
- `inpgen_executable_path`
- `fleur_executable_path`

## Recommended Usage

1. Generate the setup guide for your HPC machine.
2. Review the `prepend_text` block for required modules and environment setup.
3. Run the generated commands locally in your AiiDA environment.
4. Test the computer and verify both codes before submitting workflows.
