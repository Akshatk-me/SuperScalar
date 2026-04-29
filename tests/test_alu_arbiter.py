import cocotb
from cocotb.triggers import Timer


async def setup_arbiter(dut):
    """Initialize arbiter inputs"""
    dut.req.value = 0
    await Timer(2, unit="ns")


@cocotb.test()
async def test_arbiter_single_request(dut):
    """Test arbiter with single request"""
    await setup_arbiter(dut)

    # Request from entry 0 only
    dut.req.value = 0b0001
    await Timer(2, unit="ns")

    assert dut.valid_1.value == 1, "valid_1 should be 1"
    assert dut.valid_2.value == 0, "valid_2 should be 0"
    assert dut.grant_idx_1.value == 0, "grant_idx_1 should be 0"
    assert dut.grant_bus.value == 0b0001, "grant_bus should have bit0 set"

    # Request from entry 2 only
    dut.req.value = 0b0100
    await Timer(2, unit="ns")

    assert dut.valid_1.value == 1
    assert dut.valid_2.value == 0
    assert dut.grant_idx_1.value == 2
    assert dut.grant_bus.value == 0b0100


@cocotb.test()
async def test_arbiter_two_requests(dut):
    """Test arbiter with two requests"""
    await setup_arbiter(dut)

    # Request from entries 0 and 1
    dut.req.value = 0b0011
    await Timer(2, unit="ns")

    assert dut.valid_1.value == 1, "valid_1 should be 1"
    assert dut.valid_2.value == 1, "valid_2 should be 1"
    assert dut.grant_idx_1.value == 0, "Lower index (0) gets first grant"
    assert dut.grant_idx_2.value == 1, "Higher index (1) gets second grant"
    assert dut.grant_bus.value == 0b0011, "Both bits set"


@cocotb.test()
async def test_arbiter_three_requests(dut):
    """Test arbiter with three requests - only two granted per cycle"""
    await setup_arbiter(dut)

    # Request from entries 0, 1, 2
    dut.req.value = 0b0111
    await Timer(2, unit="ns")

    assert dut.valid_1.value == 1
    assert dut.valid_2.value == 1
    assert dut.grant_idx_1.value == 0, "First grant goes to entry 0"
    assert dut.grant_idx_2.value == 1, "Second grant goes to entry 1"
    # Entry 2 is NOT granted (only 2 grants per cycle)
    assert dut.grant_bus.value == 0b0011, "Only bits 0 and 1 set"


@cocotb.test()
async def test_arbiter_four_requests(dut):
    """Test arbiter with four requests"""
    await setup_arbiter(dut)

    dut.req.value = 0b1111
    await Timer(2, unit="ns")

    assert dut.valid_1.value == 1
    assert dut.valid_2.value == 1
    assert dut.grant_idx_1.value == 0
    assert dut.grant_idx_2.value == 1
    assert dut.grant_bus.value == 0b0011


@cocotb.test()
async def test_arbiter_grant_bus_output(dut):
    """Test grant_bus correctly indicates granted entries"""
    await setup_arbiter(dut)

    # Request entries 1 and 3
    dut.req.value = 0b1010
    await Timer(2, unit="ns")

    assert dut.grant_bus.value == 0b1010, "Both requested entries granted"
    assert dut.grant_idx_1.value == 1, "Entry 1 wins first"
    assert dut.grant_idx_2.value == 3, "Entry 3 wins second"


@cocotb.test()
async def test_arbiter_no_requests(dut):
    """Test arbiter with no requests"""
    await setup_arbiter(dut)

    dut.req.value = 0b0000
    await Timer(2, unit="ns")

    assert dut.valid_1.value == 0
    assert dut.valid_2.value == 0
    assert dut.grant_idx_1.value == 0
    assert dut.grant_idx_2.value == 0
    assert dut.grant_bus.value == 0b0000
