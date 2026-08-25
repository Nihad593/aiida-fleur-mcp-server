#!/usr/bin/env python3
"""
FLEUR workflow MCP server.

Generates runnable aiida-fleur Python scripts for common workflows such as
SCF, DOS, band structure, EOS, relaxations and magnetic calculations.
"""

from __future__ import annotations

import json
import logging
import subprocess
import tempfile
from pathlib import Path
from pprint import pformat
from typing import Any

from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("aiida-mcp.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("fleur-workflow-mcp")

SERVER_TITLE = "FLEUR Workflow MCP Server"
SERVER_AUTHOR = "Nihad Abuawwad"
SERVER_VERSION = "1.1.0"


WORKFLOW_SPECS: dict[str, dict[str, Any]] = {
    "scf": {
        "entrypoint": "fleur.scf",
        "pattern": "direct",
        "description": "Self-consistent FLEUR workflow from a structure or FleurinpData.",
    },
    "eos": {
        "entrypoint": "fleur.eos",
        "pattern": "nested_scf",
        "description": "Equation-of-state workflow using nested SCF calculations.",
    },
    "relax": {
        "entrypoint": "fleur.relax",
        "pattern": "nested_scf_with_final",
        "description": "Structure relaxation workflow with optional final SCF.",
    },
    "band": {
        "entrypoint": "fleur.banddos",
        "pattern": "banddos_like",
        "default_wf_parameters": {
            "mode": "band",
            "kpath": "auto",
            "klistname": "path-3",
            "sigma": 0.005,
            "emin": -0.5,
            "emax": 0.9,
            "inpxml_changes": [],
        },
        "description": "Band structure workflow using FleurBandDosWorkChain.",
    },
    "dos": {
        "entrypoint": "fleur.banddos",
        "pattern": "banddos_like",
        "default_wf_parameters": {
            "mode": "dos",
            "sigma": 0.005,
            "emin": -0.5,
            "emax": 0.9,
            "inpxml_changes": [],
        },
        "description": "Density-of-states workflow using FleurBandDosWorkChain.",
    },
    "mae": {
        "entrypoint": "fleur.mae",
        "pattern": "banddos_like",
        "description": "Magnetic anisotropy energy workflow.",
    },
    "ssdisp": {
        "entrypoint": "fleur.ssdisp",
        "pattern": "banddos_like",
        "description": "Spin-spiral dispersion workflow.",
    },
    "dmi": {
        "entrypoint": "fleur.dmi",
        "pattern": "banddos_like",
        "description": "Dzyaloshinskii-Moriya interaction workflow.",
    },
    "corehole": {
        "entrypoint": "fleur.corehole",
        "pattern": "direct",
        "description": "Core-hole workflow for core-level binding energies.",
    },
    "init_cls": {
        "entrypoint": "fleur.init_cls",
        "pattern": "direct",
        "description": "Initial core-level shifts workflow.",
    },
    "create_magnetic": {
        "entrypoint": "fleur.create_magnetic",
        "pattern": "create_magnetic",
        "description": "Magnetic film construction workflow for follow-up DMI/MAE/SSDisp studies.",
    },
}


WORKFLOW_DOC_LINKS = {
    "scf": "https://aiida-fleur.readthedocs.io/en/latest/user_guide/workflows/scf_wc.html",
    "eos": "https://aiida-fleur.readthedocs.io/en/latest/user_guide/workflows/eos_wc.html",
    "relax": "https://aiida-fleur.readthedocs.io/en/latest/user_guide/workflows/relax_wc.html",
    "band": "https://aiida-fleur.readthedocs.io/en/latest/user_guide/workflows/dos_band_wc.html",
    "dos": "https://aiida-fleur.readthedocs.io/en/latest/user_guide/workflows/dos_band_wc.html",
    "mae": "https://aiida-fleur.readthedocs.io/en/latest/user_guide/workflows/mae_wc.html",
    "ssdisp": "https://aiida-fleur.readthedocs.io/en/latest/user_guide/workflows/ssdisp_wc.html",
    "dmi": "https://aiida-fleur.readthedocs.io/en/latest/user_guide/workflows/dmi_wc.html",
    "corehole": "https://aiida-fleur.readthedocs.io/en/latest/user_guide/workflows/corehole_wc.html",
    "init_cls": "https://aiida-fleur.readthedocs.io/en/latest/user_guide/workflows/initial_cls_wc.html",
    "create_magnetic": "https://aiida-fleur.readthedocs.io/en/latest/user_guide/workflows/create_magnetic_wc.html",
}

WORKFLOW_TEACHING = {
    "scf": {
        "what": "Runs a self-consistent FLEUR cycle until the charge density is converged.",
        "when": "Use this as the basic electronic-structure workflow for a material before DOS, bands, MAE, DMI, or other post-processing workflows.",
        "how": "The workflow takes a structure or FleurinpData, runs `inpgen` if needed, starts FLEUR, checks convergence, and can continue over multiple FLEUR runs until the density criteria are reached.",
        "main_inputs": [
            "structure_file or structure node",
            "inpgen code",
            "fleur code",
            "SCF workflow parameters like `itmax_per_run`, `fleur_runmax`, and convergence thresholds",
            "scheduler options and resources",
        ],
        "main_outputs": [
            "converged SCF process",
            "final output parameters",
            "remote folder / retrieved data",
            "a converged starting point for later workflows",
        ],
    },
    "eos": {
        "what": "Runs an equation-of-state workflow by calculating several scaled volumes around the initial structure.",
        "when": "Use this when you want equilibrium lattice constants, bulk modulus trends, or a better starting volume before detailed production calculations.",
        "how": "The workflow rescales the structure over a range of volumes and launches a nested SCF workflow at each point. The collected energies are then used to analyze the volume-energy curve.",
        "main_inputs": [
            "initial structure",
            "EOS workflow parameters like `points`, `step`, and `guess`",
            "nested SCF settings",
            "inpgen and fleur codes",
        ],
        "main_outputs": [
            "energies for each tested volume",
            "volume-energy data for fitting",
            "an equilibrium-volume estimate",
        ],
    },
    "relax": {
        "what": "Relaxes the atomic structure iteratively using FLEUR forces.",
        "when": "Use this when the atomic positions are not yet optimized or when you want a lower-force geometry before SCF, DOS, or magnetic analysis.",
        "how": "The workflow performs repeated SCF and force evaluations, updates the structure, and optionally finishes with a final SCF run on the relaxed geometry.",
        "main_inputs": [
            "initial structure",
            "relax workflow parameters",
            "nested SCF settings",
            "optional final SCF settings",
        ],
        "main_outputs": [
            "relaxed structure",
            "force history",
            "final relaxed workflow result",
        ],
    },
    "band": {
        "what": "Calculates band structure information using the FLEUR BandDos workflow in `band` mode.",
        "when": "Use this after a well-converged SCF calculation when you want the dispersion of eigenvalues along a k-path.",
        "how": "The workflow starts from SCF or from an existing FLEUR input, applies band-structure settings such as k-path choices, and runs the band calculation mode in FLEUR.",
        "main_inputs": [
            "converged SCF starting point or structure plus SCF namespace",
            "band workflow parameters such as `kpath`, `klistname`, `emin`, `emax`, and `sigma`",
            "fleur code",
        ],
        "main_outputs": [
            "band data",
            "band-related output files",
            "data suitable for plotting with `plot_fleur`",
        ],
    },
    "dos": {
        "what": "Calculates density of states using the FLEUR BandDos workflow in `dos` mode.",
        "when": "Use this after a converged SCF calculation when you want total or projected density-of-states information.",
        "how": "The workflow reuses a converged electronic structure, switches the FLEUR run into DOS mode, and collects energy-resolved DOS information.",
        "main_inputs": [
            "converged SCF starting point or structure plus SCF namespace",
            "DOS workflow parameters such as `emin`, `emax`, and `sigma`",
            "fleur code",
        ],
        "main_outputs": [
            "DOS data",
            "spin-resolved or projected DOS information when requested",
            "data suitable for plotting with `plot_fleur`",
        ],
    },
    "mae": {
        "what": "Calculates magnetic anisotropy energy by comparing magnetization directions.",
        "when": "Use this for spin-orbit driven anisotropy studies after you already have a converged magnetic starting point.",
        "how": "The workflow uses a converged magnetic reference, applies spin-orbit and magnetization-direction settings, and evaluates total-energy differences between orientations.",
        "main_inputs": [
            "converged magnetic starting point",
            "MAE workflow parameters",
            "noncollinear / SOC-related `inpxml_changes` when needed",
        ],
        "main_outputs": [
            "anisotropy energies",
            "direction-dependent energy comparison",
        ],
    },
    "ssdisp": {
        "what": "Calculates spin-spiral dispersion.",
        "when": "Use this when studying noncollinear magnetism or spin-spiral energetics as a function of q-vector.",
        "how": "The workflow prepares noncollinear spin-spiral settings, evaluates several q-points, and returns the energy trend versus spin-spiral vector.",
        "main_inputs": [
            "magnetic starting point",
            "spin-spiral parameters like q-vectors",
            "noncollinear FLEUR settings",
        ],
        "main_outputs": [
            "spin-spiral energy dispersion",
            "q-dependent magnetic results",
        ],
    },
    "dmi": {
        "what": "Calculates Dzyaloshinskii-Moriya interaction related energy contributions.",
        "when": "Use this for chiral magnetic systems when you want to quantify DMI from a converged magnetic reference state.",
        "how": "The workflow combines spin-spiral style settings with spin-orbit coupling and evaluates the relevant energy differences for DMI analysis.",
        "main_inputs": [
            "converged magnetic starting point",
            "DMI workflow parameters",
            "SOC and noncollinear settings",
        ],
        "main_outputs": [
            "DMI-related energies",
            "data for chiral magnetic analysis",
        ],
    },
    "corehole": {
        "what": "Runs a core-hole workflow for core-level binding-energy style studies.",
        "when": "Use this when you want to simulate the effect of a core hole on a selected atom or species.",
        "how": "The workflow modifies the electronic setup to represent a core hole, runs the required FLEUR calculation steps, and compares the resulting energies or shifts.",
        "main_inputs": [
            "structure",
            "core-hole workflow settings",
            "selected atom/species information",
            "inpgen and fleur codes",
        ],
        "main_outputs": [
            "core-hole calculation results",
            "core-level energy/shift related information",
        ],
    },
    "init_cls": {
        "what": "Calculates initial core-level shifts.",
        "when": "Use this when you want a workflow-oriented estimate of initial-state core-level shifts between atoms, sites, or reference systems.",
        "how": "The workflow evaluates the initial-state electronic structure and extracts the relevant core-level information without creating the full final-state core-hole situation.",
        "main_inputs": [
            "structure",
            "initial core-level shift workflow settings",
            "inpgen and fleur codes",
        ],
        "main_outputs": [
            "initial core-level shift information",
            "site or species comparisons",
        ],
    },
    "create_magnetic": {
        "what": "Builds a magnetic film/substrate setup for later magnetic studies.",
        "when": "Use this when constructing a magnetic heterostructure or film model before MAE, DMI, or spin-spiral workflows.",
        "how": "The workflow prepares a magnetic structure model and nests other workflows such as EOS and relax to create a usable magnetic starting system.",
        "main_inputs": [
            "film/substrate construction settings",
            "EOS and relax namespaces",
            "magnetic workflow parameters",
        ],
        "main_outputs": [
            "prepared magnetic film model",
            "relaxed and/or pre-optimized structure for later magnetic workflows",
        ],
    },
}


DEFAULT_OPTIONS = {
    "resources": {"num_machines": 1, "num_mpiprocs_per_machine": 1},
    "max_wallclock_seconds": 3600,
    "withmpi": True,
}

TRANSPORT_MAP = {
    "ssh": "core.ssh_async",
    "core.ssh": "core.ssh",
    "local": "core.local",
    "core.ssh_async": "core.ssh_async",
    "core.local": "core.local",
}

SCHEDULER_MAP = {
    "slurm": "core.slurm",
    "pbspro": "core.pbspro",
    "torque": "core.torque",
    "sge": "core.sge",
    "lsf": "core.lsf",
    "direct": "core.direct",
    "core.slurm": "core.slurm",
    "core.pbspro": "core.pbspro",
    "core.torque": "core.torque",
    "core.sge": "core.sge",
    "core.lsf": "core.lsf",
    "core.direct": "core.direct",
}

SYSTEM_PRESETS = {
    "jureca": {
        "label_suffix": "jureca",
        "hostname": "jureca.fz-juelich.de",
        "scheduler": "core.slurm",
        "transport": "core.ssh",
        "computer_example": {
            "label": "jureca",
            "description": "HDF5",
            "work_dir": "/p/project1/<project>/<user>/aiida",
            "mpirun_command": "srun",
            "default_procs_per_machine": 128,
            "prepend_text": "#SBATCH --account=<project>",
        },
        "code_examples": [
            {
                "title": "CPU `inpgen` example",
                "label": "inpgencpu",
                "plugin": "fleur.inpgen",
                "description": "HDF5",
                "with_mpi": False,
                "prepend_text": "module load Stages/2026 imkl/2025.2.0 Intel/2025.2.0 ParaStationMPI/5.13.0-1 CMake/3.31.8 HDF5/1.14.6",
                "filepath_executable": "/p/project1/<project>/<user>/fleur-cpu/build/inpgen",
            },
            {
                "title": "CPU `fleur` example",
                "label": "cpufleur",
                "plugin": "fleur.fleur",
                "description": "HDF5",
                "with_mpi": True,
                "prepend_text": "module load Stages/2026 imkl/2025.2.0 Intel/2025.2.0 ParaStationMPI/5.13.0-1 CMake/3.31.8 HDF5/1.14.6",
                "filepath_executable": "/p/project1/<project>/<user>/fleur-cpu/build/fleur_MPI",
            },
        ],
        "docs": {
            "access": "https://apps.fz-juelich.de/jsc/hps/jureca/access.html",
            "modules": "https://apps.fz-juelich.de/jsc/hps/jureca/software-modules.html",
            "batch": "https://apps.fz-juelich.de/jsc/hps/jureca/batchsystem.html",
            "environment": "https://apps.fz-juelich.de/jsc/hps/jureca/environment.html",
        },
        "login_example": "ssh <yourid>@jureca.fz-juelich.de",
        "module_note": "JURECA uses the JSC hierarchical module environment; start with `module avail`, then load a compiler and MPI stack before searching for FLEUR.",
        "system_note": "JURECA login nodes are shared and JSC advises not to rely on a specific login node being available.",
    },
    "juwels-cluster": {
        "label_suffix": "juwels-cluster",
        "hostname": "juwels-cluster.fz-juelich.de",
        "scheduler": "core.slurm",
        "transport": "core.ssh",
        "docs": {
            "access": "https://apps.fz-juelich.de/jsc/hps/juwels/access.html",
            "modules": "https://apps.fz-juelich.de/jsc/hps/juwels/software-modules.html",
            "batch": "https://apps.fz-juelich.de/jsc/hps/juwels/batchsystem.html",
            "environment": "https://apps.fz-juelich.de/jsc/hps/juwels/environment.html",
        },
        "login_example": "ssh <yourid>@juwels-cluster.fz-juelich.de",
        "module_note": "JUWELS uses the same JSC hierarchical module layout as JURECA; discover software with `module avail` and `module spider`.",
        "system_note": "Use the JUWELS Cluster login host for CPU-side builds and setup tasks.",
    },
    "juwels-booster": {
        "label_suffix": "juwels-booster",
        "hostname": "juwels-booster.fz-juelich.de",
        "scheduler": "core.slurm",
        "transport": "core.ssh",
        "docs": {
            "access": "https://apps.fz-juelich.de/jsc/hps/juwels/access.html",
            "modules": "https://apps.fz-juelich.de/jsc/hps/juwels/software-modules.html",
            "batch": "https://apps.fz-juelich.de/jsc/hps/juwels/batchsystem.html",
            "environment": "https://apps.fz-juelich.de/jsc/hps/juwels/environment.html",
        },
        "login_example": "ssh <yourid>@juwels-booster.fz-juelich.de",
        "module_note": "JUWELS Booster uses the same JSC module hierarchy, but the installed software set can differ from Cluster.",
        "system_note": "Use the JUWELS Booster login host if your FLEUR build or runtime is maintained there.",
    },
    "jupiter": {
        "label_suffix": "jupiter",
        "hostname": "login.jupiter.fz-juelich.de",
        "scheduler": "core.slurm",
        "transport": "core.ssh",
        "computer_example": {
            "label": "jupiter",
            "description": "HDF5",
            "work_dir": "/e/project1/<project>/<user>/aiida",
            "mpirun_command": "srun",
            "default_procs_per_machine": 72,
            "default_memory_kb_per_machine": 30,
            "prepend_text": "",
        },
        "code_examples": [
            {
                "title": "GPU `inpgen` example with Spack",
                "label": "inpgengpu",
                "plugin": "fleur.inpgen",
                "description": "HDF5",
                "with_mpi": False,
                "prepend_text": "\n".join(
                    [
                        "module load Stages/2026 nvidia-compilers/25.9-CUDA-13 ParaStationMPI/5.13.0-1 HDF5 git",
                        "export SLURM_CPUS_PER_TASK=36",
                        'export CUDA_VISIBLE_DEVICES=\"0,1,2,3\"',
                        "source /e/project1/<project>/<user>/spack/share/spack/setup-env.sh",
                        "spack env activate gpufleur2026",
                        "spack load fleur",
                    ]
                ),
                "filepath_executable": "/e/project1/<project>/<user>/spack/opt/spack/<arch>/fleur-<hash>/bin/inpgen",
            },
            {
                "title": "GPU `fleur` example with Spack",
                "label": "fleurgpu",
                "plugin": "fleur.fleur",
                "description": "HDF5+MPI",
                "with_mpi": True,
                "prepend_text": "\n".join(
                    [
                        "module load Stages/2026 nvidia-compilers/25.9-CUDA-13 ParaStationMPI/5.13.0-1 HDF5 git",
                        "export SLURM_CPUS_PER_TASK=36",
                        'export CUDA_VISIBLE_DEVICES=\"0,1,2,3\"',
                        "source /e/project1/<project>/<user>/spack/share/spack/setup-env.sh",
                        "spack env activate gpufleur2026",
                        "spack load fleur",
                    ]
                ),
                "filepath_executable": "/e/project1/<project>/<user>/spack/opt/spack/<arch>/fleur-<hash>/bin/fleur_MPI",
            },
        ],
        "docs": {
            "access": "https://apps.fz-juelich.de/jsc/hps/jupiter/access.html",
            "modules": "https://apps.fz-juelich.de/jsc/hps/jupiter/compile.html",
            "batch": "https://apps.fz-juelich.de/jsc/hps/jupiter/batchsystem.html",
            "environment": "https://apps.fz-juelich.de/jsc/hps/jupiter/environment.html",
            "overview": "https://apps.fz-juelich.de/jsc/hps/jupiter/index.html",
        },
        "login_example": "ssh <yourid>@login.jupiter.fz-juelich.de",
        "module_note": "JUPITER provides compiler and MPI toolchains through modules, but the documentation warns that the system is still evolving and module availability may change.",
        "system_note": "JUPITER documentation explicitly warns that the system is in pre/early access and details may change.",
    },
}


class FleurWorkflowMCPServer:
    def __init__(self) -> None:
        self.server = Server("fleur-workflows")
        self.templates_dir = Path(__file__).parent / "templates"
        self.setup_handlers()

    def _load_template(self, filename: str) -> str:
        try:
            return (self.templates_dir / filename).read_text(encoding="utf-8")
        except Exception as exc:
            logger.error("Failed to load template %s: %s", filename, exc)
            return f"Error loading template: {filename}"

    def _workflow_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "workflow": {
                    "type": "string",
                    "enum": sorted(WORKFLOW_SPECS.keys()),
                    "description": "Which aiida-fleur workflow script to generate.",
                },
                "material": {
                    "type": "string",
                    "description": "Short label used in file names and log output.",
                },
                "structure_file": {
                    "type": "string",
                    "description": "Path to a CIF or any structure file ASE can read.",
                },
                "inpgen_code": {
                    "type": "string",
                    "default": "inpgen@localhost",
                    "description": "AiiDA code label for the inpgen executable.",
                },
                "fleur_code": {
                    "type": "string",
                    "default": "fleur@localhost",
                    "description": "AiiDA code label for the fleur executable.",
                },
                "output_dir": {
                    "type": "string",
                    "default": ".",
                    "description": "Directory where the generated script will be written.",
                },
                "script_filename": {
                    "type": "string",
                    "description": "Optional custom file name for the generated script.",
                },
                "submit_mode": {
                    "type": "string",
                    "enum": ["submit", "run_get_node"],
                    "default": "submit",
                    "description": "Whether the generated script submits or blocks until completion.",
                },
                "options": {
                    "type": "object",
                    "description": "AiiDA scheduler/resource options for FLEUR runs.",
                    "default": {},
                },
                "workflow_parameters": {
                    "type": "object",
                    "description": "Top-level wf_parameters for the selected workflow.",
                    "default": {},
                },
                "calc_parameters": {
                    "type": "object",
                    "description": "Inpgen/calc_parameters for direct structure-based workflows.",
                    "default": {},
                },
                "scf_workflow_parameters": {
                    "type": "object",
                    "description": "wf_parameters for nested SCF workflows.",
                    "default": {},
                },
                "final_scf_workflow_parameters": {
                    "type": "object",
                    "description": "wf_parameters for the final_scf namespace in relax workflows.",
                    "default": {},
                },
                "magnetism": {
                    "type": "object",
                    "description": "Basic magnetic setup helper. Adds common inpxml_changes for collinear/noncollinear/spin-spiral setups.",
                    "default": {},
                },
                "plot_results": {
                    "type": "boolean",
                    "default": False,
                    "description": "If true, the generated script will call plot_fleur when possible.",
                },
            },
            "required": ["workflow", "material"],
        }

    def _workflow_explanation_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "workflow": {
                    "type": "string",
                    "enum": sorted(WORKFLOW_SPECS.keys()),
                    "description": "Workflow to explain.",
                },
            },
            "required": ["workflow"],
        }

    def _plot_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "node_identifiers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of PKs or UUIDs to plot with plot_fleur.",
                },
                "output_dir": {
                    "type": "string",
                    "default": ".",
                },
                "script_filename": {
                    "type": "string",
                    "default": "plot_fleur_results.py",
                },
            },
            "required": ["node_identifiers"],
        }

    def _execute_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "script_path": {
                    "type": "string",
                    "description": "Path to a generated aiida-fleur Python script.",
                },
                "verdi_command": {
                    "type": "string",
                    "default": "verdi",
                    "description": "Command used to run the local AiiDA CLI.",
                },
            },
            "required": ["script_path"],
        }

    def _process_list_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "verdi_command": {
                    "type": "string",
                    "default": "verdi",
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                },
                "all_entries": {
                    "type": "boolean",
                    "default": True,
                },
                "process_label": {
                    "type": "string",
                    "description": "Optional process label filter.",
                },
            },
            "required": [],
        }

    def _process_status_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "identifier": {
                    "type": "string",
                    "description": "Process PK or UUID.",
                },
                "verdi_command": {
                    "type": "string",
                    "default": "verdi",
                },
                "include_report": {
                    "type": "boolean",
                    "default": True,
                },
                "max_report_lines": {
                    "type": "integer",
                    "default": 40,
                },
            },
            "required": ["identifier"],
        }

    def _output_inspection_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "identifier": {
                    "type": "string",
                    "description": "Process PK or UUID.",
                },
                "verdi_command": {
                    "type": "string",
                    "default": "verdi",
                },
                "include_extras": {
                    "type": "boolean",
                    "default": False,
                },
                "include_attributes": {
                    "type": "boolean",
                    "default": True,
                },
            },
            "required": ["identifier"],
        }

    def _setup_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "computer_label": {
                    "type": "string",
                    "description": "AiiDA label for the remote computer.",
                },
                "system_preset": {
                    "type": "string",
                    "enum": sorted(SYSTEM_PRESETS.keys()),
                    "description": "Optional named supercomputer preset. Fills in hostname, scheduler and transport defaults and adds system-specific setup steps.",
                },
                "hostname": {
                    "type": "string",
                    "description": "SSH hostname of the supercomputer login node.",
                },
                "scheduler": {
                    "type": "string",
                    "enum": ["slurm", "pbspro", "torque", "sge", "lsf", "direct", "core.slurm", "core.pbspro", "core.torque", "core.sge", "core.lsf", "core.direct"],
                    "default": "slurm",
                    "description": "Scheduler type used on the remote computer.",
                },
                "transport": {
                    "type": "string",
                    "enum": ["ssh", "local", "core.ssh", "core.ssh_async", "core.local"],
                    "default": "ssh",
                    "description": "AiiDA transport type.",
                },
                "work_dir": {
                    "type": "string",
                    "default": "/scratch/{username}/aiida_run/",
                    "description": "Remote work directory for AiiDA calculations.",
                },
                "mpirun_command": {
                    "type": "string",
                    "default": "srun -n {tot_num_mpiprocs}",
                    "description": "MPI launcher command for the remote scheduler.",
                },
                "default_memory_per_machine_mb": {
                    "type": "integer",
                    "default": 0,
                    "description": "Optional default memory per machine in MB. Use 0 to omit.",
                },
                "prepend_text": {
                    "type": "string",
                    "default": "",
                    "description": "Module loads or environment setup inserted into the AiiDA computer prepend text.",
                },
                "append_text": {
                    "type": "string",
                    "default": "",
                    "description": "Optional cleanup/postamble text for the AiiDA computer.",
                },
                "description": {
                    "type": "string",
                    "default": "Remote machine for aiida-fleur calculations",
                    "description": "Human-readable description for the AiiDA computer.",
                },
                "use_double_quotes": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether verdi should escape values using double quotes.",
                },
                "ssh_username": {
                    "type": "string",
                    "description": "SSH username for `verdi computer configure` examples.",
                },
                "ssh_port": {
                    "type": "integer",
                    "default": 22,
                    "description": "SSH port for the configure command.",
                },
                "ssh_proxy_jump": {
                    "type": "string",
                    "description": "Optional SSH proxy jump host.",
                },
                "safe_interval": {
                    "type": "integer",
                    "default": 30,
                    "description": "AiiDA safe interval in seconds.",
                },
                "inpgen_code_label": {
                    "type": "string",
                    "default": "inpgen",
                    "description": "Label for the registered inpgen code.",
                },
                "fleur_code_label": {
                    "type": "string",
                    "default": "fleur",
                    "description": "Label for the registered fleur code.",
                },
                "inpgen_executable_path": {
                    "type": "string",
                    "description": "Absolute path to the inpgen executable on the remote computer.",
                },
                "fleur_executable_path": {
                    "type": "string",
                    "description": "Absolute path to the fleur executable on the remote computer.",
                },
                "code_description": {
                    "type": "string",
                    "default": "FLEUR executable registered for aiida-fleur",
                    "description": "Description shared by the generated code commands.",
                },
                "input_plugin_inpgen": {
                    "type": "string",
                    "default": "fleur.inpgen",
                    "description": "Input plugin name for inpgen code registration.",
                },
                "input_plugin_fleur": {
                    "type": "string",
                    "default": "fleur.fleur",
                    "description": "Input plugin name for fleur code registration.",
                },
                "output_dir": {
                    "type": "string",
                    "default": ".",
                    "description": "Directory where the setup guide should be written.",
                },
                "filename": {
                    "type": "string",
                    "default": "aiida_fleur_setup_guide.md",
                    "description": "File name for the generated setup guide.",
                },
                "project_path": {
                    "type": "string",
                    "description": "Optional filesystem path or project directory on the supercomputer used in examples for work and code locations.",
                },
                "fleur_module_hint": {
                    "type": "string",
                    "default": "fleur",
                    "description": "Module name hint used in the guide when searching for FLEUR-related modules.",
                },
                "verdi_command": {
                    "type": "string",
                    "default": "verdi",
                    "description": "Command used to run the local AiiDA CLI.",
                },
                "apply": {
                    "type": "boolean",
                    "default": False,
                    "description": "If true, actually run the verdi setup commands locally.",
                },
                "replace_existing": {
                    "type": "boolean",
                    "default": False,
                    "description": "If true, delete and recreate existing computer/code entries with the same labels.",
                },
                "test_computer": {
                    "type": "boolean",
                    "default": True,
                    "description": "Run `verdi computer test` after setup.",
                },
                "test_codes": {
                    "type": "boolean",
                    "default": True,
                    "description": "Run `verdi code test` for the created codes when possible.",
                },
            },
            "required": [],
        }

    @staticmethod
    def _as_pretty_python(value: Any) -> str:
        return pformat(value, sort_dicts=False, width=100)

    @staticmethod
    def _merge_dicts(base: dict[str, Any], override: dict[str, Any] | None) -> dict[str, Any]:
        merged = dict(base)
        if override:
            merged.update(override)
        return merged

    @staticmethod
    def _script_name(material: str, workflow: str, script_filename: str | None) -> str:
        if script_filename:
            return script_filename
        clean_material = material.replace(" ", "_").replace("/", "_")
        return f"{workflow}_{clean_material}.py"

    @staticmethod
    def _shell_quote(value: str) -> str:
        return json.dumps(value) if "\n" in value else repr(value)

    @staticmethod
    def _normalize_transport(value: str) -> str:
        try:
            return TRANSPORT_MAP[value]
        except KeyError as exc:
            raise ValueError(f"Unsupported transport: {value}") from exc

    @staticmethod
    def _normalize_scheduler(value: str) -> str:
        try:
            return SCHEDULER_MAP[value]
        except KeyError as exc:
            raise ValueError(f"Unsupported scheduler: {value}") from exc

    def _missing_setup_fields(self, arguments: dict[str, Any]) -> list[str]:
        if arguments.get("system_preset") and not arguments.get("computer_label"):
            required = ["computer_label"]
        else:
            required = [
                "computer_label",
                "hostname",
                "inpgen_executable_path",
                "fleur_executable_path",
            ]
        transport = arguments.get("transport", "ssh")
        preset_name = arguments.get("system_preset")
        if preset_name and preset_name in SYSTEM_PRESETS:
            preset = SYSTEM_PRESETS[preset_name]
            if not arguments.get("hostname"):
                arguments["hostname"] = preset["hostname"]
            if not arguments.get("transport"):
                arguments["transport"] = preset["transport"]
            transport = arguments.get("transport", preset["transport"])
        normalized_transport = TRANSPORT_MAP.get(transport, transport)
        if normalized_transport == "core.ssh_async" and not arguments.get("ssh_username"):
            required.append("ssh_username")
        return [field for field in required if not arguments.get(field)]

    def _apply_system_preset(self, arguments: dict[str, Any]) -> dict[str, Any]:
        preset_name = arguments.get("system_preset")
        if not preset_name:
            return arguments
        preset = SYSTEM_PRESETS.get(preset_name)
        if not preset:
            raise ValueError(f"Unknown system preset: {preset_name}")

        merged = dict(arguments)
        if not merged.get("hostname"):
            merged["hostname"] = preset["hostname"]
        if not merged.get("scheduler"):
            merged["scheduler"] = preset["scheduler"]
        if not merged.get("transport"):
            merged["transport"] = preset["transport"]
        if not merged.get("computer_label"):
            merged["computer_label"] = preset["label_suffix"]
        return merged

    @staticmethod
    def _yaml_literal(key: str, value: str) -> str:
        if "\n" in value:
            indented = "\n".join(f"  {line}" for line in value.splitlines())
            return f"{key}: |\n{indented}\n"
        return f"{key}: {json.dumps(value)}\n"

    def _build_computer_config_yaml(
        self,
        computer_label: str,
        hostname: str,
        transport: str,
        scheduler: str,
        work_dir: str,
        mpirun_command: str,
        default_memory_per_machine_mb: int,
        prepend_text: str,
        append_text: str,
        description: str,
    ) -> str:
        text = ""
        text += self._yaml_literal("label", computer_label)
        text += self._yaml_literal("hostname", hostname)
        text += self._yaml_literal("description", description)
        text += self._yaml_literal("transport", self._normalize_transport(transport))
        text += self._yaml_literal("scheduler", self._normalize_scheduler(scheduler))
        text += self._yaml_literal("work_dir", work_dir)
        text += self._yaml_literal("mpirun_command", mpirun_command)
        if default_memory_per_machine_mb > 0:
            text += f"default_memory_per_machine: {default_memory_per_machine_mb}\n"
        text += self._yaml_literal("prepend_text", prepend_text)
        text += self._yaml_literal("append_text", append_text)
        return text

    def _build_code_config_yaml(
        self,
        label: str,
        description: str,
        default_calc_job_plugin: str,
        filepath_executable: str,
        computer_label: str,
        with_mpi: bool | None,
    ) -> str:
        text = ""
        text += self._yaml_literal("label", label)
        text += self._yaml_literal("description", description)
        text += self._yaml_literal("default_calc_job_plugin", default_calc_job_plugin)
        text += self._yaml_literal("filepath_executable", filepath_executable)
        text += self._yaml_literal("computer", computer_label)
        if with_mpi is True:
            text += "with_mpi: true\n"
        elif with_mpi is False:
            text += "with_mpi: false\n"
        return text

    def _run_local_command(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(command, capture_output=True, text=True)

    def _object_exists(self, verdi_command: str, kind: str, label: str) -> bool:
        result = self._run_local_command([verdi_command, kind, "show", label])
        return result.returncode == 0

    def _delete_existing_object(self, verdi_command: str, kind: str, label: str) -> subprocess.CompletedProcess[str]:
        if kind == "computer":
            return self._run_local_command([verdi_command, "computer", "delete", "--force", label])
        if kind == "code":
            return self._run_local_command([verdi_command, "code", "delete", "--force", label])
        raise ValueError(f"Unsupported object kind: {kind}")

    def _build_setup_guide(
        self,
        system_preset: str | None,
        computer_label: str,
        hostname: str,
        scheduler: str,
        transport: str,
        work_dir: str,
        mpirun_command: str,
        default_memory_per_machine_mb: int,
        prepend_text: str,
        append_text: str,
        description: str,
        use_double_quotes: bool,
        ssh_username: str | None,
        ssh_port: int,
        ssh_proxy_jump: str | None,
        safe_interval: int,
        inpgen_code_label: str,
        fleur_code_label: str,
        inpgen_executable_path: str,
        fleur_executable_path: str,
        code_description: str,
        input_plugin_inpgen: str,
        input_plugin_fleur: str,
        project_path: str | None,
        fleur_module_hint: str,
    ) -> str:
        normalized_transport = self._normalize_transport(transport)
        normalized_scheduler = self._normalize_scheduler(scheduler)
        preset = SYSTEM_PRESETS.get(system_preset) if system_preset else None
        quote_option = "--use-double-quotes" if use_double_quotes else ""
        command_memory_line = (
            f"  --default-memory-per-machine {default_memory_per_machine_mb} \\\n"
            if default_memory_per_machine_mb > 0
            else ""
        )
        prepend_arg = self._shell_quote(prepend_text) if prepend_text else "''"
        append_arg = self._shell_quote(append_text) if append_text else "''"
        configure_bits = [
            f"verdi computer configure {normalized_transport}",
            "  --non-interactive",
            f"  --safe-interval {safe_interval}",
        ]
        if ssh_username:
            configure_bits.append(f"  --username {ssh_username}")
        if ssh_port:
            configure_bits.append(f"  --port {ssh_port}")
        if ssh_proxy_jump:
            configure_bits.append(f"  --proxy-jump {ssh_proxy_jump}")
        configure_bits.append(f"  {computer_label}")
        configure_command = " \\\n".join(configure_bits)
        project_path_display = project_path or "<your_project_path>"
        remote_code_dir = f"{project_path_display.rstrip('/')}/codes/fleur"
        preset_section = ""
        if preset:
            docs_lines = []
            for key, value in preset["docs"].items():
                docs_lines.append(f"- {key}: {value}")
            computer_example_section = ""
            if preset.get("computer_example"):
                example = preset["computer_example"]
                example_memory = example.get("default_memory_kb_per_machine", "")
                computer_example_section = f"""
### 0.6 Example target computer profile

This is the kind of AiiDA computer profile you want to reach in the end:

```text
verdi computer show {example["label"]}
---------------------------  ------------------------------------
Label                        {example["label"]}
Description                  {example["description"]}
Hostname                     {preset["hostname"]}
Transport type               {normalized_transport}
Scheduler type               {normalized_scheduler}
Work directory               {example["work_dir"]}
Shebang                      #!/bin/bash
Mpirun command               {example["mpirun_command"]}
Default #procs/machine       {example["default_procs_per_machine"]}
Default memory (kB)/machine  {example_memory}
Prepend text                 {example["prepend_text"]}
Append text
---------------------------  ------------------------------------
```
"""
            code_examples_section = ""
            if preset.get("code_examples"):
                code_blocks: list[str] = []
                for code_example in preset["code_examples"]:
                    with_mpi_text = "True" if code_example["with_mpi"] else "False"
                    code_blocks.append(
                        f"""#### {code_example["title"]}

```text
Label                    {code_example["label"]}
Default calc job plugin  {code_example["plugin"]}
Description              {code_example["description"]}
With mpi                 {with_mpi_text}
Prepend text             {code_example["prepend_text"]}
Filepath executable      {code_example["filepath_executable"]}
```
"""
                    )
                code_examples_section = (
                    "\n### 0.7 Example code profiles\n\n"
                    "Below are generalized examples of the code entries the user should create:\n\n"
                    + "\n".join(code_blocks)
                )
            preset_section = f"""
## 0. System-specific steps for `{system_preset}`

- Recommended login host: `{preset["hostname"]}`
- SSH example: `{preset["login_example"]}`
- Note: {preset["system_note"]}
- Module note: {preset["module_note"]}

Official documentation:
{chr(10).join(docs_lines)}

### 0.1 Prepare SSH access

1. Generate or select an SSH key on your local machine.
2. Upload the public key in JuDoor for `{system_preset}`.
3. If your site policy requires source restrictions or MFA/TOTP, complete those steps in JuDoor before continuing.
4. Test the login manually:

```bash
{preset["login_example"]}
```

### 0.2 Inspect the software environment on the supercomputer

After login, inspect the module hierarchy and search for FLEUR:

```bash
module avail
module spider {fleur_module_hint}
module keyword {fleur_module_hint}
```

Then load the relevant compiler/MPI stack and the FLEUR module if available:

```bash
module load Stages
module load GCC
module load ParaStationMPI
module load {fleur_module_hint}
```

If FLEUR is not installed as a module, use your own build and record the executable paths, for example under:

```bash
mkdir -p {remote_code_dir}
```

### 0.3 Record the executable paths for AiiDA

Locate the executables you want AiiDA to register:

```bash
which inpgen
which fleur_MPI
which fleur
```

Use the resulting absolute paths as `inpgen_executable_path` and `fleur_executable_path`.

### 0.4 Choose a stable AiiDA work directory

Pick a project-backed directory instead of a temporary location. Good patterns are:

```bash
# JURECA-style
/p/project1/<project>/<user>/aiida

# JUPITER-style
/e/project1/<project>/<user>/aiida
```

### 0.5 Decide how you will provide FLEUR

You have two common choices:

1. Use a centrally installed module if available.
2. Use your own build, for example via Spack, and point AiiDA to the absolute
   executable path.

If you use Spack, verify the environment before registering the codes:

```bash
source <spack_root>/share/spack/setup-env.sh
spack env activate <your_fleur_env>
spack load fleur
which inpgen
which fleur_MPI
```
{computer_example_section}
{code_examples_section}
"""

        return f"""# AiiDA FLEUR Supercomputer Setup Guide

This guide configures an AiiDA computer and registers `inpgen` and `fleur`
codes for `aiida-fleur`.

{preset_section}

## 1. Prerequisites

- AiiDA profile already created locally
- passwordless SSH access to `{hostname}`
- working remote executables:
  - `inpgen`: `{inpgen_executable_path or '<discover with which inpgen>'}`
  - `fleur`: `{fleur_executable_path or '<discover with which fleur_MPI>'}`

## 2. Create the AiiDA computer

```bash
verdi computer setup {quote_option} \\
  --non-interactive \\
  --label {computer_label} \\
  --hostname {hostname} \\
  --description {self._shell_quote(description)} \\
  --transport {normalized_transport} \\
  --scheduler {normalized_scheduler} \\
  --work-dir {self._shell_quote(work_dir)} \\
  --mpirun-command {self._shell_quote(mpirun_command)} \\
{command_memory_line}  --prepend-text {prepend_arg} \\
  --append-text {append_arg}
```

## 3. Configure SSH access in AiiDA

```bash
{configure_command}
```

## 4. Test the computer

```bash
verdi computer test {computer_label}
```

## 5. Register the inpgen code

```bash
verdi code create core.code.installed {quote_option} \\
  --non-interactive \\
  --label {inpgen_code_label}@{computer_label} \\
  --computer {computer_label} \\
  --filepath-executable {inpgen_executable_path or '<absolute_path_to_inpgen>'} \\
  --default-calc-job-plugin {input_plugin_inpgen} \\
  --no-with-mpi \\
  --description {self._shell_quote(code_description)}
```

## 6. Register the fleur code

```bash
verdi code create core.code.installed {quote_option} \\
  --non-interactive \\
  --label {fleur_code_label}@{computer_label} \\
  --computer {computer_label} \\
  --filepath-executable {fleur_executable_path or '<absolute_path_to_fleur_or_fleur_MPI>'} \\
  --default-calc-job-plugin {input_plugin_fleur} \\
  --with-mpi \\
  --description {self._shell_quote(code_description)}
```

## 7. Test that the codes are visible

```bash
verdi code list
verdi code show {inpgen_code_label}@{computer_label}
verdi code show {fleur_code_label}@{computer_label}
```

## 8. Recommended next checks

```bash
verdi status
verdi computer show {computer_label}
verdi computer test {computer_label}
```

## 9. Example prepend text

Use this if your supercomputer needs module loads or environment activation:

```bash
module purge
module load fleur
module load mpi
export OMP_NUM_THREADS=1
```
"""

    def _build_workflow_script(
        self,
        workflow: str,
        material: str,
        structure_file: str | None,
        inpgen_code: str,
        fleur_code: str,
        submit_mode: str,
        options: dict[str, Any],
        workflow_parameters: dict[str, Any],
        calc_parameters: dict[str, Any],
        scf_workflow_parameters: dict[str, Any],
        final_scf_workflow_parameters: dict[str, Any],
        magnetism: dict[str, Any],
        plot_results: bool,
    ) -> str:
        spec = WORKFLOW_SPECS[workflow]
        top_wf = self._merge_dicts(spec.get("default_wf_parameters", {}), workflow_parameters)
        top_options = self._merge_dicts(DEFAULT_OPTIONS, options)

        config = {
            "material": material,
            "workflow": workflow,
            "entrypoint": spec["entrypoint"],
            "pattern": spec["pattern"],
            "structure_file": str(Path(structure_file).expanduser().resolve()) if structure_file else None,
            "inpgen_code": inpgen_code,
            "fleur_code": fleur_code,
            "submit_mode": submit_mode,
            "plot_results": plot_results,
            "options": top_options,
            "workflow_parameters": top_wf,
            "calc_parameters": calc_parameters or {},
            "scf_workflow_parameters": scf_workflow_parameters or {},
            "final_scf_workflow_parameters": final_scf_workflow_parameters or {},
            "magnetism": magnetism or {},
        }

        config_block = self._as_pretty_python(config)
        workflow_link = WORKFLOW_DOC_LINKS[workflow]

        return f'''#!/usr/bin/env python3
"""
Generated aiida-fleur workflow script for {material}.

Workflow: {workflow}
Entrypoint: {spec["entrypoint"]}
Docs: {workflow_link}
"""

from pprint import pprint

from aiida import load_profile, orm
from aiida.engine import run_get_node, submit
from aiida.plugins import WorkflowFactory
from ase.io import read

from aiida_fleur.data import inpxml_changes
from aiida_fleur.tools.plot import plot_fleur


# This block is the main user-editable configuration.
# Change workflow parameters, scheduler options, code labels, and magnetic
# settings here before submission.
CONFIG = {config_block}


def make_structure_node():
    """Load the structure file and convert it into an AiiDA StructureData node."""
    structure_path = CONFIG.get("structure_file")
    if not structure_path:
        return None
    atoms = read(structure_path)
    magnetic_moments = CONFIG["magnetism"].get("initial_moments")
    if magnetic_moments:
        atoms.set_initial_magnetic_moments(magnetic_moments)
    return orm.StructureData(ase=atoms)


def maybe_dict_node(data):
    """Wrap plain dictionaries as AiiDA Dict nodes only when needed."""
    return orm.Dict(dict=data) if data else None


def build_common_options():
    """Build the scheduler/resource options block used by FLEUR runs."""
    return orm.Dict(dict=CONFIG["options"])


def apply_basic_magnetism(wf_parameters):
    """Inject simple magnetic and SOC related inp.xml changes into wf_parameters."""
    magnetism = CONFIG.get("magnetism", {{}})
    if not magnetism:
        return wf_parameters

    mode = magnetism.get("mode", "none")
    extra_changes = magnetism.get("inpxml_changes", [])

    with inpxml_changes(wf_parameters) as fm:
        if mode in ("collinear", "noncollinear", "spin_spiral"):
            fm.set_inpchanges({{"jspins": 2}})
        if mode == "collinear":
            fm.set_inpchanges({{"l_noco": False}})
        elif mode == "noncollinear":
            fm.set_inpchanges({{"l_noco": True}})
        elif mode == "spin_spiral":
            fm.set_inpchanges({{"l_noco": True, "l_ss": True}})
            qss = magnetism.get("qss")
            if qss:
                fm.set_inpchanges({{"qss": " ".join(str(value) for value in qss)}})

        if magnetism.get("soc") is True:
            fm.set_inpchanges({{"l_soc": True}})
        elif magnetism.get("soc") is False:
            fm.set_inpchanges({{"l_soc": False}})

        for change in extra_changes:
            if isinstance(change, (list, tuple)) and len(change) == 2:
                method_name, kwargs = change
                getattr(fm, method_name)(**kwargs)

    return wf_parameters


def build_scf_namespace(include_structure):
    """Create the SCF namespace used by nested workflows such as EOS or relax."""
    namespace = {{}}
    if include_structure:
        structure = make_structure_node()
        if structure is not None:
            namespace["structure"] = structure

    namespace["inpgen"] = orm.load_code(CONFIG["inpgen_code"])
    namespace["fleur"] = orm.load_code(CONFIG["fleur_code"])

    calc_parameters = maybe_dict_node(CONFIG["calc_parameters"])
    if calc_parameters is not None:
        namespace["calc_parameters"] = calc_parameters

    wf_parameters = CONFIG.get("scf_workflow_parameters", {{}})
    if wf_parameters:
        wf_parameters = apply_basic_magnetism(dict(wf_parameters))
        namespace["wf_parameters"] = orm.Dict(dict=wf_parameters)

    namespace["options"] = build_common_options()
    return namespace


def build_direct_builder():
    """Build workflows that accept structure/inpgen/fleur directly at top level."""
    WorkChain = WorkflowFactory(CONFIG["entrypoint"])
    builder = WorkChain.get_builder()

    structure = make_structure_node()
    if structure is not None:
        builder.structure = structure

    builder.inpgen = orm.load_code(CONFIG["inpgen_code"])
    builder.fleur = orm.load_code(CONFIG["fleur_code"])
    builder.options = build_common_options()

    calc_parameters = maybe_dict_node(CONFIG["calc_parameters"])
    if calc_parameters is not None:
        builder.calc_parameters = calc_parameters

    wf_parameters = dict(CONFIG.get("workflow_parameters", {{}}))
    if wf_parameters or CONFIG.get("magnetism"):
        wf_parameters = apply_basic_magnetism(wf_parameters)
        builder.wf_parameters = orm.Dict(dict=wf_parameters)

    return builder


def build_nested_scf_builder():
    """Build workflows that contain a nested SCF namespace."""
    WorkChain = WorkflowFactory(CONFIG["entrypoint"])
    builder = WorkChain.get_builder()

    structure = make_structure_node()
    if structure is not None:
        builder.structure = structure

    wf_parameters = dict(CONFIG.get("workflow_parameters", {{}}))
    if wf_parameters or CONFIG.get("magnetism"):
        wf_parameters = apply_basic_magnetism(wf_parameters)
        builder.wf_parameters = orm.Dict(dict=wf_parameters)

    builder.scf = build_scf_namespace(include_structure=False)
    return builder


def build_nested_scf_with_final_builder():
    """Build workflows such as relax that use SCF and optional final SCF steps."""
    WorkChain = WorkflowFactory(CONFIG["entrypoint"])
    builder = WorkChain.get_builder()
    builder.scf = build_scf_namespace(include_structure=True)

    wf_parameters = dict(CONFIG.get("workflow_parameters", {{}}))
    if wf_parameters or CONFIG.get("magnetism"):
        wf_parameters = apply_basic_magnetism(wf_parameters)
        builder.wf_parameters = orm.Dict(dict=wf_parameters)

    final_scf = CONFIG.get("final_scf_workflow_parameters", {{}})
    if final_scf:
        builder.final_scf = {{"wf_parameters": orm.Dict(dict=final_scf)}}

    return builder


def build_banddos_like_builder():
    """Build post-SCF workflows such as band, DOS, MAE, DMI, or SSDisp."""
    WorkChain = WorkflowFactory(CONFIG["entrypoint"])
    builder = WorkChain.get_builder()
    builder.fleur = orm.load_code(CONFIG["fleur_code"])
    builder.options = build_common_options()

    wf_parameters = dict(CONFIG.get("workflow_parameters", {{}}))
    if wf_parameters or CONFIG.get("magnetism"):
        wf_parameters = apply_basic_magnetism(wf_parameters)
        builder.wf_parameters = orm.Dict(dict=wf_parameters)

    if CONFIG.get("structure_file"):
        builder.scf = build_scf_namespace(include_structure=True)
    return builder


def build_create_magnetic_builder():
    """Build the magnetic-film preparation workflow and its nested namespaces."""
    WorkChain = WorkflowFactory(CONFIG["entrypoint"])
    builder = WorkChain.get_builder()

    wf_parameters = dict(CONFIG.get("workflow_parameters", {{}}))
    if wf_parameters:
        builder.wf_parameters = orm.Dict(dict=wf_parameters)

    # This workflow is film-specific and nests EOS and Relax workflows.
    # Edit the dictionaries below for your substrate/film problem.
    eos_scf = build_scf_namespace(include_structure=False)
    relax_scf = build_scf_namespace(include_structure=False)

    builder.eos = {{
        "wf_parameters": orm.Dict(dict=CONFIG.get("workflow_parameters", {{}})),
        "scf": eos_scf,
    }}
    builder.relax = {{
        "wf_parameters": orm.Dict(dict=CONFIG.get("workflow_parameters", {{}})),
        "scf": relax_scf,
    }}
    return builder


def build_builder():
    """Dispatch to the correct builder layout for the selected workflow."""
    pattern = CONFIG["pattern"]
    if pattern == "direct":
        return build_direct_builder()
    if pattern == "nested_scf":
        return build_nested_scf_builder()
    if pattern == "nested_scf_with_final":
        return build_nested_scf_with_final_builder()
    if pattern == "banddos_like":
        return build_banddos_like_builder()
    if pattern == "create_magnetic":
        return build_create_magnetic_builder()
    raise ValueError(f"Unsupported builder pattern: {{pattern}}")


def main():
    # 1. Load the local AiiDA profile so `orm.load_code`, `submit`, and
    # `run_get_node` work against the configured database.
    load_profile()

    # 2. Build the exact AiiDA builder for the selected aiida-fleur workflow.
    builder = build_builder()

    # 3. Print the final configuration so the user can verify all settings
    # before or after submission.
    print(f"Launching {{CONFIG['workflow']}} workflow for {{CONFIG['material']}}")
    pprint(CONFIG)

    if CONFIG["submit_mode"] == "run_get_node":
        # 4a. `run_get_node` blocks until the workflow finishes and is useful
        # for small tests or interactive debugging.
        results, node = run_get_node(builder)
        print(f"Finished with PK: {{node.pk}}")
        print(f"State: {{node.process_state}}")
        if CONFIG.get("plot_results"):
            plot_fleur(node)
        return results, node

    # 4b. `submit` sends the workflow to the AiiDA daemon and returns
    # immediately. This is the usual submission mode on clusters.
    node = submit(builder)
    print(f"Submitted PK: {{node.pk}}")
    print("Monitor with: verdi process show", node.pk)
    print("Plot later with: aiida-fleur plot", node.pk)
    return node


if __name__ == "__main__":
    main()
'''

    def _build_plot_script(self, node_identifiers: list[str]) -> str:
        pretty_nodes = self._as_pretty_python(node_identifiers)
        return f'''#!/usr/bin/env python3
"""
Plot aiida-fleur results using plot_fleur.
"""

from aiida import load_profile
from aiida.orm import load_node
from aiida_fleur.tools.plot import plot_fleur


NODE_IDENTIFIERS = {pretty_nodes}


def main():
    load_profile()
    nodes = []
    for identifier in NODE_IDENTIFIERS:
        try:
            identifier = int(identifier)
        except (TypeError, ValueError):
            pass
        nodes.append(load_node(identifier))

    if len(nodes) == 1:
        plot_fleur(nodes[0])
    else:
        plot_fleur(nodes)


if __name__ == "__main__":
    main()
'''

    def _server_functions_text(self) -> str:
        workflow_names = ", ".join(sorted(WORKFLOW_SPECS.keys()))
        return (
            "Functions of this server:\n\n"
            "- Setup of supercomputers and AiiDA codes.\n"
            "- System-specific setup steps for named machines such as JURECA, JUWELS Cluster, JUWELS Booster, and JUPITER.\n"
            "- Interactive setup support: if required setup information is missing, the server asks for the missing fields.\n"
            "- Local AiiDA setup execution: create/configure/test computers and register `inpgen` and `fleur` codes with `verdi`.\n"
            "- Generation of setup documentation files in the workspace.\n"
            f"- Generation of workflow input scripts for aiida-fleur workflows: {workflow_names}.\n"
            "- List of supported workflows with their AiiDA entry points and documentation links.\n"
            "- Basic magnetic workflow helpers for collinear, noncollinear, and spin-spiral setups.\n"
            "- Execution of generated aiida-fleur workflow scripts with `verdi run`.\n"
            "- Listing and monitoring of AiiDA processes.\n"
            "- Inspection and summary of process outputs, output nodes, and workflow status.\n"
            "- Generation of plotting scripts for aiida-fleur results using `plot_fleur`.\n"
            "- Generation of workflow runner scripts in the workspace."
        )

    @staticmethod
    def _server_overview_text() -> str:
        return (
            f"{SERVER_TITLE}\n\n"
            f"Author: {SERVER_AUTHOR}\n"
            f"Version: {SERVER_VERSION}\n\n"
            "This MCP server is organized to help users work with aiida-fleur in a practical way.\n\n"
            "It is mainly for:\n"
            "- learning what each aiida-fleur workflow does\n"
            "- setting up supercomputers, AiiDA computers, and FLEUR codes\n"
            "- generating exact workflow and submission scripts\n"
            "- executing workflows and inspecting outputs\n\n"
            "Suggested order for new users:\n"
            "1. Read the overview and server functions.\n"
            "2. Read the workflow or setup guide.\n"
            "3. Ask for a workflow explanation or setup guide.\n"
            "4. Generate a submission script.\n"
            "5. Run and monitor the calculation.\n\n"
            "Main discovery tools:\n"
            "- `describe_server_functions`\n"
            "- `list_fleur_workflows`\n"
            "- `explain_fleur_workflow`\n"
            "- `generate_aiida_setup_guide`\n"
            "- `generate_fleur_submission_script`\n"
            "- `execute_fleur_workflow_script`\n"
            "- `inspect_aiida_outputs`\n"
        )

    @staticmethod
    def _client_usage_policy_text() -> str:
        return (
            "Recommended client usage policy for this MCP server:\n\n"
            "- Use this MCP server as the primary tool for FLEUR setup, workflow explanation, workflow script generation, execution, monitoring, and output inspection.\n"
            "- Ask the user only for information that is strictly required for the selected tool or workflow.\n"
            "- If some required fields are missing, request only those missing fields and nothing extra.\n"
            "- Do not display chain-of-thought or internal reasoning.\n"
            "- Respond with concise, task-focused output: required questions first, final result second.\n"
            "- Prefer returning generated scripts, setup steps, process summaries, and workflow explanations directly from this server instead of broad general discussion.\n"
            "- When the server already provides an explanation or summary tool, use that tool instead of composing a longer answer manually.\n"
            "- When the user asks for a submission script, prefer the annotated submission script function so the result includes notes for each important block.\n\n"
            "Important note:\n"
            "- This policy is a recommendation for the MCP client or assistant prompt. The MCP server can provide it, but cannot by itself force the client to hide reasoning or forbid other tools."
        )

    def _workflow_explanation_text(self, workflow: str) -> str:
        spec = WORKFLOW_SPECS[workflow]
        teaching = WORKFLOW_TEACHING[workflow]
        main_inputs = "\n".join(f"- {item}" for item in teaching["main_inputs"])
        main_outputs = "\n".join(f"- {item}" for item in teaching["main_outputs"])
        return (
            f"Workflow: {workflow}\n\n"
            f"Entry point: `{spec['entrypoint']}`\n"
            f"Pattern: `{spec['pattern']}`\n"
            f"Documentation: {WORKFLOW_DOC_LINKS[workflow]}\n\n"
            f"What it does:\n{teaching['what']}\n\n"
            f"When to use it:\n{teaching['when']}\n\n"
            f"How it works:\n{teaching['how']}\n\n"
            f"Main inputs:\n{main_inputs}\n\n"
            f"Main outputs:\n{main_outputs}"
        )

    @staticmethod
    def _truncate_lines(text: str, max_lines: int) -> str:
        lines = text.splitlines()
        if len(lines) <= max_lines:
            return text
        return "\n".join(lines[:max_lines] + [f"... ({len(lines) - max_lines} more lines)"])

    @staticmethod
    def _extract_process_pk(text: str) -> str | None:
        for line in text.splitlines():
            if "PK:" in line or "pk:" in line:
                for token in line.replace(":", " ").split():
                    if token.isdigit():
                        return token
        return None

    def _run_verdi_script(
        self,
        verdi_command: str,
        script_text: str,
        args: list[str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory(prefix="aiida-fleur-run-") as tmpdir:
            script_path = Path(tmpdir) / "verdi_helper.py"
            script_path.write_text(script_text, encoding="utf-8")
            command = [verdi_command, "run", str(script_path)]
            if args:
                command.extend(args)
            return self._run_local_command(command)

    def _apply_aiida_setup(
        self,
        verdi_command: str,
        computer_label: str,
        hostname: str,
        scheduler: str,
        transport: str,
        work_dir: str,
        mpirun_command: str,
        default_memory_per_machine_mb: int,
        prepend_text: str,
        append_text: str,
        description: str,
        ssh_username: str | None,
        ssh_port: int,
        ssh_proxy_jump: str | None,
        safe_interval: int,
        inpgen_code_label: str,
        fleur_code_label: str,
        inpgen_executable_path: str,
        fleur_executable_path: str,
        code_description: str,
        input_plugin_inpgen: str,
        input_plugin_fleur: str,
        replace_existing: bool,
        test_computer: bool,
        test_codes: bool,
    ) -> dict[str, Any]:
        normalized_transport = self._normalize_transport(transport)
        normalized_scheduler = self._normalize_scheduler(scheduler)
        inpgen_full_label = f"{inpgen_code_label}@{computer_label}"
        fleur_full_label = f"{fleur_code_label}@{computer_label}"

        logs: list[dict[str, Any]] = []

        def run_and_record(command: list[str], label: str) -> subprocess.CompletedProcess[str]:
            result = self._run_local_command(command)
            logs.append(
                {
                    "step": label,
                    "command": command,
                    "returncode": result.returncode,
                    "stdout": result.stdout.strip(),
                    "stderr": result.stderr.strip(),
                }
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"{label} failed with exit code {result.returncode}\n"
                    f"stdout:\n{result.stdout}\n"
                    f"stderr:\n{result.stderr}"
                )
            return result

        if self._object_exists(verdi_command, "computer", computer_label):
            if replace_existing:
                run_and_record(
                    [verdi_command, "computer", "delete", "--dry-run", computer_label],
                    "preview delete existing computer",
                )
                run_and_record(
                    [verdi_command, "computer", "delete", "--force", computer_label],
                    "delete existing computer",
                )
            else:
                raise RuntimeError(
                    f"Computer `{computer_label}` already exists. "
                    "Set `replace_existing=true` to recreate it."
                )

        for code_label in [inpgen_full_label, fleur_full_label]:
            if self._object_exists(verdi_command, "code", code_label):
                if replace_existing:
                    run_and_record(
                        [verdi_command, "code", "delete", "--force", code_label],
                        f"delete existing code {code_label}",
                    )
                else:
                    raise RuntimeError(
                        f"Code `{code_label}` already exists. "
                        "Set `replace_existing=true` to recreate it."
                    )

        computer_config = self._build_computer_config_yaml(
            computer_label=computer_label,
            hostname=hostname,
            transport=normalized_transport,
            scheduler=normalized_scheduler,
            work_dir=work_dir,
            mpirun_command=mpirun_command,
            default_memory_per_machine_mb=default_memory_per_machine_mb,
            prepend_text=prepend_text,
            append_text=append_text,
            description=description,
        )
        inpgen_config = self._build_code_config_yaml(
            label=inpgen_full_label,
            description=code_description,
            default_calc_job_plugin=input_plugin_inpgen,
            filepath_executable=inpgen_executable_path,
            computer_label=computer_label,
            with_mpi=False,
        )
        fleur_config = self._build_code_config_yaml(
            label=fleur_full_label,
            description=code_description,
            default_calc_job_plugin=input_plugin_fleur,
            filepath_executable=fleur_executable_path,
            computer_label=computer_label,
            with_mpi=True,
        )

        with tempfile.TemporaryDirectory(prefix="aiida-fleur-setup-") as tmpdir:
            tmpdir_path = Path(tmpdir)
            computer_config_path = tmpdir_path / "computer.yml"
            inpgen_config_path = tmpdir_path / "inpgen.yml"
            fleur_config_path = tmpdir_path / "fleur.yml"
            computer_config_path.write_text(computer_config, encoding="utf-8")
            inpgen_config_path.write_text(inpgen_config, encoding="utf-8")
            fleur_config_path.write_text(fleur_config, encoding="utf-8")

            run_and_record(
                [
                    verdi_command,
                    "computer",
                    "setup",
                    "--non-interactive",
                    "--config",
                    str(computer_config_path),
                ],
                "create computer",
            )

            configure_command = [
                verdi_command,
                "computer",
                "configure",
                normalized_transport,
                "--non-interactive",
                "--safe-interval",
                str(safe_interval),
            ]
            if normalized_transport == "core.ssh_async":
                if ssh_username:
                    configure_command.extend(["--username", ssh_username])
                if ssh_port:
                    configure_command.extend(["--port", str(ssh_port)])
                if ssh_proxy_jump:
                    configure_command.extend(["--proxy-jump", ssh_proxy_jump])
            configure_command.append(computer_label)
            run_and_record(configure_command, "configure computer transport")

            if test_computer:
                run_and_record(
                    [verdi_command, "computer", "test", computer_label],
                    "test computer",
                )

            run_and_record(
                [
                    verdi_command,
                    "code",
                    "create",
                    "core.code.installed",
                    "--non-interactive",
                    "--config",
                    str(inpgen_config_path),
                ],
                "create inpgen code",
            )
            run_and_record(
                [
                    verdi_command,
                    "code",
                    "create",
                    "core.code.installed",
                    "--non-interactive",
                    "--config",
                    str(fleur_config_path),
                ],
                "create fleur code",
            )

            if test_codes:
                run_and_record(
                    [verdi_command, "code", "test", inpgen_full_label],
                    "test inpgen code",
                )
                run_and_record(
                    [verdi_command, "code", "test", fleur_full_label],
                    "test fleur code",
                )

        return {
            "computer_label": computer_label,
            "hostname": hostname,
            "transport": normalized_transport,
            "scheduler": normalized_scheduler,
            "inpgen_code": inpgen_full_label,
            "fleur_code": fleur_full_label,
            "logs": logs,
        }

    def setup_handlers(self) -> None:
        async def handle_list_resources(
            _context: Any,
            _params: types.PaginatedRequestParams,
        ) -> types.ListResourcesResult:
            return types.ListResourcesResult(
                resources=[
                    types.Resource(
                        uri="fleur://docs/overview",
                        name="FLEUR Server Overview",
                        description="Welcome page with purpose, author, and suggested usage order for the server.",
                        mimeType="text/markdown",
                    ),
                    types.Resource(
                        uri="fleur://docs/workflow_guide",
                        name="FLEUR Workflow Guide",
                        description="Overview of supported aiida-fleur workflows and script generator conventions.",
                        mimeType="text/markdown",
                    ),
                    types.Resource(
                        uri="fleur://docs/setup_guide",
                        name="FLEUR Setup Guide",
                        description="How to configure AiiDA supercomputers and register inpgen/fleur codes.",
                        mimeType="text/markdown",
                    ),
                    types.Resource(
                        uri="fleur://docs/client_policy",
                        name="FLEUR Client Usage Policy",
                        description="Recommended instructions for a client like Claude: use this server first, ask only for required fields, and return concise outputs without showing internal reasoning.",
                        mimeType="text/markdown",
                    ),
                ]
            )

        async def handle_read_resource(
            _context: Any,
            params: types.ReadResourceRequestParams,
        ) -> types.ReadResourceResult:
            if params.uri == "fleur://docs/overview":
                text = self._server_overview_text()
            elif params.uri == "fleur://docs/workflow_guide":
                text = self._load_template("fleur_workflow_server_guide.md")
            elif params.uri == "fleur://docs/setup_guide":
                text = self._load_template("fleur_setup_server_guide.md")
            elif params.uri == "fleur://docs/client_policy":
                text = self._client_usage_policy_text()
            else:
                raise ValueError(f"Unknown resource: {params.uri}")

            return types.ReadResourceResult(
                contents=[
                    types.TextResourceContents(
                        uri=params.uri,
                        mimeType="text/markdown",
                        text=text,
                    )
                ]
            )

        async def handle_list_tools(
            _context: Any,
            _params: types.PaginatedRequestParams,
        ) -> types.ListToolsResult:
            return types.ListToolsResult(
                tools=[
                    types.Tool(
                        name="get_server_overview",
                        description="Return a welcome/overview text with author information and suggested usage order.",
                        inputSchema={"type": "object", "properties": {}, "required": []},
                    ),
                    types.Tool(
                        name="describe_server_functions",
                        description="Return the functions of this server as a bullet list.",
                        inputSchema={"type": "object", "properties": {}, "required": []},
                    ),
                    types.Tool(
                        name="get_client_usage_policy",
                        description="Return recommended client instructions: use this server first, ask only for required fields, and avoid showing internal reasoning.",
                        inputSchema={"type": "object", "properties": {}, "required": []},
                    ),
                    types.Tool(
                        name="list_fleur_workflows",
                        description="List the supported aiida-fleur workflows and their entry points.",
                        inputSchema={"type": "object", "properties": {}, "required": []},
                    ),
                    types.Tool(
                        name="explain_fleur_workflow",
                        description="Explain what a selected aiida-fleur workflow does, when to use it, how it works, and what inputs/outputs to expect.",
                        inputSchema=self._workflow_explanation_schema(),
                    ),
                    types.Tool(
                        name="generate_fleur_workflow_script",
                        description="Generate a runnable annotated Python workflow/submission script for a selected aiida-fleur workflow.",
                        inputSchema=self._workflow_schema(),
                    ),
                    types.Tool(
                        name="generate_fleur_submission_script",
                        description="Generate an exact annotated submission script with notes explaining what each block does.",
                        inputSchema=self._workflow_schema(),
                    ),
                    types.Tool(
                        name="generate_fleur_plot_script",
                        description="Generate a small Python script that plots aiida-fleur results with plot_fleur.",
                        inputSchema=self._plot_schema(),
                    ),
                    types.Tool(
                        name="execute_fleur_workflow_script",
                        description="Run a generated aiida-fleur Python script with `verdi run`.",
                        inputSchema=self._execute_schema(),
                    ),
                    types.Tool(
                        name="list_aiida_processes",
                        description="List recent AiiDA processes, optionally filtered by process label.",
                        inputSchema=self._process_list_schema(),
                    ),
                    types.Tool(
                        name="check_aiida_process",
                        description="Inspect the status and report of an AiiDA process by PK or UUID.",
                        inputSchema=self._process_status_schema(),
                    ),
                    types.Tool(
                        name="inspect_aiida_outputs",
                        description="Load an AiiDA process and summarize its outputs and result nodes.",
                        inputSchema=self._output_inspection_schema(),
                    ),
                    types.Tool(
                        name="generate_aiida_setup_guide",
                        description="Generate a setup procedure for an AiiDA supercomputer and register inpgen/fleur codes.",
                        inputSchema=self._setup_schema(),
                    ),
                    types.Tool(
                        name="setup_aiida_computer_and_codes",
                        description="Ask for missing supercomputer details if needed, then create the AiiDA computer and register the inpgen/fleur codes locally with verdi.",
                        inputSchema=self._setup_schema(),
                    ),
                ]
            )

        async def handle_call_tool(
            _context: Any,
            params: types.CallToolRequestParams,
        ) -> types.CallToolResult:
            arguments = params.arguments or {}

            if params.name == "get_server_overview":
                content = [types.TextContent(type="text", text=self._server_overview_text())]
            elif params.name == "describe_server_functions":
                content = [types.TextContent(type="text", text=self._server_functions_text())]
            elif params.name == "get_client_usage_policy":
                content = [types.TextContent(type="text", text=self._client_usage_policy_text())]
            elif params.name == "list_fleur_workflows":
                content = await self.list_fleur_workflows()
            elif params.name == "explain_fleur_workflow":
                content = await self.explain_fleur_workflow(**arguments)
            elif params.name == "generate_fleur_workflow_script":
                content = await self.generate_fleur_workflow_script(**arguments)
            elif params.name == "generate_fleur_submission_script":
                content = await self.generate_fleur_workflow_script(**arguments)
            elif params.name == "generate_fleur_plot_script":
                content = await self.generate_fleur_plot_script(**arguments)
            elif params.name == "execute_fleur_workflow_script":
                content = await self.execute_fleur_workflow_script(**arguments)
            elif params.name == "list_aiida_processes":
                content = await self.list_aiida_processes(**arguments)
            elif params.name == "check_aiida_process":
                content = await self.check_aiida_process(**arguments)
            elif params.name == "inspect_aiida_outputs":
                content = await self.inspect_aiida_outputs(**arguments)
            elif params.name == "generate_aiida_setup_guide":
                content = await self.generate_aiida_setup_guide(**arguments)
            elif params.name == "setup_aiida_computer_and_codes":
                result = await self.setup_aiida_computer_and_codes(**arguments)
                return result
            else:
                raise ValueError(f"Unknown tool: {params.name}")

            return types.CallToolResult(content=content)

        self.server.add_request_handler("resources/list", types.PaginatedRequestParams, handle_list_resources)
        self.server.add_request_handler("resources/read", types.ReadResourceRequestParams, handle_read_resource)
        self.server.add_request_handler("tools/list", types.PaginatedRequestParams, handle_list_tools)
        self.server.add_request_handler("tools/call", types.CallToolRequestParams, handle_call_tool)

    async def list_fleur_workflows(self) -> list[types.TextContent]:
        lines = []
        for name, spec in WORKFLOW_SPECS.items():
            lines.append(
                f"- {name}: `{spec['entrypoint']}` - {spec['description']}\n"
                f"  docs: {WORKFLOW_DOC_LINKS[name]}"
            )
        return [types.TextContent(type="text", text="Supported workflows:\n\n" + "\n".join(lines))]

    async def explain_fleur_workflow(self, workflow: str) -> list[types.TextContent]:
        try:
            if workflow not in WORKFLOW_SPECS:
                raise ValueError(f"Unsupported workflow: {workflow}")
            return [types.TextContent(type="text", text=self._workflow_explanation_text(workflow))]
        except Exception as exc:
            return [types.TextContent(type="text", text=f"Failed to explain workflow: {exc}")]

    async def generate_fleur_workflow_script(
        self,
        workflow: str,
        material: str,
        structure_file: str | None = None,
        inpgen_code: str = "inpgen@localhost",
        fleur_code: str = "fleur@localhost",
        output_dir: str = ".",
        script_filename: str | None = None,
        submit_mode: str = "submit",
        options: dict[str, Any] | None = None,
        workflow_parameters: dict[str, Any] | None = None,
        calc_parameters: dict[str, Any] | None = None,
        scf_workflow_parameters: dict[str, Any] | None = None,
        final_scf_workflow_parameters: dict[str, Any] | None = None,
        magnetism: dict[str, Any] | None = None,
        plot_results: bool = False,
    ) -> list[types.TextContent]:
        try:
            if workflow not in WORKFLOW_SPECS:
                raise ValueError(f"Unsupported workflow: {workflow}")

            output_path = Path(output_dir).expanduser().resolve()
            output_path.mkdir(parents=True, exist_ok=True)
            filename = self._script_name(material, workflow, script_filename)
            script_path = output_path / filename

            script_content = self._build_workflow_script(
                workflow=workflow,
                material=material,
                structure_file=structure_file,
                inpgen_code=inpgen_code,
                fleur_code=fleur_code,
                submit_mode=submit_mode,
                options=options or {},
                workflow_parameters=workflow_parameters or {},
                calc_parameters=calc_parameters or {},
                scf_workflow_parameters=scf_workflow_parameters or {},
                final_scf_workflow_parameters=final_scf_workflow_parameters or {},
                magnetism=magnetism or {},
                plot_results=plot_results,
            )

            script_path.write_text(script_content, encoding="utf-8")
            script_path.chmod(0o755)

            summary = {
                "workflow": workflow,
                "entrypoint": WORKFLOW_SPECS[workflow]["entrypoint"],
                "material": material,
                "script_path": str(script_path),
                "structure_file": structure_file,
                "submit_mode": submit_mode,
                "plot_results": plot_results,
                "docs": WORKFLOW_DOC_LINKS[workflow],
            }
            return [types.TextContent(type="text", text=json.dumps(summary, indent=2))]
        except Exception as exc:
            return [types.TextContent(type="text", text=f"Failed to generate workflow script: {exc}")]

    async def generate_fleur_plot_script(
        self,
        node_identifiers: list[str],
        output_dir: str = ".",
        script_filename: str = "plot_fleur_results.py",
    ) -> list[types.TextContent]:
        try:
            output_path = Path(output_dir).expanduser().resolve()
            output_path.mkdir(parents=True, exist_ok=True)
            script_path = output_path / script_filename
            script_path.write_text(self._build_plot_script(node_identifiers), encoding="utf-8")
            script_path.chmod(0o755)

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "script_path": str(script_path),
                            "node_identifiers": node_identifiers,
                        },
                        indent=2,
                    ),
                )
            ]
        except Exception as exc:
            return [types.TextContent(type="text", text=f"Failed to generate plot script: {exc}")]

    async def execute_fleur_workflow_script(
        self,
        script_path: str,
        verdi_command: str = "verdi",
    ) -> list[types.TextContent]:
        try:
            resolved = Path(script_path).expanduser().resolve()
            if not resolved.is_file():
                raise FileNotFoundError(f"Script not found: {resolved}")

            result = self._run_local_command([verdi_command, "run", str(resolved)])
            pk = self._extract_process_pk(result.stdout)
            summary = {
                "script_path": str(resolved),
                "returncode": result.returncode,
                "process_pk": pk,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
            }
            return [types.TextContent(type="text", text=json.dumps(summary, indent=2))]
        except Exception as exc:
            return [types.TextContent(type="text", text=f"Failed to execute workflow script: {exc}")]

    async def list_aiida_processes(
        self,
        verdi_command: str = "verdi",
        limit: int = 10,
        all_entries: bool = True,
        process_label: str | None = None,
    ) -> list[types.TextContent]:
        try:
            command = [verdi_command, "process", "list", "-p", str(limit)]
            if all_entries:
                command.append("-a")
            result = self._run_local_command(command)
            if result.returncode != 0:
                raise RuntimeError(result.stderr or result.stdout)

            text = result.stdout.strip()
            if process_label:
                lines = text.splitlines()
                filtered = [lines[0]] if lines else []
                filtered.extend([line for line in lines[1:] if process_label in line])
                text = "\n".join(filtered)

            return [types.TextContent(type="text", text=text or "No processes found.")]
        except Exception as exc:
            return [types.TextContent(type="text", text=f"Failed to list processes: {exc}")]

    async def check_aiida_process(
        self,
        identifier: str,
        verdi_command: str = "verdi",
        include_report: bool = True,
        max_report_lines: int = 40,
    ) -> list[types.TextContent]:
        try:
            show_result = self._run_local_command([verdi_command, "process", "show", identifier])
            if show_result.returncode != 0:
                raise RuntimeError(show_result.stderr or show_result.stdout)

            parts = [f"Process status for {identifier}:\n\n{show_result.stdout.strip()}"]
            if include_report:
                report_result = self._run_local_command([verdi_command, "process", "report", identifier])
                report_text = report_result.stdout if report_result.returncode == 0 else report_result.stderr
                report_text = self._truncate_lines(report_text.strip(), max_report_lines)
                parts.append(f"Report:\n{report_text or '<empty>'}")

            return [types.TextContent(type="text", text="\n\n".join(parts))]
        except Exception as exc:
            return [types.TextContent(type="text", text=f"Failed to check process: {exc}")]

    async def inspect_aiida_outputs(
        self,
        identifier: str,
        verdi_command: str = "verdi",
        include_extras: bool = False,
        include_attributes: bool = True,
    ) -> list[types.TextContent]:
        try:
            helper_script = f"""
import json
import sys
from aiida.orm import load_node

identifier = sys.argv[1]
node = load_node(int(identifier) if str(identifier).isdigit() else identifier)
summary = {{
    "pk": node.pk,
    "uuid": str(node.uuid),
    "process_label": getattr(node, "process_label", None),
    "process_state": str(getattr(node, "process_state", None)),
    "exit_status": getattr(node, "exit_status", None),
    "exit_message": getattr(node, "exit_message", None),
    "is_finished_ok": bool(getattr(node, "is_finished_ok", False)),
    "called_descendants": [child.pk for child in getattr(node, "called_descendants", [])],
    "outputs": {{}},
}}
if {include_attributes!r}:
    try:
        summary["attributes"] = node.base.attributes.all
    except Exception:
        summary["attributes"] = {{}}
if {include_extras!r}:
    try:
        summary["extras"] = node.base.extras.all
    except Exception:
        summary["extras"] = {{}}
for key, output in node.outputs.items():
    entry = {{
        "pk": output.pk,
        "node_type": output.node_type,
    }}
    try:
        entry["attributes"] = output.base.attributes.all
    except Exception:
        pass
    try:
        entry["dict"] = output.get_dict()
    except Exception:
        pass
    summary["outputs"][key] = entry
print(json.dumps(summary, indent=2, default=str))
"""
            result = self._run_verdi_script(verdi_command, helper_script, [identifier])
            if result.returncode != 0:
                raise RuntimeError(result.stderr or result.stdout)
            return [types.TextContent(type="text", text=result.stdout.strip())]
        except Exception as exc:
            return [types.TextContent(type="text", text=f"Failed to inspect outputs: {exc}")]

    async def generate_aiida_setup_guide(
        self,
        system_preset: str | None = None,
        computer_label: str | None = None,
        hostname: str | None = None,
        inpgen_executable_path: str | None = None,
        fleur_executable_path: str | None = None,
        scheduler: str = "slurm",
        transport: str = "ssh",
        work_dir: str = "/scratch/{username}/aiida_run/",
        mpirun_command: str = "srun -n {tot_num_mpiprocs}",
        default_memory_per_machine_mb: int = 0,
        prepend_text: str = "",
        append_text: str = "",
        description: str = "Remote machine for aiida-fleur calculations",
        use_double_quotes: bool = False,
        ssh_username: str | None = None,
        ssh_port: int = 22,
        ssh_proxy_jump: str | None = None,
        safe_interval: int = 30,
        inpgen_code_label: str = "inpgen",
        fleur_code_label: str = "fleur",
        code_description: str = "FLEUR executable registered for aiida-fleur",
        input_plugin_inpgen: str = "fleur.inpgen",
        input_plugin_fleur: str = "fleur.fleur",
        output_dir: str = ".",
        filename: str = "aiida_fleur_setup_guide.md",
        project_path: str | None = None,
        fleur_module_hint: str = "fleur",
    ) -> list[types.TextContent]:
        try:
            arguments = self._apply_system_preset({
                "system_preset": system_preset,
                "computer_label": computer_label,
                "hostname": hostname,
                "inpgen_executable_path": inpgen_executable_path,
                "fleur_executable_path": fleur_executable_path,
                "scheduler": scheduler,
                "transport": transport,
                "ssh_username": ssh_username,
            })
            guide_missing_fields = [
                field
                for field in self._missing_setup_fields(dict(arguments))
                if field not in {"inpgen_executable_path", "fleur_executable_path"}
            ]
            if guide_missing_fields:
                return [
                    types.TextContent(
                        type="text",
                        text=(
                            "Missing setup information. Please provide these fields to generate the guide:\n- "
                            + "\n- ".join(guide_missing_fields)
                        ),
                    )
                ]

            output_path = Path(output_dir).expanduser().resolve()
            output_path.mkdir(parents=True, exist_ok=True)
            guide_path = output_path / filename
            guide_text = self._build_setup_guide(
                system_preset=system_preset,
                computer_label=arguments["computer_label"],
                hostname=arguments["hostname"],
                scheduler=arguments.get("scheduler", scheduler),
                transport=arguments.get("transport", transport),
                work_dir=work_dir,
                mpirun_command=mpirun_command,
                default_memory_per_machine_mb=default_memory_per_machine_mb,
                prepend_text=prepend_text,
                append_text=append_text,
                description=description,
                use_double_quotes=use_double_quotes,
                ssh_username=ssh_username,
                ssh_port=ssh_port,
                ssh_proxy_jump=ssh_proxy_jump,
                safe_interval=safe_interval,
                inpgen_code_label=inpgen_code_label,
                fleur_code_label=fleur_code_label,
                inpgen_executable_path=arguments.get("inpgen_executable_path"),
                fleur_executable_path=arguments.get("fleur_executable_path"),
                code_description=code_description,
                input_plugin_inpgen=input_plugin_inpgen,
                input_plugin_fleur=input_plugin_fleur,
                project_path=project_path,
                fleur_module_hint=fleur_module_hint,
            )
            guide_path.write_text(guide_text, encoding="utf-8")

            summary = {
                "guide_path": str(guide_path),
                "system_preset": system_preset,
                "computer_label": arguments["computer_label"],
                "hostname": arguments["hostname"],
                "scheduler": arguments.get("scheduler", scheduler),
                "inpgen_code": f"{inpgen_code_label}@{arguments['computer_label']}",
                "fleur_code": f"{fleur_code_label}@{arguments['computer_label']}",
            }
            return [types.TextContent(type="text", text=json.dumps(summary, indent=2))]
        except Exception as exc:
            return [types.TextContent(type="text", text=f"Failed to generate setup guide: {exc}")]

    async def setup_aiida_computer_and_codes(
        self,
        system_preset: str | None = None,
        computer_label: str | None = None,
        hostname: str | None = None,
        inpgen_executable_path: str | None = None,
        fleur_executable_path: str | None = None,
        scheduler: str = "slurm",
        transport: str = "ssh",
        work_dir: str = "/scratch/{username}/aiida_run/",
        mpirun_command: str = "srun -n {tot_num_mpiprocs}",
        default_memory_per_machine_mb: int = 0,
        prepend_text: str = "",
        append_text: str = "",
        description: str = "Remote machine for aiida-fleur calculations",
        use_double_quotes: bool = False,
        ssh_username: str | None = None,
        ssh_port: int = 22,
        ssh_proxy_jump: str | None = None,
        safe_interval: int = 30,
        inpgen_code_label: str = "inpgen",
        fleur_code_label: str = "fleur",
        code_description: str = "FLEUR executable registered for aiida-fleur",
        input_plugin_inpgen: str = "fleur.inpgen",
        input_plugin_fleur: str = "fleur.fleur",
        output_dir: str = ".",
        filename: str = "aiida_fleur_setup_guide.md",
        project_path: str | None = None,
        fleur_module_hint: str = "fleur",
        verdi_command: str = "verdi",
        apply: bool = False,
        replace_existing: bool = False,
        test_computer: bool = True,
        test_codes: bool = True,
    ) -> types.CallToolResult:
        arguments = self._apply_system_preset({
            "system_preset": system_preset,
            "computer_label": computer_label,
            "hostname": hostname,
            "inpgen_executable_path": inpgen_executable_path,
            "fleur_executable_path": fleur_executable_path,
            "scheduler": scheduler,
            "transport": transport,
            "ssh_username": ssh_username,
        })
        missing_fields = self._missing_setup_fields(arguments)
        if missing_fields:
            return types.CallToolResult(
                resultType="input_required",
                content=[
                    types.TextContent(
                        type="text",
                        text=(
                            "I need a few setup details before I can configure the AiiDA computer and the codes.\n"
                            "Please provide:\n- " + "\n- ".join(missing_fields)
                        ),
                    )
                ],
                structuredContent={
                    "missing_fields": missing_fields,
                    "next_step": "Call setup_aiida_computer_and_codes again with those fields filled in.",
                },
            )

        if not apply:
            guide_content = await self.generate_aiida_setup_guide(
                system_preset=system_preset,
                computer_label=arguments["computer_label"],
                hostname=arguments["hostname"],
                inpgen_executable_path=inpgen_executable_path,
                fleur_executable_path=fleur_executable_path,
                scheduler=arguments.get("scheduler", scheduler),
                transport=arguments.get("transport", transport),
                work_dir=work_dir,
                mpirun_command=mpirun_command,
                default_memory_per_machine_mb=default_memory_per_machine_mb,
                prepend_text=prepend_text,
                append_text=append_text,
                description=description,
                use_double_quotes=use_double_quotes,
                ssh_username=ssh_username,
                ssh_port=ssh_port,
                ssh_proxy_jump=ssh_proxy_jump,
                safe_interval=safe_interval,
                inpgen_code_label=inpgen_code_label,
                fleur_code_label=fleur_code_label,
                code_description=code_description,
                input_plugin_inpgen=input_plugin_inpgen,
                input_plugin_fleur=input_plugin_fleur,
                output_dir=output_dir,
                filename=filename,
                project_path=project_path,
                fleur_module_hint=fleur_module_hint,
            )
            preview_text = guide_content[0].text if guide_content else ""
            return types.CallToolResult(
                content=[
                    types.TextContent(
                        type="text",
                        text=(
                            "Setup preview generated. Review the guide, then call this tool again with `apply=true` "
                            "to actually run the local `verdi` setup commands.\n\n"
                            f"{preview_text}"
                        ),
                    )
                ],
                structuredContent={
                    "apply": False,
                    "system_preset": system_preset,
                    "computer_label": arguments["computer_label"],
                    "hostname": arguments["hostname"],
                    "verdi_command": verdi_command,
                },
            )

        try:
            summary = self._apply_aiida_setup(
                verdi_command=verdi_command,
                computer_label=arguments["computer_label"],
                hostname=arguments["hostname"],
                scheduler=arguments.get("scheduler", scheduler),
                transport=arguments.get("transport", transport),
                work_dir=work_dir,
                mpirun_command=mpirun_command,
                default_memory_per_machine_mb=default_memory_per_machine_mb,
                prepend_text=prepend_text,
                append_text=append_text,
                description=description,
                ssh_username=ssh_username,
                ssh_port=ssh_port,
                ssh_proxy_jump=ssh_proxy_jump,
                safe_interval=safe_interval,
                inpgen_code_label=inpgen_code_label,
                fleur_code_label=fleur_code_label,
                inpgen_executable_path=arguments["inpgen_executable_path"],
                fleur_executable_path=arguments["fleur_executable_path"],
                code_description=code_description,
                input_plugin_inpgen=input_plugin_inpgen,
                input_plugin_fleur=input_plugin_fleur,
                replace_existing=replace_existing,
                test_computer=test_computer,
                test_codes=test_codes,
            )
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=json.dumps(summary, indent=2))],
                structuredContent=summary,
            )
        except Exception as exc:
            return types.CallToolResult(
                isError=True,
                content=[types.TextContent(type="text", text=f"Failed to apply setup: {exc}")],
            )

    async def run(self) -> None:
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="fleur-workflows",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )


if __name__ == "__main__":
    import asyncio

    server = FleurWorkflowMCPServer()
    asyncio.run(server.run())
