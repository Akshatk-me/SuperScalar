library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

entity retirement_rat is
  port (
    clk : in    std_logic;
    rst : in    std_logic;

    -- ==========================================
    -- COMMIT INTERFACE (From the ROB)
    -- ==========================================
    commit_valid_1 : in    std_logic;
    commit_we_1    : in    std_logic;
    commit_arch_1  : in    std_logic_vector(3 downto 0); -- 0-7: R0-R7, 8: C, 9: Z
    commit_phys_1  : in    std_logic_vector(4 downto 0);

    commit_valid_2 : in    std_logic;
    commit_we_2    : in    std_logic;
    commit_arch_2  : in    std_logic_vector(3 downto 0);
    commit_phys_2  : in    std_logic_vector(4 downto 0);

    -- ==========================================
    -- FREE LIST INTERFACE (Reclaiming dead registers)
    -- ==========================================
    free_en_1   : out   std_logic;
    free_phys_1 : out   std_logic_vector(4 downto 0);

    free_en_2   : out   std_logic;
    free_phys_2 : out   std_logic_vector(4 downto 0);

    -- ==========================================
    -- BRANCH RECOVERY (To the Front-End RAT)
    -- ==========================================
    -- On a mispredict, we flatten the entire RRAT array into a 50-bit vector
    -- (10 registers * 5 bits) and copy it back to the Front-End RAT.
    rrat_snapshot : out   std_logic_vector(49 downto 0)
  );
end entity retirement_rat;

architecture behavioral of retirement_rat is

  -- 10 Architectural Registers: R0-R7 (0-7), Carry (8), Zero (9)

  type rrat_array is array (0 to 9) of std_logic_vector(4 downto 0);

  signal rrat : rrat_array;

begin

  -- Flatten the RRAT array to send to the Front-End RAT for recovery
  process (rrat) is
  begin

    for i in 0 to 9 loop

      rrat_snapshot((i * 5) + 4 downto (i * 5)) <= rrat(i);

    end loop;

  end process;

  -- ==========================================
  -- COMBINATIONAL LOGIC: Feeding the Free List
  -- ==========================================
  process (commit_valid_1, commit_we_1, commit_arch_1, commit_phys_1,
           commit_valid_2, commit_we_2, commit_arch_2, commit_phys_2, rrat) is
  begin

    -- Default assignments
    free_en_1   <= '0';
    free_phys_1 <= (others => '0');
    free_en_2   <= '0';
    free_phys_2 <= (others => '0');

    -- Instruction 1 Committing
    if (commit_valid_1 = '1' and commit_we_1 = '1') then
      free_en_1 <= '1';
      -- The old physical register is now dead, send it to the Free List
      free_phys_1 <= rrat(to_integer(unsigned(commit_arch_1)));
    end if;

    -- Instruction 2 Committing
    if (commit_valid_2 = '1' and commit_we_2 = '1') then
      free_en_2 <= '1';

      -- WAW HAZARD CHECK: What if Inst 1 and Inst 2 both wrote to R1 in the same cycle?
      if (commit_valid_1 = '1' and commit_we_1 = '1' and commit_arch_1 = commit_arch_2) then
        -- Inst 2 overwrites Inst 1 immediately.
        -- Therefore, the physical register Inst 1 *just* tried to map is already dead!
        free_phys_2 <= commit_phys_1;
      else
        -- Normal case: Free whatever was in the RRAT previously
        free_phys_2 <= rrat(to_integer(unsigned(commit_arch_2)));
      end if;
    end if;

  end process;

  -- ==========================================
  -- SYNCHRONOUS LOGIC: Updating the RRAT State
  -- ==========================================
  process (clk) is
  begin

    if rising_edge(clk) then
      if (rst = '1') then
        -- INITIAL STATE: Same as Front-End RAT
        -- R0->P0, R1->P1 ... C->P8, Z->P9
        for i in 0 to 9 loop

          rrat(i) <= std_logic_vector(to_unsigned(i, 5));

        end loop;

      else
        -- Sequential updates (Order matters!)
        if (commit_valid_1 = '1' and commit_we_1 = '1') then
          rrat(to_integer(unsigned(commit_arch_1))) <= commit_phys_1;
        end if;

        -- If both write to the same arch register, Inst 2 executes last and wins.
        if (commit_valid_2 = '1' and commit_we_2 = '1') then
          rrat(to_integer(unsigned(commit_arch_2))) <= commit_phys_2;
        end if;
      end if;
    end if;

  end process;

end architecture behavioral;
