import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

# ============================================================
# PROGRAM MEMORY (ROM)
# ============================================================

PROG_ROM = {
    0x0000: 0x1001,
    0x0002: 0x2002,
    0x0004: 0x3003,
    0x0006: 0x4004,
    0x0008: 0x5005,
    0x000A: 0x6006,
    0x000C: 0x7007,
    0x000E: 0x8008,
}


# ============================================================
# CLOCKED TB BASE
# ============================================================


class ClockedTB:
    def __init__(self, dut):
        self.dut = dut

    async def start(self):
        cocotb.start_soon(Clock(self.dut.clk, 10, unit="ns").start())

    async def tick(self):
        await RisingEdge(self.dut.clk)

    async def reset(self):
        self.dut.rst.value = 1
        self.clear_inputs()

        for _ in range(3):
            await self.tick()

        self.dut.rst.value = 0
        await self.tick()

    def clear_inputs(self):
        self.dut.redirect_valid.value = 0
        self.dut.redirect_pc.value = 0
        self.dut.full_stall.value = 0
        self.dut.stall_lane_2.value = 0
        self.dut.btb_update_valid.value = 0
        self.dut.btb_update_pc.value = 0
        self.dut.btb_update_target.value = 0
        self.dut.btb_update_taken.value = 0


# ============================================================
# SAFE SIGNAL READ
# ============================================================


def safe_int(signal, default=0):
    val = signal.value
    return int(val) if val.is_resolvable else default


# ============================================================
# MEMORY MODEL (FIXED + SAFE)
# ============================================================


async def mock_instruction_memory(dut):
    """Cycle-safe combinational memory model"""

    # Wait for reset to deassert
    while dut.rst.value != 0:
        await RisingEdge(dut.clk)

    # One extra cycle to stabilize PC
    await RisingEdge(dut.clk)

    while True:
        pc = safe_int(dut.imem_pc)

        inst1 = PROG_ROM.get(pc, 0x0000)
        inst2 = PROG_ROM.get(pc + 2, 0x0000)

        # combinational delay
        await Timer(1, unit="ns")

        dut.imem_inst_1.value = inst1
        dut.imem_inst_2.value = inst2

        await RisingEdge(dut.clk)


# ============================================================
# PC GOLDEN MODEL
# ============================================================


class PCModel:
    def __init__(self):
        self.pc = 0

    def step(self, redirect_valid, redirect_pc, full_stall, stall_lane_2):
        if redirect_valid:
            self.pc = redirect_pc

        elif full_stall:
            pass

        elif stall_lane_2:
            self.pc += 2

        else:
            self.pc += 4

        self.pc &= 0xFFFF
        return self.pc


# ============================================================
# PC CHECKER
# ============================================================


class PCChecker:
    def __init__(self, dut):
        self.dut = dut
        self.model = PCModel()
        self.cycle = 0

    def update_model(self):
        self.model.step(
            redirect_valid=int(self.dut.redirect_valid.value),
            redirect_pc=int(self.dut.redirect_pc.value),
            full_stall=int(self.dut.full_stall.value),
            stall_lane_2=int(self.dut.stall_lane_2.value),
        )

    async def check(self):
        await RisingEdge(self.dut.clk)

        actual = self.dut.imem_pc.value
        expected = self.model.pc

        if actual.is_resolvable:
            actual_val = int(actual)
            assert actual_val == expected, (
                f"[Cycle {self.cycle}] PC mismatch: "
                f"expected {expected:#06x}, got {actual_val:#06x}"
            )
        else:
            self.dut._log.warning(f"[Cycle {self.cycle}] PC not resolvable")

        self.cycle += 1


# ============================================================
# TEST
# ============================================================


@cocotb.test()
async def frontend_with_pc_check(dut):

    tb = ClockedTB(dut)
    await tb.start()
    await tb.reset()

    # start memory AFTER reset
    cocotb.start_soon(mock_instruction_memory(dut))

    checker = PCChecker(dut)

    dut._log.info("Starting PC tracking test")

    # ========================================================
    # WARMUP
    # ========================================================
    for _ in range(3):
        checker.update_model()
        await checker.check()

    # ========================================================
    # TEST 1: FULL STALL
    # ========================================================
    dut._log.info("Testing FULL STALL")
    dut.full_stall.value = 1

    for _ in range(2):
        checker.update_model()
        await checker.check()

    dut.full_stall.value = 0

    # ========================================================
    # TEST 2: LANE 2 STALL (+2 increment)
    # ========================================================
    dut._log.info("Testing LANE 2 STALL")

    dut.stall_lane_2.value = 1
    checker.update_model()
    await checker.check()
    dut.stall_lane_2.value = 0

    # ========================================================
    # TEST 3: REDIRECT
    # ========================================================
    dut._log.info("Testing REDIRECT")

    dut.redirect_valid.value = 1
    dut.redirect_pc.value = 0x0008

    checker.update_model()
    await checker.check()

    dut.redirect_valid.value = 0

    # ========================================================
    # POST-REDIRECT RUN
    # ========================================================
    for _ in range(4):
        checker.update_model()
        await checker.check()

    dut._log.info("Frontend PC tracking test PASSED")
