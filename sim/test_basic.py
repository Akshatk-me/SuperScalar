import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge  # Event trigger for clock edges


@cocotb.test()
async def test_pc(dut):

    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    dut.reset.value = 1
    await RisingEdge(dut.clk)

    dut.reset.value = 0
    await RisingEdge(dut.clk)
    print("pc_out raw:", dut.pc_out.value)

    assert dut.pc_out.value.to_unsigned() == 0

    await RisingEdge(dut.clk)
    assert dut.pc_out.value.to_unsigned() == 2
