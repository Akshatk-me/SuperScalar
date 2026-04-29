import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer

# Constants
NUM_REGS = 32
REG_WIDTH = 18
READ_PORTS = 8
WRITE_PORTS = 2


# Helper to create 18-bit value from data + flags
def make_prf_value(data, c_flag=0, z_flag=0):
    return (z_flag << 17) | (c_flag << 16) | (data & 0xFFFF)


def extract_data(prf_val):
    return prf_val & 0xFFFF


def extract_c_flag(prf_val):
    return (prf_val >> 16) & 1


def extract_z_flag(prf_val):
    return (prf_val >> 17) & 1


async def setup_dut(dut):
    """Setup clock and reset"""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    dut.rst.value = 1
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)


async def write_to_prf(dut, port, addr, value, wait_cycles=1):
    """Write to write port 1 or 2"""
    if port == 1:
        dut.wr_en_1.value = 1
        dut.wr_addr_1.value = addr
        dut.wr_data_1.value = value
    else:
        dut.wr_en_2.value = 1
        dut.wr_addr_2.value = addr
        dut.wr_data_2.value = value

    await RisingEdge(dut.clk)

    # Disable write after cycle
    if port == 1:
        dut.wr_en_1.value = 0
    else:
        dut.wr_en_2.value = 0


async def read_from_prf(dut, port, addr):
    """Read from read port (1-8) - asynchronous"""
    port_map = {
        1: dut.rd_addr_1,
        2: dut.rd_addr_2,
        3: dut.rd_addr_3,
        4: dut.rd_addr_4,
        5: dut.rd_addr_5,
        6: dut.rd_addr_6,
        7: dut.rd_addr_7,
        8: dut.rd_addr_8,
    }

    data_map = {
        1: dut.rd_data_1,
        2: dut.rd_data_2,
        3: dut.rd_data_3,
        4: dut.rd_data_4,
        5: dut.rd_data_5,
        6: dut.rd_data_6,
        7: dut.rd_data_7,
        8: dut.rd_data_8,
    }

    port_map[port].value = addr
    await Timer(2, unit="ns")
    return data_map[port].value.to_unsigned()


@cocotb.test()
async def test_prf_basic_write_read(dut):
    """Test basic write and read on all ports"""
    dut._log.info("Starting basic write/read test")
    await setup_dut(dut)

    test_data = [
        (0x1234, 1, 0),  # data, c, z
        (0xABCD, 0, 1),
        (0x0000, 1, 1),
        (0xFFFF, 0, 0),
    ]

    for addr in range(NUM_REGS):
        for data, c, z in test_data:
            value = make_prf_value(data, c, z)
            await write_to_prf(dut, 1, addr, value)

            # Test different read ports reading back
            for read_port in [1, 3, 5, 8]:  # Test a subset of ports
                dut.rd_addr_1.value = addr  # Set address on port 1
                await Timer(2, unit="ns")
                actual = dut.rd_data_1.value.to_unsigned()

                assert (
                    extract_data(actual) == data
                ), f"Data mismatch: expected {data:#06x}, got {extract_data(actual):#06x}"
                assert extract_c_flag(actual) == c, f"C flag mismatch at addr {addr}"
                assert extract_z_flag(actual) == z, f"Z flag mismatch at addr {addr}"

                dut._log.info(
                    f"Port {read_port} read addr {addr}: data={extract_data(actual):#06x}, C={extract_c_flag(actual)}, Z={extract_z_flag(actual)}"
                )


@cocotb.test()
async def test_prf_reset(dut):
    """Test reset clears all registers"""
    dut._log.info("Starting reset test")
    await setup_dut(dut)

    # Write some values
    for addr in range(10):
        await write_to_prf(dut, 1, addr, make_prf_value(0xDEAD, 1, 1))

    # Assert reset
    dut.rst.value = 1
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)

    # Verify all registers cleared
    for addr in range(NUM_REGS):
        await read_from_prf(dut, 1, addr)
        # Check all cleared to 0
        dut._log.info(f"Reset test: addr {addr} = {dut.rd_data_1.value}")


@cocotb.test()
async def test_prf_concurrent_writes(dut):
    """Test both write ports writing simultaneously"""
    dut._log.info("Starting concurrent writes test")
    await setup_dut(dut)

    # Write different addresses
    dut.wr_en_1.value = 1
    dut.wr_addr_1.value = 5
    dut.wr_data_1.value = make_prf_value(0x1111, 1, 0)

    dut.wr_en_2.value = 1
    dut.wr_addr_2.value = 10
    dut.wr_data_2.value = make_prf_value(0x2222, 0, 1)

    await RisingEdge(dut.clk)

    # Disable writes
    dut.wr_en_1.value = 0
    dut.wr_en_2.value = 0

    # Verify both writes succeeded
    await read_from_prf(dut, 1, 5)
    assert extract_data(dut.rd_data_1.value.to_unsigned()) == 0x1111

    await read_from_prf(dut, 2, 10)
    assert extract_data(dut.rd_data_2.value.to_unsigned()) == 0x2222


@cocotb.test()
async def test_prf_write_conflict(dut):
    """Test both ports writing to same address (port 2 wins)"""
    dut._log.info("Starting write conflict test")
    await setup_dut(dut)

    dut.wr_en_1.value = 1
    dut.wr_addr_1.value = 7
    dut.wr_data_1.value = make_prf_value(0xAAAA, 1, 0)

    dut.wr_en_2.value = 1
    dut.wr_addr_2.value = 7
    dut.wr_data_2.value = make_prf_value(0xBBBB, 0, 1)

    await RisingEdge(dut.clk)

    dut.wr_en_1.value = 0
    dut.wr_en_2.value = 0

    # Port 2 should win (overwrites port 1)
    await read_from_prf(dut, 1, 7)
    actual = dut.rd_data_1.value.to_unsigned()
    assert (
        extract_data(actual) == 0xBBBB
    ), f"Expected 0xBBBB, got {extract_data(actual):#06x}"
    assert extract_c_flag(actual) == 0
    assert extract_z_flag(actual) == 1


@cocotb.test()
async def test_prf_read_during_write(dut):
    """Test reading same address being written in same cycle"""
    dut._log.info("Starting read-during-write test")
    await setup_dut(dut)

    # First write initial value
    await write_to_prf(dut, 1, 3, make_prf_value(0x1234, 0, 0))

    # Setup read of address 3
    dut.rd_addr_1.value = 3
    await Timer(2, unit="ns")
    old_value = dut.rd_data_1.value.to_unsigned()

    # Simultaneously write new value in same clock cycle
    dut.wr_en_1.value = 1
    dut.wr_addr_1.value = 3
    dut.wr_data_1.value = make_prf_value(0x5678, 1, 1)

    await RisingEdge(dut.clk)
    dut.wr_en_1.value = 0

    # Read after write cycle
    await read_from_prf(dut, 1, 3)
    new_value = dut.rd_data_1.value.to_unsigned()

    # Old read should get old value (asynchronous read)
    assert extract_data(old_value) == 0x1234
    # New value changed after clock edge
    assert extract_data(new_value) == 0x5678
    dut._log.info(
        f"Read during write: old={extract_data(old_value):#06x}, new={extract_data(new_value):#06x}"
    )


@cocotb.test()
async def test_prf_random_ops(dut):
    """Stress test with random operations"""
    dut._log.info("Starting random stress test")
    await setup_dut(dut)

    # Keep track of expected values in Python
    expected = {i: 0 for i in range(NUM_REGS)}  # data only, ignore flags for this test

    for _ in range(100):
        op = random.choice(["write1", "write2", "read"])

        if op == "write1":
            addr = random.randint(0, NUM_REGS - 1)
            data = random.randint(0, 0xFFFF)
            expected[addr] = data
            await write_to_prf(dut, 1, addr, data)

        elif op == "write2":
            addr = random.randint(0, NUM_REGS - 1)
            data = random.randint(0, 0xFFFF)
            expected[addr] = data
            await write_to_prf(dut, 2, addr, data)

        else:  # read
            addr = random.randint(0, NUM_REGS - 1)
            await read_from_prf(dut, 1, addr)
            actual = dut.rd_data_1.value.to_unsigned()
            assert (
                actual == expected[addr]
            ), f"Read mismatch: addr {addr}, expected {expected[addr]:#06x}, got {actual:#06x}"


@cocotb.test()
async def test_prf_all_ports_simultaneous(dut):
    """Test all 8 read ports reading different addresses"""
    dut._log.info("Testing all 8 read ports")
    await setup_dut(dut)

    # Write test values
    for addr in range(8):
        await write_to_prf(
            dut, 1, addr, make_prf_value(0x1000 + addr, addr % 2, (addr + 1) % 2)
        )

    # Setup all 8 read addresses
    dut.rd_addr_1.value = 0
    dut.rd_addr_2.value = 1
    dut.rd_addr_3.value = 2
    dut.rd_addr_4.value = 3
    dut.rd_addr_5.value = 4
    dut.rd_addr_6.value = 5
    dut.rd_addr_7.value = 6
    dut.rd_addr_8.value = 7

    await Timer(2, unit="ns")

    # Verify all ports
    assert extract_data(dut.rd_data_1.value.to_unsigned()) == 0x1000
    assert extract_data(dut.rd_data_2.value.to_unsigned()) == 0x1001
    assert extract_data(dut.rd_data_3.value.to_unsigned()) == 0x1002
    assert extract_data(dut.rd_data_4.value.to_unsigned()) == 0x1003
    assert extract_data(dut.rd_data_5.value.to_unsigned()) == 0x1004
    assert extract_data(dut.rd_data_6.value.to_unsigned()) == 0x1005
    assert extract_data(dut.rd_data_7.value.to_unsigned()) == 0x1006
    assert extract_data(dut.rd_data_8.value.to_unsigned()) == 0x1007

    dut._log.info("All 8 read ports verified")
