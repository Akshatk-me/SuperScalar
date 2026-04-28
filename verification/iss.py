# verification/iss.py


class IITB_RISC_ISS:
    def __init__(self):
        # 8 general-purpose registers. R0 is the PC.
        self.regs = [0] * 8

        # Condition codes
        self.flag_c = 0
        self.flag_z = 0

        # Sparse memory model (Dictionary)
        self.memory = {}

    # --- Properties to make code readable ---
    @property
    def pc(self):
        return self.regs[0]

    @pc.setter
    def pc(self, value):
        # Ensure the PC stays within 16-bit bounds
        self.regs[0] = value & 0xFFFF

    # --- Memory Access ---
    def read_mem(self, address):
        return self.memory.get(address, 0x0000)

    # --- The Main Execution Loop ---
    def step(self):
        """Executes a single instruction and updates the architectural state."""

        # 1. FETCH
        # Fetch the 16-bit instruction at the current PC
        instruction = self.read_mem(self.pc)

        # 2. PRE-INCREMENT PC
        # Always fetch two bytes for instruction[cite: 20].
        # We increment before execution so instructions like JLR can save PC+2[cite: 56, 57, 58].
        self.pc += 2

        # 3. DECODE
        opcode = (instruction >> 12) & 0xF

        # 4. EXECUTE
        self._execute_instruction(opcode, instruction)

    def _execute_instruction(self, opcode, instruction):
        """Routes the instruction to the correct logic block based on Opcode."""

        # Example 1: I-Type (e.g., ADI - Add Immediate)
        if opcode == 0b0000:
            ra = (instruction >> 9) & 0x7
            imm6 = (instruction >> 3) & 0x3F
            rb = instruction & 0x7

            # Sign-extend the 6-bit immediate
            if imm6 & 0x20:
                imm6 -= 64

            # Execute the addition
            result = self.regs[ra] + imm6

            # Update Flags
            self.flag_c = 1 if result > 0xFFFF else 0
            self.flag_z = 1 if (result & 0xFFFF) == 0 else 0

            # Write back to Destination Register (RB for ADI)
            # If RB happens to be R0, this naturally causes a branch!
            self.regs[rb] = result & 0xFFFF

        # Example 2: R-Type Math (ADA, ADC, ADZ, etc.)
        elif opcode == 0b0001:
            ra = (instruction >> 9) & 0x7
            rb = (instruction >> 6) & 0x7
            rc = (instruction >> 3) & 0x7
            condition = instruction & 0x3

            # Predicated execution logic goes here based on condition bits
            # ...
