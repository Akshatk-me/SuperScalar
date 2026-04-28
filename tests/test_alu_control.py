import cocotb
import pytest
from cocotb.triggers import Timer

# ALU operation codes
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

# Test data: (alu_op, funct, expected_ctrl, description)
ADD_FAMILY_TESTS = [
    # (funct, expected_op, description)
    (0b000, OP_ADD, "ADA (Add)"),
    (0b001, OP_ADDIFZ, "ADZ (Add if Zero)"),
    (0b010, OP_ADDIFC, "ADC (Add if Carry)"),
    (0b011, OP_ADDWC, "AWC (Add with Carry)"),
    (0b100, OP_ADD, "ACA (Add Complement)"),
    (0b101, OP_ADDIFZ, "ACZ (Add Complement if Zero)"),
    (0b110, OP_ADDIFC, "ACC (Add Complement if Carry)"),
    (0b111, OP_ADDWC, "ACW (Add Complement with Carry)"),
]

NAND_FAMILY_TESTS = [
    (0b000, OP_NAND, "NDU (NAND)"),
    (0b001, OP_NANDIFZ, "NDZ (NAND if Zero)"),
    (0b010, OP_NANDIFC, "NDC (NAND if Carry)"),
    (0b100, OP_NAND, "NCU (NAND Complement)"),
    (0b101, OP_NANDIFZ, "NCZ (NAND Complement if Zero)"),
    (0b110, OP_NANDIFC, "NCC (NAND Complement if Carry)"),
]

BRANCH_TESTS = [
    (0b1000, "BEQ"),
    (0b1001, "BLT/BLE"),
]

LOAD_STORE_TESTS = [
    (0b0100, "LW"),
    (0b0101, "SW"),
    (0b0110, "LM/LMF"),
    (0b0111, "SM/SMF"),
]

JUMP_TESTS = [
    (0b1100, OP_PASS, "JAL"),
    (0b1101, OP_PASS, "JLR"),
    (0b1111, OP_ADD, "JRI"),
]


async def check_alu_ctrl(dut, alu_op, funct, expected_ctrl, description):
    """Helper to test a single case"""
    dut.alu_op.value = alu_op
    dut.funct.value = funct
    await Timer(1, unit="ns")

    actual = dut.alu_ctrl.value.to_unsigned()
    assert (
        actual == expected_ctrl
    ), f"{description}: got {actual:05b}, expected {expected_ctrl:05b}"
    dut._log.info(f"{description} -> alu_ctrl={actual:05b}")


@cocotb.test()
async def test_adi(dut):
    await check_alu_ctrl(
        dut, alu_op=0b0000, funct=0b000, expected_ctrl=OP_ADD, description="ADI"
    )


@cocotb.test()
async def test_lli(dut):
    await check_alu_ctrl(
        dut, alu_op=0b0011, funct=0b000, expected_ctrl=OP_LLI, description="LLI"
    )


# Parametrized tests using pytest (but cocotb doesn't play nice with @pytest.mark.parametrize)
# So we loop inside each test
@cocotb.test()
async def test_add_family(dut):
    for funct, expected_op, desc in ADD_FAMILY_TESTS:
        complement = (funct >> 2) & 1
        expected = (complement << 4) | expected_op
        await check_alu_ctrl(
            dut, alu_op=0b0001, funct=funct, expected_ctrl=expected, description=desc
        )


@cocotb.test()
async def test_nand_family(dut):
    for funct, expected_op, desc in NAND_FAMILY_TESTS:
        complement = (funct >> 2) & 1
        expected = (complement << 4) | expected_op
        await check_alu_ctrl(
            dut, alu_op=0b0010, funct=funct, expected_ctrl=expected, description=desc
        )


@cocotb.test()
async def test_branch(dut):
    for alu_op, desc in BRANCH_TESTS:
        await check_alu_ctrl(
            dut, alu_op=alu_op, funct=0b000, expected_ctrl=OP_COMPARE, description=desc
        )


@cocotb.test()
async def test_load_store(dut):
    for alu_op, desc in LOAD_STORE_TESTS:
        await check_alu_ctrl(
            dut, alu_op=alu_op, funct=0b000, expected_ctrl=OP_PASS, description=desc
        )


@cocotb.test()
async def test_jump(dut):
    for alu_op, expected_op, desc in JUMP_TESTS:
        await check_alu_ctrl(
            dut, alu_op=alu_op, funct=0b000, expected_ctrl=expected_op, description=desc
        )


@cocotb.test()
async def test_invalid_opcode(dut):
    await check_alu_ctrl(
        dut,
        alu_op=0b1010,
        funct=0b000,
        expected_ctrl=OP_PASS,
        description="Invalid opcode",
    )
