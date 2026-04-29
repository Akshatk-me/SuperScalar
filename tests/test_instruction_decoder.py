import random

import cocotb
from cocotb.triggers import Timer
from instruction_builder import *


async def setup_decoder(dut):
    """Initialize decoder inputs"""
    dut.instruction.value = 0
    await Timer(2, unit="ns")


# ==========================================
# FIELD EXTRACTION TESTS
# ==========================================


@cocotb.test()
async def test_decoder_field_extraction_r_type(dut):
    """Test R-Type field extraction"""
    await setup_decoder(dut)

    instr = ADA(ra=5, rb=6, rc=7)
    dut.instruction.value = instr
    await Timer(2, unit="ns")

    assert dut.opcode_out.value == 0b0001
    assert dut.ra_out.value == 5
    assert dut.rb_out.value == 6
    assert dut.rc_out.value == 7
    assert dut.complet_bit.value == 0
    assert dut.cz_flags.value == 0b00


@cocotb.test()
async def test_decoder_field_extraction_i_type(dut):
    """Test I-Type field extraction"""
    await setup_decoder(dut)

    instr = ADI(ra=3, rb=4, imm6=0x2A)
    dut.instruction.value = instr
    await Timer(2, unit="ns")

    assert dut.opcode_out.value == 0b0000
    assert dut.ra_out.value == 3
    assert dut.rb_out.value == 4
    assert dut.imm6_ext.value.signed_integer == -22  # Positive immediate


@cocotb.test()
async def test_decoder_field_extraction_j_type(dut):
    """Test J-Type field extraction"""
    await setup_decoder(dut)

    instr = LLI(ra=2, imm9=0x1FF)
    dut.instruction.value = instr
    await Timer(2, unit="ns")

    assert dut.opcode_out.value == 0b0011
    assert dut.ra_out.value == 2
    assert dut.imm9_ext.value.signed_integer == -1


# ==========================================
# ADD FAMILY TESTS
# ==========================================


@cocotb.test()
async def test_decoder_add_family(dut):
    """Test all ADD family instructions"""
    await setup_decoder(dut)

    test_cases = [
        (ADA(1, 2, 3), 0, 0b00, "ADA", True, True, False, False),
        (ADC(1, 2, 3), 0, 0b10, "ADC", True, True, True, False),
        (ADZ(1, 2, 3), 0, 0b01, "ADZ", True, True, False, True),
        (AWC(1, 2, 3), 0, 0b11, "AWC", True, True, False, False),
        (ACA(1, 2, 3), 1, 0b00, "ACA", True, True, False, False),
        (ACC(1, 2, 3), 1, 0b10, "ACC", True, True, True, False),
        (ACZ(1, 2, 3), 1, 0b01, "ACZ", True, True, False, True),
        (ACW(1, 2, 3), 1, 0b11, "ACW", True, True, False, False),
    ]

    for (
        instr,
        exp_complet,
        exp_cz,
        name,
        exp_writes_c,
        exp_writes_z,
        exp_wants_c,
        exp_wants_z,
    ) in test_cases:
        dut.instruction.value = instr
        await Timer(2, unit="ns")

        assert dut.complet_bit.value == exp_complet, f"{name} complet bit"
        assert dut.cz_flags.value == exp_cz, f"{name} CZ flags"
        assert dut.dest_reg.value == 3, f"{name} destination reg"
        assert dut.writes_c_flag.value == exp_writes_c, f"{name} writes C"
        assert dut.writes_z_flag.value == exp_writes_z, f"{name} writes Z"
        assert dut.wants_c_flag.value == exp_wants_c, f"{name} wants C"
        assert dut.wants_z_flag.value == exp_wants_z, f"{name} wants Z"


# ==========================================
# NAND FAMILY TESTS
# ==========================================


@cocotb.test()
async def test_decoder_nand_family(dut):
    """Test all NAND family instructions"""
    await setup_decoder(dut)

    test_cases = [
        (NDU(1, 2, 3), 0, 0b00, "NDU", False, True, False, False),
        (NDC(1, 2, 3), 0, 0b10, "NDC", False, True, True, False),
        (NDZ(1, 2, 3), 0, 0b01, "NDZ", False, True, False, True),
        (NCU(1, 2, 3), 1, 0b00, "NCU", False, True, False, False),
        (NCC(1, 2, 3), 1, 0b10, "NCC", False, True, True, False),
        (NCZ(1, 2, 3), 1, 0b01, "NCZ", False, True, False, True),
    ]

    for (
        instr,
        exp_complet,
        exp_cz,
        name,
        exp_writes_c,
        exp_writes_z,
        exp_wants_c,
        exp_wants_z,
    ) in test_cases:
        dut.instruction.value = instr
        await Timer(2, unit="ns")

        assert dut.complet_bit.value == exp_complet, f"{name} complet bit"
        assert dut.cz_flags.value == exp_cz, f"{name} CZ flags"
        assert dut.dest_reg.value == 3, f"{name} destination reg"
        assert (
            dut.writes_c_flag.value == exp_writes_c
        ), f"{name} writes C (should be 0 for NAND)"
        assert dut.writes_z_flag.value == exp_writes_z, f"{name} writes Z"
        assert dut.wants_c_flag.value == exp_wants_c, f"{name} wants C"
        assert dut.wants_z_flag.value == exp_wants_z, f"{name} wants Z"


# ==========================================
# DESTINATION TESTS
# ==========================================


@cocotb.test()
async def test_decoder_destinations(dut):
    """Test destination register for each instruction type"""
    await setup_decoder(dut)

    # R-Type: destination = rc
    dut.instruction.value = ADA(ra=1, rb=2, rc=7)
    await Timer(2, unit="ns")
    assert dut.dest_reg.value == 7

    # I-Type (ADI, LW): destination = rb
    dut.instruction.value = ADI(ra=1, rb=6, imm6=10)
    await Timer(2, unit="ns")
    assert dut.dest_reg.value == 6

    dut.instruction.value = LW(ra=1, rb=5, imm6=10)
    await Timer(2, unit="ns")
    assert dut.dest_reg.value == 5

    # J-Type (LLI, JAL): destination = ra
    dut.instruction.value = LLI(ra=4, imm9=100)
    await Timer(2, unit="ns")
    assert dut.dest_reg.value == 4

    dut.instruction.value = JAL(ra=3, imm9=100)
    await Timer(2, unit="ns")
    assert dut.dest_reg.value == 3

    # No destination instructions
    for instr in [
        SW(1, 2, 10),
        BEQ(1, 2, 10),
        BLT(1, 2, 10),
        BLE(1, 2, 10),
        JRI(1, 100),
    ]:
        dut.instruction.value = instr
        await Timer(2, unit="ns")
        assert dut.dest_valid.value == 0


# ==========================================
# BRANCH DETECTION TESTS
# ==========================================


@cocotb.test()
async def test_decoder_branch_detection(dut):
    """Test branch instruction detection"""
    await setup_decoder(dut)

    branches = [
        ("BEQ", BEQ(0, 0, 0)),
        ("BLT", BLT(0, 0, 0)),
        ("BLE", BLE(0, 0, 0)),
        ("JAL", JAL(0, 0)),
        ("JLR", JLR(0, 0)),
        ("JRI", JRI(0, 0)),
    ]

    for name, instr in branches:
        dut.instruction.value = instr
        await Timer(2, unit="ns")
        assert dut.is_branch.value == 1, f"{name} should be branch"

    # Non-branch instructions
    non_branches = [ADA(0, 0, 0), ADI(0, 0, 0), LW(0, 0, 0), SW(0, 0, 0), LLI(0, 0)]
    for instr in non_branches:
        dut.instruction.value = instr
        await Timer(2, unit="ns")
        assert dut.is_branch.value == 0


# ==========================================
# IMPLICIT BRANCH TEST (Writing to R0)
# ==========================================


@cocotb.test()
async def test_decoder_implicit_branch(dut):
    """Test writing to R0 causes implicit branch"""
    await setup_decoder(dut)

    # Writing to R0 (dest_reg=0) should set is_implicit_branch
    dut.instruction.value = ADA(ra=1, rb=2, rc=0)  # rc=0 means R0
    await Timer(2, unit="ns")
    assert dut.is_implicit_branch.value == 1

    # Writing to other register (R3) should not
    dut.instruction.value = ADA(ra=1, rb=2, rc=3)
    await Timer(2, unit="ns")
    assert dut.is_implicit_branch.value == 0


# ==========================================
# COMPLEX MEMORY TESTS
# ==========================================


@cocotb.test()
async def test_decoder_complex_memory(dut):
    """Test LM/SM detection"""
    await setup_decoder(dut)

    # LM should be complex memory
    dut.instruction.value = LM(ra=0, bitmap=0xFF)
    await Timer(2, unit="ns")
    assert dut.is_complex_mem.value == 1
    assert dut.is_load_multiple.value == 1
    assert dut.is_store_multiple.value == 0

    # SM should be complex memory
    dut.instruction.value = SM(ra=0, bitmap=0xFF)
    await Timer(2, unit="ns")
    assert dut.is_complex_mem.value == 1
    assert dut.is_load_multiple.value == 0
    assert dut.is_store_multiple.value == 1

    # LMF should also be complex memory
    dut.instruction.value = LMF(ra=0, bitmap=0xFF)
    await Timer(2, unit="ns")
    assert dut.is_complex_mem.value == 1


# ==========================================
# RANDOMIZED TEST
# ==========================================


@cocotb.test()
async def test_decoder_random(dut):
    """Randomized test comparing decoder outputs against golden model"""
    await setup_decoder(dut)

    # Golden model for instruction info
    def get_instruction_info(instr):
        opcode = (instr >> 12) & 0xF

        info = {
            # ADI: writes both flags
            0b0000: {"dest_valid": 1, "writes_c": 1, "writes_z": 1, "is_branch": 0},
            # ADD Family: writes both flags
            0b0001: {"dest_valid": 1, "writes_c": 1, "writes_z": 1, "is_branch": 0},
            # NAND Family: writes Z only (not C)
            0b0010: {"dest_valid": 1, "writes_c": 0, "writes_z": 1, "is_branch": 0},
            # LLI: writes Z only
            0b0011: {"dest_valid": 1, "writes_c": 0, "writes_z": 1, "is_branch": 0},
            # LW: writes Z only
            0b0100: {"dest_valid": 1, "writes_c": 0, "writes_z": 1, "is_branch": 0},
            # SW: no writes
            0b0101: {"dest_valid": 0, "writes_c": 0, "writes_z": 0, "is_branch": 0},
            # LM/LMF: no writes (sequencer handles)
            0b0110: {
                "dest_valid": 0,
                "writes_c": 0,
                "writes_z": 0,
                "is_branch": 0,
                "complex_mem": 1,
            },
            # SM/SMF: no writes
            0b0111: {
                "dest_valid": 0,
                "writes_c": 0,
                "writes_z": 0,
                "is_branch": 0,
                "complex_mem": 1,
            },
            # BEQ, BLT, BLE: no writes
            0b1000: {"dest_valid": 0, "writes_c": 0, "writes_z": 0, "is_branch": 1},
            0b1001: {"dest_valid": 0, "writes_c": 0, "writes_z": 0, "is_branch": 1},
            0b1010: {"dest_valid": 0, "writes_c": 0, "writes_z": 0, "is_branch": 1},
            # JAL: writes destination, no flags
            0b1100: {"dest_valid": 1, "writes_c": 0, "writes_z": 0, "is_branch": 1},
            # JLR: writes destination, no flags
            0b1101: {"dest_valid": 1, "writes_c": 0, "writes_z": 0, "is_branch": 1},
            # JRI: no destination, no flags
            0b1111: {"dest_valid": 0, "writes_c": 0, "writes_z": 0, "is_branch": 1},
        }

        return info.get(
            opcode, {"dest_valid": 0, "writes_c": 0, "writes_z": 0, "is_branch": 0}
        )

    # Test random instructions
    for _ in range(100):
        # Generate random instruction
        opcode = random.choice([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 15])
        ra = random.randint(0, 7)
        rb = random.randint(0, 7)
        rc = random.randint(0, 7)
        imm6 = random.randint(0, 0x3F)
        imm9 = random.randint(0, 0x1FF)

        if opcode == 1:  # ADD family
            complet = random.randint(0, 1)
            cz = random.randint(0, 3)
            instr = build_r_type(opcode, ra, rb, rc, complet, cz)
        elif opcode == 2:  # NAND family
            complet = random.randint(0, 1)
            cz = random.choice([0, 1, 2])  # 3 is reserved
            instr = build_r_type(opcode, ra, rb, rc, complet, cz)
        elif opcode in [0, 4, 5, 8, 9, 10, 13]:  # I-Type
            instr = build_i_type(opcode, ra, rb, imm6)
        else:  # J-Type
            instr = build_j_type(opcode, ra, imm9)

        dut.instruction.value = instr
        await Timer(2, unit="ns")

        expected = get_instruction_info(instr)

        # After setting dut.instruction.value and Timer
        if dut.writes_c_flag.value != expected["writes_c"]:
            dut._log.info(f"FAIL: instr=0x{instr:04X}, opcode=0x{opcode:01X}")
            dut._log.info(
                f"  writes_c_flag: got={dut.writes_c_flag.value}, exp={expected['writes_c']}"
            )
            dut._log.info(
                f"  writes_z_flag: got={dut.writes_z_flag.value}, exp={expected['writes_z']}"
            )
            dut._log.info(
                f"  dest_valid: got={dut.dest_valid.value}, exp={expected['dest_valid']}"
            )
            dut._log.info(
                f"  is_branch: got={dut.is_branch.value}, exp={expected['is_branch']}"
            )
            # Also print the raw instruction fields
            dut._log.info(f"  opcode field = {(instr >> 12) & 0xF}")
            dut._log.info(f"  complet bit = {(instr >> 2) & 1}")
            dut._log.info(f"  cz bits = {instr & 0x3}")

        # Verify
        assert dut.dest_valid.value == expected["dest_valid"]
        assert dut.writes_c_flag.value == expected["writes_c"]
        assert dut.writes_z_flag.value == expected["writes_z"]
        assert dut.is_branch.value == expected["is_branch"]
