# FLEUR Setup Server Guide

> [!IMPORTANT]
> This guide is not limited to FZJ systems. It can be used as a model for
> JURECA, JUWELS, JUPITER, and also for non-FZJ clusters with similar schedulers.

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

## Adapting The Guide Outside FZJ

If your machine is not one of the built-in examples, you can still use the same
procedure. Replace the machine-specific values with your own site values.

### Minimum information you need

- cluster label
- login hostname
- scheduler family
- transport type
- AiiDA work directory
- MPI launcher command
- module loads or environment activation commands
- absolute path to `inpgen`
- absolute path to `fleur` or `fleur_MPI`

### Common scheduler mappings

| HPC environment | Likely AiiDA scheduler plugin |
| --- | --- |
| SLURM | `core.slurm` |
| PBS Pro | `core.pbspro` |
| Torque | `core.torque` |
| LSF | `core.lsf` |

### Common ways the codes are provided

- centrally installed module environment
- local user build
- Spack environment
- project-specific software stack

### Good adaptation workflow

1. Ask the server for a setup guide using the closest known preset.
2. Replace the hostname, work directory, module block, and executable paths.
3. Adjust the scheduler plugin if your site is not SLURM-based.
4. Test with `verdi computer test`.
5. Confirm the codes with `verdi code show`.
