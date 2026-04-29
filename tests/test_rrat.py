import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

# Constants
ARCH_REGS = 10  # 0-7: R0-R7, 8: C flag, 9: Z flag


async def setup_rrat(dut):
    """Setup clock and reset"""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    # Initialize inputs
    dut.commit_valid_1.value = 0
    dut.commit_we_1.value = 0
    dut.commit_arch_1.value = 0
    dut.commit_phys_1.value = 0
    dut.commit_valid_2.value = 0
    dut.commit_we_2.value = 0
    dut.commit_arch_2.value = 0
    dut.commit_phys_2.value = 0

    # Reset sequence
    dut.rst.value = 1
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)
    await Timer(2, unit="ns")


async def commit_instruction(dut, arch, phys, we=True, port=1):
    """Commit an instruction and return the combinational free-list outputs"""
    if port == 1:
        dut.commit_valid_1.value = 1
        dut.commit_we_1.value = 1 if we else 0
        dut.commit_arch_1.value = arch
        dut.commit_phys_1.value = phys
    else:
        dut.commit_valid_2.value = 1
        dut.commit_we_2.value = 1 if we else 0
        dut.commit_arch_2.value = arch
        dut.commit_phys_2.value = phys

    # Wait for the VHDL combinational logic to settle
    await Timer(1, unit="ns")

    # CAPTURE the outputs BEFORE the clock edge clears the inputs!
    f_en1 = dut.free_en_1.value if dut.free_en_1.value.is_resolvable else 0
    f_p1 = dut.free_phys_1.value if dut.free_phys_1.value.is_resolvable else 0
    f_en2 = dut.free_en_2.value if dut.free_en_2.value.is_resolvable else 0
    f_p2 = dut.free_phys_2.value if dut.free_phys_2.value.is_resolvable else 0

    await RisingEdge(dut.clk)

    # Clear after commit
    if port == 1:
        dut.commit_valid_1.value = 0
        dut.commit_we_1.value = 0
    else:
        dut.commit_valid_2.value = 0
        dut.commit_we_2.value = 0
    await Timer(2, unit="ns")

    return f_en1, f_p1, f_en2, f_p2


async def commit_two_instructions(dut, arch1, phys1, arch2, phys2, we1=True, we2=True):
    """Commit two instructions and return the combinational free-list outputs"""
    dut.commit_valid_1.value = 1
    dut.commit_we_1.value = 1 if we1 else 0
    dut.commit_arch_1.value = arch1
    dut.commit_phys_1.value = phys1

    dut.commit_valid_2.value = 1
    dut.commit_we_2.value = 1 if we2 else 0
    dut.commit_arch_2.value = arch2
    dut.commit_phys_2.value = phys2

    # Wait for the VHDL combinational logic to settle
    await Timer(1, unit="ns")

    # CAPTURE
    f_en1 = dut.free_en_1.value if dut.free_en_1.value.is_resolvable else 0
    f_p1 = dut.free_phys_1.value if dut.free_phys_1.value.is_resolvable else 0
    f_en2 = dut.free_en_2.value if dut.free_en_2.value.is_resolvable else 0
    f_p2 = dut.free_phys_2.value if dut.free_phys_2.value.is_resolvable else 0

    await RisingEdge(dut.clk)

    dut.commit_valid_1.value = 0
    dut.commit_we_1.value = 0
    dut.commit_valid_2.value = 0
    dut.commit_we_2.value = 0
    await Timer(2, unit="ns")

    return f_en1, f_p1, f_en2, f_p2


def extract_rrat_snapshot(rrat_snapshot):
    """Extract individual mappings from 50-bit snapshot"""
    mappings = []
    for i in range(10):
        start = i * 5
        val = (rrat_snapshot >> start) & 0x1F
        mappings.append(val)
    return mappings


@cocotb.test()
async def test_rrat_reset(dut):
    """Test reset initializes mapping: R0→P0, R1→P1, ..., C→P8, Z→P9"""
    dut._log.info("Starting RRAT reset test")
    await setup_rrat(dut)

    snapshot = int(dut.rrat_snapshot.value)
    mappings = extract_rrat_snapshot(snapshot)

    for i in range(10):
        assert mappings[i] == i, f"Arch {i} should map to P{i}, got P{mappings[i]}"

    dut._log.info("Reset test passed")


@cocotb.test()
async def test_rrat_single_commit(dut):
    """Test single instruction commit updates RRAT"""
    dut._log.info("Starting single commit test")
    await setup_rrat(dut)

    # We now receive the combinational outputs back from the helper!
    f_en1, f_p1, f_en2, f_p2 = await commit_instruction(
        dut, arch=5, phys=20, we=True, port=1
    )

    snapshot = int(dut.rrat_snapshot.value)
    mappings = extract_rrat_snapshot(snapshot)
    assert mappings[5] == 20, f"R5 should map to P20, got P{mappings[5]}"

    # Assert against our captured values, not the DUT directly
    assert f_en1 == 1, "Free enable should be set"
    assert f_p1 == 5, f"Should free P5, got P{f_p1}"

    dut._log.info("Single commit test passed")


@cocotb.test()
async def test_rrat_non_we_commit(dut):
    """Test commit of non-write instruction (branch, NOP)"""
    dut._log.info("Starting non-WE commit test")
    await setup_rrat(dut)

    f_en1, f_p1, f_en2, f_p2 = await commit_instruction(
        dut, arch=5, phys=20, we=False, port=1
    )

    snapshot = int(dut.rrat_snapshot.value)
    mappings = extract_rrat_snapshot(snapshot)
    assert mappings[5] == 5, f"R5 should still be P5, got P{mappings[5]}"

    assert f_en1 == 0, "Free enable should be 0 for non-WE"

    dut._log.info("Non-WE commit test passed")


@cocotb.test()
async def test_rrat_two_commits_different_regs(dut):
    """Test two commits to different architectural registers"""
    dut._log.info("Starting two commits different regs test")
    await setup_rrat(dut)

    f_en1, f_p1, f_en2, f_p2 = await commit_two_instructions(
        dut, arch1=5, phys1=20, arch2=6, phys2=21
    )

    snapshot = int(dut.rrat_snapshot.value)
    mappings = extract_rrat_snapshot(snapshot)
    assert mappings[5] == 20, "R5 should map to P20"
    assert mappings[6] == 21, "R6 should map to P21"

    assert f_en1 == 1, "Free1 enable should be set"
    assert f_p1 == 5, "Should free P5"
    assert f_en2 == 1, "Free2 enable should be set"
    assert f_p2 == 6, "Should free P6"

    dut._log.info("Two commits different regs test passed")


@cocotb.test()
async def test_rrat_same_register_commit(dut):
    """Test both commits to same architectural register (WAW hazard)"""
    dut._log.info("Starting same register commit test")
    await setup_rrat(dut)

    f_en1, f_p1, f_en2, f_p2 = await commit_two_instructions(
        dut, arch1=5, phys1=20, arch2=5, phys2=21
    )

    snapshot = int(dut.rrat_snapshot.value)
    mappings = extract_rrat_snapshot(snapshot)
    assert mappings[5] == 21, f"R5 should map to P21 (second wins), got P{mappings[5]}"

    assert f_en1 == 1, "Free1 enable should be set"
    assert f_p1 == 5, "First should free P5"
    assert f_en2 == 1, "Free2 enable should be set"
    assert f_p2 == 20, "Second should free P20 (Inst1's phys)"

    dut._log.info("Same register commit test passed")


@cocotb.test()
async def test_rrat_flag_updates(dut):
    """Test C and Z flag updates"""
    dut._log.info("Starting flag update test")
    await setup_rrat(dut)

    await commit_instruction(dut, arch=8, phys=30, we=True, port=1)
    snapshot = int(dut.rrat_snapshot.value)
    mappings = extract_rrat_snapshot(snapshot)
    assert mappings[8] == 30, f"C flag should map to P30, got P{mappings[8]}"

    await commit_instruction(dut, arch=9, phys=31, we=True, port=1)
    snapshot = int(dut.rrat_snapshot.value)
    mappings = extract_rrat_snapshot(snapshot)
    assert mappings[9] == 31, f"Z flag should map to P31, got P{mappings[9]}"


@cocotb.test()
async def test_rrat_sequential_updates(dut):
    """Test sequential commits to same register"""
    dut._log.info("Starting sequential updates test")
    await setup_rrat(dut)

    f_en1, f_p1, f_en2, f_p2 = await commit_instruction(
        dut, arch=5, phys=20, we=True, port=1
    )
    snapshot = int(dut.rrat_snapshot.value)
    mappings = extract_rrat_snapshot(snapshot)
    assert mappings[5] == 20, "R5 should be P20"
    assert f_p1 == 5, "Should free P5"

    f_en1, f_p1, f_en2, f_p2 = await commit_instruction(
        dut, arch=5, phys=25, we=True, port=1
    )
    snapshot = int(dut.rrat_snapshot.value)
    mappings = extract_rrat_snapshot(snapshot)
    assert mappings[5] == 25, "R5 should now be P25"
    assert f_p1 == 20, "Should free P20 (previous mapping)"


@cocotb.test()
async def test_rrat_snapshot_consistency(dut):
    """Test RRAT snapshot is consistent with internal state"""
    dut._log.info("Starting snapshot consistency test")
    await setup_rrat(dut)

    await commit_instruction(dut, arch=5, phys=20, we=True, port=1)
    await commit_instruction(dut, arch=6, phys=21, we=True, port=1)
    await commit_instruction(dut, arch=8, phys=30, we=True, port=1)

    snapshot = int(dut.rrat_snapshot.value)
    mappings = extract_rrat_snapshot(snapshot)

    assert mappings[5] == 20, "R5 mismatch"
    assert mappings[6] == 21, "R6 mismatch"
    assert mappings[8] == 30, "C flag mismatch"
    assert mappings[0] == 0, "R0 should still be P0"


@cocotb.test()
async def test_rrat_random_stress(dut):
    """Random stress test"""
    dut._log.info("Starting random stress test")
    await setup_rrat(dut)

    expected = list(range(10))

    for cycle in range(100):
        num_commits = random.choice([1, 2])
        commits = []
        for i in range(num_commits):
            arch = random.randint(0, 9)
            phys = random.randint(10, 31)
            we = random.choice([True, False])
            commits.append((arch, phys, we))

        if num_commits == 1:
            arch, phys, we = commits[0]
            old_phys = expected[arch] if we else None

            f_en1, f_p1, f_en2, f_p2 = await commit_instruction(
                dut, arch=arch, phys=phys, we=we, port=1
            )

            if we:
                expected[arch] = phys
                assert f_en1 == 1, "Free enable should be set"
                assert f_p1 == old_phys, f"Should free P{old_phys}"
            else:
                assert f_en1 == 0, "Free enable should be 0 for non-WE"

        else:
            (arch1, phys1, we1), (arch2, phys2, we2) = commits
            old_phys1 = expected[arch1] if we1 else None
            old_phys2 = expected[arch2] if we2 else None

            f_en1, f_p1, f_en2, f_p2 = await commit_two_instructions(
                dut, arch1, phys1, arch2, phys2, we1, we2
            )

            if we1:
                expected[arch1] = phys1
            if we2:
                if arch2 == arch1 and we1 and we2:
                    expected[arch1] = phys2
                else:
                    expected[arch2] = phys2

            if we1:
                assert f_en1 == 1
                assert f_p1 == old_phys1
            else:
                assert f_en1 == 0

        snapshot = int(dut.rrat_snapshot.value)
        mappings = extract_rrat_snapshot(snapshot)

        for i in range(10):
            assert (
                mappings[i] == expected[i]
            ), f"Cycle {cycle}: Arch {i} expected P{expected[i]}, got P{mappings[i]}"

    dut._log.info("Random stress test passed")
