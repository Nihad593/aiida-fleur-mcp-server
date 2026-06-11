from aiida import load_profile, orm
from aiida.plugins import WorkflowFactory
from aiida.engine import run_get_node
from ase import io

load_profile()

# Load structure
structure = io.read("Si.cif")

# Setup workflow
FleurEosWorkChain = WorkflowFactory("fleur.eos")
builder = FleurEosWorkChain.get_builder()

builder.structure = orm.StructureData(ase=structure)
builder.wf_parameters = orm.Dict(
    dict={
        "points": 9,
        "step": 0.002,
        "guess": 1.0,
    }
)

builder.scf.wf_parameters = orm.Dict(
    dict={
        "fleur_runmax": 4,
        "itmax_per_run": 30,
        "density_converged": 0.0002,
        "mode": "density",
    }
)
builder.scf.options = orm.Dict(
    dict={
        "resources": {
            "num_machines": 1,
            "num_mpiprocs_per_machine": 1,
        },
        "max_wallclock_seconds": 3600,
        "withmpi": True,
    }
)
builder.scf.inpgen = orm.load_code("inpgen@localhost")
builder.scf.fleur = orm.load_code("fleur@localhost")

# Run calculation after reviewing the inputs above
results, calc = run_get_node(builder)
