from cocotb.triggers import RisingEdge


async def reset(dut):
    dut.reset.value = 1
    await RisingEdge(dut.clk)
    dut.reset.value = 0
    await RisingEdge(dut.clk)


async def step(dut, n=1):
    for _ in range(n):
        await RisingEdge(dut.clk)


def pc(dut):
    return dut.pc_out.value.integer
