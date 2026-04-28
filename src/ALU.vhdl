library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

entity alu is
  port (
    data1       : in    std_logic_vector(15 downto 0);
    data2       : in    std_logic_vector(15 downto 0);
    c_in        : in    std_logic;
    z_in        : in    std_logic;
    alu_control : in    std_logic_vector(4 downto 0); -- [COMPL(1)][OPCODE(4)]
    alu_result  : out   std_logic_vector(15 downto 0);
    zero        : out   std_logic;
    carry       : out   std_logic;
    lt          : out   std_logic;
    eq          : out   std_logic;
    le          : out   std_logic
  );
end entity alu;

architecture behavioral of alu is

  -- ALU Operation Codes (4 bits)
  constant op_add     : std_logic_vector(3 downto 0) := "0000";
  constant op_addifc  : std_logic_vector(3 downto 0) := "0001";
  constant op_addifz  : std_logic_vector(3 downto 0) := "0010";
  constant op_addwc   : std_logic_vector(3 downto 0) := "0011";
  constant op_nand    : std_logic_vector(3 downto 0) := "0100";
  constant op_nandifc : std_logic_vector(3 downto 0) := "0101";
  constant op_nandifz : std_logic_vector(3 downto 0) := "0110";
  constant op_compare : std_logic_vector(3 downto 0) := "0111"; -- Unified compare
  constant op_pass    : std_logic_vector(3 downto 0) := "1000"; -- Pass data2
  constant op_lli     : std_logic_vector(3 downto 0) := "1001"; -- Load Lower Immediate

  -- For comparison sub-operations
  constant cmp_eq : std_logic_vector(1 downto 0) := "00";
  constant cmp_lt : std_logic_vector(1 downto 0) := "01";
  constant cmp_le : std_logic_vector(1 downto 0) := "10";

begin

  process (data1, data2, c_in, z_in, alu_control) is

    variable v_data2_actual : std_logic_vector(15 downto 0);
    variable v_alu_result   : unsigned(16 downto 0);
    variable v_zero         : std_logic;
    variable v_carry        : std_logic;
    variable v_compare_type : std_logic_vector(1 downto 0);

  begin

    -- Default outputs
    v_alu_result   := (others => '0');
    v_zero         := '0';
    v_carry        := '0';
    lt             <= '0';
    eq             <= '0';
    le             <= '0';
    v_compare_type := "00";

    -- Handle complement for data2 (BIT 4 of alu_control)
    if (alu_control(4) = '1') then
      v_data2_actual := NOT data2;
    else
      v_data2_actual := data2;
    end if;

    -- Main operation based on lower 4 bits
    case alu_control(3 downto 0) is

      -- ============================================
      -- ADD Operations (with complement support)
      -- ============================================
      when op_add =>

        -- Simple addition
        v_alu_result := unsigned('0' & data1) + unsigned('0' & v_data2_actual);
        v_carry      := v_alu_result(16);

        if (v_alu_result(15 downto 0) = x"0000") then
          v_zero := '1';
        end if;

      when op_addifc =>

        -- Add if Carry flag is set
        if (c_in = '1') then
          v_alu_result := unsigned('0' & data1) + unsigned('0' & v_data2_actual);
          v_carry      := v_alu_result(16);
          if (v_alu_result(15 downto 0) = x"0000") then
            v_zero := '1';
          end if;
        else
          -- When c_in=0, pass data1 through (not zero!)
          v_alu_result(15 downto 0) := unsigned(data1);
        end if;

      when op_addifz =>

        -- Add if Zero flag is set
        if (z_in = '1') then
          v_alu_result := unsigned('0' & data1) + unsigned('0' & v_data2_actual);
          v_carry      := v_alu_result(16);
          if (v_alu_result(15 downto 0) = x"0000") then
            v_zero := '1';
          end if;
        else
          -- When z_in=0, pass data1 through
          v_alu_result(15 downto 0) := unsigned(data1);
        end if;

      when op_addwc =>

        -- Add with Carry (include c_in in addition)
        v_alu_result := unsigned('0' & data1) + unsigned('0' & v_data2_actual) +
                        ("0000000000000000" & c_in);
        v_carry      := v_alu_result(16);

        if (v_alu_result(15 downto 0) = x"0000") then
          v_zero := '1';
        end if;

      -- ============================================
      -- NAND Operations
      -- Note: NAND doesn't modify carry flag
      -- ============================================
      when op_nand =>

        v_alu_result(15 downto 0) := unsigned(NOT (data1 and v_data2_actual));

        if (v_alu_result(15 downto 0) = x"0000") then
          v_zero := '1';
        end if;

      -- Carry remains 0 for NAND operations

      when op_nandifc =>

        if (c_in = '1') then
          v_alu_result(15 downto 0) := unsigned(NOT (data1 and v_data2_actual));
          if (v_alu_result(15 downto 0) = x"0000") then
            v_zero := '1';
          end if;
        else
          -- Pass data1 through when condition false
          v_alu_result(15 downto 0) := unsigned(data1);
        end if;

      when op_nandifz =>

        if (z_in = '1') then
          v_alu_result(15 downto 0) := unsigned(NOT (data1 and v_data2_actual));
          if (v_alu_result(15 downto 0) = x"0000") then
            v_zero := '1';
          end if;
        else
          v_alu_result(15 downto 0) := unsigned(data1);
        end if;

      -- ============================================
      -- Comparison Operations (BEQ, BLT, BLE)
      -- ============================================
      when op_compare =>

        -- For comparisons, we use alu_result to pass through data2
        -- The comparison results go to eq/lt/le outputs
        v_alu_result(15 downto 0) := unsigned(data2);

        -- Extract compare type from lower bits of alu_control
        -- In a real implementation, you'd have a separate compare_type input
        -- For now, we'll use the complement bit to distinguish
        if (alu_control(4) = '0') then
          -- BEQ: Branch if Equal
          if (data1 = data2) then
            eq <= '1';
          end if;
        else
          -- BLT/BLE would need separate encoding
          -- This part needs to be connected to your instruction decoder properly
          if (unsigned(data1) < unsigned(data2)) then
            lt <= '1';
          end if;
          if (unsigned(data1) <= unsigned(data2)) then
            le <= '1';
          end if;
        end if;

      -- ============================================
      -- Pass-through Operations
      -- ============================================
      when op_pass =>

        -- Simply pass data2 to result
        v_alu_result(15 downto 0) := unsigned(data2);

      -- ============================================
      -- LLI: Load Lower Immediate
      -- ============================================
      when op_lli =>

        -- Immediate value should come from data2 lower 9 bits
        -- Zeros in upper 7 bits
        v_alu_result(8 downto 0)  := unsigned(data2(8 downto 0));
        v_alu_result(15 downto 9) := (others => '0');
        -- Zero flag if result is zero
        if (v_alu_result(15 downto 0) = x"0000") then
          v_zero := '1';
        end if;

      -- Carry unchanged for LLI

      -- ============================================
      -- Default
      -- ============================================
      when others =>

        v_alu_result(15 downto 0) := unsigned(data2);

    end case;

    -- Drive outputs
    alu_result <= std_logic_vector(v_alu_result(15 downto 0));
    zero       <= v_zero;
    carry      <= v_carry;

  end process;

end architecture behavioral;
