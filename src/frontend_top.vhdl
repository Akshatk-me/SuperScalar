library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

entity frontend_top is
  port (
    clk : in    std_logic;
    rst : in    std_logic;

    -- ==========================================
    -- PIPELINE STALLS & FLUSHES (From Dispatch / BEU)
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
    -- BTB UPDATE INTERFACE (From BEU)
    -- ==========================================
    btb_update_valid  : in    std_logic;
    btb_update_pc     : in    std_logic_vector(15 downto 0);
    btb_update_target : in    std_logic_vector(15 downto 0);
    btb_update_taken  : in    std_logic;

    -- ==========================================
    -- DECODE BUS OUTPUT (To Dispatch_Top)
    -- ==========================================
    -- Lane 1
    dec_valid_1      : out   std_logic;
    dec_dest_valid_1 : out   std_logic;
    dec_dest_reg_1   : out   std_logic_vector(2 downto 0);
    dec_ra_1         : out   std_logic_vector(2 downto 0);
    dec_rb_1         : out   std_logic_vector(2 downto 0);
    dec_opcode_1     : out   std_logic_vector(3 downto 0);
    dec_imm_1        : out   std_logic_vector(7 downto 0);
    pred_taken_1     : out   std_logic;
    fetch_pc_1_out   : out   std_logic_vector(15 downto 0);

    -- Lane 2
    dec_valid_2      : out   std_logic;
    dec_dest_valid_2 : out   std_logic;
    dec_dest_reg_2   : out   std_logic_vector(2 downto 0);
    dec_ra_2         : out   std_logic_vector(2 downto 0);
    dec_rb_2         : out   std_logic_vector(2 downto 0);
    dec_opcode_2     : out   std_logic_vector(3 downto 0);
    dec_imm_2        : out   std_logic_vector(7 downto 0);
    pred_taken_2     : out   std_logic;
    fetch_pc_2_out   : out   std_logic_vector(15 downto 0)
  );
end entity frontend_top;

architecture structural of frontend_top is

  -- ==========================================
  -- COMPONENT DECLARATIONS
  -- ==========================================
  component fetch_unit is
    port (
      clk                : in    std_logic;
      rst                : in    std_logic;
      redirect_valid     : in    std_logic;
      redirect_pc        : in    std_logic_vector(15 downto 0);
      full_stall         : in    std_logic;
      stall_lane_2       : in    std_logic;
      imem_pc            : out   std_logic_vector(15 downto 0);
      imem_inst_1        : in    std_logic_vector(15 downto 0);
      imem_inst_2        : in    std_logic_vector(15 downto 0);
      btb_update_valid   : in    std_logic;
      btb_update_pc      : in    std_logic_vector(15 downto 0);
      btb_update_target  : in    std_logic_vector(15 downto 0);
      btb_update_taken   : in    std_logic;
      fetch_pc_1         : out   std_logic_vector(15 downto 0);
      fetch_pc_2         : out   std_logic_vector(15 downto 0);
      fetch_inst_1       : out   std_logic_vector(15 downto 0);
      fetch_inst_2       : out   std_logic_vector(15 downto 0);
      fetch_pred_taken_1 : out   std_logic;
      fetch_pred_taken_2 : out   std_logic
    );
  end component fetch_unit;

  component instruction_decoder is
    port (
      inst_in : in    std_logic_vector(15 downto 0);
      pc_in   : in    std_logic_vector(15 downto 0);

      valid_out  : out   std_logic;
      dest_valid : out   std_logic;
      dest_reg   : out   std_logic_vector(2 downto 0);
      ra_reg     : out   std_logic_vector(2 downto 0);
      rb_reg     : out   std_logic_vector(2 downto 0);
      opcode     : out   std_logic_vector(3 downto 0);
      imm_out    : out   std_logic_vector(7 downto 0)
    );
  end component instruction_decoder;

  -- ==========================================
  -- INTERNAL SIGNALS (The wiring between Fetch and Decode)
  -- ==========================================
  signal internal_pc_1   : std_logic_vector(15 downto 0);
  signal internal_pc_2   : std_logic_vector(15 downto 0);
  signal internal_inst_1 : std_logic_vector(15 downto 0);
  signal internal_inst_2 : std_logic_vector(15 downto 0);

begin

  -- Output the PC values for the BEU (Branch Execution Unit) to use later
  fetch_pc_1_out <= internal_pc_1;
  fetch_pc_2_out <= internal_pc_2;

  -- ==========================================
  -- INSTANTIATE FETCH UNIT
  -- ==========================================
  fetch_stage : component fetch_unit
    port map (
      clk            => clk,
      rst            => rst,
      redirect_valid => redirect_valid,
      redirect_pc    => redirect_pc,
      full_stall     => full_stall,
      stall_lane_2   => stall_lane_2,

      imem_pc     => imem_pc,
      imem_inst_1 => imem_inst_1,
      imem_inst_2 => imem_inst_2,

      btb_update_valid  => btb_update_valid,
      btb_update_pc     => btb_update_pc,
      btb_update_target => btb_update_target,
      btb_update_taken  => btb_update_taken,

      fetch_pc_1   => internal_pc_1,
      fetch_pc_2   => internal_pc_2,
      fetch_inst_1 => internal_inst_1,
      fetch_inst_2 => internal_inst_2,

      fetch_pred_taken_1 => pred_taken_1,
      fetch_pred_taken_2 => pred_taken_2
    );

  -- ==========================================
  -- INSTANTIATE DECODER 1
  -- ==========================================
  decode_lane_1 : component instruction_decoder
    port map (
      inst_in => internal_inst_1,
      pc_in   => internal_pc_1,

      valid_out  => dec_valid_1,
      dest_valid => dec_dest_valid_1,
      dest_reg   => dec_dest_reg_1,
      ra_reg     => dec_ra_1,
      rb_reg     => dec_rb_1,
      opcode     => dec_opcode_1,
      imm_out    => dec_imm_1
    );

  -- ==========================================
  -- INSTANTIATE DECODER 2
  -- ==========================================
  decode_lane_2 : component instruction_decoder
    port map (
      inst_in => internal_inst_2,
      pc_in   => internal_pc_2,

      valid_out  => dec_valid_2,
      dest_valid => dec_dest_valid_2,
      dest_reg   => dec_dest_reg_2,
      ra_reg     => dec_ra_2,
      rb_reg     => dec_rb_2,
      opcode     => dec_opcode_2,
      imm_out    => dec_imm_2
    );

end architecture structural;
