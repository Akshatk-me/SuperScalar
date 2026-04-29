"""
Instruction Builder for IITB-RISC ISA
Generates correct instruction encodings programmatically
"""


def build_r_type(opcode, ra, rb, rc, complet, cz):
    """Build R-Type instruction: [opcode(4)][ra(3)][rb(3)][rc(3)][complet(1)][cz(2)]"""
    return (opcode << 12) | (ra << 9) | (rb << 6) | (rc << 3) | (complet << 2) | cz


def build_i_type(opcode, ra, rb, imm6):
    """Build I-Type instruction: [opcode(4)][ra(3)][rb(3)][imm6(6)]"""
    return (opcode << 12) | (ra << 9) | (rb << 6) | (imm6 & 0x3F)


def build_j_type(opcode, ra, imm9):
    """Build J-Type instruction: [opcode(4)][ra(3)][imm9(9)]"""
    return (opcode << 12) | (ra << 9) | (imm9 & 0x1FF)


# ==========================================
# ADD FAMILY (R-Type, opcode=0b0001)
# ==========================================
def ADA(ra, rb, rc):
    """Add: rc = ra + rb, modifies C and Z"""
    return build_r_type(0b0001, ra, rb, rc, 0, 0b00)


def ADC(ra, rb, rc):
    """Add if Carry: rc = ra + rb (if C=1), modifies C and Z"""
    return build_r_type(0b0001, ra, rb, rc, 0, 0b10)


def ADZ(ra, rb, rc):
    """Add if Zero: rc = ra + rb (if Z=1), modifies C and Z"""
    return build_r_type(0b0001, ra, rb, rc, 0, 0b01)


def AWC(ra, rb, rc):
    """Add with Carry: rc = ra + rb + C, modifies C and Z"""
    return build_r_type(0b0001, ra, rb, rc, 0, 0b11)


def ACA(ra, rb, rc):
    """Add Complement: rc = ra + (~rb), modifies C and Z"""
    return build_r_type(0b0001, ra, rb, rc, 1, 0b00)


def ACC(ra, rb, rc):
    """Add Complement if Carry: rc = ra + (~rb) (if C=1), modifies C and Z"""
    return build_r_type(0b0001, ra, rb, rc, 1, 0b10)


def ACZ(ra, rb, rc):
    """Add Complement if Zero: rc = ra + (~rb) (if Z=1), modifies C and Z"""
    return build_r_type(0b0001, ra, rb, rc, 1, 0b01)


def ACW(ra, rb, rc):
    """Add Complement with Carry: rc = ra + (~rb) + C, modifies C and Z"""
    return build_r_type(0b0001, ra, rb, rc, 1, 0b11)


# ==========================================
# NAND FAMILY (R-Type, opcode=0b0010)
# ==========================================
def NDU(ra, rb, rc):
    """NAND: rc = ~(ra & rb), modifies Z only"""
    return build_r_type(0b0010, ra, rb, rc, 0, 0b00)


def NDC(ra, rb, rc):
    """NAND if Carry: rc = ~(ra & rb) (if C=1), modifies Z only"""
    return build_r_type(0b0010, ra, rb, rc, 0, 0b10)


def NDZ(ra, rb, rc):
    """NAND if Zero: rc = ~(ra & rb) (if Z=1), modifies Z only"""
    return build_r_type(0b0010, ra, rb, rc, 0, 0b01)


def NCU(ra, rb, rc):
    """NAND Complement: rc = ~(ra & ~rb), modifies Z only"""
    return build_r_type(0b0010, ra, rb, rc, 1, 0b00)


def NCC(ra, rb, rc):
    """NAND Complement if Carry: rc = ~(ra & ~rb) (if C=1), modifies Z only"""
    return build_r_type(0b0010, ra, rb, rc, 1, 0b10)


def NCZ(ra, rb, rc):
    """NAND Complement if Zero: rc = ~(ra & ~rb) (if Z=1), modifies Z only"""
    return build_r_type(0b0010, ra, rb, rc, 1, 0b01)


# ==========================================
# I-TYPE INSTRUCTIONS
# ==========================================
def ADI(ra, rb, imm6):
    """Add Immediate: rb = ra + sext(imm6), modifies C and Z"""
    return build_i_type(0b0000, ra, rb, imm6)


def LW(ra, rb, imm6):
    """Load Word: ra = mem[rb + sext(imm6)], modifies Z"""
    return build_i_type(0b0100, ra, rb, imm6)


def SW(ra, rb, imm6):
    """Store Word: mem[rb + sext(imm6)] = ra, no destination"""
    return build_i_type(0b0101, ra, rb, imm6)


def BEQ(ra, rb, imm6):
    """Branch if Equal: PC += sext(imm6)*2 if ra == rb"""
    return build_i_type(0b1000, ra, rb, imm6)


def BLT(ra, rb, imm6):
    """Branch if Less Than: PC += sext(imm6)*2 if ra < rb"""
    return build_i_type(0b1001, ra, rb, imm6)


def BLE(ra, rb, imm6):
    """Branch if Less or Equal: PC += sext(imm6)*2 if ra <= rb"""
    return build_i_type(0b1010, ra, rb, imm6)


def JLR(ra, rb):
    """Jump and Link Register: PC = rb, ra = PC+2"""
    return build_i_type(0b1101, ra, rb, 0)


# ==========================================
# J-TYPE INSTRUCTIONS
# ==========================================
def LLI(ra, imm9):
    """Load Lower Immediate: ra[8:0] = imm9, ra[15:9] = 0"""
    return build_j_type(0b0011, ra, imm9)


def LM(ra, bitmap):
    """Load Multiple: Load registers according to bitmap"""
    return build_j_type(0b0110, ra, bitmap)


def LMF(ra, bitmap):
    """Load Multiple with Flag: Load flags first, then registers"""
    return build_j_type(0b0110, ra, bitmap | 0x100)  # Set bit 8 for flag


def SM(ra, bitmap):
    """Store Multiple: Store registers according to bitmap"""
    return build_j_type(0b0111, ra, bitmap)


def SMF(ra, bitmap):
    """Store Multiple with Flag: Store flags first, then registers"""
    return build_j_type(0b0111, ra, bitmap | 0x100)


def JAL(ra, imm9):
    """Jump and Link: PC += imm9*2, ra = PC+2"""
    return build_j_type(0b1100, ra, imm9)


def JRI(ra, imm9):
    """Jump Register Immediate: PC = ra + imm9*2, no destination"""
    return build_j_type(0b1111, ra, imm9)
