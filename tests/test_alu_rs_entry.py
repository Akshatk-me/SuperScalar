import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


async def setup_rs(dut):
    """Setup clock and reset"""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    # Initialize inputs
    dut.dispatch_en.value = 0
    dut.in_rs1_tag.value = 0
    dut.in_rs1_rdy.value = 0
    dut.in_rs2_tag.value = 0
    dut.in_rs2_rdy.value = 0
    dut.in_c_tag.value = 0
    dut.in_c_rdy.value = 0
    dut.in_z_tag.value = 0
    dut.in_z_rdy.value = 0
    dut.in_dest_tag.value = 0
    dut.in_opcode.value = 0
    dut.cdb1_valid.value = 0
    dut.cdb1_tag.value = 0
    dut.cdb2_valid.value = 0
    dut.cdb2_tag.value = 0
    dut.issue_grant.value = 0

    # Reset
    dut.rst.value = 1
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)
    await Timer(2, unit="ns")


@cocotb.test()
async def test_rs_dispatch_and_busy(dut):
    """Test dispatching an instruction makes entry busy"""
    await setup_rs(dut)

    assert dut.busy.value == 0, "Should be free after reset"

    # Dispatch instruction
    dut.dispatch_en.value = 1
    dut.in_opcode.value = 0b0001  # ADD
    dut.in_dest_tag.value = 15
    dut.in_rs1_tag.value = 5
    dut.in_rs1_rdy.value = 1
    dut.in_rs2_tag.value = 6
    dut.in_rs2_rdy.value = 1

    await RisingEdge(dut.clk)
    dut.dispatch_en.value = 0
    await Timer(2, unit="ns")

    assert dut.busy.value == 1, "Entry should be busy after dispatch"
    assert dut.out_opcode.value == 0b0001
    assert dut.out_dest_tag.value == 15


@cocotb.test()
async def test_rs_ready_when_all_ready(dut):
    """Test ready_to_iss when all operands ready"""
    await setup_rs(dut)

    # Dispatch with all operands ready
    dut.dispatch_en.value = 1
    dut.in_rs1_rdy.value = 1
    dut.in_rs2_rdy.value = 1
    dut.in_c_rdy.value = 1
    dut.in_z_rdy.value = 1

    await RisingEdge(dut.clk)
    dut.dispatch_en.value = 0
    await Timer(2, unit="ns")

    assert dut.ready_to_iss.value == 1, "Should be ready to issue"


@cocotb.test()
async def test_rs_not_ready_when_waiting(dut):
    """Test ready_to_iss false when waiting for operands"""
    await setup_rs(dut)

    # Dispatch with operand not ready
    dut.dispatch_en.value = 1
    dut.in_rs1_rdy.value = 0  # Not ready
    dut.in_rs2_rdy.value = 1
    dut.in_rs1_tag.value = 10

    await RisingEdge(dut.clk)
    dut.dispatch_en.value = 0
    await Timer(2, unit="ns")

    assert dut.ready_to_iss.value == 0, "Should NOT be ready"


@cocotb.test()
async def test_rs_cdb_wakeup(dut):
    """Test CDB wakes up waiting operand"""
    await setup_rs(dut)

    # Dispatch with rs1 not ready, waiting for tag 10
    dut.dispatch_en.value = 1
    dut.in_rs1_rdy.value = 0
    dut.in_rs1_tag.value = 10
    dut.in_rs2_rdy.value = 1
    dut.in_c_rdy.value = 1
    dut.in_z_rdy.value = 1

    await RisingEdge(dut.clk)
    dut.dispatch_en.value = 0
    await Timer(2, unit="ns")

    assert dut.ready_to_iss.value == 0, "Should NOT be ready yet"

    # CDB broadcasts tag 10
    dut.cdb1_valid.value = 1
    dut.cdb1_tag.value = 10

    # IMPORTANT: Need a clock edge for the wakeup to register
    await RisingEdge(dut.clk)
    dut.cdb1_valid.value = 0
    await Timer(2, unit="ns")

    # Now ready_to_iss should be 1 (after the clock edge)
    assert dut.ready_to_iss.value == 1, "Should be ready after CDB wakeup"
    dut._log.info("CDB wakeup test passed")


@cocotb.test()
async def test_rs_cdb_wakeup_two_operands(dut):
    """Test CDB wakes up both waiting operands"""
    await setup_rs(dut)

    # Dispatch with rs1 and rs2 both waiting
    dut.dispatch_en.value = 1
    dut.in_rs1_rdy.value = 0
    dut.in_rs1_tag.value = 10
    dut.in_rs2_rdy.value = 0
    dut.in_rs2_tag.value = 20
    dut.in_c_rdy.value = 1
    dut.in_z_rdy.value = 1

    await RisingEdge(dut.clk)
    dut.dispatch_en.value = 0
    await Timer(2, unit="ns")

    assert dut.ready_to_iss.value == 0

    # CDB1 broadcasts tag 10
    dut.cdb1_valid.value = 1
    dut.cdb1_tag.value = 10
    await RisingEdge(dut.clk)
    dut.cdb1_valid.value = 0
    await Timer(2, unit="ns")

    assert dut.ready_to_iss.value == 0, "Still waiting for rs2"

    # CDB2 broadcasts tag 20
    dut.cdb2_valid.value = 1
    dut.cdb2_tag.value = 20
    await RisingEdge(dut.clk)
    dut.cdb2_valid.value = 0
    await Timer(2, unit="ns")

    assert dut.ready_to_iss.value == 1, "Both ready now"


@cocotb.test()
async def test_rs_issue_grant_clears_entry(dut):
    """Test issue grant clears the busy flag"""
    await setup_rs(dut)

    # Dispatch instruction
    dut.dispatch_en.value = 1
    dut.in_rs1_rdy.value = 1
    dut.in_rs2_rdy.value = 1

    await RisingEdge(dut.clk)
    dut.dispatch_en.value = 0
    await Timer(2, unit="ns")

    assert dut.busy.value == 1

    # Issue grant
    dut.issue_grant.value = 1
    await RisingEdge(dut.clk)
    dut.issue_grant.value = 0
    await Timer(2, unit="ns")

    assert dut.busy.value == 0, "Entry should be free after issue grant"


@cocotb.test()
async def test_rs_cdb_wakeup_on_both_buses(dut):
    """Test CDB wakeup from both buses simultaneously"""
    await setup_rs(dut)

    dut.dispatch_en.value = 1
    dut.in_rs1_rdy.value = 0
    dut.in_rs1_tag.value = 10
    dut.in_rs2_rdy.value = 0
    dut.in_rs2_tag.value = 20
    dut.in_c_rdy.value = 0
    dut.in_c_tag.value = 30
    dut.in_z_rdy.value = 1

    await RisingEdge(dut.clk)
    dut.dispatch_en.value = 0
    await Timer(2, unit="ns")

    # Both CDBs broadcast different tags
    dut.cdb1_valid.value = 1
    dut.cdb1_tag.value = 10
    dut.cdb2_valid.value = 1
    dut.cdb2_tag.value = 20
    await RisingEdge(dut.clk)
    dut.cdb1_valid.value = 0
    dut.cdb2_valid.value = 0
    await Timer(2, unit="ns")

    # rs1 and rs2 should be ready, but c still waiting
    assert dut.ready_to_iss.value == 0, "Still waiting for c flag"

    # Wake up c flag
    dut.cdb1_valid.value = 1
    dut.cdb1_tag.value = 30
    await RisingEdge(dut.clk)
    dut.cdb1_valid.value = 0
    await Timer(2, unit="ns")

    assert dut.ready_to_iss.value == 1, "All ready now"
