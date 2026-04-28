# MISC Design Stuff learnt on the way

## System design

As usual modular design is good and it's a standard practice as well.

Now the main thing is that these modules should really be what they claim to be, i.e. "modular".
To create a maintainable system we need to follow the principle of **Architectural isolation**.

Have **Standardized Interfaces**:
Never wire custom signals between major blocks unless necessary, instead use standardized handshake protocols.
Every major data path should use a `Valid` / `Ready` handshake. Sender says data is valid, reciever will claim it's ready recieve the data.
Industry standard interfaces are `AXI4-Stream` or `Wishbone`.

Have **Parameterization**:
Never hardcode a bus width, register count, or an opcode size. Make everything a parameter.
In verilog it's `parameters`, in VHDL it's `generics`. Modern hardware generators like **Chisel** and **Amaranth** have this built into the language (since they use python and have OOP features).

Use **Interfaces**:
Writing massive lists of ports for every module is bad, use interface to bundle signals together. This makes for a more maintainable code.
If you add a signal, modify the interface not the modules that touch the bus.

## Testing and Verification Practices

**Use assertions, and only if things fail stare at waveform to rind why things failed**.

Drivers: Never manually write `dut.clk.value = 1` or `dut.data.value = 0x5` directly in the main test loop.

## Project Structure

```
my_processor_project/
├── rtl/               # (Register Transfer Level) ALL synthesizable hardware goes here.
│   ├── core/          # e.g., alu.sv, decoder.vhd
│   └── interfaces/    # Standard bus definitions (AXI, etc.)
├── tb/                # (Testbench) ALL verification code goes here.
│   ├── tests/         # test_alu.py, test_fetch.py
│   └── model/         # Python golden models (software ALU)
├── sim/               # The "Trash Can". All compilation outputs, waveforms, and logs.
├── scripts/           # Automation scripts (Tcl for Vivado, CI/CD yamls)
├── Makefile           # The master build script.
└── .gitignore         # Tells Git to ignore the 'sim/' folder.
```

The `sim` folder must be ephemeral, deleting it should cost us nothing of value.

## Build System

Use Makefiles for automation, otherwise use `pytest` it's much better when combined with `cocotb.runner`. It allows you to run your entire build and simulation pipeline directly in python. For more advanced projects, teams use `FuseSoC` or `VUnit`.

## Version Control (Collaboration)

Use `.gitignore` properly and only have things of worth value.
Create branches, and only merge once the automated tests are passing.

## About Wrappers

Try to avoid creating wrappers, the creation of a wrapper depends on:

- If entity's ports use standard VHDL types: `std_logic`, `signed`, `unsigned`, etc don't create a wrapper
- If you use custom `record` types, multi-dimensional arrays or custom unconstrained arrays do create a wrapper of `std_logic_vector` so Python or your testing toolkit can read it.

Actionable Advice: Keep the ports on your top-level modules (ALU, Register File) restricted to std_logic_vector. It makes your life much easier.

# Misc

## About GHW

VCD (Value Change Dump) defined in the Verilog language and extended six years later to EVCD (extended VCD), is simple and compact and can be use for tools apart from verilog simulation tools.

VHDL had some signal types that couldn't be handled by VCD, so Tristan Gingold (author of GHDL) implemented an alternative format named GHW.
