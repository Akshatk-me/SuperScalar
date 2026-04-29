import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

NUM_PHYS_REGS = 32
INIT_FREE_START = 10
INIT_FREE_COUNT = 22


async def setup_dut(dut):
    """Setup clock and reset"""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    # Initialize inputs
    dut.req_1.value = 0
    dut.req_2.value = 0
    dut.free_en_1.value = 0
    dut.free_en_2.value = 0
    dut.free_phys_1.value = 0
    dut.free_phys_2.value = 0
    dut.recover_en.value = 0
    dut.recover_ptr.value = 0

    # Reset sequence
    dut.rst.value = 1
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)
    await Timer(2, unit="ns")


async def allocate(dut, count=1):
    """Allocate 1 or 2 registers"""
    dut._log.info(f"ALLOCATE START: count={count}")
    if count == 1:
        dut.req_1.value = 1
        dut.req_2.value = 0
    else:
        dut.req_1.value = 1
        dut.req_2.value = 1

    await RisingEdge(dut.clk)

    phys1 = dut.alloc_phys_1.value
    phys2 = dut.alloc_phys_2.value if count == 2 else None

    dut.req_1.value = 0
    dut.req_2.value = 0
    await Timer(2, unit="ns")
    dut._log.info(f"ALLOCATE RESULT: phys1={phys1}, phys2={phys2}")

    return phys1, phys2


async def free_registers(dut, phys1, phys2=None):
    """Free 1 or 2 registers back to free list (goes to back of FIFO)"""
    dut.free_en_1.value = 1
    dut.free_phys_1.value = phys1

    if phys2 is not None:
        dut.free_en_2.value = 1
        dut.free_phys_2.value = phys2

    await RisingEdge(dut.clk)

    dut.free_en_1.value = 0
    dut.free_en_2.value = 0
    await Timer(2, unit="ns")


@cocotb.test()
async def test_free_list_reset(dut):
    """Test reset initializes free list with P10-P31"""
    dut._log.info("Starting reset test")
    await setup_dut(dut)

    phys1, _ = await allocate(dut, 1)
    assert phys1 == 10, f"First allocation should be P10, got P{phys1}"

    phys1, _ = await allocate(dut, 1)
    assert phys1 == 11, f"Second allocation should be P11, got P{phys1}"

    dut._log.info("Reset test passed")


@cocotb.test()
async def test_free_list_single_allocate(dut):
    """Test single register allocation"""
    dut._log.info("Starting single allocate test")
    await setup_dut(dut)

    for i in range(5):
        phys, _ = await allocate(dut, 1)
        assert phys == 10 + i, f"Allocation {i}: expected P{10+i}, got P{phys}"

    dut._log.info("Single allocate test passed")


@cocotb.test()
async def test_free_list_double_allocate(dut):
    """Test double register allocation in one cycle"""
    dut._log.info("Starting double allocate test")
    await setup_dut(dut)

    phys1, phys2 = await allocate(dut, 2)
    assert phys1 == 10, f"First should be P10, got P{phys1}"
    assert phys2 == 11, f"Second should be P11, got P{phys2}"

    phys1, _ = await allocate(dut, 1)
    assert phys1 == 12, f"Next should be P12, got P{phys1}"

    dut._log.info("Double allocate test passed")


@cocotb.test()
async def test_free_list_single_free(dut):
    """Test FIFO behavior: freed register goes to BACK of queue"""
    await setup_dut(dut)

    # Allocate P10, P11, P12
    await allocate(dut, 1)  # P10
    await allocate(dut, 1)  # P11
    await allocate(dut, 1)  # P12

    # Free P10
    await free_registers(dut, 10)

    # FIFO CORRECT BEHAVIOR: Next allocation should be P13
    # (P10 is at the back, behind P13-P31)
    phys, _ = await allocate(dut, 1)
    assert phys == 13, f"FIFO violation: Expected P13, got P{phys}"

    # If your hardware gives P12 here, your free list is NOT a FIFO


@cocotb.test()
async def test_free_list_double_free(dut):
    """Test freeing two registers - FIFO order preserved"""
    dut._log.info("Starting double free test")
    await setup_dut(dut)

    # Allocate P10, P11, P12, P13 (4 separate allocations)
    phys, _ = await allocate(dut, 1)
    assert phys == 10
    phys, _ = await allocate(dut, 1)
    assert phys == 11
    phys, _ = await allocate(dut, 1)
    assert phys == 12
    phys, _ = await allocate(dut, 1)
    assert phys == 13

    dut._log.info("Allocated P10, P11, P12, P13")

    # Free P10 and P11
    await free_registers(dut, 10, 11)
    dut._log.info("Freed P10 and P11")

    # FIFO behavior: Next allocations should be P14, P15, etc. (NOT P10, P11)
    # Because freed registers go to the back of the queue

    # Allocate P14
    phys, _ = await allocate(dut, 1)
    assert phys == 14, f"Should get P14, got P{phys}"
    dut._log.info("Allocated P14")

    # Allocate P15
    phys, _ = await allocate(dut, 1)
    assert phys == 15, f"Should get P15, got P{phys}"
    dut._log.info("Allocated P15")

    # Allocate the rest (P16 through P31)
    for i in range(16, 32):
        phys, _ = await allocate(dut, 1)
        assert phys == i, f"Should get P{i}, got P{phys}"

    dut._log.info("Allocated all remaining registers P16-P31")

    # Now queue should be empty (all 22 registers allocated: P10-P31)
    # But note: P10 and P11 were freed and pushed to back,
    # so they should be the next available
    await Timer(2, unit="ns")
    dut._log.info(f"Empty flag after all allocations: {dut.empty.value}")

    # Free P10 and P11 again (they should be the only ones in queue)
    # Actually they should still be in queue from before? Let's check FIFO behavior

    # According to FIFO: After allocating all 22 registers,
    # the freed P10 and P11 should be the only ones in the queue
    # So allocate should get P10, then P11

    phys, _ = await allocate(dut, 1)
    assert phys == 10, f"After empty, should get P10, got P{phys}"
    dut._log.info("Got P10 back")

    phys, _ = await allocate(dut, 1)
    assert phys == 11, f"After empty, should get P11, got P{phys}"
    dut._log.info("Got P11 back")

    dut._log.info("Double free test passed (FIFO behavior)")


@cocotb.test()
async def test_free_list_allocate_free_interleaved(dut):
    """Test interleaved allocate/free - FIFO order"""
    dut._log.info("Starting interleaved test")
    await setup_dut(dut)

    # Allocate P10, P11
    await allocate(dut, 2)

    # Free P10
    await free_registers(dut, 10)

    # FIFO: P10 goes to back, next allocate gives P12
    phys, _ = await allocate(dut, 1)
    assert phys == 12, f"Should get P12, got P{phys}"

    # Free P11, allocate - should get P13
    await free_registers(dut, 11)
    phys, _ = await allocate(dut, 1)
    assert phys == 13, f"Should get P13, got P{phys}"

    # Now P10 and P11 are in queue (in that order)
    # Allocate all remaining (P14-P31)
    for i in range(14, 32):
        await allocate(dut, 1)

    # Queue empty, allocate should get P10 then P11
    phys, _ = await allocate(dut, 1)
    assert phys == 10, f"Should get P10, got P{phys}"

    phys, _ = await allocate(dut, 1)
    assert phys == 11, f"Should get P11, got P{phys}"

    dut._log.info("Interleaved test passed (FIFO behavior)")


@cocotb.test()
async def test_free_list_empty(dut):
    """Test empty flag"""
    dut._log.info("Starting empty flag test")
    await setup_dut(dut)

    # Initially not empty
    assert dut.empty.value == 0, "Should not be empty initially"

    # Allocate all 22 registers
    for i in range(22):
        await allocate(dut, 1)

    await Timer(2, unit="ns")
    assert dut.empty.value == 1, "Should be empty after 22 allocations"

    # Free one, should not be empty
    await free_registers(dut, 10)
    await Timer(2, unit="ns")
    assert dut.empty.value == 0, "Should not be empty after freeing"

    dut._log.info("Empty flag test passed")


@cocotb.test()
async def test_free_list_wraparound(dut):
    """Test circular buffer wraparound"""
    dut._log.info("Starting wraparound test")
    await setup_dut(dut)

    # Allocate all registers
    allocated = []
    for i in range(22):
        phys, _ = await allocate(dut, 1)
        allocated.append(phys)

    assert allocated == list(range(10, 32)), f"Expected P10-P31, got {allocated}"

    # Free P10 and allocate - should get P10 after wraparound
    await free_registers(dut, 10)

    # Need to allocate all to trigger wraparound first
    # This tests your circular buffer logic
    phys, _ = await allocate(dut, 1)
    assert phys == 10, f"Should get P10, got P{phys}"

    dut._log.info("Wraparound test passed")


@cocotb.test()
async def test_free_list_recovery(dut):
    """Test branch misprediction recovery"""
    dut._log.info("Starting recovery test")
    await setup_dut(dut)

    # Allocate some registers
    await allocate(dut, 3)  # P10, P11, P12

    # Save current state (head_ptr should be 3)
    # Recover to head_ptr=3
    dut.recover_en.value = 1
    dut.recover_ptr.value = 3
    await RisingEdge(dut.clk)
    dut.recover_en.value = 0
    await Timer(2, unit="ns")

    # Should allocate P13 again (not P10)
    phys, _ = await allocate(dut, 1)
    assert phys == 13, f"After recovery should get P13, got P{phys}"

    dut._log.info("Recovery test passed")


@cocotb.test()
async def test_free_list_allocate_free_same_cycle(dut):
    """Test allocate and free in same cycle"""
    dut._log.info("Starting allocate+free same cycle test")
    await setup_dut(dut)

    # Allocate P10
    phys, _ = await allocate(dut, 1)
    assert phys == 10

    # Same cycle: allocate and free
    dut.req_1.value = 1
    dut.free_en_1.value = 1
    dut.free_phys_1.value = 10

    await RisingEdge(dut.clk)

    dut.req_1.value = 0
    dut.free_en_1.value = 0
    await Timer(2, unit="ns")

    # In FIFO with simultaneous push/pop, freed register may not be available
    # until next cycle depending on your implementation
    phys, _ = await allocate(dut, 1)
    dut._log.info(f"After allocate+free cycle, allocated P{phys}")

    dut._log.info("Allocate+free same cycle test completed")


@cocotb.test()
async def test_free_list_random_stress(dut):
    """Random stress test with FIFO behavior"""
    dut._log.info("Starting random stress test")
    await setup_dut(dut)

    # Track allocated registers (not free ones)
    allocated_set = set()
    free_list_expected = list(range(10, 32))  # Start with P10-P31

    for cycle in range(100):
        # Only allow free if we have allocated registers
        can_free = len(allocated_set) > 0

        if can_free and random.choice([True, False]):
            # FREE operation - free a previously allocated register
            phys = random.choice(list(allocated_set))
            allocated_set.remove(phys)

            # Free it
            await free_registers(dut, phys)

            # In FIFO, freed goes to end of expected queue
            free_list_expected.append(phys)

        else:
            # ALLOCATE operation
            if free_list_expected:
                count = random.choice([1, 2])
                count = min(count, len(free_list_expected))

                expected_phys = free_list_expected[0]

                phys, phys2 = await allocate(dut, count)

                # Convert LogicArray to integer for comparison
                phys_int = int(phys)

                assert (
                    phys_int == expected_phys
                ), f"Cycle {cycle}: expected P{expected_phys}, got P{phys_int}"

                # Remove from front of expected queue
                free_list_expected.pop(0)
                allocated_set.add(phys_int)

                if count == 2:
                    expected_phys2 = free_list_expected[0]
                    phys2_int = int(phys2)
                    assert (
                        phys2_int == expected_phys2
                    ), f"Cycle {cycle}: expected P{expected_phys2}, got P{phys2_int}"
                    free_list_expected.pop(0)
                    allocated_set.add(phys2_int)

        # Verify empty flag
        actual_empty = dut.empty.value
        expected_empty = 1 if len(free_list_expected) == 0 else 0
        assert (
            actual_empty == expected_empty
        ), f"Cycle {cycle}: empty={actual_empty}, expected={expected_empty}"

        if cycle % 20 == 0:
            dut._log.debug(
                f"Cycle {cycle}: free_count={len(free_list_expected)}, allocated_count={len(allocated_set)}"
            )

    dut._log.info("Random stress test passed")


@cocotb.test()
async def test_free_list_boundary_conditions(dut):
    """Test boundary conditions with FIFO behavior"""
    dut._log.info("Starting boundary conditions test")
    await setup_dut(dut)

    # Allocate all registers
    for i in range(22):
        phys, _ = await allocate(dut, 1)
        dut._log.debug(f"Allocated P{phys}")

    assert dut.empty.value == 1, "Should be empty after 22 allocations"

    # Free one register
    await free_registers(dut, 10)
    assert dut.empty.value == 0, "Should not be empty after freeing"

    # FIFO: allocate gets P10
    phys, _ = await allocate(dut, 1)
    assert phys == 10, f"Should get P10, got P{phys}"

    # Empty again
    assert dut.empty.value == 1, "Should be empty again"

    dut._log.info("Boundary conditions test passed")


@cocotb.test()
async def test_debug_allocation_order(dut):
    """Debug: see what order registers are allocated"""
    await setup_dut(dut)

    for i in range(5):
        phys, _ = await allocate(dut, 1)
        dut._log.info(f"Allocation {i}: got P{phys}")

    # This will show you the actual sequence


@cocotb.test()
async def test_debug_pointers(dut):
    await setup_dut(dut)

    # Read initial pointers
    dut._log.info(
        f"Initial head_ptr={dut.head_ptr.value}, tail_ptr={dut.tail_ptr.value}"
    )

    # Allocate all registers
    for i in range(22):
        await allocate(dut, 1)
        dut._log.info(
            f"After alloc {i+1}: head_ptr={dut.head_ptr.value}, tail_ptr={dut.tail_ptr.value}"
        )

    # Check empty after all allocated
    dut._log.info(
        f"Final: head_ptr={dut.head_ptr.value}, tail_ptr={dut.tail_ptr.value}, empty={dut.empty.value}"
    )


@cocotb.test()
async def test_free_list_fifo_order(dut):
    """Dedicated test to verify FIFO behavior of freed registers"""
    await setup_dut(dut)

    dut._log.info("=" * 60)
    dut._log.info("TESTING FIFO BEHAVIOR")
    dut._log.info("=" * 60)

    # Step 1: Allocate first 3 registers
    phys1, _ = await allocate(dut, 1)  # Should be P10
    phys2, _ = await allocate(dut, 1)  # Should be P11
    phys3, _ = await allocate(dut, 1)  # Should be P12

    dut._log.info(f"Allocated: P{phys1}, P{phys2}, P{phys3}")
    assert phys1 == 10, f"Expected P10, got P{phys1}"
    assert phys2 == 11, f"Expected P11, got P{phys2}"
    assert phys3 == 12, f"Expected P12, got P{phys3}"

    # Step 2: Free P10 (the first allocated)
    await free_registers(dut, 10)
    dut._log.info("Freed P10")

    # Step 3: Allocate next register
    # CORRECT FIFO BEHAVIOR: Should get P13 (the next sequential from initial list)
    # Because P10 goes to the BACK of the queue, behind P13-P31
    phys4, _ = await allocate(dut, 1)
    dut._log.info(f"After freeing P10, allocated: P{phys4}")

    # This assertion tells you if your free list is a true FIFO
    if phys4 == 13:
        dut._log.info("✅ PASS: Freed P10 went to back, got P13 (CORRECT FIFO)")
        fifo_correct = True
    elif phys4 == 10:
        dut._log.info("❌ FAIL: Freed P10 went to front, got P10 (LIFO behavior)")
        fifo_correct = False
    elif phys4 == 12:
        dut._log.info("❌ FAIL: Freed P10 overwrote P12, got P12 (CORRUPTION)")
        fifo_correct = False
    else:
        dut._log.info(f"❌ FAIL: Unexpected behavior, got P{phys4}")
        fifo_correct = False

    # Step 4: Continue allocating to see what comes next
    phys5, _ = await allocate(dut, 1)
    phys6, _ = await allocate(dut, 1)
    dut._log.info(f"Next allocations: P{phys5}, P{phys6}")

    # Step 5: If FIFO worked, P10 should appear after all P13-P31 are exhausted
    if fifo_correct:
        dut._log.info("FIFO behavior VERIFIED: Freed registers go to back of queue")
    else:
        dut._log.warning(
            "FIFO behavior NOT verified - check your free list implementation"
        )

    assert fifo_correct, "Free list does not implement FIFO behavior correctly"
