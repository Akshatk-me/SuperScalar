library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

entity dispatch_top is
  port (
    clk : in    std_logic;
    rst : in    std_logic;

    -- ==========================================
    -- INPUTS FROM FRONT-END (Decode Bus)
    -- ==========================================
    dec_valid_1      : in    std_logic;
    dec_dest_valid_1 : in    std_logic;
    dec_dest_reg_1   : in    std_logic_vector(2 downto 0);
    dec_ra_1         : in    std_logic_vector(2 downto 0);
    dec_rb_1         : in    std_logic_vector(2 downto 0);
    dec_opcode_1     : in    std_logic_vector(3 downto 0);
    dec_imm_1        : in    std_logic_vector(7 downto 0);
    dec_we_c_1       : in    std_logic;
    dec_we_z_1       : in    std_logic;

    dec_valid_2      : in    std_logic;
    dec_dest_valid_2 : in    std_logic;
    dec_dest_reg_2   : in    std_logic_vector(2 downto 0);
    dec_ra_2         : in    std_logic_vector(2 downto 0);
    dec_rb_2         : in    std_logic_vector(2 downto 0);
    dec_opcode_2     : in    std_logic_vector(3 downto 0);
    dec_imm_2        : in    std_logic_vector(7 downto 0);
    dec_we_c_2       : in    std_logic;
    dec_we_z_2       : in    std_logic;

    -- ==========================================
    -- BACKEND STALL SIGNALS
    -- ==========================================
    rob_spaces_avail : in    unsigned(1 downto 0);
    rs_full          : in    std_logic;

    -- ==========================================
    -- RECOVERY SIGNALS
    -- ==========================================
    branch_flush : in    std_logic;
    recover_ptr  : in    std_logic_vector(4 downto 0);
    rrat_state   : in    std_logic_vector(49 downto 0);

    -- ==========================================
    -- RETIREMENT SIGNALS
    -- ==========================================
    free_en_1   : in    std_logic;
    free_phys_1 : in    std_logic_vector(4 downto 0);
    free_en_2   : in    std_logic;
    free_phys_2 : in    std_logic_vector(4 downto 0);

    -- ==========================================
    -- OUTPUTS TO FRONT-END
    -- ==========================================
    stall_lane_2 : out   std_logic;
    full_stall   : out   std_logic;

    -- ==========================================
    -- OUTPUTS TO EXECUTION
    -- ==========================================
    disp_en_1        : out   std_logic;
    disp_opcode_1    : out   std_logic_vector(3 downto 0);
    disp_phys_dest_1 : out   std_logic_vector(4 downto 0);
    disp_phys_ra_1   : out   std_logic_vector(4 downto 0);
    disp_phys_rb_1   : out   std_logic_vector(4 downto 0);
    disp_imm_1       : out   std_logic_vector(7 downto 0);

    disp_en_2        : out   std_logic;
    disp_opcode_2    : out   std_logic_vector(3 downto 0);
    disp_phys_dest_2 : out   std_logic_vector(4 downto 0);
    disp_phys_ra_2   : out   std_logic_vector(4 downto 0);
    disp_phys_rb_2   : out   std_logic_vector(4 downto 0);
    disp_imm_2       : out   std_logic_vector(7 downto 0)
  );
end entity dispatch_top;

architecture structural of dispatch_top is

  -- ==========================================
  -- COMPONENTS
  -- ==========================================
  component dispatch_controller is
    port (
      clk              : in    std_logic;
      rst              : in    std_logic;
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

      free_regs_avail  : in    unsigned(1 downto 0);
      free_reg_1       : in    std_logic_vector(4 downto 0);
      free_reg_2       : in    std_logic_vector(4 downto 0);
      rob_spaces_avail : in    unsigned(1 downto 0);
      rs_full          : in    std_logic;
      rat_p_ra_2       : in    std_logic_vector(4 downto 0);
      rat_p_rb_2       : in    std_logic_vector(4 downto 0);
      stall_lane_2     : out   std_logic;
      full_stall       : out   std_logic;
      free_list_pop_1  : out   std_logic;
      free_list_pop_2  : out   std_logic;
      dispatch_valid_1 : out   std_logic;
      dispatch_valid_2 : out   std_logic;
      l2_phys_tag_ra   : out   std_logic_vector(4 downto 0);
      l2_phys_tag_rb   : out   std_logic_vector(4 downto 0)
    );
  end component dispatch_controller;

  component free_list is
    port (
      clk          : in    std_logic;
      rst          : in    std_logic;
      req_1        : in    std_logic;
      req_2        : in    std_logic;
      alloc_phys_1 : out   std_logic_vector(4 downto 0);
      alloc_phys_2 : out   std_logic_vector(4 downto 0);
      empty        : out   std_logic;
      free_en_1    : in    std_logic;
      free_phys_1  : in    std_logic_vector(4 downto 0);
      free_en_2    : in    std_logic;
      free_phys_2  : in    std_logic_vector(4 downto 0);
      recover_en   : in    std_logic;
      recover_ptr  : in    std_logic_vector(4 downto 0)
    );
  end component free_list;

  component front_end_rat is
    port (
      clk          : in    std_logic;
      rst          : in    std_logic;
      recover_en   : in    std_logic;
      rrat_state   : in    std_logic_vector(49 downto 0);
      alloc_phys_1 : in    std_logic_vector(4 downto 0);
      alloc_phys_2 : in    std_logic_vector(4 downto 0);
      rs1_addr_1   : in    std_logic_vector(2 downto 0);
      rs2_addr_1   : in    std_logic_vector(2 downto 0);
      phys_rs1_1   : out   std_logic_vector(4 downto 0);
      phys_rs2_1   : out   std_logic_vector(4 downto 0);
      we_reg_1     : in    std_logic;
      dest_addr_1  : in    std_logic_vector(2 downto 0);
      rs1_addr_2   : in    std_logic_vector(2 downto 0);
      rs2_addr_2   : in    std_logic_vector(2 downto 0);
      phys_rs1_2   : out   std_logic_vector(4 downto 0);
      phys_rs2_2   : out   std_logic_vector(4 downto 0);
      we_reg_2     : in    std_logic;
      dest_addr_2  : in    std_logic_vector(2 downto 0)
    );
  end component front_end_rat;

  -- ==========================================
  -- INTERNAL SIGNALS
  -- ==========================================
  signal fl_alloc_1,      fl_alloc_2 : std_logic_vector(4 downto 0);
  signal fl_pop_1,        fl_pop_2   : std_logic;
  signal fl_empty                    : std_logic;
  signal fl_regs_avail               : unsigned(1 downto 0);

  signal rat_p_rs1_1,     rat_p_rs2_1 : std_logic_vector(4 downto 0);
  signal rat_p_rs1_2,     rat_p_rs2_2 : std_logic_vector(4 downto 0);

  signal bypass_ra_2,     bypass_rb_2     : std_logic_vector(4 downto 0);
  signal internal_disp_1, internal_disp_2 : std_logic;

begin

  -- ==========================================
  -- FREE LIST
  -- ==========================================
  fl_regs_avail <= "00" when fl_empty = '1' else
                   "10";

  u_freelist : component free_list
    port map (
      clk          => clk,
      rst          => rst,
      req_1        => fl_pop_1,
      req_2        => fl_pop_2,
      alloc_phys_1 => fl_alloc_1,
      alloc_phys_2 => fl_alloc_2,
      empty        => fl_empty,
      free_en_1    => free_en_1,
      free_phys_1  => free_phys_1,
      free_en_2    => free_en_2,
      free_phys_2  => free_phys_2,
      recover_en   => branch_flush,
      recover_ptr  => recover_ptr
    );

  -- ==========================================
  -- FRONT-END RAT
  -- ==========================================
  u_rat : component front_end_rat
    port map (
      clk        => clk,
      rst        => rst,
      recover_en => branch_flush,
      rrat_state => rrat_state,

      alloc_phys_1 => fl_alloc_1,
      alloc_phys_2 => fl_alloc_2,

      rs1_addr_1  => dec_ra_1,
      rs2_addr_1  => dec_rb_1,
      phys_rs1_1  => rat_p_rs1_1,
      phys_rs2_1  => rat_p_rs2_1,
      we_reg_1    => dec_dest_valid_1,
      dest_addr_1 => dec_dest_reg_1,

      rs1_addr_2  => dec_ra_2,
      rs2_addr_2  => dec_rb_2,
      phys_rs1_2  => rat_p_rs1_2,
      phys_rs2_2  => rat_p_rs2_2,
      we_reg_2    => dec_dest_valid_2,
      dest_addr_2 => dec_dest_reg_2
    );

  -- ==========================================
  -- DISPATCH CONTROLLER
  -- ==========================================
  u_ctrl : component dispatch_controller
    port map (
      clk => clk,
      rst => rst,

      dec_valid_1      => dec_valid_1,
      dec_dest_valid_1 => dec_dest_valid_1,
      dec_dest_reg_1   => dec_dest_reg_1,
      dec_ra_1         => dec_ra_1,
      dec_rb_1         => dec_rb_1,

      dec_valid_2      => dec_valid_2,
      dec_dest_valid_2 => dec_dest_valid_2,
      dec_dest_reg_2   => dec_dest_reg_2,
      dec_ra_2         => dec_ra_2,
      dec_rb_2         => dec_rb_2,

      free_regs_avail => fl_regs_avail,
      free_reg_1      => fl_alloc_1,
      free_reg_2      => fl_alloc_2,

      rob_spaces_avail => rob_spaces_avail,
      rs_full          => rs_full,

      rat_p_ra_2 => rat_p_rs1_2,
      rat_p_rb_2 => rat_p_rs2_2,

      stall_lane_2 => stall_lane_2,
      full_stall   => full_stall,

      free_list_pop_1 => fl_pop_1,
      free_list_pop_2 => fl_pop_2,

      dispatch_valid_1 => internal_disp_1,
      dispatch_valid_2 => internal_disp_2,

      l2_phys_tag_ra => bypass_ra_2,
      l2_phys_tag_rb => bypass_rb_2
    );

  -- ==========================================
  -- OUTPUTS
  -- ==========================================
  disp_en_1        <= internal_disp_1;
  disp_opcode_1    <= dec_opcode_1;
  disp_phys_dest_1 <= fl_alloc_1 when dec_dest_valid_1 = '1' else
                      (others => '0');
  disp_phys_ra_1   <= rat_p_rs1_1;
  disp_phys_rb_1   <= rat_p_rs2_1;
  disp_imm_1       <= dec_imm_1;

  disp_en_2        <= internal_disp_2;
  disp_opcode_2    <= dec_opcode_2;
  disp_phys_dest_2 <= fl_alloc_2 when dec_dest_valid_2 = '1' else
                      (others => '0');
  disp_phys_ra_2   <= bypass_ra_2;
  disp_phys_rb_2   <= bypass_rb_2;
  disp_imm_2       <= dec_imm_2;

end architecture structural;
