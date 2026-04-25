library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity ALU is
    Port (
        data1       : in  STD_LOGIC_VECTOR(15 downto 0);
        data2       : in  STD_LOGIC_VECTOR(15 downto 0);
        C_in        : in  STD_LOGIC;  -- The architectural condition flags
        Z_in        : in  STD_LOGIC;  -- 
        ALU_control : in  STD_LOGIC_VECTOR(4 downto 0); -- Now 5 bits
        ALU_result  : out STD_LOGIC_VECTOR(15 downto 0);
        zero        : out STD_LOGIC;
        carry       : out STD_LOGIC;
        lt          : out STD_LOGIC;
        eq          : out STD_LOGIC;
        le          : out STD_LOGIC
    );
end ALU;

architecture Behavioral of ALU is
    constant OP_ADD        : STD_LOGIC_VECTOR(3 downto 0) := "0000";
    constant OP_ADDIFC     : STD_LOGIC_VECTOR(3 downto 0) := "0001";
    constant OP_ADDIFZ     : STD_LOGIC_VECTOR(3 downto 0) := "0010";
    constant OP_ADDWC      : STD_LOGIC_VECTOR(3 downto 0) := "0011";
    constant OP_NAND       : STD_LOGIC_VECTOR(3 downto 0) := "0100";
    constant OP_NANDIFC    : STD_LOGIC_VECTOR(3 downto 0) := "0101";
    constant OP_NANDIFZ    : STD_LOGIC_VECTOR(3 downto 0) := "0110";
    constant OP_COMPAREBEQ : STD_LOGIC_VECTOR(3 downto 0) := "0111";
    constant OP_COMPAREBLT : STD_LOGIC_VECTOR(3 downto 0) := "1000";
    constant OP_COMPAREBLE : STD_LOGIC_VECTOR(3 downto 0) := "1001";
    constant OP_PASSDATA2  : STD_LOGIC_VECTOR(3 downto 0) := "1010";
    
begin
    process(data1, data2, C_in, Z_in, ALU_control)
        variable v_data2_actual : STD_LOGIC_VECTOR(15 downto 0);
        variable v_ALU_result   : UNSIGNED(16 downto 0); -- 17 bits to catch the carry out
        variable v_zero         : STD_LOGIC;
        variable v_carry        : STD_LOGIC;
    begin
        -- 1. Initialize Default Outputs to prevent VHDL latches
        v_ALU_result := (others => '0');
        v_zero       := '0';
        v_carry      := '0';
        lt           <= '0';
        eq           <= '0';
        le           <= '0';
        
        -- 2. Process the Complement Toggle (The MSB of ALU_control)
        if ALU_control(4) = '1' then
            v_data2_actual := NOT data2;
        else
            v_data2_actual := data2;
        end if;

        -- 3. Perform Operation based on lower 4 bits
        case ALU_control(3 downto 0) is
            when OP_ADD =>
                v_ALU_result := UNSIGNED('0' & data1) + UNSIGNED('0' & v_data2_actual);
                v_carry := v_ALU_result(16);
                if v_ALU_result(15 downto 0) = x"0000" then v_zero := '1'; end if;

            when OP_ADDIFC =>
                if C_in = '1' then
                    v_ALU_result := UNSIGNED('0' & data1) + UNSIGNED('0' & v_data2_actual);
                    v_carry := v_ALU_result(16);
                    if v_ALU_result(15 downto 0) = x"0000" then v_zero := '1'; end if;
                end if; -- If C_in = 0, it acts as a NOP (result remains 0)

            when OP_ADDIFZ =>
                if Z_in = '1' then
                    v_ALU_result := UNSIGNED('0' & data1) + UNSIGNED('0' & v_data2_actual);
                    v_carry := v_ALU_result(16);
                    if v_ALU_result(15 downto 0) = x"0000" then v_zero := '1'; end if;
                end if;

            when OP_ADDWC =>
                -- Here we mathematically ADD the incoming Carry flag!
                v_ALU_result := UNSIGNED('0' & data1) + UNSIGNED('0' & v_data2_actual) + ("0000000000000000" & C_in);
                v_carry := v_ALU_result(16);
                if v_ALU_result(15 downto 0) = x"0000" then v_zero := '1'; end if;

            when OP_NAND =>
                v_ALU_result(15 downto 0) := UNSIGNED(NOT (data1 AND v_data2_actual));
                if v_ALU_result(15 downto 0) = x"0000" then v_zero := '1'; end if;

            when OP_NANDIFC =>
                if C_in = '1' then
                    v_ALU_result(15 downto 0) := UNSIGNED(NOT (data1 AND v_data2_actual));
                    if v_ALU_result(15 downto 0) = x"0000" then v_zero := '1'; end if;
                end if;

            when OP_NANDIFZ =>
                if Z_in = '1' then
                    v_ALU_result(15 downto 0) := UNSIGNED(NOT (data1 AND v_data2_actual));
                    if v_ALU_result(15 downto 0) = x"0000" then v_zero := '1'; end if;
                end if;

            when OP_COMPAREBEQ =>
                if data1 = data2 then eq <= '1'; end if;

            when OP_COMPAREBLT =>
                if UNSIGNED(data1) < UNSIGNED(data2) then lt <= '1'; end if;

            when OP_COMPAREBLE =>
                if UNSIGNED(data1) <= UNSIGNED(data2) then le <= '1'; end if;

            when OP_PASSDATA2 =>
                v_ALU_result(15 downto 0) := UNSIGNED(data2);

            when others =>
                null;
        end case;

        -- 4. Drive the output signals
        ALU_result <= STD_LOGIC_VECTOR(v_ALU_result(15 downto 0));
        zero       <= v_zero;
        carry      <= v_carry;

    end process;
end Behavioral;
