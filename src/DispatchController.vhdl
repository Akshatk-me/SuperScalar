library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

entity dispatch_controller is
  port (
    clk : in    std_logic;
    rst : in    std_logic;

    -- ==========================================
    -- INPUTS FROM DECODER (Lane 1 & 2)
    -- ==========================================
    dec_valid_1      : in    std_logic;
    dec_dest_valid_1 : in    std_logic;
    dec_dest_reg_1   : in    std_logic_vector(2 downto 0);
    dec_ra_1         : in    std_logic_vector(2 downto 0);
    dec_rb_1         : in    std_logic_vector(2 downto 0);

    dec_valid_2      : in    std_logic;
    dec_dest_valid_2 : in    std_logic;
    dec_dest_reg_2   : in    std_logic_vector(2 downto 0);
    dec_ra_2         : in    std_logic_vector(2 downto 0);
    dec_rb_2         : in    std_logic_vector(2 downto 0);

    -- ==========================================
    -- BACKEND RESOURCE INPUTS
    -- ==========================================
    free_regs_avail : in    unsigned(1 downto 0);         -- 0, 1, or 2+
    free_reg_1      : in    std_logic_vector(5 downto 0); -- Tag from Free List
    free_reg_2      : in    std_logic_vector(5 downto 0); -- Tag from Free List

    rob_spaces_avail : in    unsigned(1 downto 0); -- 0, 1, or 2+ spaces left
    rs_full          : in    std_logic;            -- Are Reservation Stations full?

    -- RAT Read Ports (Current Mapping)
    rat_p_ra_2 : in    std_logic_vector(5 downto 0);
    rat_p_rb_2 : in    std_logic_vector(5 downto 0);

    -- ==========================================
    -- OUTPUTS TO FETCH UNIT
    -- ==========================================
    stall_lane_2 : out   std_logic;
    full_stall   : out   std_logic;

    -- ==========================================
    -- OUTPUTS TO BACKEND (Free List, RAT, RS, ROB)
    -- ==========================================
    free_list_pop_1 : out   std_logic;
    free_list_pop_2 : out   std_logic;

    dispatch_valid_1 : out   std_logic;
    dispatch_valid_2 : out   std_logic;

    -- The dynamically routed physical tags for Lane 2
    l2_phys_tag_ra : out   std_logic_vector(5 downto 0);
    l2_phys_tag_rb : out   std_logic_vector(5 downto 0)
  );
end entity dispatch_controller;

architecture behavioral of dispatch_controller is

  -- Hazard calculations
  signal needs_preg_1,   needs_preg_2 : std_logic;
  signal total_pregs_needed           : unsigned(1 downto 0);

  -- Intra-cycle bypass flags
  signal match_l2_ra_to_l1_dest : std_logic;
  signal match_l2_rb_to_l1_dest : std_logic;

  -- Internal dispatch decisions
  signal can_dispatch_1, can_dispatch_2 : std_logic;

begin

  -- ==========================================
  -- 1. RESOURCE CALCULATION
  -- ==========================================
  needs_preg_1 <= dec_valid_1 and dec_dest_valid_1;
  needs_preg_2 <= dec_valid_2 and dec_dest_valid_2;

  process (needs_preg_1, needs_preg_2) is
  begin

    if (needs_preg_1 = '1' and needs_preg_2 = '1') then
      total_pregs_needed <= "10";                         -- Need 2
    elsif (needs_preg_1 = '1' or needs_preg_2 = '1') then
      total_pregs_needed <= "01";                         -- Need 1
    else
      total_pregs_needed <= "00";                         -- Need 0
    end if;

  end process;

  -- ==========================================
  -- 2. STRUCTURAL HAZARD & PRIORITY LOGIC
  -- ==========================================
  process (dec_valid_1, dec_valid_2, free_regs_avail, total_pregs_needed, rob_spaces_avail, rs_full, needs_preg_1, needs_preg_2) is
  begin

    -- Defaults
    can_dispatch_1 <= '0';
    can_dispatch_2 <= '0';
    stall_lane_2   <= '0';
    full_stall     <= '0';

    if (rs_full = '1' or rob_spaces_avail = "00") then
      -- Absolute gridlock in the backend.
      full_stall <= '1';
    elsif (dec_valid_1 = '1') then
      -- Lane 1 has a valid instruction. Let's see if it can dispatch.
      if (needs_preg_1 = '0' or (needs_preg_1 = '1' and free_regs_avail >= "01")) then
        can_dispatch_1 <= '1';

        -- Now check Lane 2
        if (dec_valid_2 = '1') then
          if (rob_spaces_avail >= "10" and (total_pregs_needed <= free_regs_avail)) then
            -- Plenty of space! Dispatch both!
            can_dispatch_2 <= '1';
          else
            -- We dispatched Lane 1, but lacked resources for Lane 2.
            stall_lane_2 <= '1';
          end if;
        end if;
      else
        -- Even Lane 1 couldn't get a register. Total stall.
        full_stall <= '1';
      end if;
    end if;

  end process;

  -- Map internal decisions to outputs
  dispatch_valid_1 <= can_dispatch_1;
  dispatch_valid_2 <= can_dispatch_2;

  -- Only pop the free list if the instruction is actively dispatching AND needs a register
  free_list_pop_1 <= can_dispatch_1 and needs_preg_1;
  free_list_pop_2 <= can_dispatch_2 and needs_preg_2;

  -- ==========================================
  -- 3. INTRA-CYCLE DATA HAZARD BYPASS
  -- ==========================================
  -- Does Lane 2 read what Lane 1 is writing?
  match_l2_ra_to_l1_dest <= '1' when (dec_ra_2 = dec_dest_reg_1) and (can_dispatch_1 = '1' and dec_dest_valid_1 = '1') else
                            '0';
  match_l2_rb_to_l1_dest <= '1' when (dec_rb_2 = dec_dest_reg_1) and (can_dispatch_1 = '1' and dec_dest_valid_1 = '1') else
                            '0';

  -- Bypass Muxes for Lane 2 physical routing
  l2_phys_tag_ra <= free_reg_1 when match_l2_ra_to_l1_dest = '1' else
                    rat_p_ra_2;
  l2_phys_tag_rb <= free_reg_1 when match_l2_rb_to_l1_dest = '1' else
                    rat_p_rb_2;

end architecture behavioral;
