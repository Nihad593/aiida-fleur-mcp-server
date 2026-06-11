from aiida import orm
from aiida.plugins import WorkflowFactory
from ase import io

# Reusable inputs for aiida-fleur EOS workflow: {material}
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

# Reuse this builder in:
# submit(builder)
# run_get_node(builder)
