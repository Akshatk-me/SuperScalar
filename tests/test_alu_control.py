import cocotb
from cocotb.triggers import Timer

# ALU Operation Codes (expected outputs)
OP_ADD = 0b0000
OP_ADDIFC = 0b0001
OP_ADDIFZ = 0b0010
OP_ADDWC = 0b0011
OP_NAND = 0b0100
OP_NANDIFC = 0b0101
OP_NANDIFZ = 0b0110
OP_COMPARE = 0b0111
OP_PASS = 0b1000
OP_LLI = 0b1001

# 4-bit opcodes from IITB-RISC ISA (from the document)
OPCODE_ADI = 0b0000  # Add Immediate (I-Type)
OPCODE_ADD_FAMILY = 0b0001  # ADA, ADC, ADZ, AWC and complements (R-Type)
OPCODE_NAND_FAMILY = 0b0010  # NDU, NDC, NDZ, NCU, NCC, NCZ (R-Type)
OPCODE_LLI = 0b0011  # Load Lower Immediate (J-Type)
OPCODE_LW = 0b0100  # Load Word (I-Type)
OPCODE_SW = 0b0101  # Store Word (I-Type)
OPCODE_LM_LMF = 0b0110  # Load Multiple (J-Type)
OPCODE_SM_SMF = 0b0111  # Store Multiple (J-Type)
OPCODE_BEQ = 0b1000  # Branch if Equal (I-Type)
OPCODE_BLT_BLE = 0b1001  # Branch if Less Than/Equal (I-Type)
OPCODE_JAL = 0b1100  # Jump and Link (J-Type)
OPCODE_JLR = 0b1101  # Jump and Link Register (I-Type)
OPCODE_JRI = 0b1111  # Jump Register Immediate (J-Type)


async def set_alu_control_inputs(dut, alu_op, funct):
    """Helper to set ALU_Control inputs"""
    dut.alu_op.value = alu_op
    dut.funct.value = funct
    await Timer(1, units="ns")


@cocotb.test()
async def test_control_adi(dut):
    """Test ADI (Add Immediate) - I-Type"""
    dut._log.info("Testing ADI instruction")

    await set_alu_control_inputs(dut, alu_op=OPCODE_ADI, funct=0b000)

    # ADI should output OP_ADD with complement=0
    expected = (0 << 4) | OP_ADD  # 0b00000
    actual = dut.alu_ctrl.value.integer

    assert actual == expected, f"ADI failed: got {actual:05b}, expected {expected:05b}"
    dut._log.info(f"ADI -> alu_ctrl = {actual:05b}")


@cocotb.test()
async def test_control_add_family(dut):
    """Test all ADD family instructions (ADA, ADC, ADZ, AWC, ACA, ACC, ACZ, ACW)"""
    dut._log.info("Testing ADD family instructions")

    test_cases = [
        # (funct[COMPL][CZ], expected_op, description)
        (0b000, OP_ADD, "ADA (Add)"),
        (0b001, OP_ADDIFZ, "ADZ (Add if Zero)"),
        (0b010, OP_ADDIFC, "ADC (Add if Carry)"),
        (0b011, OP_ADDWC, "AWC (Add with Carry)"),
        # With complement (COMPL=1) - Note: CZ bits same as above
        (0b100, OP_ADD, "ACA (Add Complement)"),
        (0b101, OP_ADDIFZ, "ACZ (Add Complement if Zero)"),
        (0b110, OP_ADDIFC, "ACC (Add Complement if Carry)"),
        (0b111, OP_ADDWC, "ACW (Add Complement with Carry)"),
    ]

    for funct, expected_op, desc in test_cases:
        await set_alu_control_inputs(dut, alu_op=OPCODE_ADD_FAMILY, funct=funct)

        complement = (funct >> 2) & 1
        expected = (complement << 4) | expected_op
        actual = dut.alu_ctrl.value.integer

        assert (
            actual == expected
        ), f"{desc} failed: got {actual:05b}, expected {expected:05b}"
        dut._log.info(f"{desc}: funct={funct:03b} -> alu_ctrl={actual:05b}")


@cocotb.test()
async def test_control_nand_family(dut):
    """Test all NAND family instructions (NDU, NDC, NDZ, NCU, NCC, NCZ)"""
    dut._log.info("Testing NAND family instructions")

    test_cases = [
        # Without complement (COMPL=0)
        (0b000, OP_NAND, "NDU (NAND)"),
        (0b001, OP_NANDIFZ, "NDZ (NAND if Zero)"),
        (0b010, OP_NANDIFC, "NDC (NAND if Carry)"),
        (0b011, OP_NAND, "NDU (NAND - default)"),  # CZ=11 defaults to NAND
        # With complement (COMPL=1)
        (0b100, OP_NAND, "NCU (NAND Complement)"),
        (0b101, OP_NANDIFZ, "NCZ (NAND Complement if Zero)"),
        (0b110, OP_NANDIFC, "NCC (NAND Complement if Carry)"),
        (0b111, OP_NAND, "NCU (NAND Complement - default)"),
    ]

    for funct, expected_op, desc in test_cases:
        await set_alu_control_inputs(dut, alu_op=OPCODE_NAND_FAMILY, funct=funct)

        complement = (funct >> 2) & 1
        expected = (complement << 4) | expected_op
        actual = dut.alu_ctrl.value.integer

        assert (
            actual == expected
        ), f"{desc} failed: got {actual:05b}, expected {expected:05b}"
        dut._log.info(f"{desc}: funct={funct:03b} -> alu_ctrl={actual:05b}")


@cocotb.test()
async def test_control_lli(dut):
    """Test LLI (Load Lower Immediate) - J-Type"""
    dut._log.info("Testing LLI instruction")

    await set_alu_control_inputs(dut, alu_op=OPCODE_LLI, funct=0b000)

    # LLI should output OP_LLI with complement=0
    expected = (0 << 4) | OP_LLI  # 0b01001
    actual = dut.alu_ctrl.value.integer

    assert actual == expected, f"LLI failed: got {actual:05b}, expected {expected:05b}"
    dut._log.info(f"LLI -> alu_ctrl = {actual:05b}")


@cocotb.test()
async def test_control_branch(dut):
    """Test branch instructions (BEQ, BLT, BLE)"""
    dut._log.info("Testing branch instructions")

    test_cases = [
        (OPCODE_BEQ, "BEQ"),
        (OPCODE_BLT_BLE, "BLT/BLE"),  # Note: BLT and BLE share same opcode
    ]

    for alu_op, desc in test_cases:
        await set_alu_control_inputs(dut, alu_op=alu_op, funct=0b000)

        # Branches should output OP_COMPARE
        expected = (0 << 4) | OP_COMPARE  # 0b00111
        actual = dut.alu_ctrl.value.integer

        assert (
            actual == expected
        ), f"{desc} failed: got {actual:05b}, expected {expected:05b}"
        dut._log.info(f"{desc}: alu_op={alu_op:04b} -> alu_ctrl={actual:05b}")


@cocotb.test()
async def test_control_load_store(dut):
    """Test load/store instructions (LW, SW, LM, SM)"""
    dut._log.info("Testing load/store instructions")

    test_cases = [
        (OPCODE_LW, "LW"),
        (OPCODE_SW, "SW"),
        (OPCODE_LM_LMF, "LM/LMF"),
        (OPCODE_SM_SMF, "SM/SMF"),
    ]

    for alu_op, desc in test_cases:
        await set_alu_control_inputs(dut, alu_op=alu_op, funct=0b000)

        # Load/Store should output OP_PASS for address calculation
        expected = (0 << 4) | OP_PASS  # 0b01000
        actual = dut.alu_ctrl.value.integer

        assert (
            actual == expected
        ), f"{desc} failed: got {actual:05b}, expected {expected:05b}"
        dut._log.info(f"{desc}: alu_op={alu_op:04b} -> alu_ctrl={actual:05b}")


@cocotb.test()
async def test_control_jump(dut):
    """Test jump instructions (JAL, JLR, JRI)"""
    dut._log.info("Testing jump instructions")

    test_cases = [
        (OPCODE_JAL, "JAL", OP_PASS),  # JAL: passes PC+2
        (OPCODE_JLR, "JLR", OP_PASS),  # JLR: passes address from regB
        (OPCODE_JRI, "JRI", OP_ADD),  # JRI: RA + Imm*2
    ]

    for alu_op, desc, expected_op in test_cases:
        await set_alu_control_inputs(dut, alu_op=alu_op, funct=0b000)

        expected = (0 << 4) | expected_op
        actual = dut.alu_ctrl.value.integer

        assert (
            actual == expected
        ), f"{desc} failed: got {actual:05b}, expected {expected:05b}"
        dut._log.info(f"{desc}: alu_op={alu_op:04b} -> alu_ctrl={actual:05b}")


@cocotb.test()
async def test_control_all_add_funct_combinations(dut):
    """Test ALL 8 funct combinations for ADD family"""
    dut._log.info("Testing all 8 funct combinations for ADD family")

    for funct in range(8):
        await set_alu_control_inputs(dut, alu_op=OPCODE_ADD_FAMILY, funct=funct)

        complement = (funct >> 2) & 1
        cz = funct & 0b11

        # Map CZ bits to operation based on ADD family
        if cz == 0b00:
            expected_op = OP_ADD
        elif cz == 0b01:
            expected_op = OP_ADDIFZ
        elif cz == 0b10:
            expected_op = OP_ADDIFC
        else:  # 0b11
            expected_op = OP_ADDWC

        expected = (complement << 4) | expected_op
        actual = dut.alu_ctrl.value.integer

        dut._log.info(
            f"funct={funct:03b} -> complement={complement}, CZ={cz:02b} -> alu_ctrl={actual:05b}"
        )
        assert (
            actual == expected
        ), f"ADD family funct={funct:03b}: got {actual:05b}, expected {expected:05b}"


@cocotb.test()
async def test_control_all_nand_funct_combinations(dut):
    """Test ALL 8 funct combinations for NAND family"""
    dut._log.info("Testing all 8 funct combinations for NAND family")

    for funct in range(8):
        await set_alu_control_inputs(dut, alu_op=OPCODE_NAND_FAMILY, funct=funct)

        complement = (funct >> 2) & 1
        cz = funct & 0b11

        # Map CZ bits to operation based on NAND family
        if cz == 0b00:
            expected_op = OP_NAND
        elif cz == 0b01:
            expected_op = OP_NANDIFZ
        elif cz == 0b10:
            expected_op = OP_NANDIFC
        else:  # 0b11 - default to NAND as per spec
            expected_op = OP_NAND

        expected = (complement << 4) | expected_op
        actual = dut.alu_ctrl.value.integer

        dut._log.info(
            f"funct={funct:03b} -> complement={complement}, CZ={cz:02b} -> alu_ctrl={actual:05b}"
        )
        assert (
            actual == expected
        ), f"NAND family funct={funct:03b}: got {actual:05b}, expected {expected:05b}"


@cocotb.test()
async def test_control_invalid_opcode(dut):
    """Test behavior with invalid/undefined opcode"""
    dut._log.info("Testing invalid opcode handling")

    # Test with an undefined opcode (e.g., 0b1010)
    await set_alu_control_inputs(dut, alu_op=0b1010, funct=0b000)

    # Should default to OP_PASS
    expected = (0 << 4) | OP_PASS
    actual = dut.alu_ctrl.value.integer

    dut._log.info(f"Invalid opcode 0b1010 -> alu_ctrl={actual:05b}")
    assert (
        actual == expected
    ), f"Invalid opcode handling failed: got {actual:05b}, expected {expected:05b}"


@cocotb.test()
async def test_control_specific_example_from_spec(dut):
    """Test a specific example from the specification"""
    dut._log.info("Testing specific examples from spec")

    # Example: ADC (Add if Carry) should be:
    # - Opcode: ADD_FAMILY (0b0001)
    # - funct: CZ=10 (Carry), COMPL=0 -> 0b010
    await set_alu_control_inputs(dut, alu_op=OPCODE_ADD_FAMILY, funct=0b010)

    # Should output: complement=0, OP_ADDIFC=0001 -> 0b00001
    expected = 0b00001
    actual = dut.alu_ctrl.value.integer

    assert (
        actual == expected
    ), f"ADC example failed: got {actual:05b}, expected {expected:05b}"
    dut._log.info(f"ADC (Add if Carry) -> alu_ctrl={actual:05b}")
