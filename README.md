## Testing

I'm using pytest

```
project_root/
├── src/
│   └── alu.vhdl         # Your VHDL code
└── tests/
    └── test_alu.py      # Your Pytest + Cocotb code
```

So the sim directory is for manual tests if we need, mostly we'll use testing using test_alu.py etc stuff.

Let's say we have `alu.vhdl` to test. We'll take it's port info, then write a `tests/test_alu.py`. This single file will contain both simulation runner and the hardware tests.

Simulation runner is easy to configure, at the bottom of the `test_module.py` put:

```py
def test_alu_runner():
    """This function is found by Pytest and configures GHDL/Cocotb."""

    # Point to the specific VHDL files needed for this test
    # os.path.join ensures it works on both Windows and Linux/Mac
    src_dir = os.path.join(os.path.dirname(__file__), "..", "src")
    sources = [os.path.join(src_dir, "alu.vhdl")]

    # Run the simulator
    run(
        simulator="ghdl",
        vhdl_sources=sources,
        toplevel="alu",            # The name of the VHDL entity
        module="test_alu",         # The name of THIS python file (without .py)
        sim_build="sim_build/alu", # Creates a neat build folder for temp files
        waves=True                 # Generates wave.vcd automatically!
    )

```

The Hardware Verification can be done using cocotb tests, like this:

```py
@cocotb.test()
async def test_alu_addition(dut):
    """Test that the ALU correctly adds two numbers."""

    # 1. DRIVE: Assign values to the VHDL inputs
    dut.opcode.value = 1       # Assuming 1 is ADD
    dut.in_a.value = 10        # Python handles the integer-to-binary conversion!
    dut.in_b.value = 5

    # 2. WAIT: Let the combinational logic settle
    # Since an ALU is purely combinational (no clock), we just wait a tiny amount of time.
    await Timer(1, units="ns")

    # 3. CHECK: Assert the outputs are mathematically correct
    assert dut.result.value == 15, f"Expected 15, got {dut.result.value}"
    assert dut.flag_z.value == 0, "Zero flag should not be set!"

@cocotb.test()
async def test_alu_zero_flag(dut):
    """Test that the ALU sets the Zero flag correctly."""
    dut.opcode.value = 1       # ADD
    dut.in_a.value = 0
    dut.in_b.value = 0
    await Timer(1, units="ns")

    assert dut.result.value == 0
    assert dut.flag_z.value == 1, "Zero flag should be set when result is 0!"

```

Run the test using

```sh
pytest tests/test_alu.py -s
```
