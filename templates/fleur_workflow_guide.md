# AiiDA-FLEUR EOS Workflow Guide

This template follows the `fleur.eos` workchain from `aiida-fleur` and is meant for equation-of-state calculations. The main MCP goal is to generate the AiiDA input/builder block for this workflow.

## Required Inputs

- `structure`: input crystal structure
- `scf.inpgen`: configured AiiDA code for `inpgen`
- `scf.fleur`: configured AiiDA code for `fleur`
- `wf_parameters`: EOS settings such as:
  - `points`: number of scaling points
  - `step`: spacing between scale factors
  - `guess`: initial scale-factor guess
- `scf.wf_parameters`: SCF convergence settings
- `scf.options`: scheduler and resource options

## Basic Pattern

1. Load the AiiDA profile
2. Read the structure file with ASE
3. Build `WorkflowFactory("fleur.eos")`
4. Attach the structure and EOS `wf_parameters`
5. Configure the nested `scf` namespace with `inpgen`, `fleur`, `options`, and SCF workflow parameters
6. Reuse the builder with `submit(builder)` or `run_get_node(builder)`

## Example Settings

- `points = 9`
- `step = 0.002`
- `guess = 1.0`
- `fleur_runmax = 4`
- `itmax_per_run = 30`
- `density_converged = 0.0002`

## Reuse

After generating inputs, you can insert them into your own workflow driver. For example:

```python
from aiida.engine import submit

process = submit(builder)
print(process.pk)
```

## Notes

- The exact `inpgen` and `fleur` labels depend on the user's AiiDA setup.
- Queue and MPI settings should be adjusted to the target machine.
- `aiida-fleur` documentation describes `fleur.eos` as an EOS workflow built on nested `fleur.scf` runs.
