# TODO(akshat): Create documentation on what all is tested exactly @medium file:golden_model.py

import random

import cocotb
from cocotb.triggers import Timer

# ALU Operation Codes
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


async def set_alu_inputs(dut, data1, data2, alu_control, c_in=0, z_in=0):
    """Helper to set ALU inputs"""
    dut.data1.value = data1
    dut.data2.value = data2
    dut.alu_control.value = alu_control
    dut.c_in.value = c_in
    dut.z_in.value = z_in
    await Timer(2, unit="ns")


# Operation configuration: (opcode, has_condition, uses_carry, uses_zero, is_nand)
OP_CONFIG = {
    OP_ADD: {
        "has_condition": False,
        "uses_carry": False,
        "uses_zero": False,
        "is_nand": False,
    },
    OP_ADDIFC: {
        "has_condition": True,
        "uses_carry": True,
        "uses_zero": False,
        "is_nand": False,
    },
    OP_ADDIFZ: {
        "has_condition": True,
        "uses_carry": False,
        "uses_zero": True,
        "is_nand": False,
    },
    OP_ADDWC: {
        "has_condition": False,
        "uses_carry": True,
        "uses_zero": False,
        "is_nand": False,
    },
    OP_NAND: {
        "has_condition": False,
        "uses_carry": False,
        "uses_zero": False,
        "is_nand": True,
    },
    OP_NANDIFC: {
        "has_condition": True,
        "uses_carry": True,
        "uses_zero": False,
        "is_nand": True,
    },
    OP_NANDIFZ: {
        "has_condition": True,
        "uses_carry": False,
        "uses_zero": True,
        "is_nand": True,
    },
    OP_LLI: {
        "has_condition": False,
        "uses_carry": False,
        "uses_zero": False,
        "is_nand": False,
        "is_lli": True,
    },
}

NUM_RANDOM_TESTS = 50
MAX_16BIT = 0xFFFF


def compute_expected(op, a, b, c_in=0, z_in=0):
    """Golden model for ALU operations"""
    config = OP_CONFIG.get(op, {})

    # Handle conditional execution
    if config.get("has_condition", False):
        if (config.get("uses_carry", False) and c_in == 0) or (
            config.get("uses_zero", False) and z_in == 0
        ):
            # Condition failed - return data1
            return a, 0, (1 if a == 0 else 0)

    # Perform the actual operation
    if config.get("is_lli", False):
        # LLI: lower 9 bits from b, upper 7 bits zero
        result = b & 0x1FF
        carry = 0
    elif config.get("is_nand", False):
        # NAND operation (carry always 0)
        result = (~(a & b)) & MAX_16BIT
        carry = 0
    else:
        if op == OP_ADDWC:
            total = a + b + c_in
        else:
            total = a + b
        # ADD operations
        result = total & MAX_16BIT
        carry = 1 if total > MAX_16BIT else 0

    zero = 1 if result == 0 else 0
    return result, carry, zero


async def test_alu_op(dut, op, description, num_tests=NUM_RANDOM_TESTS):
    """Generic test function for any ALU operation"""
    config = OP_CONFIG.get(op, {})
    dut._log.info(f"Starting {description} tests")

    for i in range(num_tests):
        a = random.randint(0, MAX_16BIT)
        b = random.randint(0, MAX_16BIT)
        c_in = random.randint(0, 1) if config.get("uses_carry", False) else 0
        z_in = random.randint(0, 1) if config.get("uses_zero", False) else 0

        expected, expected_carry, expected_zero = compute_expected(op, a, b, c_in, z_in)

        dut.data1.value = a
        dut.data2.value = b
        dut.alu_control.value = op
        dut.c_in.value = c_in
        dut.z_in.value = z_in
        await Timer(2, unit="ns")

        actual = dut.alu_result.value
        actual_carry = dut.carry.value
        actual_zero = dut.zero.value

        assert (
            actual == expected
        ), f"{description} #{i}: {a:#06x} op {b:#06x} (c={c_in},z={z_in}) -> got {actual:#06x}, expected {expected:#06x}"

        if config.get("uses_carry", False) or not config.get("is_nand", False):
            assert (
                actual_carry == expected_carry
            ), f"{description} #{i}: carry got {actual_carry}, expected {expected_carry}"

        assert (
            actual_zero == expected_zero
        ), f"{description} #{i}: zero got {actual_zero}, expected {expected_zero}"


# ============= Individual Tests (one per op for pytest discovery) =============


@cocotb.test()
async def test_alu_add(dut):
    await test_alu_op(dut, OP_ADD, "ADD")


@cocotb.test()
async def test_alu_addifc(dut):
    await test_alu_op(dut, OP_ADDIFC, "ADDIFC")


@cocotb.test()
async def test_alu_addifz(dut):
    await test_alu_op(dut, OP_ADDIFZ, "ADDIFZ")


@cocotb.test()
async def test_alu_addwc(dut):
    await test_alu_op(dut, OP_ADDWC, "ADDWC")


@cocotb.test()
async def test_alu_nand(dut):
    await test_alu_op(dut, OP_NAND, "NAND")


@cocotb.test()
async def test_alu_nandifc(dut):
    await test_alu_op(dut, OP_NANDIFC, "NANDIFC")


@cocotb.test()
async def test_alu_nandifz(dut):
    await test_alu_op(dut, OP_NANDIFZ, "NANDIFZ")


@cocotb.test()
async def test_alu_lli(dut):
    await test_alu_op(dut, OP_LLI, "LLI")


# ============= Edge Cases =============


@cocotb.test()
async def test_alu_edge_cases(dut):
    """Test specific edge cases for all operations"""
    dut._log.info("Testing edge cases")

    edge_values = [0, 1, MAX_16BIT, MAX_16BIT - 1, 0x8000, 0x7FFF]
    ops_to_test = [
        OP_ADD,
        OP_ADDIFC,
        OP_ADDIFZ,
        OP_ADDWC,
        OP_NAND,
        OP_NANDIFC,
        OP_NANDIFZ,
    ]

    for op in ops_to_test:
        config = OP_CONFIG.get(op, {})
        for a in edge_values:
            for b in edge_values:
                for c_in in ([0, 1] if config.get("uses_carry", False) else [0]):
                    for z_in in ([0, 1] if config.get("uses_zero", False) else [0]):
                        expected, exp_carry, exp_zero = compute_expected(
                            op, a, b, c_in, z_in
                        )

                        dut.data1.value = a
                        dut.data2.value = b
                        dut.alu_control.value = op
                        dut.c_in.value = c_in
                        dut.z_in.value = z_in
                        await Timer(2, unit="ns")

                        actual = dut.alu_result.value
                        assert (
                            actual == expected
                        ), f"Edge: op={op:04b}, a={a:#06x}, b={b:#06x}, c={c_in}, z={z_in} -> got {actual:#06x}, exp {expected:#06x}"


# ============= Comparison Operations (BEQ/BLT/BLE) =============


@cocotb.test()
async def test_alu_comparisons(dut):
    """Test comparison outputs for branch conditions"""
    dut._log.info("Starting comparison tests")

    test_cases = [
        # (a, b, expected_eq, expected_lt, expected_le)
        (5, 5, 1, 0, 1),
        (3, 5, 0, 1, 1),
        (5, 3, 0, 0, 0),
        (0, 0, 1, 0, 1),
        (0xFFFF, 0, 0, 0, 0),  # Unsigned comparison
        (0, 0xFFFF, 0, 1, 1),
        (0x7FFF, 0x8000, 0, 1, 1),
        (0x8000, 0x7FFF, 0, 0, 0),
    ]

    for a, b, exp_eq, exp_lt, exp_le in test_cases:
        await set_alu_inputs(dut, a, b, OP_COMPARE)

        actual_eq = dut.eq.value
        actual_lt = dut.lt.value
        actual_le = dut.le.value

        assert (
            actual_eq == exp_eq
        ), f"EQ: {a} vs {b} -> got {actual_eq}, expected {exp_eq}"
        assert (
            actual_lt == exp_lt
        ), f"LT: {a} vs {b} -> got {actual_lt}, expected {exp_lt}"
        assert (
            actual_le == exp_le
        ), f"LE: {a} vs {b} -> got {actual_le}, expected {exp_le}"

        dut._log.info(
            f"CMP {a:#06x} vs {b:#06x}: EQ={actual_eq}, LT={actual_lt}, LE={actual_le}"
        )


# ============= Pass-through Test =============


@cocotb.test()
async def test_alu_pass(dut):
    """Test OP_PASS - should just output data2"""
    dut._log.info("Testing PASS operation")

    for _ in range(NUM_RANDOM_TESTS):
        data2 = random.randint(0, MAX_16BIT)
        await set_alu_inputs(dut, data1=0, data2=data2, alu_control=OP_PASS)

        actual = dut.alu_result.value
        assert actual == data2, f"PASS: expected {data2:#06x}, got {actual:#06x}"
