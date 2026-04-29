import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

# Constants
NUM_ARCH_REGS = 8  # R0-R7
RAT_ENTRIES = 10  # 0-7 for regs, 8 for C, 9 for Z
PHYS_REGS = 32  # 5-bit physical register addresses


async def setup_dut(dut):
    """Setup clock and reset"""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    # Initialize all inputs
    dut.recover_en.value = 0
    dut.rrat_state.value = 0
    dut.alloc_phys_1.value = 0
    dut.alloc_phys_2.value = 0
    dut.rs1_addr_1.value = 0
    dut.rs2_addr_1.value = 0
    dut.we_reg_1.value = 0
    dut.dest_addr_1.value = 0
    dut.we_c_1.value = 0
    dut.we_z_1.value = 0
    dut.rs1_addr_2.value = 0
    dut.rs2_addr_2.value = 0
    dut.we_reg_2.value = 0
    dut.dest_addr_2.value = 0
    dut.we_c_2.value = 0
    dut.we_z_2.value = 0

    # Reset sequence
    dut.rst.value = 1
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)
    await Timer(2, unit="ns")


async def wait_cycle(dut):
    """Wait one clock cycle"""
    await RisingEdge(dut.clk)
    await Timer(2, unit="ns")


def build_rrat_state(mappings):
    """Build 50-bit RRAT state from 10 mappings (each 5 bits)"""
    state = 0
    for i, mapping in enumerate(mappings):
        state |= (mapping & 0x1F) << (i * 5)
    return state


@cocotb.test()
async def test_rat_reset(dut):
    """Test reset maps R0->P0, R1->P1, ..., C->P8, Z->P9"""
    dut._log.info("Starting RAT reset test")
    await setup_dut(dut)

    # Check architectural registers R0-R7
    for arch_reg in range(8):
        dut.rs1_addr_1.value = arch_reg
        await Timer(2, unit="ns")
        expected_phys = arch_reg  # R0->P0, R1->P1, etc.
        actual = dut.phys_rs1_1.value.integer
        assert (
            actual == expected_phys
        ), f"R{arch_reg} should map to P{expected_phys}, got P{actual}"

    # Check C flag (index 8)
    # dut.rs1_addr_1.value = 8  # Invalid, but we have phys_c_1
    actual_c = dut.phys_c_1.value.integer
    assert actual_c == 8, f"C flag should map to P8, got P{actual_c}"

    # Check Z flag (index 9)
    actual_z = dut.phys_z_1.value.integer
    assert actual_z == 9, f"Z flag should map to P9, got P{actual_z}"

    dut._log.info("Reset test passed")


@cocotb.test()
async def test_rat_single_rename(dut):
    """Test single instruction rename"""
    dut._log.info("Starting single rename test")
    await setup_dut(dut)

    # Rename: Write to R5 with physical register P15
    dut.we_reg_1.value = 1
    dut.dest_addr_1.value = 5  # R5
    dut.alloc_phys_1.value = 15

    await wait_cycle(dut)
    dut.we_reg_1.value = 0

    # Read back R5
    dut.rs1_addr_1.value = 5
    await Timer(2, unit="ns")
    actual = dut.phys_rs1_1.value.integer
    assert actual == 15, f"R5 should map to P15, got P{actual}"

    dut._log.info("Single rename test passed")


@cocotb.test()
async def test_rat_two_instructions_parallel(dut):
    """Test two instructions renaming in same cycle"""
    dut._log.info("Starting two-instruction parallel rename test")
    await setup_dut(dut)

    # Instruction 1: Write R2 with P10
    dut.we_reg_1.value = 1
    dut.dest_addr_1.value = 2
    dut.alloc_phys_1.value = 10

    # Instruction 2: Write R5 with P20
    dut.we_reg_2.value = 1
    dut.dest_addr_2.value = 5
    dut.alloc_phys_2.value = 20

    await wait_cycle(dut)
    dut.we_reg_1.value = 0
    dut.we_reg_2.value = 0

    # Verify both mappings
    dut.rs1_addr_1.value = 2
    await Timer(2, unit="ns")
    assert dut.phys_rs1_1.value.integer == 10, "R2 mapping incorrect"

    dut.rs1_addr_1.value = 5
    await Timer(2, unit="ns")
    assert dut.phys_rs1_1.value.integer == 20, "R5 mapping incorrect"

    dut._log.info("Two-instruction parallel rename passed")


@cocotb.test()
async def test_rat_forwarding(dut):
    """Test Inst2 reads Inst1's destination in same cycle"""
    dut._log.info("Starting forwarding test")
    await setup_dut(dut)

    # Inst1: Writes to R3, gets physical P12
    dut.we_reg_1.value = 1
    dut.dest_addr_1.value = 3
    dut.alloc_phys_1.value = 12

    # Inst2: Reads R3 (should forward P12, not read from RAT)
    dut.rs2_addr_2.value = 3

    # Read immediately (combinatorial logic)
    await Timer(2, unit="ns")

    # Inst2 should see Inst1's physical register
    actual = dut.phys_rs2_2.value.integer
    assert actual == 12, f"Inst2 should see P12 from forwarding, got P{actual}"

    # Also verify RAT still has old mapping (R3->P3 from reset)
    dut.rs1_addr_1.value = 3
    await Timer(2, unit="ns")
    rat_mapping = dut.phys_rs1_1.value.integer
    assert rat_mapping == 3, f"RAT should still have old mapping P3, got P{rat_mapping}"

    await wait_cycle(dut)
    dut.we_reg_1.value = 0

    dut._log.info("Forwarding test passed")


@cocotb.test()
async def test_rat_flag_renaming(dut):
    """Test C and Z flag renaming"""
    dut._log.info("Starting flag renaming test")
    await setup_dut(dut)

    # Rename C flag to P25
    dut.we_c_1.value = 1
    dut.we_z_1.value = 1
    dut.alloc_phys_1.value = 25  # One physical register for both flags

    await wait_cycle(dut)
    dut.we_c_1.value = 0
    dut.we_z_1.value = 0

    # Read C and Z flag
    await Timer(2, unit="ns")
    actual_c = dut.phys_c_1.value.integer
    actual_z = dut.phys_z_1.value.integer
    assert actual_c == 25, f"C flag should map to P25, got P{actual_c}"
    assert actual_z == 25, f"Z flag should map to P25, got P{actual_z}"

    dut._log.info("Flag renaming test passed")


@cocotb.test()
async def test_rat_write_priority(dut):
    """Test Inst2 wins when both write same register"""
    dut._log.info("Starting write priority test")
    await setup_dut(dut)

    # Both instructions write to R4
    dut.we_reg_1.value = 1
    dut.dest_addr_1.value = 4
    dut.alloc_phys_1.value = 15

    dut.we_reg_2.value = 1
    dut.dest_addr_2.value = 4
    dut.alloc_phys_2.value = 25

    await wait_cycle(dut)
    dut.we_reg_1.value = 0
    dut.we_reg_2.value = 0

    # Inst2's mapping should win
    dut.rs1_addr_1.value = 4
    await Timer(2, unit="ns")
    actual = dut.phys_rs1_1.value.integer
    assert actual == 25, f"Inst2 should win: expected P25, got P{actual}"

    dut._log.info("Write priority test passed")


@cocotb.test()
async def test_rat_flag_priority(dut):
    """Test Inst2 wins for flag updates"""
    dut._log.info("Starting flag priority test")
    await setup_dut(dut)

    # Both update C flag
    dut.we_c_1.value = 1
    dut.alloc_phys_1.value = 15

    dut.we_c_2.value = 1
    dut.alloc_phys_2.value = 25

    await wait_cycle(dut)
    dut.we_c_1.value = 0
    dut.we_c_2.value = 0

    # Inst2's mapping should win
    await Timer(2, unit="ns")
    actual_c = dut.phys_c_1.value.integer
    assert actual_c == 25, f"C flag: Inst2 should win, got P{actual_c}"

    dut._log.info("Flag priority test passed")


@cocotb.test()
async def test_rat_recovery(dut):
    """Test branch misprediction recovery"""
    dut._log.info("Starting recovery test")
    await setup_dut(dut)

    # First, create some mappings
    dut.we_reg_1.value = 1
    dut.dest_addr_1.value = 2
    dut.alloc_phys_1.value = 10
    await wait_cycle(dut)

    dut.we_reg_1.value = 1
    dut.dest_addr_1.value = 5
    dut.alloc_phys_1.value = 20
    await wait_cycle(dut)
    dut.we_reg_1.value = 0

    # Verify new mappings
    dut.rs1_addr_1.value = 2
    await Timer(2, unit="ns")
    assert dut.phys_rs1_1.value.integer == 10

    dut.rs1_addr_1.value = 5
    await Timer(2, unit="ns")
    assert dut.phys_rs1_1.value.integer == 20

    # Build recovery state (R0->P0, R1->P1, R2->P2, R3->P3, ...)
    recovery_mappings = list(range(10))  # 0-9
    rrat_state = build_rrat_state(recovery_mappings)

    # Trigger recovery
    dut.recover_en.value = 1
    dut.rrat_state.value = rrat_state
    await wait_cycle(dut)
    dut.recover_en.value = 0

    # Verify all mappings restored
    for arch_reg in range(8):
        dut.rs1_addr_1.value = arch_reg
        await Timer(2, unit="ns")
        actual = dut.phys_rs1_1.value.integer
        assert (
            actual == arch_reg
        ), f"After recovery R{arch_reg} should map to P{arch_reg}, got P{actual}"

    # Check flags
    actual_c = dut.phys_c_1.value.integer
    actual_z = dut.phys_z_1.value.integer
    assert actual_c == 8, f"C flag should be P8, got P{actual_c}"
    assert actual_z == 9, f"Z flag should be P9, got P{actual_z}"

    dut._log.info("Recovery test passed")


@cocotb.test()
async def test_rat_complex_forwarding_scenario(dut):
    """Test complex forwarding: Inst2 reads multiple values from Inst1"""
    dut._log.info("Starting complex forwarding test")
    await setup_dut(dut)

    # Inst1: Writes to R1, R2, C flag
    dut.we_reg_1.value = 1
    dut.dest_addr_1.value = 1
    dut.alloc_phys_1.value = 10

    dut.we_c_1.value = 1
    # Same alloc_phys_1 for both

    await wait_cycle(dut)

    # In same cycle, Inst2 reads R1, R2, and C flag
    # But need to set up Inst2 in the SAME cycle as the write is happening
    # This requires setting inputs before the clock edge

    # Reset and do it in one cycle
    await setup_dut(dut)  # Fresh start

    # Set up both instructions in same cycle BEFORE clock edge
    dut.we_reg_1.value = 1
    dut.dest_addr_1.value = 1
    dut.alloc_phys_1.value = 10

    dut.we_c_1.value = 1

    # Inst2 reads what Inst1 is writing
    dut.rs1_addr_2.value = 1  # Read R1
    dut.phys_c_2  # Read C flag

    await Timer(2, unit="ns")  # Let combinatorial logic settle

    # Check forwarding
    assert dut.phys_rs1_2.value.integer == 10, "Inst2 should see Inst1's R1 mapping"
    assert dut.phys_c_2.value.integer == 10, "Inst2 should see Inst1's C flag mapping"

    await wait_cycle(dut)

    dut._log.info("Complex forwarding test passed")


@cocotb.test()
async def test_rat_random_stress(dut):
    """Random stress test"""
    dut._log.info("Starting random stress test")
    await setup_dut(dut)

    # Keep Python model of expected mappings
    expected_regs = list(range(8))  # R0->P0, etc.
    expected_c = 8
    expected_z = 9

    for cycle in range(50):
        # Randomly choose operations
        do_inst1 = random.choice([True, False])
        do_inst2 = random.choice([True, False])

        inst1_phys = random.randint(0, 31)
        inst2_phys = random.randint(0, 31)

        # Instruction 1
        if do_inst1:
            dest_reg = random.randint(0, 7)
            dut.we_reg_1.value = 1
            dut.dest_addr_1.value = dest_reg
            dut.alloc_phys_1.value = inst1_phys

            # Update expected (but Inst2 might override)
            expected_regs[dest_reg] = inst1_phys

            # Random flag updates
            if random.choice([True, False]):
                dut.we_c_1.value = 1
                expected_c = inst1_phys
            if random.choice([True, False]):
                dut.we_z_1.value = 1
                expected_z = inst1_phys

        # Instruction 2 (higher priority)
        if do_inst2:
            dest_reg = random.randint(0, 7)
            dut.we_reg_2.value = 1
            dut.dest_addr_2.value = dest_reg
            dut.alloc_phys_2.value = inst2_phys

            # Inst2 overrides Inst1 for same register
            expected_regs[dest_reg] = inst2_phys

            if random.choice([True, False]):
                dut.we_c_2.value = 1
                expected_c = inst2_phys
            if random.choice([True, False]):
                dut.we_z_2.value = 1
                expected_z = inst2_phys

        await wait_cycle(dut)

        # Clear enables
        dut.we_reg_1.value = 0
        dut.we_reg_2.value = 0
        dut.we_c_1.value = 0
        dut.we_c_2.value = 0
        dut.we_z_1.value = 0
        dut.we_z_2.value = 0

        # Verify random register
        test_reg = random.randint(0, 7)
        dut.rs1_addr_1.value = test_reg
        await Timer(2, unit="ns")
        actual = dut.phys_rs1_1.value.integer
        assert (
            actual == expected_regs[test_reg]
        ), f"Cycle {cycle}: R{test_reg} expected P{expected_regs[test_reg]}, got P{actual}"

        # Verify flags occasionally
        if cycle % 10 == 0:
            actual_c = dut.phys_c_1.value.integer
            actual_z = dut.phys_z_1.value.integer
            assert (
                actual_c == expected_c
            ), f"Cycle {cycle}: C flag expected P{expected_c}, got P{actual_c}"
            assert (
                actual_z == expected_z
            ), f"Cycle {cycle}: Z flag expected P{expected_z}, got P{actual_z}"

        dut._log.debug(f"Cycle {cycle} completed")

    dut._log.info("Random stress test passed")
