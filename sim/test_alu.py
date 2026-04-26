import random

import cocotb
from alu_model import alu_model
from cocotb.triggers import Timer


@cocotb.test()
async def test_alu_random(dut):

    for _ in range(100):

        data1 = random.randint(0, 0xFFFF)
        data2 = random.randint(0, 0xFFFF)
        alu_ctrl = random.randint(0, 31)

        # Drive inputs
        dut.data1.value = data1
        dut.data2.value = data2
        dut.alu_control.value = alu_ctrl
        dut.c_in.value = 0
        dut.z_in.value = 0

        await Timer(1, units="ns")  # combinational delay

        # Get DUT outputs
        dut_res = dut.alu_result.value.integer
        dut_zero = dut.zero.value.integer
        dut_carry = dut.carry.value.integer

        # Expected
        exp_res, exp_zero, exp_carry, exp_lt, exp_eq, exp_le = alu_model(
            data1, data2, alu_ctrl
        )

        assert dut_res == exp_res, f"Result mismatch: {data1},{data2},{alu_ctrl}"
        assert dut_zero == exp_zero
        assert dut_carry == exp_carry
