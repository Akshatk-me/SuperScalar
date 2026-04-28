import cocotb
from cocotb.triggers import RisingEdge

# (Assume you import your ISS and Assembler here)
# TODO(akshat): Write the ISS and Assembler @medium file:golden_model.py
from verification.iss import IITB_RISC_ISS


@cocotb.test()
async def test_basic_addition(dut):
    # 1. Initialize the Golden Model
    iss = IITB_RISC_ISS()

    # 2. Setup your hardware clock and reset here...

    MAX_INSTRUCTIONS = 500
    instructions_executed = 0

    # 3. The Execution Loop
    while instructions_executed < MAX_INSTRUCTIONS:
        old_pc = iss.pc

        # Step the Golden Model
        iss.step()

        # Step the Hardware (Wait for one instruction to commit from the ROB)
        # Note: In a superscalar, you might commit 0, 1, or 2 instructions per cycle.
        # You'll need a trigger here that waits for the hardware 'commit_valid' signal.
        await RisingEdge(dut.clk)

        # Check for the clean halt (The Self-Loop Trap)
        if iss.pc == old_pc:
            dut._log.info(
                f"Program completed cleanly after {instructions_executed} instructions."
            )
            break

        instructions_executed += 1

    # 4. The Timeout Failsafe Check
    if instructions_executed >= MAX_INSTRUCTIONS:
        raise TimeoutError("Simulation killed: Reached maximum instruction limit!")

    # 5. Final State Verification
    # Assert that VHDL registers match ISS registers here...
