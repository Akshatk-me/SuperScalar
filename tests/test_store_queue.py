import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

SQ_SIZE = 8


async def setup_sq(dut):
    """Setup clock and reset the Store Queue"""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    # Initialize all inputs to 0
    dut.alloc_en.value = 0
    dut.agu_valid.value = 0
    dut.agu_sq_idx.value = 0
    dut.agu_addr.value = 0
    dut.data_valid.value = 0
    dut.data_sq_idx.value = 0
    dut.data_val.value = 0
    dut.load_req_valid.value = 0
    dut.load_req_addr.value = 0
    dut.commit_en.value = 0
    dut.branch_flush.value = 0

    # Reset
    dut.rst.value = 1
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)
    await Timer(2, unit="ns")


# ==========================================
# DIRECTED TESTS
# ==========================================


@cocotb.test()
async def test_sq_reset(dut):
    """Test that reset clears the queue and sets full to 0"""
    dut._log.info("Starting SQ reset test")
    await setup_sq(dut)

    assert dut.sq_full.value == 0, "SQ should not be full after reset"
    assert dut.mem_write_en.value == 0, "Should not write to memory on reset"
    dut._log.info("Reset test passed")


@cocotb.test()
async def test_sq_allocate_and_full(dut):
    """Test allocating entries until the queue is full"""
    dut._log.info("Starting allocate and full test")
    await setup_sq(dut)

    # Allocate 7 entries (Full flag is set when count >= 7 based on your VHDL)
    for i in range(7):
        dut.alloc_en.value = 1
        await RisingEdge(dut.clk)

    dut.alloc_en.value = 0
    await Timer(2, unit="ns")

    assert dut.sq_full.value == 1, "SQ should be full after 7 allocations"
    dut._log.info("Allocate and full test passed")


@cocotb.test()
async def test_sq_out_of_order_execute(dut):
    """Test address and data arriving out of order"""
    dut._log.info("Starting out-of-order execute test")
    await setup_sq(dut)

    # Allocate entry at index 0
    dut.alloc_en.value = 1
    await RisingEdge(dut.clk)
    dut.alloc_en.value = 0

    # Execute Data first (out of order)
    dut.data_valid.value = 1
    dut.data_sq_idx.value = 0
    dut.data_val.value = 0xDEAD
    await RisingEdge(dut.clk)
    dut.data_valid.value = 0

    # Try to commit - should fail because address isn't ready
    dut.commit_en.value = 1
    await Timer(1, unit="ns")
    assert dut.mem_write_en.value == 0, "Should not commit without address"

    # FIX: Turn commit_en OFF before the clock edge so we don't accidentally pop!
    dut.commit_en.value = 0
    await RisingEdge(dut.clk)

    # Execute Address
    dut.agu_valid.value = 1
    dut.agu_sq_idx.value = 0
    dut.agu_addr.value = 0x1000
    await RisingEdge(dut.clk)
    dut.agu_valid.value = 0

    # Now it should be ready to commit
    dut.commit_en.value = 1
    await Timer(1, unit="ns")
    assert dut.mem_write_en.value == 1, "Should be ready to commit"
    assert dut.mem_write_addr.value == 0x1000, "Commit address mismatch"
    assert dut.mem_write_data.value == 0xDEAD, "Commit data mismatch"
    dut._log.info("Out-of-order execute test passed")


@cocotb.test()
async def test_sq_store_to_load_forwarding(dut):
    """Test STLF CAM matching logic"""
    dut._log.info("Starting Store-to-Load Forwarding test")
    await setup_sq(dut)

    # Allocate entry 0
    dut.alloc_en.value = 1
    await RisingEdge(dut.clk)
    dut.alloc_en.value = 0

    # Provide Address and Data for entry 0
    dut.agu_valid.value = 1
    dut.agu_sq_idx.value = 0
    dut.agu_addr.value = 0x2000

    dut.data_valid.value = 1
    dut.data_sq_idx.value = 0
    dut.data_val.value = 0xBEEF
    await RisingEdge(dut.clk)

    dut.agu_valid.value = 0
    dut.data_valid.value = 0

    # Load requests address 0x2000
    dut.load_req_valid.value = 1
    dut.load_req_addr.value = 0x2000
    await Timer(1, unit="ns")

    assert dut.forward_hit.value == 1, "Forwarding should hit"
    assert dut.forward_data.value == 0xBEEF, "Forwarded data should be 0xBEEF"

    # Load requests different address
    dut.load_req_addr.value = 0x2004
    await Timer(1, unit="ns")
    assert dut.forward_hit.value == 0, "Forwarding should miss on different address"

    dut._log.info("Store-to-Load Forwarding test passed")


@cocotb.test()
async def test_sq_branch_flush(dut):
    """Test flushing the store queue on mispredict"""
    dut._log.info("Starting branch flush test")
    await setup_sq(dut)

    # Allocate a few entries
    dut.alloc_en.value = 1
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.alloc_en.value = 0

    # Flush it
    dut.branch_flush.value = 1
    await RisingEdge(dut.clk)
    dut.branch_flush.value = 0
    await Timer(1, unit="ns")

    assert dut.sq_full.value == 0, "Queue should be empty after flush"
    dut._log.info("Branch flush test passed")


# ==========================================
# GOLDEN MODEL (RANDOM STRESS TEST)
# ==========================================


@cocotb.test()
async def test_sq_random_stress(dut):
    """Cycle-accurate random stress test using a Python golden model"""
    dut._log.info("Starting Random Stress test")
    await setup_sq(dut)

    # Golden Model State
    sq_state = [
        {"valid": False, "addr_ready": False, "data_ready": False, "addr": 0, "data": 0}
        for _ in range(SQ_SIZE)
    ]
    head = 0
    tail = 0
    count = 0

    for cycle in range(500):
        # 1. GENERATE STIMULUS
        do_alloc = count < 7 and random.choice(
            [True, False]
        )  # VHDL full flag trips at >= 7

        # Pick random valid entries to receive address/data (that don't have it yet)
        valid_unready_addrs = [
            i
            for i, entry in enumerate(sq_state)
            if entry["valid"] and not entry["addr_ready"]
        ]
        do_agu = len(valid_unready_addrs) > 0 and random.choice([True, False])
        agu_idx = random.choice(valid_unready_addrs) if do_agu else 0
        agu_addr = random.randint(0x1000, 0xFFFF) if do_agu else 0

        valid_unready_data = [
            i
            for i, entry in enumerate(sq_state)
            if entry["valid"] and not entry["data_ready"]
        ]
        do_data = len(valid_unready_data) > 0 and random.choice([True, False])
        data_idx = random.choice(valid_unready_data) if do_data else 0
        data_val = random.randint(0, 0xFFFF) if do_data else 0

        # Attempt commit
        # Attempt commit (FIX: Only attempt if the head is actually ready, mimicking a real ROB)
        head_ready = (
            sq_state[head]["valid"]
            and sq_state[head]["addr_ready"]
            and sq_state[head]["data_ready"]
        )
        do_commit = head_ready and random.choice([True, False])

        # Random Load request to test STLF
        do_load = random.choice([True, False])
        load_addr = agu_addr if (do_load and do_agu) else random.randint(0x1000, 0x100F)

        # Random Flush (rare)
        do_flush = random.random() < 0.02

        # Apply inputs to DUT
        dut.alloc_en.value = 1 if do_alloc else 0
        dut.agu_valid.value = 1 if do_agu else 0
        dut.agu_sq_idx.value = agu_idx
        dut.agu_addr.value = agu_addr
        dut.data_valid.value = 1 if do_data else 0
        dut.data_sq_idx.value = data_idx
        dut.data_val.value = data_val
        dut.commit_en.value = 1 if do_commit else 0
        dut.load_req_valid.value = 1 if do_load else 0
        dut.load_req_addr.value = load_addr
        dut.branch_flush.value = 1 if do_flush else 0

        await Timer(1, unit="ns")  # Let combinational logic settle

        # 2. VERIFY COMBINATIONAL OUTPUTS (Against Golden Model)

        # Verify STLF
        exp_hit = False
        exp_forward_data = 0
        if do_load:
            # Replicate VHDL logic: scans 0 to 7
            for i in range(SQ_SIZE):
                if (
                    sq_state[i]["valid"]
                    and sq_state[i]["addr_ready"]
                    and sq_state[i]["data_ready"]
                ):
                    if sq_state[i]["addr"] == load_addr:
                        exp_hit = True
                        exp_forward_data = sq_state[i]["data"]

        assert dut.forward_hit.value == (
            1 if exp_hit else 0
        ), f"Cycle {cycle}: STLF Hit mismatch"
        if exp_hit:
            assert (
                dut.forward_data.value == exp_forward_data
            ), f"Cycle {cycle}: STLF Data mismatch"

        # Verify Commit outputs
        exp_mem_write = (
            do_commit
            and sq_state[head]["valid"]
            and sq_state[head]["addr_ready"]
            and sq_state[head]["data_ready"]
        )
        assert dut.mem_write_en.value == (
            1 if exp_mem_write else 0
        ), f"Cycle {cycle}: Mem Write En mismatch"

        if exp_mem_write:
            assert dut.mem_write_addr.value == sq_state[head]["addr"]
            assert dut.mem_write_data.value == sq_state[head]["data"]

        # Verify Full Flag
        exp_full = 1 if count >= 7 else 0
        assert dut.sq_full.value == exp_full, f"Cycle {cycle}: Full flag mismatch"

        # 3. ADVANCE TIME
        await RisingEdge(dut.clk)

        # 4. UPDATE PYTHON STATE
        if do_flush:
            for i in range(SQ_SIZE):
                sq_state[i]["valid"] = False
            head = 0
            tail = 0
            count = 0
        else:
            if exp_mem_write:
                sq_state[head]["valid"] = False
                head = (head + 1) % SQ_SIZE
                count -= 1

            if do_alloc:
                sq_state[tail]["valid"] = True
                sq_state[tail]["addr_ready"] = False
                sq_state[tail]["data_ready"] = False
                tail = (tail + 1) % SQ_SIZE
                count += 1

            if do_agu:
                sq_state[agu_idx]["addr"] = agu_addr
                sq_state[agu_idx]["addr_ready"] = True

            if do_data:
                sq_state[data_idx]["data"] = data_val
                sq_state[data_idx]["data_ready"] = True

    dut._log.info("Random Stress test passed!")
