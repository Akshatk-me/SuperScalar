library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

entity branch_execution_unit is
  port (
    clk : in    std_logic;
    rst : in    std_logic;

    -- Inputs from ALU (Execution complete)
    alu_valid        : in    std_logic;
    alu_is_branch    : in    std_logic;                     -- '1' if arch_dest == R0
    alu_result       : in    std_logic_vector(15 downto 0); -- The actual calculated PC
    alu_predicted_pc : in    std_logic_vector(15 downto 0); -- What the BTB predicted
    alu_pc           : in    std_logic_vector(15 downto 0); -- The PC of the branch itself

    -- Outputs to Fetch Unit & ROB & Free List
    branch_flush   : out   std_logic;
    correct_target : out   std_logic_vector(15 downto 0);

    -- Outputs to BTB for training
    btb_update_valid  : out   std_logic;
    btb_update_pc     : out   std_logic_vector(15 downto 0);
    btb_update_target : out   std_logic_vector(15 downto 0);
    btb_update_taken  : out   std_logic
  );
end entity branch_execution_unit;

architecture behavioral of branch_execution_unit is

begin

  process (clk) is
  begin

    if rising_edge(clk) then
      if (rst = '1') then
        branch_flush     <= '0';
        btb_update_valid <= '0';
      else
        -- Default states
        branch_flush     <= '0';
        btb_update_valid <= '0';

        if (alu_valid = '1' and alu_is_branch = '1') then
          -- Train the BTB regardless of prediction success
          btb_update_valid  <= '1';
          btb_update_pc     <= alu_pc;
          btb_update_target <= alu_result;

          -- If the PC didn't advance to the next sequential instruction, it was "taken"
          if (alu_result /= std_logic_vector(unsigned(alu_pc) + 2)) then
            btb_update_taken <= '1';
          else
            btb_update_taken <= '0';
          end if;

          -- MISPREDICTION CHECK: Did the ALU calculate a different PC than we fetched?
          if (alu_result /= alu_predicted_pc) then
            branch_flush   <= '1';
            correct_target <= alu_result;
          end if;
        end if;
      end if;
    end if;

  end process;

end architecture behavioral;
