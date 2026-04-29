# Superscalar Processor Architecture

## Module Overview

| Module        | File               | Purpose                            | Status     |
| ------------- | ------------------ | ---------------------------------- | ---------- |
| ALU           | `ALU.vhdl`         | Arithmetic & logic operations      | ✅ Tested  |
| ALU Control   | `ALU_Control.vhdl` | Decodes instructions to ALU ops    | ✅ Tested  |
| Unified PRF   | `UnifiedPRF.vhdl`  | Physical register file (32x18-bit) | ✅ Tested  |
| Front End RAT | `FrontEndRAT.vhdl` | Architectural→Physical mapping     | ✅ Tested  |
| PC            | `PC.vhdl`          | Program counter with branch logic  | ⏳ Pending |
| CZ Flags      | `CZFlags.vhdl`     | Architectural flag register        | ⏳ Pending |
| Top Level     | `top.vhdl`         | Full processor integration         | ⏳ Pending |

## Detailed Module Documentation

### ALU

- **Inputs**: data1, data2 (16-bit), c_in, z_in, alu_control (5-bit)
- **Outputs**: alu_result (16-bit), zero, carry, lt, eq, le
- **Operations**: ADD, ADDIFC, ADDIFZ, ADDWC, NAND, NANDIFC, NANDIFZ, COMPARE, PASS, LLI
- **Key Feature**: Complement bit (alu_control[4]) enables data2 complement for ADD family

### Unified PRF

- **Size**: 32 entries × 18 bits [Z(1)][C(1)][Data(16)]
- **Read ports**: 8 asynchronous (4 per instruction × 2)
- **Write ports**: 2 synchronous (2 instructions/cycle commit)
- **Conflict resolution**: Port 2 wins when writing same address

### Front End RAT

- **Entries**: 10 (R0-R7 at 0-7, C at 8, Z at 9)
- **Rename bandwidth**: 2 instructions/cycle
- **Forwarding**: Inst2 sees Inst1's writes combinatorially
- **Recovery**: 1-cycle branch misprediction recovery
