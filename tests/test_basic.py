import cocotb
import utils
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge  # Event trigger for clock edges


@cocotb.test()
async def test_pc_increment(dut):

    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    print("pc_out raw:", dut.pc_out.value)  # will print UUUUUUUUUUUUUUUU
    await utils.reset(dut)
    assert dut.pc_out.value.to_unsigned() == 0
    print("pc_out raw:", dut.pc_out.value)  # will print 0000000000000000

    await utils.step(dut, 3)
    print("pc_out raw:", dut.pc_out.value)  # will print 0000000000000110
    assert dut.pc_out.value.to_unsigned() == 6
