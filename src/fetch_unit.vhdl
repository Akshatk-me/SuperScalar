library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

entity fetch_unit is
  port (
    clk : in    std_logic;
    rst : in    std_logic;

    -- ==========================================
    -- PIPELINE CONTROL (From Dispatch / ROB)
    -- ==========================================
    redirect_valid : in    std_logic;
    redirect_pc    : in    std_logic_vector(15 downto 0);
    full_stall     : in    std_logic;
    stall_lane_2   : in    std_logic;

    -- ==========================================
    -- INSTRUCTION MEMORY INTERFACE
    -- ==========================================
    imem_pc     : out   std_logic_vector(15 downto 0);
    imem_inst_1 : in    std_logic_vector(15 downto 0);
    imem_inst_2 : in    std_logic_vector(15 downto 0);

    -- ==========================================
    -- BTB UPDATE INTERFACE (From Backend/ROB)
    -- ==========================================
    btb_update_valid  : in    std_logic;
    btb_update_pc     : in    std_logic_vector(15 downto 0);
    btb_update_target : in    std_logic_vector(15 downto 0);
    btb_update_taken  : in    std_logic;

    -- ==========================================
    -- OUTPUTS TO DECODE / DISPATCH
    -- ==========================================
    fetch_pc_1   : out   std_logic_vector(15 downto 0);
    fetch_pc_2   : out   std_logic_vector(15 downto 0);
    fetch_inst_1 : out   std_logic_vector(15 downto 0);
    fetch_inst_2 : out   std_logic_vector(15 downto 0);

    -- Let the Dispatch unit know a branch was predicted so it can
    -- save the snapshot and potentially squash Lane 2!
    fetch_pred_taken_1 : out   std_logic;
    fetch_pred_taken_2 : out   std_logic
  );
end entity fetch_unit;

architecture behavioral of fetch_unit is

  -- Component declaration for the BTB we just wrote
  component branch_target_buffer is
    port (
      clk           : in    std_logic;
      rst           : in    std_logic;
      pc_1          : in    std_logic_vector(15 downto 0);
      pred_taken_1  : out   std_logic;
      pred_target_1 : out   std_logic_vector(15 downto 0);
      pc_2          : in    std_logic_vector(15 downto 0);
      pred_taken_2  : out   std_logic;
      pred_target_2 : out   std_logic_vector(15 downto 0);
      update_valid  : in    std_logic;
      update_pc     : in    std_logic_vector(15 downto 0);
      update_target : in    std_logic_vector(15 downto 0);
      update_taken  : in    std_logic
    );
  end component branch_target_buffer;

  signal pc_reg : std_logic_vector(15 downto 0);

  -- Internal BTB signals
  signal btb_taken_1,  btb_taken_2  : std_logic;
  signal btb_target_1, btb_target_2 : std_logic_vector(15 downto 0);
  signal pc_plus_2                  : std_logic_vector(15 downto 0);

begin

  pc_plus_2 <= std_logic_vector(unsigned(pc_reg) + 2);

  -- Instantiate the Branch Target Buffer
  btb_inst : component branch_target_buffer
    port map (
      clk => clk,
      rst => rst,

      -- Read ports mapped to the current PC and PC+2
      pc_1          => pc_reg,
      pred_taken_1  => btb_taken_1,
      pred_target_1 => btb_target_1,

      pc_2          => pc_plus_2,
      pred_taken_2  => btb_taken_2,
      pred_target_2 => btb_target_2,

      -- Update ports mapped straight to the entity inputs
      update_valid  => btb_update_valid,
      update_pc     => btb_update_pc,
      update_target => btb_update_target,
      update_taken  => btb_update_taken
    );

  -- 1. PC Register State Machine with BTB Integration
  process (clk) is
  begin

    if rising_edge(clk) then
      if (rst = '1') then
        pc_reg <= (others => '0');
      else
        -- Priority 1: Backend flush (Mispredict or Exception)
        if (redirect_valid = '1') then
          pc_reg <= redirect_pc;

        -- Priority 2: Structural hazard on both lanes
        elsif (full_stall = '1') then
          pc_reg <= pc_reg;

        -- Priority 3: Lane 1 is a taken branch!
        elsif (btb_taken_1 = '1') then
          pc_reg <= btb_target_1;

        -- Priority 4: Structural hazard on Lane 2
        elsif (stall_lane_2 = '1') then
          pc_reg <= pc_plus_2;

        -- Priority 5: Lane 2 is a taken branch!
        elsif (btb_taken_2 = '1') then
          pc_reg <= btb_target_2;

        -- Default: Normal 2-way fetch
        else
          pc_reg <= std_logic_vector(unsigned(pc_reg) + 4);
        end if;
      end if;
    end if;

  end process;

  -- 2. Wiring to Asynchronous IMEM
  imem_pc <= pc_reg;

  -- 3. Outputs to Decode/Dispatch
  fetch_pc_1 <= pc_reg;
  fetch_pc_2 <= pc_plus_2;

  fetch_inst_1 <= imem_inst_1;
  fetch_inst_2 <= imem_inst_2;

  fetch_pred_taken_1 <= btb_taken_1;
  fetch_pred_taken_2 <= btb_taken_2;

end architecture behavioral;
