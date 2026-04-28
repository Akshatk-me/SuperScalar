# verification/assembler.py
from verification.isa_def import INSTRUCTIONS, REGISTERS


def parse_line(line):
    # Strip comments and whitespace
    line = line.split("#")[0].strip().upper()
    if not line:
        return None

    # Replace commas with spaces, then split into parts
    parts = line.replace(",", " ").split()
    mnemonic = parts[0]
    operands = parts[1:]

    return assemble_instruction(mnemonic, operands)


def format_immediate(imm_str, bit_width):
    """
    Converts a string immediate to an integer and applies a 2's complement mask.
    """
    val = int(imm_str)

    # Create a mask of '1's for the given bit width.
    # For 6 bits: (1 << 6) - 1 = 63 (which is 0b111111)
    mask = (1 << bit_width) - 1

    # Apply the mask. Positive numbers are unaffected.
    # Negative numbers lose their infinite leading 1s.
    return val & mask


def assemble_instruction(mnemonic, operands):
    if mnemonic not in INSTRUCTIONS:
        raise ValueError(f"Unknown instruction: {mnemonic}")

    fmt, opcode, comp, cond = INSTRUCTIONS[mnemonic]

    if fmt == "R":
        # R-Type: Opcode(4) | RA(3) | RB(3) | RC(3) | Comp(1) | Cond(2)
        ra = REGISTERS[
            operands[1]
        ]  # Note: Spec says e.g. "ada rc, ra, rb" so operands[1] is RA
        rb = REGISTERS[operands[2]]
        rc = REGISTERS[operands[0]]

        machine_code = (
            (opcode << 12) | (ra << 9) | (rb << 6) | (rc << 3) | (comp << 2) | cond
        )
        return f"{machine_code:04X}"

    elif fmt == "I":
        # I-Type: Opcode(4) | RA(3) | Imm(6) | RB(3)
        # Assembly format varies (e.g., "ADI rb, ra, imm6" vs "LW ra, rb, imm6")
        # Let's assume standard parsing puts operands as [Dest, Src, Imm] or similar

        # Example for ADI: ADI rb, ra, imm6 -> operands[0]=rb, operands[1]=ra, operands[2]=imm
        ra = REGISTERS[operands[1]]
        rb = REGISTERS[operands[0]]

        # Cleanly get the 6-bit masked immediate
        imm6 = format_immediate(operands[2], bit_width=6)

        machine_code = (opcode << 12) | (ra << 9) | (imm6 << 3) | rb
        return f"{machine_code:04X}"

    elif fmt == "J":
        # J-Type: Opcode(4) | RA(3) | Imm(9)
        # Example for LLI: lli ra, imm9 -> operands[0]=ra, operands[1]=imm
        ra = REGISTERS[operands[0]]

        # Cleanly get the 9-bit masked immediate
        imm9 = format_immediate(operands[1], bit_width=9)

        machine_code = (opcode << 12) | (ra << 9) | imm9
        return f"{machine_code:04X}"

    return "0000"
