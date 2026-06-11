#!/usr/bin/env python3
"""
AiiDA-FLEUR EOS MCP Server
Provides tools for generating aiida-fleur equation-of-state workflow inputs.
"""

import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aiida-mcp")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("aiida-mcp.log"),
        logging.StreamHandler()
    ]
)


class AiidaMCPServer:
    def __init__(self):
        self.server = Server("aiida-fleur-eos")
        self.templates_dir = Path(__file__).parent / "templates"
        self.setup_handlers()

    def _load_template(self, filename: str) -> str:
        """Load template from file."""
        try:
            return (self.templates_dir / filename).read_text()
        except Exception as exc:
            logger.error("Failed to load template %s: %s", filename, exc)
            return f"Error loading template: {filename}"

    def setup_handlers(self):
        """Setup all MCP handlers."""

        @self.server.list_resources()
        async def handle_list_resources() -> list[types.Resource]:
            return [
                types.Resource(
                    uri="aiida://examples/fleur_eos_inputs",
                    name="FLEUR EOS Inputs Example",
                    description="Reusable AiiDA builder inputs for aiida-fleur EOS workflows",
                    mimeType="text/x-python",
                ),
                types.Resource(
                    uri="aiida://examples/fleur_eos_workflow",
                    name="FLEUR EOS Workflow Example",
                    description="Runnable aiida-fleur equation-of-state workflow example",
                    mimeType="text/x-python",
                ),
                types.Resource(
                    uri="aiida://docs/fleur_eos_guide",
                    name="FLEUR EOS Workflow Documentation",
                    description="Step-by-step guide for aiida-fleur EOS calculations",
                    mimeType="text/markdown",
                ),
            ]

        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            if uri == "aiida://examples/fleur_eos_inputs":
                return self.get_fleur_eos_inputs_template()
            if uri == "aiida://examples/fleur_eos_workflow":
                return self.get_fleur_eos_workflow_template()
            if uri == "aiida://docs/fleur_eos_guide":
                return self.get_fleur_eos_guide()
            raise ValueError(f"Unknown resource: {uri}")

        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            return [
                types.Tool(
                    name="generate_fleur_eos_inputs",
                    description="Generate reusable AiiDA inputs for the aiida-fleur equation-of-state workflow",
                    inputSchema=self._fleur_eos_schema(),
                ),
                types.Tool(
                    name="generate_fleur_eos_script",
                    description="Generate a runnable Python script for aiida-fleur equation-of-state calculation",
                    inputSchema=self._fleur_eos_schema(),
                ),
                types.Tool(
                    name="execute_calculation",
                    description="Execute a generated aiida-fleur EOS calculation script with verdi run",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "script_path": {
                                "type": "string",
                                "description": "Path to the Python script"
                            }
                        },
                        "required": ["script_path"]
                    }
                ),
                types.Tool(
                    name="check_calculation_status",
                    description="Check status of running AiiDA calculations",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "process_id": {
                                "type": "string",
                                "description": "Optional process ID to check a specific calculation"
                            }
                        },
                        "required": []
                    }
                ),
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
            if name == "generate_fleur_eos_inputs":
                return await self.generate_fleur_eos_inputs(**arguments)
            if name == "generate_fleur_eos_script":
                return await self.generate_fleur_eos_script(**arguments)
            if name == "execute_calculation":
                return await self.execute_calculation(arguments["script_path"])
            if name == "check_calculation_status":
                return await self.check_calculation_status(arguments.get("process_id"))
            raise ValueError(f"Unknown tool: {name}")

    def _fleur_eos_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "material": {"type": "string"},
                "structure_file": {"type": "string"},
                "inpgen_code": {
                    "type": "string",
                    "default": "inpgen@localhost"
                },
                "fleur_code": {
                    "type": "string",
                    "default": "fleur@localhost"
                },
                "points": {
                    "type": "integer",
                    "default": 9
                },
                "step": {
                    "type": "number",
                    "default": 0.002
                },
                "guess": {
                    "type": "number",
                    "default": 1.0
                },
                "fleur_runmax": {
                    "type": "integer",
                    "default": 4
                },
                "itmax_per_run": {
                    "type": "integer",
                    "default": 30
                },
                "density_converged": {
                    "type": "number",
                    "default": 0.0002
                },
                "num_machines": {
                    "type": "integer",
                    "default": 1
                },
                "num_mpiprocs_per_machine": {
                    "type": "integer",
                    "default": 1
                },
                "max_wallclock_seconds": {
                    "type": "integer",
                    "default": 3600
                },
                "queue_name": {
                    "type": "string",
                    "default": ""
                }
            },
            "required": ["material", "structure_file"]
        }

    async def generate_fleur_eos_inputs(
        self,
        material: str,
        structure_file: str,
        inpgen_code: str = "inpgen@localhost",
        fleur_code: str = "fleur@localhost",
        points: int = 9,
        step: float = 0.002,
        guess: float = 1.0,
        fleur_runmax: int = 4,
        itmax_per_run: int = 30,
        density_converged: float = 0.0002,
        num_machines: int = 1,
        num_mpiprocs_per_machine: int = 1,
        max_wallclock_seconds: int = 3600,
        queue_name: str = ""
    ) -> list[types.TextContent]:
        """Generate reusable AiiDA inputs for aiida-fleur EOS workflow."""
        inputs_template = self._load_template("fleur_eos_inputs_template.py")
        inputs_content = inputs_template.format(
            material=material,
            structure_file=structure_file,
            inpgen_code=inpgen_code,
            fleur_code=fleur_code,
            points=points,
            step=step,
            guess=guess,
            fleur_runmax=fleur_runmax,
            itmax_per_run=itmax_per_run,
            density_converged=density_converged,
            num_machines=num_machines,
            num_mpiprocs_per_machine=num_mpiprocs_per_machine,
            max_wallclock_seconds=max_wallclock_seconds,
            queue_name=queue_name
        )

        queue_name_display = queue_name or "<none>"

        return [types.TextContent(
            type="text",
            text=f"AiiDA EOS inputs for {material}:\n\n{inputs_content}\n\n"
                 f"Summary:\n"
                 f"- Structure: {structure_file}\n"
                 f"- inpgen code: {inpgen_code}\n"
                 f"- fleur code: {fleur_code}\n"
                 f"- EOS points: {points}\n"
                 f"- EOS step: {step}\n"
                 f"- EOS guess: {guess}\n"
                 f"- fleur_runmax: {fleur_runmax}\n"
                 f"- itmax_per_run: {itmax_per_run}\n"
                 f"- density_converged: {density_converged}\n"
                 f"- resources: {num_machines} machine(s), "
                 f"{num_mpiprocs_per_machine} MPI proc(s) per machine\n"
                 f"- queue_name: {queue_name_display}\n"
                 f"- max_wallclock_seconds: {max_wallclock_seconds}"
        )]

    async def generate_fleur_eos_script(
        self,
        material: str,
        structure_file: str,
        inpgen_code: str = "inpgen@localhost",
        fleur_code: str = "fleur@localhost",
        points: int = 9,
        step: float = 0.002,
        guess: float = 1.0,
        fleur_runmax: int = 4,
        itmax_per_run: int = 30,
        density_converged: float = 0.0002,
        num_machines: int = 1,
        num_mpiprocs_per_machine: int = 1,
        max_wallclock_seconds: int = 3600,
        queue_name: str = ""
    ) -> list[types.TextContent]:
        """Generate a runnable Python script for aiida-fleur EOS calculation."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        script_name = f"fleur_eos_calculation_{material}_{timestamp}.py"

        script_template = self._load_template("fleur_eos_script_template.py")
        script_content = script_template.format(
            material=material,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            structure_file=structure_file,
            inpgen_code=inpgen_code,
            fleur_code=fleur_code,
            points=points,
            step=step,
            guess=guess,
            fleur_runmax=fleur_runmax,
            itmax_per_run=itmax_per_run,
            density_converged=density_converged,
            num_machines=num_machines,
            num_mpiprocs_per_machine=num_mpiprocs_per_machine,
            max_wallclock_seconds=max_wallclock_seconds,
            queue_name=queue_name
        )

        script_path = Path.cwd() / script_name
        script_path.write_text(script_content)
        script_path.chmod(0o755)

        queue_name_display = queue_name or "<none>"

        return [types.TextContent(
            type="text",
            text=f"Generated script: {script_path}\n\nScript saved with parameters:\n"
                 f"- Material: {material}\n"
                 f"- Structure: {structure_file}\n"
                 f"- inpgen code: {inpgen_code}\n"
                 f"- fleur code: {fleur_code}\n"
                 f"- EOS points: {points}\n"
                 f"- EOS step: {step}\n"
                 f"- EOS guess: {guess}\n"
                 f"- fleur_runmax: {fleur_runmax}\n"
                 f"- itmax_per_run: {itmax_per_run}\n"
                 f"- density_converged: {density_converged}\n"
                 f"- resources: {num_machines} machine(s), "
                 f"{num_mpiprocs_per_machine} MPI proc(s) per machine\n"
                 f"- queue_name: {queue_name_display}\n"
                 f"- max_wallclock_seconds: {max_wallclock_seconds}"
        )]

    async def execute_calculation(self, script_path: str) -> list[types.TextContent]:
        """Execute a generated aiida-fleur EOS calculation script."""
        try:
            result = subprocess.run(
                ["verdi", "run", script_path],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                pk = None
                for line in result.stdout.split("\n"):
                    if "pk:" in line.lower():
                        import re
                        match = re.search(r"\d+", line)
                        if match:
                            pk = match.group()
                            break

                response = f"Calculation started successfully!\n{result.stdout}"
                if pk:
                    response += f"\n\nProcess ID: {pk}\nMonitor with: verdi process show {pk}"

                return [types.TextContent(type="text", text=response)]

            return [types.TextContent(
                type="text",
                text=f"Error starting calculation:\n{result.stderr}"
            )]
        except Exception as exc:
            return [types.TextContent(
                type="text",
                text=f"Execution failed: {exc}"
            )]

    async def check_calculation_status(
        self,
        process_id: Optional[str] = None
    ) -> list[types.TextContent]:
        """Check status of calculations."""
        try:
            if process_id:
                result = subprocess.run(
                    ["verdi", "process", "show", process_id],
                    capture_output=True,
                    text=True
                )
            else:
                result = subprocess.run(
                    ["verdi", "process", "list", "-p", "5", "-a"],
                    capture_output=True,
                    text=True
                )

            return [types.TextContent(
                type="text",
                text=result.stdout if result.returncode == 0 else result.stderr
            )]
        except Exception as exc:
            return [types.TextContent(
                type="text",
                text=f"Error checking status: {exc}"
            )]

    def get_fleur_eos_inputs_template(self) -> str:
        return self._load_template("fleur_eos_inputs_template.py")

    def get_fleur_eos_workflow_template(self) -> str:
        return self._load_template("fleur_eos_workflow_template.py")

    def get_fleur_eos_guide(self) -> str:
        return self._load_template("fleur_workflow_guide.md")

    async def run(self):
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="aiida-fleur-eos",
                    server_version="0.1.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )


if __name__ == "__main__":
    import asyncio

    server = AiidaMCPServer()
    asyncio.run(server.run())
