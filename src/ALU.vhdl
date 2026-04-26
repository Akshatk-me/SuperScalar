library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

entity alu is
  port (
    data1       : in    std_logic_vector(15 downto 0);
    data2       : in    std_logic_vector(15 downto 0);
    c_in        : in    std_logic;                    -- The architectural condition flags
    z_in        : in    std_logic;                    --
    alu_control : in    std_logic_vector(4 downto 0); -- Now 5 bits
    alu_result  : out   std_logic_vector(15 downto 0);
    zero        : out   std_logic;
    carry       : out   std_logic;
    lt          : out   std_logic;
    eq          : out   std_logic;
    le          : out   std_logic
  );
end entity alu;

architecture behavioral of alu is

  constant op_add        : std_logic_vector(3 downto 0) := "0000";
  constant op_addifc     : std_logic_vector(3 downto 0) := "0001";
  constant op_addifz     : std_logic_vector(3 downto 0) := "0010";
  constant op_addwc      : std_logic_vector(3 downto 0) := "0011";
  constant op_nand       : std_logic_vector(3 downto 0) := "0100";
  constant op_nandifc    : std_logic_vector(3 downto 0) := "0101";
  constant op_nandifz    : std_logic_vector(3 downto 0) := "0110";
  constant op_comparebeq : std_logic_vector(3 downto 0) := "0111";
  constant op_compareblt : std_logic_vector(3 downto 0) := "1000";
  constant op_compareble : std_logic_vector(3 downto 0) := "1001";
  constant op_passdata2  : std_logic_vector(3 downto 0) := "1010";

begin

  process (data1, data2, c_in, z_in, alu_control) is

    variable v_data2_actual : std_logic_vector(15 downto 0);
    variable v_alu_result   : unsigned(16 downto 0); -- 17 bits to catch the carry out
    variable v_zero         : std_logic;
    variable v_carry        : std_logic;

  begin

    -- 1. Initialize Default Outputs to prevent VHDL latches
    v_alu_result := (others => '0');
    v_zero       := '0';
    v_carry      := '0';
    lt           <= '0';
    eq           <= '0';
    le           <= '0';

    -- 2. Process the Complement Toggle (The MSB of ALU_control)
    if (alu_control(4) = '1') then
      v_data2_actual := NOT data2;
    else
      v_data2_actual := data2;
    end if;

    -- 3. Perform Operation based on lower 4 bits
    case alu_control(3 downto 0) is

      when op_add =>

        v_alu_result := UNSIGNED('0' & data1) + UNSIGNED('0' & v_data2_actual);
        v_carry      := v_ALU_result(16);

        if (v_ALU_result(15 downto 0) = x"0000") then
          v_zero := '1';
        end if;

      when op_addifc =>

        if (c_in = '1') then
          v_alu_result := UNSIGNED('0' & data1) + UNSIGNED('0' & v_data2_actual);
          v_carry      := v_ALU_result(16);
          if (v_ALU_result(15 downto 0) = x"0000") then
            v_zero := '1';
          end if;
        end if; -- If C_in = 0, it acts as a NOP (result remains 0)

      when op_addifz =>

        if (z_in = '1') then
          v_alu_result := UNSIGNED('0' & data1) + UNSIGNED('0' & v_data2_actual);
          v_carry      := v_ALU_result(16);
          if (v_ALU_result(15 downto 0) = x"0000") then
            v_zero := '1';
          end if;
        end if;

      when op_addwc =>

        -- Here we mathematically ADD the incoming Carry flag!
        v_alu_result := UNSIGNED('0' & data1) + UNSIGNED('0' & v_data2_actual) + ("0000000000000000" & c_in);
        v_carry      := v_ALU_result(16);

        if (v_ALU_result(15 downto 0) = x"0000") then
          v_zero := '1';
        end if;

      when op_nand =>

        v_alu_result(15 downto 0) := UNSIGNED(NOT (data1 and v_data2_actual));

        if (v_ALU_result(15 downto 0) = x"0000") then
          v_zero := '1';
        end if;

      when op_nandifc =>

        if (c_in = '1') then
          v_alu_result(15 downto 0) := UNSIGNED(NOT (data1 and v_data2_actual));
          if (v_ALU_result(15 downto 0) = x"0000") then
            v_zero := '1';
          end if;
        end if;

      when op_nandifz =>

        if (z_in = '1') then
          v_alu_result(15 downto 0) := UNSIGNED(NOT (data1 and v_data2_actual));
          if (v_ALU_result(15 downto 0) = x"0000") then
            v_zero := '1';
          end if;
        end if;

      when op_comparebeq =>

        if (data1 = data2) then
          eq <= '1';
        end if;

      when op_compareblt =>

        if (UNSIGNED(data1) < UNSIGNED(data2)) then
          lt <= '1';
        end if;

      when op_compareble =>

        if (UNSIGNED(data1) <= UNSIGNED(data2)) then
          le <= '1';
        end if;

      when op_passdata2 =>

        v_alu_result(15 downto 0) := UNSIGNED(data2);

      when others =>

        null;

    end case;

    -- 4. Drive the output signals
    alu_result <= STD_LOGIC_VECTOR(v_ALU_result(15 downto 0));
    zero       <= v_zero;
    carry      <= v_carry;

  end process;

end architecture behavioral;
