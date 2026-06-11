#!/usr/bin/env python3
"""
aiida-fleur EOS calculation for {material}
Generated on {timestamp}
"""

from aiida import load_profile, orm
from aiida.engine import submit
from aiida.plugins import WorkflowFactory
from ase import io


def main():
    load_profile()

    print("Starting aiida-fleur EOS calculation for {material}")
    print("=" * 60)

    print("Loading structure from: {structure_file}")
    structure = io.read("{structure_file}")

    FleurEosWorkChain = WorkflowFactory("fleur.eos")
    builder = FleurEosWorkChain.get_builder()

    builder.structure = orm.StructureData(ase=structure)
    builder.wf_parameters = orm.Dict(
        dict={{
            "points": {points},
            "step": {step},
            "guess": {guess},
        }}
    )

    builder.scf.wf_parameters = orm.Dict(
        dict={{
            "fleur_runmax": {fleur_runmax},
            "itmax_per_run": {itmax_per_run},
            "density_converged": {density_converged},
            "mode": "density",
        }}
    )

    options = {{
        "resources": {{
            "num_machines": {num_machines},
            "num_mpiprocs_per_machine": {num_mpiprocs_per_machine},
        }},
        "max_wallclock_seconds": {max_wallclock_seconds},
        "withmpi": True,
    }}
    queue_name = "{queue_name}"
    if queue_name:
        options["queue_name"] = queue_name

    builder.scf.options = orm.Dict(dict=options)
    builder.scf.inpgen = orm.load_code("{inpgen_code}")
    builder.scf.fleur = orm.load_code("{fleur_code}")

    print("Submitting EOS workflow...")
    process = submit(builder)

    print(f"Workflow submitted with PK: {{process.pk}}")
    print("=" * 60)
    print("Monitor progress with:")
    print(f"  verdi process show {{process.pk}}")
    print(f"  verdi process report {{process.pk}}")
    print(f"  verdi process status {{process.pk}}")
    print("=" * 60)

    with open("last_calculation_pk.txt", "w", encoding="utf-8") as handle:
        handle.write(str(process.pk))

    print("Process ID saved to: last_calculation_pk.txt")


if __name__ == "__main__":
    main()
