library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

entity branch_target_buffer is
  port (
    clk : in    std_logic;
    rst : in    std_logic;

    -- ==========================================
    -- READ PORTS (Combinational, for Fetch Unit)
    -- ==========================================
    pc_1          : in    std_logic_vector(15 downto 0);
    pred_taken_1  : out   std_logic;
    pred_target_1 : out   std_logic_vector(15 downto 0);

    pc_2          : in    std_logic_vector(15 downto 0);
    pred_taken_2  : out   std_logic;
    pred_target_2 : out   std_logic_vector(15 downto 0);

    -- ==========================================
    -- UPDATE PORT (Synchronous, from ROB/ALU when branch resolves)
    -- ==========================================
    update_valid  : in    std_logic;
    update_pc     : in    std_logic_vector(15 downto 0); -- The PC of the branch
    update_target : in    std_logic_vector(15 downto 0); -- Where it actually went
    update_taken  : in    std_logic                      -- 1 if it actually branched, 0 if not
  );
end entity branch_target_buffer;

architecture behavioral of branch_target_buffer is

  -- BTB Entry Structure

  type btb_entry is record
    valid     : std_logic;
    tag       : std_logic_vector(9 downto 0); -- PC(15 downto 6)
    target_pc : std_logic_vector(15 downto 0);
    state     : unsigned(1 downto 0);         -- 2-bit saturating counter
  end record btb_entry;

  -- 32-Entry Array (Indexed by PC(5 downto 1))

  type btb_array is array (0 to 31) of btb_entry;

  signal btb : btb_array;

begin

  -- ==========================================
  -- READ PORT 1 (For Instruction 1)
  -- ==========================================
  process (pc_1, btb) is

    variable idx1 : integer;
    variable tag1 : std_logic_vector(9 downto 0);

  begin

    idx1 := to_integer(unsigned(pc_1(5 downto 1)));
    tag1 := pc_1(15 downto 6);

    -- Default to not taken
    pred_taken_1  <= '0';
    pred_target_1 <= (others => '0');

    if (btb(idx1).valid = '1' and btb(idx1).tag = tag1) then
      -- If state is 10 (Weakly Taken) or 11 (Strongly Taken)
      if (btb(idx1).state(1) = '1') then
        pred_taken_1  <= '1';
        pred_target_1 <= btb(idx1).target_pc;
      end if;
    end if;

  end process;

  -- ==========================================
  -- READ PORT 2 (For Instruction 2)
  -- ==========================================
  process (pc_2, btb) is

    variable idx2 : integer;
    variable tag2 : std_logic_vector(9 downto 0);

  begin

    idx2 := to_integer(unsigned(pc_2(5 downto 1)));
    tag2 := pc_2(15 downto 6);

    pred_taken_2  <= '0';
    pred_target_2 <= (others => '0');

    if (btb(idx2).valid = '1' and btb(idx2).tag = tag2) then
      if (btb(idx2).state(1) = '1') then
        pred_taken_2  <= '1';
        pred_target_2 <= btb(idx2).target_pc;
      end if;
    end if;

  end process;

  -- ==========================================
  -- UPDATE PORT (Synchronous Write)
  -- ==========================================
  process (clk) is

    variable up_idx    : integer;
    variable up_tag    : std_logic_vector(9 downto 0);
    variable cur_state : unsigned(1 downto 0);

  begin

    if rising_edge(clk) then
      if (rst = '1') then
        -- Clear the BTB on reset
        for i in 0 to 31 loop

          btb(i).valid <= '0';
          btb(i).state <= "00";

        end loop;

      elsif (update_valid = '1') then
        up_idx := to_integer(unsigned(update_pc(5 downto 1)));
        up_tag := update_pc(15 downto 6);

        -- If this is a new branch we haven't seen before
        if (btb(up_idx).valid = '0' or btb(up_idx).tag /= up_tag) then
          btb(up_idx).valid     <= '1';
          btb(up_idx).tag       <= up_tag;
          btb(up_idx).target_pc <= update_target;

          if (update_taken = '1') then
            btb(up_idx).state <= "10";                                 -- Init to Weakly Taken
          else
            btb(up_idx).state <= "01";                                 -- Init to Weakly Not Taken
          end if;

        -- If we are updating an existing branch
        else
          cur_state := btb(up_idx).state;

          if (update_taken = '1') then
            -- Saturating Add
            if (cur_state /= "11") then
              btb(up_idx).state <= cur_state + 1;
            end if;
          else
            -- Saturating Subtract
            if (cur_state /= "00") then
              btb(up_idx).state <= cur_state - 1;
            end if;
          end if;

          -- Always update the target just in case it's an indirect jump that changed
          btb(up_idx).target_pc <= update_target;
        end if;
      end if;
    end if;

  end process;

end architecture behavioral;
