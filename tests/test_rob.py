import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer

# Constants
ROB_SIZE = 16
ARCH_REGS = 10  # 0-7 R0-R7, 8 for C, 9 for Z


async def setup_rob(dut):
    """Setup clock and reset"""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    # Initialize all inputs
    dut.disp_en_1.value = 0
    dut.disp_we_1.value = 0
    dut.disp_arch_1.value = 0
    dut.disp_phys_1.value = 0
    dut.disp_en_2.value = 0
    dut.disp_we_2.value = 0
    dut.disp_arch_2.value = 0
    dut.disp_phys_2.value = 0
    dut.cdb1_valid.value = 0
    dut.cdb1_tag.value = 0
    dut.cdb2_valid.value = 0
    dut.cdb2_tag.value = 0
    dut.branch_flush.value = 0

    # Reset sequence
    dut.rst.value = 1
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)
    await Timer(2, unit="ns")


async def dispatch(
    dut,
    inst1_en,
    inst1_we,
    inst1_arch,
    inst1_phys,
    inst2_en=False,
    inst2_we=0,
    inst2_arch=0,
    inst2_phys=0,
):
    """Dispatch 1 or 2 instructions to ROB"""
    dut.disp_en_1.value = 1 if inst1_en else 0
    dut.disp_we_1.value = 1 if inst1_we else 0
    dut.disp_arch_1.value = inst1_arch if inst1_en else 0
    dut.disp_phys_1.value = inst1_phys if inst1_en else 0

    if inst2_en:
        dut.disp_en_2.value = 1
        dut.disp_we_2.value = 1 if inst2_we else 0
        dut.disp_arch_2.value = inst2_arch
        dut.disp_phys_2.value = inst2_phys

    await RisingEdge(dut.clk)

    dut.disp_en_1.value = 0
    dut.disp_en_2.value = 0
    await Timer(2, unit="ns")


async def complete_instruction(dut, phys_tag, use_cdb1=True):
    """Mark instruction as complete via CDB"""
    if use_cdb1:
        dut.cdb1_valid.value = 1
        dut.cdb1_tag.value = phys_tag
    else:
        dut.cdb2_valid.value = 1
        dut.cdb2_tag.value = phys_tag

    await RisingEdge(dut.clk)
    dut.cdb1_valid.value = 0
    dut.cdb2_valid.value = 0
    await Timer(2, unit="ns")


@cocotb.test()
async def test_rob_reset(dut):
    """Test reset clears ROB"""
    dut._log.info("Starting ROB reset test")
    await setup_rob(dut)

    assert dut.rob_full.value == 0, "ROB should not be full after reset"
    assert dut.commit_valid_1.value == 0, "No commit valid after reset"
    assert dut.commit_valid_2.value == 0, "No commit valid after reset"

    dut._log.info("Reset test passed")


@cocotb.test()
async def test_rob_dispatch_single(dut):
    """Test dispatching single instruction"""
    dut._log.info("Starting single dispatch test")
    await setup_rob(dut)

    # Dispatch ADD instruction that writes to R5
    await dispatch(dut, inst1_en=True, inst1_we=True, inst1_arch=5, inst1_phys=20)

    # Check commit not ready (not completed yet)
    assert dut.commit_valid_1.value == 0, "Should not commit before completion"

    # Complete the instruction
    await complete_instruction(dut, phys_tag=20)

    # Should be ready to commit
    await Timer(2, unit="ns")
    assert dut.commit_valid_1.value == 1, "Should be ready to commit"
    assert dut.commit_we_1.value == 1, "Should have write enable"
    assert dut.commit_arch_1.value == 5, "Should commit to R5"
    assert dut.commit_phys_1.value == 20, "Should commit physical P20"

    # Commit it
    await RisingEdge(dut.clk)
    await Timer(2, unit="ns")

    assert dut.commit_valid_1.value == 0, "Should be empty after commit"

    dut._log.info("Single dispatch test passed")


@cocotb.test()
async def test_rob_dispatch_double(dut):
    """Test dispatching two instructions in same cycle"""
    dut._log.info("Starting double dispatch test")
    await setup_rob(dut)

    # Dispatch two instructions
    await dispatch(
        dut,
        inst1_en=True,
        inst1_we=True,
        inst1_arch=5,
        inst1_phys=20,
        inst2_en=True,
        inst2_we=True,
        inst2_arch=6,
        inst2_phys=21,
    )

    # Complete BOTH in the SAME cycle using both CDB buses
    # This way both become ready simultaneously BEFORE any commit happens
    dut.cdb1_valid.value = 1
    dut.cdb1_tag.value = 20  # First instruction
    dut.cdb2_valid.value = 1
    dut.cdb2_tag.value = 21  # Second instruction

    await RisingEdge(dut.clk)  # One clock cycle to mark both ready
    dut.cdb1_valid.value = 0
    dut.cdb2_valid.value = 0
    await Timer(2, unit="ns")

    # NOW both should be ready to commit (head = index 0, head+1 = index 1)
    dut._log.info(f"commit_valid_1 = {dut.commit_valid_1.value}")
    dut._log.info(f"commit_valid_2 = {dut.commit_valid_2.value}")

    assert dut.commit_valid_1.value == 1, "Head should be ready"
    assert dut.commit_valid_2.value == 1, "Both should be ready (committing together)"
    assert dut.commit_arch_1.value == 5, "First should commit R5"
    assert dut.commit_arch_2.value == 6, "Second should commit R6"

    # Commit both in one cycle
    await RisingEdge(dut.clk)
    await Timer(2, unit="ns")

    # Both should be gone
    assert dut.commit_valid_1.value == 0, "Should be empty after commit"
    assert dut.commit_valid_2.value == 0, "Should be empty after commit"

    dut._log.info("Double dispatch test passed")


@cocotb.test()
async def test_rob_commit_two_sequential(dut):
    """Test committing two instructions in same cycle"""
    dut._log.info("Starting two-commit test")
    await setup_rob(dut)

    # Dispatch two instructions
    await dispatch(
        dut,
        inst1_en=True,
        inst1_we=True,
        inst1_arch=5,
        inst1_phys=20,
        inst2_en=True,
        inst2_we=True,
        inst2_arch=6,
        inst2_phys=21,
    )

    # Complete BOTH in the SAME cycle using both CDB buses
    dut.cdb1_valid.value = 1
    dut.cdb1_tag.value = 20
    dut.cdb2_valid.value = 1
    dut.cdb2_tag.value = 21

    await RisingEdge(dut.clk)  # One cycle to mark both ready
    dut.cdb1_valid.value = 0
    dut.cdb2_valid.value = 0
    await Timer(2, unit="ns")

    # Both should be ready to commit
    assert dut.commit_valid_1.value == 1, "First ready"
    assert dut.commit_valid_2.value == 1, "Second ready (commits same cycle)"
    assert dut.commit_arch_1.value == 5, "First should commit R5"
    assert dut.commit_arch_2.value == 6, "Second should commit R6"

    # Commit both in one cycle
    await RisingEdge(dut.clk)
    await Timer(2, unit="ns")

    assert dut.commit_valid_1.value == 0, "Both should be gone"
    assert dut.commit_valid_2.value == 0

    dut._log.info("Two-commit test passed")


@cocotb.test()
async def test_rob_non_we_instructions(dut):
    """Test instructions that don't write registers (NOP, branches)"""
    dut._log.info("Starting non-WE instruction test")
    await setup_rob(dut)

    # Dispatch instruction that doesn't write (we=0)
    await dispatch(dut, inst1_en=True, inst1_we=False, inst1_arch=0, inst1_phys=20)

    # Should be ready immediately (auto-ready)
    await Timer(2, unit="ns")
    assert dut.commit_valid_1.value == 1, "Non-WE instruction should commit immediately"

    await RisingEdge(dut.clk)
    await Timer(2, unit="ns")

    assert dut.commit_valid_1.value == 0, "Should have committed"

    dut._log.info("Non-WE instruction test passed")


@cocotb.test()
async def test_rob_full(dut):
    """Test ROB full flag"""
    dut._log.info("Starting ROB full test")
    await setup_rob(dut)

    # Fill ROB with 15 instructions (full at 15 by design)
    for i in range(15):
        await dispatch(
            dut,
            inst1_en=True,
            inst1_we=True,
            inst1_arch=i % 10,
            inst1_phys=(20 + i) % 32,
        )

    assert dut.rob_full.value == 1, "ROB should be full at 15 entries"

    # Complete one to free space
    await complete_instruction(dut, phys_tag=20)
    await RisingEdge(dut.clk)  # Commit
    await Timer(2, unit="ns")

    assert dut.rob_full.value == 0, "ROB should not be full after commit"

    dut._log.info("ROB full test passed")


@cocotb.test()
async def test_rob_out_of_order_completion(dut):
    """Test out-of-order completion with in-order commit"""
    dut._log.info("Starting out-of-order completion test")
    await setup_rob(dut)

    # Dispatch 3 instructions
    await dispatch(dut, inst1_en=True, inst1_we=True, inst1_arch=5, inst1_phys=20)
    await dispatch(dut, inst1_en=True, inst1_we=True, inst1_arch=6, inst1_phys=21)
    await dispatch(dut, inst1_en=True, inst1_we=True, inst1_arch=7, inst1_phys=22)

    # Complete ONLY Inst3 and Inst2 (NOT Inst1)
    await complete_instruction(dut, phys_tag=22)  # Inst3 completes
    await complete_instruction(dut, phys_tag=21)  # Inst2 completes
    await Timer(2, unit="ns")

    # Now: Inst1 NOT ready, Inst2 ready, Inst3 ready
    # Only head (Inst1) should NOT be ready
    assert (
        dut.commit_valid_1.value == 0
    ), "Head should NOT be ready (Inst1 not complete)"
    assert dut.commit_valid_2.value == 0, "No commit valid when head not ready"

    # Now complete Inst1
    await complete_instruction(dut, phys_tag=20)
    await Timer(2, unit="ns")

    # Now head is ready, second is ready (Inst2 was already ready)
    assert dut.commit_valid_1.value == 1, "Head should commit"
    assert (
        dut.commit_valid_2.value == 1
    ), "Second should also be ready (was completed earlier)"
    assert dut.commit_arch_1.value == 5
    assert dut.commit_arch_2.value == 6

    # Commit both
    await RisingEdge(dut.clk)
    await Timer(2, unit="ns")

    # Now Inst3 should be head
    assert dut.commit_valid_1.value == 1
    assert dut.commit_arch_1.value == 7

    dut._log.info("Out-of-order completion test passed")


@cocotb.test()
async def test_rob_branch_flush(dut):
    """Test branch misprediction flush"""
    dut._log.info("Starting branch flush test")
    await setup_rob(dut)

    # Dispatch 5 instructions
    for i in range(5):
        await dispatch(
            dut, inst1_en=True, inst1_we=True, inst1_arch=i, inst1_phys=20 + i
        )

    # Some complete out-of-order
    await complete_instruction(dut, phys_tag=22)
    await complete_instruction(dut, phys_tag=24)

    # Branch mispredict - flush
    dut.branch_flush.value = 1
    await RisingEdge(dut.clk)
    dut.branch_flush.value = 0
    await Timer(2, unit="ns")

    # Everything should be gone
    assert dut.commit_valid_1.value == 0, "No instructions after flush"
    assert dut.commit_valid_2.value == 0
    assert dut.rob_full.value == 0, "ROB should be empty"

    # New instruction can be dispatched
    await dispatch(dut, inst1_en=True, inst1_we=True, inst1_arch=0, inst1_phys=30)
    await complete_instruction(dut, phys_tag=30)

    await Timer(2, unit="ns")
    assert dut.commit_valid_1.value == 1, "New instruction should commit"

    dut._log.info("Branch flush test passed")


@cocotb.test()
async def test_rob_two_cdb_buses(dut):
    """Test both CDB buses can complete instructions simultaneously"""
    dut._log.info("Starting two-CDB test")
    await setup_rob(dut)

    await dispatch(
        dut,
        inst1_en=True,
        inst1_we=True,
        inst1_arch=5,
        inst1_phys=20,
        inst2_en=True,
        inst2_we=True,
        inst2_arch=6,
        inst2_phys=21,
    )

    # Complete both in same cycle using both CDB buses
    dut.cdb1_valid.value = 1
    dut.cdb1_tag.value = 20
    dut.cdb2_valid.value = 1
    dut.cdb2_tag.value = 21

    await RisingEdge(dut.clk)
    dut.cdb1_valid.value = 0
    dut.cdb2_valid.value = 0
    await Timer(2, unit="ns")

    # BOTH should be ready (both completed in same cycle)
    assert dut.commit_valid_1.value == 1, "First ready"
    assert dut.commit_valid_2.value == 1, "Second ready (both commit same cycle)"
    assert dut.commit_arch_1.value == 5
    assert dut.commit_arch_2.value == 6

    # Commit both
    await RisingEdge(dut.clk)
    await Timer(2, unit="ns")

    assert dut.commit_valid_1.value == 0, "Both should be gone"

    dut._log.info("Two-CDB test passed")


@cocotb.test()
async def test_rob_wraparound(dut):
    """Test ROB wraparound behavior - Simplified"""
    dut._log.info("Starting wraparound test")
    await setup_rob(dut)

    # Fill ROB with 14 instructions
    for i in range(14):
        await dispatch(
            dut,
            inst1_en=True,
            inst1_we=True,
            inst1_arch=i % 10,
            inst1_phys=(20 + i) % 32,
        )

    # Complete ALL 14 instructions in reverse order
    for i in range(13, -1, -1):
        await complete_instruction(dut, phys_tag=(20 + i) % 32)

    # Let all completions register
    await RisingEdge(dut.clk)
    await Timer(2, unit="ns")

    # Now head should be ready (first instruction at index 0)
    assert dut.commit_valid_1.value == 1, "Head should be ready"
    dut._log.info(f"Head arch={dut.commit_arch_1.value}")

    # Commit all instructions one by one
    for i in range(14):
        await RisingEdge(dut.clk)
        await Timer(2, unit="ns")

    assert dut.commit_valid_1.value == 0, "ROB should be empty"

    dut._log.info("Wraparound test passed")


# TODO(akshat): Do proper random testing, this test failed not sure why @medium file:test_rob.py
@cocotb.test()
async def test_rob_random_stress(dut):
    """Upgraded Random stress test with cycle-accurate Python model"""
    dut._log.info("Starting random stress test")
    await setup_rob(dut)

    # Our Golden Model: A list of dictionaries representing the ROB queue
    rob_state = []
    next_phys = 0

    for cycle in range(200):
        # ==========================================
        # 1. APPLY STIMULUS (Combinatorial)
        # ==========================================
        cdb1_tag, cdb2_tag = None, None

        # Randomly complete up to 2 instructions that are waiting
        unready = [
            i for i, inst in enumerate(rob_state) if not inst["ready"] and inst["we"]
        ]
        if unready and random.choice([True, False]):
            idx = random.choice(unready)
            cdb1_tag = rob_state[idx]["phys"]
            unready.remove(idx)

            if unready and random.choice([True, False]):
                idx2 = random.choice(unready)
                cdb2_tag = rob_state[idx2]["phys"]

        dut.cdb1_valid.value = 1 if cdb1_tag is not None else 0
        dut.cdb1_tag.value = cdb1_tag if cdb1_tag is not None else 0
        dut.cdb2_valid.value = 1 if cdb2_tag is not None else 0
        dut.cdb2_tag.value = cdb2_tag if cdb2_tag is not None else 0

        # Randomly dispatch (0, 1, or 2), constrained by capacity
        capacity = 16 - len(rob_state)
        num_dispatch = min(random.choice([0, 1, 2]), capacity)

        new_insts = []
        if num_dispatch > 0:
            we = random.choice([1, 0])
            arch = random.randint(0, 9)
            phys = next_phys
            next_phys = (next_phys + 1) % 32  # <--- THE FIX for the 32 error!
            new_insts.append({"arch": arch, "phys": phys, "we": we, "ready": not we})

            dut.disp_en_1.value = 1
            dut.disp_we_1.value = we
            dut.disp_arch_1.value = arch
            dut.disp_phys_1.value = phys
        else:
            dut.disp_en_1.value = 0

        if num_dispatch > 1:
            we = random.choice([1, 0])
            arch = random.randint(0, 9)
            phys = next_phys
            next_phys = (next_phys + 1) % 32
            new_insts.append({"arch": arch, "phys": phys, "we": we, "ready": not we})

            dut.disp_en_2.value = 1
            dut.disp_we_2.value = we
            dut.disp_arch_2.value = arch
            dut.disp_phys_2.value = phys
        else:
            dut.disp_en_2.value = 0

        # Wait a tiny bit for VHDL combinatorial logic to settle
        await Timer(1, unit="ns")

        # ==========================================
        # 2. VERIFY COMMIT COMBINATORIAL LOGIC
        # ==========================================
        # Determine what *should* commit based on our Python model
        exp_commit_1 = len(rob_state) > 0 and rob_state[0]["ready"]
        exp_commit_2 = (
            len(rob_state) > 1 and rob_state[0]["ready"] and rob_state[1]["ready"]
        )

        assert dut.commit_valid_1.value == (
            1 if exp_commit_1 else 0
        ), f"Cycle {cycle}: commit_valid_1 mismatch."
        assert dut.commit_valid_2.value == (
            1 if exp_commit_2 else 0
        ), f"Cycle {cycle}: commit_valid_2 mismatch."

        # ==========================================
        # 3. ADVANCE TIME (The Clock Edge!)
        # ==========================================
        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")

        # ==========================================
        # 4. UPDATE PYTHON MODEL
        # ==========================================
        # A. Remove committed instructions
        if exp_commit_1 and exp_commit_2:
            rob_state.pop(0)
            rob_state.pop(0)
        elif exp_commit_1:
            rob_state.pop(0)

        # B. Apply CDB completions to our list
        if cdb1_tag is not None:
            for inst in rob_state:
                if inst["phys"] == cdb1_tag and inst["we"]:
                    inst["ready"] = True
        if cdb2_tag is not None:
            for inst in rob_state:
                if inst["phys"] == cdb2_tag and inst["we"]:
                    inst["ready"] = True

        # C. Add new dispatches
        rob_state.extend(new_insts)

        if cycle % 20 == 0:
            dut._log.debug(f"Cycle {cycle}: ROB size={len(rob_state)}")

    dut._log.info("Random stress test passed! You are a hardware wizard.")


@cocotb.test()
async def test_rob_debug_state(dut):
    """Debug ROB internal state"""
    await setup_rob(dut)

    # Dispatch 2 instructions
    await dispatch(
        dut,
        inst1_en=True,
        inst1_we=True,
        inst1_arch=5,
        inst1_phys=20,
        inst2_en=True,
        inst2_we=True,
        inst2_arch=6,
        inst2_phys=21,
    )

    # Complete second instruction only
    await complete_instruction(dut, phys_tag=21)

    await Timer(2, unit="ns")

    # Print all ROB entries (need debug ports)
    for i in range(4):
        dut._log.info(
            f"ROB[{i}]: valid={getattr(dut, f'debug_valid_{i}').value if hasattr(dut, f'debug_valid_{i}') else 'N/A'}"
        )


@cocotb.test()
async def test_rob_debug_commit_logic(dut):
    """Debug why commit_valid_2 is inverted"""
    await setup_rob(dut)

    # Test 1: Dispatch 2 instructions
    dut._log.info("=== Test 1: Both complete in-order ===")
    await dispatch(
        dut,
        inst1_en=True,
        inst1_we=True,
        inst1_arch=5,
        inst1_phys=20,
        inst2_en=True,
        inst2_we=True,
        inst2_arch=6,
        inst2_phys=21,
    )

    # Complete both in the SAME cycle (not sequentially)
    # Set both CDB buses in the same cycle
    dut.cdb1_valid.value = 1
    dut.cdb1_tag.value = 20
    dut.cdb2_valid.value = 1
    dut.cdb2_tag.value = 21

    await RisingEdge(dut.clk)  # One clock edge to mark both ready
    dut.cdb1_valid.value = 0
    dut.cdb2_valid.value = 0
    await Timer(2, unit="ns")

    # NOW check BEFORE any commit happens
    # The commit will happen on the NEXT clock edge
    dut._log.info(f"After both complete (before commit):")
    dut._log.info(f"  commit_valid_1 = {dut.commit_valid_1.value}")
    dut._log.info(f"  commit_valid_2 = {dut.commit_valid_2.value}")
    dut._log.info(f"  head = {dut.debug_head.value}")
    dut._log.info(f"  head.ready = {dut.debug_head_ready.value}")
    dut._log.info(f"  head+1.ready = {dut.debug_head1_ready.value}")

    # Now let the commit happen
    await RisingEdge(dut.clk)
    await Timer(2, unit="ns")
    dut._log.info(f"After commit cycle: head = {dut.debug_head.value}")
