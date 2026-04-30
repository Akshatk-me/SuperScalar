library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

entity alu_rs_entry is
  port (
    clk : in    std_logic;
    rst : in    std_logic;

    -- ==========================================
    -- DISPATCH INTERFACE (From Rename Stage)
    -- ==========================================
    dispatch_en : in    std_logic; -- 1 if allocating to this specific RS entry

    -- The physical registers this instruction needs
    in_rs1_tag : in    std_logic_vector(4 downto 0);
    in_rs1_rdy : in    std_logic;

    in_rs2_tag : in    std_logic_vector(4 downto 0);
    in_rs2_rdy : in    std_logic;

    in_c_tag : in    std_logic_vector(4 downto 0);
    in_c_rdy : in    std_logic;

    in_z_tag : in    std_logic_vector(4 downto 0);
    in_z_rdy : in    std_logic;

    -- The physical register this instruction will write to
    in_dest_tag : in    std_logic_vector(4 downto 0);
    in_opcode   : in    std_logic_vector(3 downto 0);

    -- ==========================================
    -- COMMON DATA BUS SNOOPING (Wakeup Logic)
    -- ==========================================
    cdb1_valid : in    std_logic;
    cdb1_tag   : in    std_logic_vector(4 downto 0);

    cdb2_valid : in    std_logic;
    cdb2_tag   : in    std_logic_vector(4 downto 0);

    -- Immediate related singnals
    in_imm     : in    std_logic_vector(15 downto 0); -- Extended to 16-bit for ALU
    in_use_imm : in    std_logic;                     -- 1 if we use the immediate instead of RS2

    out_imm     : out   std_logic_vector(15 downto 0);
    out_use_imm : out   std_logic;

    -- ==========================================
    -- ISSUE INTERFACE (Select Logic to ALU)
    -- ==========================================
    busy         : out   std_logic; -- 1 if this entry is occupied
    ready_to_iss : out   std_logic; -- 1 if all operands are ready

    -- Grant signal from the Arbiter to actually send to ALU
    issue_grant : in    std_logic;

    -- Outputs sent to the ALU / PRF read ports
    out_rs1_tag  : out   std_logic_vector(4 downto 0);
    out_rs2_tag  : out   std_logic_vector(4 downto 0);
    out_c_tag    : out   std_logic_vector(4 downto 0);
    out_z_tag    : out   std_logic_vector(4 downto 0);
    out_dest_tag : out   std_logic_vector(4 downto 0);
    out_opcode   : out   std_logic_vector(3 downto 0)
  );
end entity alu_rs_entry;

architecture behavioral of alu_rs_entry is

  -- Internal state registers for this RS slot
  signal is_busy : std_logic;

  signal rs1_tag     : std_logic_vector(4 downto 0);
  signal rs2_tag     : std_logic_vector(4 downto 0);
  signal c_tag       : std_logic_vector(4 downto 0);
  signal z_tag       : std_logic_vector(4 downto 0);
  signal dest_tag    : std_logic_vector(4 downto 0);
  signal rs1_rdy     : std_logic;
  signal rs2_rdy     : std_logic;
  signal c_rdy       : std_logic;
  signal z_rdy       : std_logic;
  signal opcode      : std_logic_vector(3 downto 0);
  signal imm_reg     : std_logic_vector(15 downto 0);
  signal use_imm_reg : std_logic;

begin

  busy <= is_busy;

  -- Expose tags to the outside world (for the PRF read ports and Arbiter)
  out_rs1_tag  <= rs1_tag;
  out_rs2_tag  <= rs2_tag;
  out_c_tag    <= c_tag;
  out_z_tag    <= z_tag;
  out_dest_tag <= dest_tag;
  out_opcode   <= opcode;

  -- Imm stuff
  out_imm     <= imm_reg;
  out_use_imm <= use_imm_reg;

  -- ==========================================
  -- WAKEUP & SELECT LOGIC (Combinational)
  -- ==========================================
  -- An entry is ready to issue if it is busy AND all operands are ready.
  -- We also include "Bypass" logic: if a tag matches the CDB in the current cycle,
  -- it is considered ready immediately (so it can issue next cycle).

  process (is_busy, rs1_rdy, rs2_rdy, c_rdy, z_rdy, rs1_tag, rs2_tag, c_tag, z_tag,
           cdb1_valid, cdb1_tag, cdb2_valid, cdb2_tag) is

    variable rs1_match : boolean;
    variable rs2_match : boolean;
    variable c_match   : boolean;
    variable z_match   : boolean;

  begin

    -- Check for tag matches on either CDB
    rs1_match := (cdb1_valid = '1' and cdb1_tag = rs1_tag) or (cdb2_valid = '1' and cdb2_tag = rs1_tag);
    rs2_match := (cdb1_valid = '1' and cdb1_tag = rs2_tag) or (cdb2_valid = '1' and cdb2_tag = rs2_tag);
    c_match   := (cdb1_valid = '1' and cdb1_tag = c_tag)   or (cdb2_valid = '1' and cdb2_tag = c_tag);
    z_match   := (cdb1_valid = '1' and cdb1_tag = z_tag)   or (cdb2_valid = '1' and cdb2_tag = z_tag);

    if (is_busy = '1' and
        (rs1_rdy = '1' or rs1_match) and
        (rs2_rdy = '1' or rs2_match) and
        (c_rdy = '1' or c_match)   and
        (z_rdy = '1' or z_match)) then
      ready_to_iss <= '1';
    else
      ready_to_iss <= '0';
    end if;

  end process;

  -- ==========================================
  -- SYNCHRONOUS UPDATE (Dispatch & CDB Snooping)
  -- ==========================================
  process (clk) is
  begin

    if rising_edge(clk) then
      if (rst = '1') then
        is_busy <= '0';
        rs1_rdy <= '0';
        rs2_rdy <= '0';
        c_rdy   <= '0';
        z_rdy   <= '0';
      elsif (issue_grant = '1') then
        -- The arbiter has selected this entry to go to the ALU.
        -- It frees up this slot for the next instruction.
        is_busy <= '0';
      elsif (dispatch_en = '1') then
        -- Load a new instruction into this RS slot
        is_busy     <= '1';
        opcode      <= in_opcode;
        dest_tag    <= in_dest_tag;
        imm_reg     <= in_imm;
        use_imm_reg <= in_use_imm;

        rs1_tag <= in_rs1_tag;
        rs1_rdy <= in_rs1_rdy;
        rs2_tag <= in_rs2_tag;
        rs2_rdy <= in_rs2_rdy;
        c_tag   <= in_c_tag;
        c_rdy   <= in_c_rdy;
        z_tag   <= in_z_tag;
        z_rdy   <= in_z_rdy;
      elsif (is_busy = '1') then
        -- SNOOP THE CDB:
        -- If we are busy and waiting for an operand, check if the CDB
        -- is broadcasting the physical register tag we need.

        if (rs1_rdy = '0') then
          if ((cdb1_valid = '1' and cdb1_tag = rs1_tag) or
              (cdb2_valid = '1' and cdb2_tag = rs1_tag)) then
            rs1_rdy <= '1';
          end if;
        end if;

        if (rs2_rdy = '0') then
          if ((cdb1_valid = '1' and cdb1_tag = rs2_tag) or
              (cdb2_valid = '1' and cdb2_tag = rs2_tag)) then
            rs2_rdy <= '1';
          end if;
        end if;

        if (c_rdy = '0') then
          if ((cdb1_valid = '1' and cdb1_tag = c_tag) or
              (cdb2_valid = '1' and cdb2_tag = c_tag)) then
            c_rdy <= '1';
          end if;
        end if;

        if (z_rdy = '0') then
          if ((cdb1_valid = '1' and cdb1_tag = z_tag) or
              (cdb2_valid = '1' and cdb2_tag = z_tag)) then
            z_rdy <= '1';
          end if;
        end if;
      end if;
    end if;

  end process;

end architecture behavioral;
