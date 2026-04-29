import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, ReadOnly, RisingEdge


async def reset_dut(dut):
    """Helper to reset the Micro-Op Sequencer"""
    dut.rst.value = 1
    dut.is_complex_mem.value = 0
    dut.base_addr_in.value = 0
    dut.bitmap_in.value = 0
    dut.is_store.value = 0

    await ClockCycles(dut.clk, 2)
    dut.rst.value = 0
    await RisingEdge(dut.clk)


@cocotb.test()
async def test_lm_sparse_bitmap(dut):
    """Test cracking an LM instruction for R0, R2, and R5"""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)

    # Dispatch LM R0, R2, R5
    # Bitmap: R0(bit 0), R2(bit 2), R5(bit 5) => 00100101 in binary => 0x25
    # Base Address: 0x1000
    dut.is_complex_mem.value = 1
    dut.is_store.value = 0
    dut.bitmap_in.value = 0x25
    dut.base_addr_in.value = 0x1000

    await RisingEdge(dut.clk)
    dut.is_complex_mem.value = (
        0  # Drop the signal (acts like a 1-cycle pulse from decode)
    )

    # Wait and collect generated micro-ops
    uops = []
    timeout = 20
    cycles = 0

    while cycles < timeout:
        await ReadOnly()  # Sample at the very end of the cycle

        if dut.uop_valid.value == 1:
            uops.append(
                {
                    "reg": int(dut.uop_reg_idx.value),
                    "addr": hex(int(dut.uop_mem_addr.value)),
                    "is_store": int(dut.uop_is_store.value),
                }
            )

        await RisingEdge(dut.clk)
        cycles += 1

        # Stop collecting when the FSM finishes and drops the stall signal
        if dut.stall_fetch.value == 0 and cycles > 2:
            break

    # We expect exactly 3 micro-ops to be generated
    assert len(uops) == 3, f"Expected 3 uops, got {len(uops)}"
    assert uops[0] == {
        "reg": 0,
        "addr": "0x1000",
        "is_store": 0,
    }, f"Uop 0 wrong: {uops[0]}"
    assert uops[1] == {
        "reg": 2,
        "addr": "0x1002",
        "is_store": 0,
    }, f"Uop 1 wrong: {uops[1]}"
    assert uops[2] == {
        "reg": 5,
        "addr": "0x1004",
        "is_store": 0,
    }, f"Uop 2 wrong: {uops[2]}"

    dut._log.info("Sparse LM Test Passed!")


@cocotb.test()
async def test_sm_full_bitmap(dut):
    """Test cracking an SM instruction for all 8 registers (R0-R7)"""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)

    # Dispatch SM R0-R7 (Bitmap: 11111111 => 0xFF)
    dut.is_complex_mem.value = 1
    dut.is_store.value = 1
    dut.bitmap_in.value = 0xFF
    dut.base_addr_in.value = 0x2000

    await RisingEdge(dut.clk)
    dut.is_complex_mem.value = 0

    uops = []

    while True:
        await ReadOnly()
        if dut.uop_valid.value == 1:
            uops.append(int(dut.uop_reg_idx.value))

        await RisingEdge(dut.clk)
        if dut.stall_fetch.value == 0 and len(uops) > 0:
            break

    # Verify all 8 registers were output sequentially
    assert len(uops) == 8, f"Expected 8 uops, got {len(uops)}"
    assert uops == [0, 1, 2, 3, 4, 5, 6, 7], f"Register sequence wrong: {uops}"

    dut._log.info("Full SM Test Passed!")


@cocotb.test()
async def test_early_exit_optimization(dut):
    """Test that the FSM exits quickly if no bits (or only low bits) are set"""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)

    # Dispatch LM R0 only (Bitmap: 00000001 => 0x01)
    dut.is_complex_mem.value = 1
    dut.bitmap_in.value = 0x01

    await RisingEdge(dut.clk)
    dut.is_complex_mem.value = 0

    cycles_stalled = 0
    while True:
        await ReadOnly()
        if dut.stall_fetch.value == 1:
            cycles_stalled += 1

        await RisingEdge(dut.clk)
        if dut.stall_fetch.value == 0 and cycles_stalled > 0:
            break

    # With early exit, cracking R0 only shouldn't take 8+ cycles.
    # It should take ~3 cycles (IDLE -> R0_CRACK -> DONE -> IDLE)
    assert (
        cycles_stalled <= 4
    ), f"FSM did not early exit! Stalled for {cycles_stalled} cycles"

    dut._log.info("Early Exit Optimization Test Passed!")


import random


@cocotb.test()
async def test_randomized_bitmaps(dut):
    """Test 100 completely random complex memory instructions"""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)

    for i in range(100):
        # 1. Generate Random Inputs
        rand_bitmap = random.randint(1, 255)  # 1 to 0xFF (Skip 0 to avoid no-ops)
        rand_base_addr = random.randint(0, 0xEFF0) & 0xFFFE  # Random even address
        rand_is_store = random.choice([0, 1])

        # 2. Compute Expected Output in Python (The Golden Model)
        expected_uops = []
        current_addr = rand_base_addr
        for reg_idx in range(8):
            if (rand_bitmap & (1 << reg_idx)) != 0:
                expected_uops.append(
                    {"reg": reg_idx, "addr": current_addr, "is_store": rand_is_store}
                )
                current_addr += 2

        # 3. Drive the Hardware
        dut.is_complex_mem.value = 1
        dut.is_store.value = rand_is_store
        dut.bitmap_in.value = rand_bitmap
        dut.base_addr_in.value = rand_base_addr

        await RisingEdge(dut.clk)
        dut.is_complex_mem.value = 0

        # 4. Collect Hardware Output
        actual_uops = []
        cycles_stalled = 0

        while True:
            await ReadOnly()
            if dut.uop_valid.value == 1:
                actual_uops.append(
                    {
                        "reg": int(dut.uop_reg_idx.value),
                        "addr": int(dut.uop_mem_addr.value),
                        "is_store": int(dut.uop_is_store.value),
                    }
                )

            if dut.stall_fetch.value == 1:
                cycles_stalled += 1

            await RisingEdge(dut.clk)
            if dut.stall_fetch.value == 0 and cycles_stalled > 0:
                break  # FSM Finished

        # 5. Assert Hardware matches Python Model
        assert len(actual_uops) == len(
            expected_uops
        ), f"Iter {i}: Length mismatch for bitmap {hex(rand_bitmap)}"
        for actual, expected in zip(actual_uops, expected_uops):
            assert (
                actual == expected
            ), f"Iter {i}: Uop mismatch! Expected {expected}, got {actual}"

    dut._log.info("Completed 100 Randomized Tests Successfully!")
