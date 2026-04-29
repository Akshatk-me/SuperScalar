import os

import pytest
from cocotb_test.simulator import run

# Automatically find the path to your VHDL files
tests_dir = os.path.dirname(__file__)
vhdl_dir = os.path.abspath(
    os.path.join(tests_dir, "..", "src")
)  # Adjust based on your folder structure

# If you use GHDL, make sure to set the simulator.
# You can also set this via environment variable: SIM=ghdl pytest test_runner.py
SIMULATOR = os.getenv("SIM", "ghdl")


@pytest.mark.parametrize(
    "module_name, top_level, vhdl_file",
    [
        ("test_alu", "alu", "ALU.vhdl"),
        ("test_alu_control", "alu_control", "ALU_Control.vhdl"),
        ("test_unified_prf", "unified_prf", "UnifiedPRF.vhdl"),
    ],
)
def test_hardware_modules(module_name, top_level, vhdl_file):
    """Run cocotb tests for specified modules."""
    run(
        simulator=SIMULATOR,
        vhdl_sources=[os.path.join(vhdl_dir, vhdl_file)],
        toplevel=top_level,
        module=module_name,
        toplevel_lang="vhdl",
        waves=True,
    )
