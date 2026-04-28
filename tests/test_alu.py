import random

import cocotb
from cocotb.triggers import Timer

# Replicate VHDL constants in Python
OP_ADD = 0b0000
OP_ADDIFC = 0b0001
OP_ADDIFZ = 0b0010
OP_ADDWC = 0b0011
OP_NAND = 0b0100
OP_COMPAREBEQ = 0b0111
# ... Add the rest as needed


async def set_alu_inputs(dut, data1, data2, ctrl, c_in=0, z_in=0):
    dut.data1.value = data1
    dut.data2.value = data2
    dut.alu_control.value = ctrl
    dut.c_in.value = c_in
    dut.z_in.value = z_in
    await Timer(1, unit="ns")


@cocotb.test()
async def test_alu_addition(dut):
    """Test basic addition operation without complement."""
    # Test a few random values
    for _ in range(10):
        a = random.randint(0, 0x7FFF)
        b = random.randint(0, 0x7FFF)

        await set_alu_inputs(dut, a, b, OP_ADD)

        expected = a + b
        dut._log.info(f"10, 5 gave ADDIFC {dut.alu_result.value}")
        assert (
            dut.alu_result.value == expected
        ), f"ADD Failed: {a} + {b} != {dut.alu_result.value}"

        # Check Zero flag
        expected_z = 1 if expected == 0 else 0
        assert dut.zero.value == expected_z, "Zero flag incorrect"


@cocotb.test()
async def test_alu_nand(dut):
    """Test basic NAND operation."""
    a = 0xAAAA
    b = 0x5555
    await set_alu_inputs(dut, a, b, OP_NAND)

    # Python bitwise NAND for 16-bit
    expected = ~(a & b) & 0xFFFF
    assert dut.alu_result.value == expected, "NAND Failed"


@cocotb.test()
async def test_alu_conditional_add(dut):
    """Test ADDIFC (Add if Carry is set)."""
    a = 10
    b = 5

    # If c_in is 0, it should probably just output data1 (or 0, depending on your architecture)
    # Assuming it outputs data1 if condition fails:
    await set_alu_inputs(dut, a, b, OP_ADDIFC, c_in=0)
    # Modify this assertion based on your actual VHDL logic for a failed condition
    dut._log.info(f"10, 5 gave ADDIFC {dut.alu_result.value}")
    assert dut.alu_result.value == a, "ADDIFC failed when c_in=0"

    # If c_in is 1, it should add
    await set_alu_inputs(dut, a, b, OP_ADDIFC, c_in=1)
    assert dut.alu_result.value == 15, "ADDIFC failed when c_in=1"
