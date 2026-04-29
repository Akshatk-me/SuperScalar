--------------------------------------------------------------------------------
-- FRONT END RAT (Register Alias Table)
--
-- Purpose: Maps architectural registers (R0-R7, C, Z) to physical registers
--
-- Architecture:
--   - 10 entries: indices 0-7 for R0-R7, 8 for C flag, 9 for Z flag
--   - 2-way superscalar rename: handles 2 instructions per cycle
--   - Forwarding: Inst2 can see Inst1's writes in same cycle
--   - Write priority: Inst2 (younger) overrides Inst1 on conflicts
--   - Recovery: 50-bit RRAT state restores all mappings in 1 cycle
--
-- Ports:
--   - alloc_phys_1/2: Physical registers allocated to each instruction
--   - we_reg_1/2, we_c_1/2, we_z_1/2: Write enables for registers/flags
--   - recover_en + rrat_state: Branch misprediction recovery
--
-- Reset: Identity mapping (R0→P0, R1→P1, ..., C→P8, Z→P9)
--------------------------------------------------------------------------------

library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

entity front_end_rat is
  port (
    clk : in    std_logic;
    rst : in    std_logic;

    -- ==========================================
    -- BRANCH MISPREDICTION RECOVERY
    -- ==========================================
    recover_en : in    std_logic;
    -- Flattened 50-bit vector from the RRAT (10 entries * 5 bits)
    -- Entry 0 is bits 4:0, Entry 1 is bits 9:5, etc.
    rrat_state : in    std_logic_vector(49 downto 0);

    -- ==========================================
    -- RENAME ALLOCATIONS (From Free List)
    -- ==========================================
    alloc_phys_1 : in    std_logic_vector(4 downto 0); -- P_reg assigned to Inst 1
    alloc_phys_2 : in    std_logic_vector(4 downto 0); -- P_reg assigned to Inst 2

    -- ==========================================
    -- INSTRUCTION 1 (Older) RENAME PORTS
    -- ==========================================
    -- Read Addresses (Architectural)
    rs1_addr_1 : in    std_logic_vector(2 downto 0); -- R0 to R7
    rs2_addr_1 : in    std_logic_vector(2 downto 0);

    -- Outputs (Physical Pointers)
    phys_rs1_1 : out   std_logic_vector(4 downto 0);
    phys_rs2_1 : out   std_logic_vector(4 downto 0);
    phys_c_1   : out   std_logic_vector(4 downto 0);
    phys_z_1   : out   std_logic_vector(4 downto 0);

    -- Write Enablers and Destination
    we_reg_1    : in    std_logic;                    -- 1 if Inst 1 writes to a reg
    dest_addr_1 : in    std_logic_vector(2 downto 0); -- Dest R0-R7
    we_c_1      : in    std_logic;                    -- 1 if Inst 1 updates C flag
    we_z_1      : in    std_logic;                    -- 1 if Inst 1 updates Z flag

    -- ==========================================
    -- INSTRUCTION 2 (Younger) RENAME PORTS
    -- ==========================================
    -- Read Addresses (Architectural)
    rs1_addr_2 : in    std_logic_vector(2 downto 0);
    rs2_addr_2 : in    std_logic_vector(2 downto 0);

    -- Outputs (Physical Pointers)
    phys_rs1_2 : out   std_logic_vector(4 downto 0);
    phys_rs2_2 : out   std_logic_vector(4 downto 0);
    phys_c_2   : out   std_logic_vector(4 downto 0);
    phys_z_2   : out   std_logic_vector(4 downto 0);

    -- Write Enablers and Destination
    we_reg_2    : in    std_logic;
    dest_addr_2 : in    std_logic_vector(2 downto 0);
    we_c_2      : in    std_logic;
    we_z_2      : in    std_logic
  );
end entity front_end_rat;

architecture behavioral of front_end_rat is

  -- Array of 10 entries (0-7 for R0-R7, 8 for C, 9 for Z)

  type rat_array_type is array (0 to 9) of std_logic_vector(4 downto 0);

  signal rat_reg : rat_array_type;

begin

  -- ==========================================
  -- ASYNCHRONOUS READ LOGIC & FORWARDING
  -- ==========================================

  -- Instruction 1 is the oldest in the pair. It just reads from the RAT directly.
  phys_rs1_1 <= rat_reg(to_integer(unsigned(rs1_addr_1)));
  phys_rs2_1 <= rat_reg(to_integer(unsigned(rs2_addr_1)));
  phys_c_1   <= rat_reg(8);
  phys_z_1   <= rat_reg(9);

  -- Instruction 2 is younger. It MUST check if Inst 1 is writing to the
  -- register it needs right now. If so, forward Inst 1's physical register.

  phys_rs1_2 <= alloc_phys_1 when (we_reg_1 = '1' and dest_addr_1 = rs1_addr_2) else
                rat_reg(to_integer(unsigned(rs1_addr_2)));

  phys_rs2_2 <= alloc_phys_1 when (we_reg_1 = '1' and dest_addr_1 = rs2_addr_2) else
                rat_reg(to_integer(unsigned(rs2_addr_2)));

  phys_c_2 <= alloc_phys_1 when (we_c_1 = '1') else
              rat_reg(8);

  phys_z_2 <= alloc_phys_1 when (we_z_1 = '1') else
              rat_reg(9);

  -- ==========================================
  -- SYNCHRONOUS WRITE LOGIC & PRIORITIZATION
  -- ==========================================
  process (clk) is
  begin

    if rising_edge(clk) then
      if (rst = '1') then
        -- Reset maps R0->P0, R1->P1, etc.
        for i in 0 to 9 loop

          rat_reg(i) <= std_logic_vector(to_unsigned(i, 5));

        end loop;

      elsif (recover_en = '1') then
        -- Branch Misprediction! Instantly load safe state from RRAT.
        for i in 0 to 9 loop

          rat_reg(i) <= rrat_state((i * 5) + 4 downto i * 5);

        end loop;

      else
        -- Normal Superscalar Updates with Prioritization
        -- We loop through R0 to R7
        for i in 0 to 7 loop

          -- Instruction 2 has priority over Instruction 1 because it is younger!
          if (we_reg_2 = '1' and to_integer(unsigned(dest_addr_2)) = i) then
            rat_reg(i) <= alloc_phys_2;
          elsif (we_reg_1 = '1' and to_integer(unsigned(dest_addr_1)) = i) then
            rat_reg(i) <= alloc_phys_1;
          end if;

        end loop;

        -- Update C Flag Mapping (Index 8)
        if (we_c_2 = '1') then
          rat_reg(8) <= alloc_phys_2;
        elsif (we_c_1 = '1') then
          rat_reg(8) <= alloc_phys_1;
        end if;

        -- Update Z Flag Mapping (Index 9)
        if (we_z_2 = '1') then
          rat_reg(9) <= alloc_phys_2;
        elsif (we_z_1 = '1') then
          rat_reg(9) <= alloc_phys_1;
        end if;
      end if;
    end if;

  end process;

end architecture behavioral;
