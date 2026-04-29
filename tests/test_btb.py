import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

# ============================================================
# CONFIG
# ============================================================

BTB_SIZE = 32


def extract_index(pc):
    return (pc >> 1) & 0x1F


def extract_tag(pc):
    return (pc >> 6) & 0x3FF


def saturating_update(state, taken):
    return min(3, state + 1) if taken else max(0, state - 1)


def should_predict_taken(state):
    return state >= 2


# ============================================================
# GOLDEN MODEL
# ============================================================


class BTBGoldenModel:
    def __init__(self):
        self.entries = [
            {"valid": False, "tag": 0, "target": 0, "state": 0} for _ in range(BTB_SIZE)
        ]

    def update(self, pc, target, taken):
        idx = extract_index(pc)
        tag = extract_tag(pc)

        entry = self.entries[idx]

        if not entry["valid"] or entry["tag"] != tag:
            entry["valid"] = True
            entry["tag"] = tag
            entry["target"] = target
            entry["state"] = 2 if taken else 1
        else:
            entry["target"] = target
            entry["state"] = saturating_update(entry["state"], taken)

    def predict(self, pc):
        idx = extract_index(pc)
        tag = extract_tag(pc)

        entry = self.entries[idx]

        if (
            entry["valid"]
            and entry["tag"] == tag
            and should_predict_taken(entry["state"])
        ):
            return True, entry["target"]

        return False, 0


# ============================================================
# CLOCKED TB WRAPPER
# ============================================================


class ClockedTB:
    def __init__(self, dut):
        self.dut = dut

    async def start(self):
        clock = Clock(self.dut.clk, 10, unit="ns")
        cocotb.start_soon(clock.start())

    async def reset(self):
        self.dut.rst.value = 1
        self.clear_inputs()

        for _ in range(3):
            await self.tick()

        self.dut.rst.value = 0
        await self.tick()

    async def tick(self):
        await RisingEdge(self.dut.clk)

    def clear_inputs(self):
        self.dut.update_valid.value = 0
        self.dut.pc_1.value = 0
        self.dut.pc_2.value = 0


# ============================================================
# BTB INTERFACE (TIMING-CORRECT)
# ============================================================


class BTBInterface:
    def __init__(self, tb: ClockedTB):
        self.tb = tb
        self.dut = tb.dut

    async def update(self, pc, target, taken):
        self.dut.update_valid.value = 1
        self.dut.update_pc.value = pc
        self.dut.update_target.value = target
        self.dut.update_taken.value = int(taken)

        await self.tb.tick()

        self.dut.update_valid.value = 0

    async def query(self, pc1, pc2):
        self.dut.pc_1.value = pc1
        self.dut.pc_2.value = pc2

        # allow combinational settle within same cycle
        await Timer(1, unit="ns")

        pred1 = (
            int(self.dut.pred_taken_1.value),
            int(self.dut.pred_target_1.value),
        )
        pred2 = (
            int(self.dut.pred_taken_2.value),
            int(self.dut.pred_target_2.value),
        )

        return pred1, pred2


# ============================================================
# TESTS
# ============================================================


@cocotb.test()
async def test_btb_directed(dut):
    tb = ClockedTB(dut)
    await tb.start()
    await tb.reset()

    btb = BTBInterface(tb)
    model = BTBGoldenModel()

    pc = 0x1000
    target = 0x2000

    await btb.update(pc, target, True)
    model.update(pc, target, True)

    pred1, _ = await btb.query(pc, 0)
    gold = model.predict(pc)

    assert pred1[0] == gold[0]
    assert pred1[1] == gold[1]

    await tb.tick()

    dut._log.info("Directed test passed")


@cocotb.test()
async def test_btb_random(dut):
    tb = ClockedTB(dut)
    await tb.start()
    await tb.reset()

    btb = BTBInterface(tb)
    model = BTBGoldenModel()

    for cycle in range(500):

        if random.random() < 0.4:
            pc = random.randint(0, 0xFFFF) & 0xFFFE
            target = random.randint(0, 0xFFFF) & 0xFFFE
            taken = random.choice([True, False])

            await btb.update(pc, target, taken)
            model.update(pc, target, taken)

        else:
            pc1 = random.randint(0, 0xFFFF) & 0xFFFE
            pc2 = random.randint(0, 0xFFFF) & 0xFFFE

            pred1, pred2 = await btb.query(pc1, pc2)
            gold1 = model.predict(pc1)
            gold2 = model.predict(pc2)

            assert pred1[0] == gold1[0], f"Cycle {cycle}: PC1 taken mismatch"
            if gold1[0]:
                assert pred1[1] == gold1[1], f"Cycle {cycle}: PC1 target mismatch"

            assert pred2[0] == gold2[0], f"Cycle {cycle}: PC2 taken mismatch"
            if gold2[0]:
                assert pred2[1] == gold2[1], f"Cycle {cycle}: PC2 target mismatch"

            await tb.tick()

        if cycle % 100 == 0:
            dut._log.info(f"Cycle {cycle} passed")

    dut._log.info("Random test passed")


@cocotb.test()
async def test_btb_aliasing(dut):
    tb = ClockedTB(dut)
    await tb.start()
    await tb.reset()

    btb = BTBInterface(tb)
    model = BTBGoldenModel()

    # same index, different tags
    pc1 = 0x0002
    pc2 = 0x0042

    await btb.update(pc1, 0x1111, True)
    model.update(pc1, 0x1111, True)

    await btb.update(pc2, 0x2222, True)
    model.update(pc2, 0x2222, True)

    pred1, pred2 = await btb.query(pc1, pc2)

    gold1 = model.predict(pc1)
    gold2 = model.predict(pc2)

    assert pred1 == gold1
    assert pred2 == gold2

    await tb.tick()

    dut._log.info("Aliasing test passed")
