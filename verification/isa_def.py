# verification/isa_def.py

# 1. Register Mapping
REGISTERS = {f"R{i}": i for i in range(8)}  # {'R0': 0, 'R1': 1, ..., 'R7': 7}

# 2. Instruction Definitions
# Format: "MNEMONIC": ("FORMAT_TYPE", OPCODE, COMPLEMENT_BIT, CONDITION_BITS)
# Note: For I and J types, complement and condition are usually None.
INSTRUCTIONS = {
    # --- R-Type Math (Opcode 0001) ---
    "ADA": ("R", 0b0001, 0b0, 0b00),
    "ADC": ("R", 0b0001, 0b0, 0b10),
    "ADZ": ("R", 0b0001, 0b0, 0b01),
    "AWC": ("R", 0b0001, 0b0, 0b11),
    "ACA": ("R", 0b0001, 0b1, 0b00),
    # --- R-Type Logic (Opcode 0010) ---
    "NDU": ("R", 0b0010, 0b0, 0b00),
    "NDC": ("R", 0b0010, 0b0, 0b10),
    "NDZ": ("R", 0b0010, 0b0, 0b01),
    # --- I-Type Math/Memory ---
    "ADI": ("I", 0b0000, None, None),
    "LW": ("I", 0b0100, None, None),
    "SW": ("I", 0b0101, None, None),
    "BEQ": ("I", 0b1000, None, None),
    # --- J-Type ---
    "LLI": ("J", 0b0011, None, None),
    "JAL": ("J", 0b1100, None, None),
    # TODO(akshat): You will add the remaining instructions from the spec here @medium file:isa_def.py
}
