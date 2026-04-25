library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity ALU_Control is
    Port (
        alu_op      : in  STD_LOGIC_VECTOR(2 downto 0);
        funct       : in  STD_LOGIC_VECTOR(2 downto 0); -- {COMPL, CZ(1 downto 0)}
        alu_ctrl : out STD_LOGIC_VECTOR(4 downto 0)  -- UPGRADED TO 5 BITS
    );
end ALU_Control;

architecture Behavioral of ALU_Control is
    -- Base operations (Lower 4 bits)
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
    constant OP_PASSDATA2  : STD_LOGIC_VECTOR(3 downto 0) := "1010"; -- For memory/immediates

begin
    process(alu_op, funct)
        variable comp_bit : STD_LOGIC;
    begin
        -- Default Initialization
        comp_bit := '0';
        
        if alu_op = "000" then      -- I-Type ADD (ADI)
            alu_ctrl <= '0' & OP_ADD;
        elsif alu_op = "001" then   -- BEQ
            alu_ctrl <= '0' & OP_COMPAREBEQ;
        elsif alu_op = "100" then   -- BLT
            alu_ctrl <= '0' & OP_COMPAREBLT;
        elsif alu_op = "101" then   -- BLE
            alu_ctrl <= '0' & OP_COMPAREBLE;
            
        elsif alu_op = "010" then   -- R-Type ADD variants
            comp_bit := funct(2);   -- Extract the complement bit
            if funct(1 downto 0) = "00" then
                alu_ctrl <= comp_bit & OP_ADD;
            elsif funct(1 downto 0) = "10" then
                alu_ctrl <= comp_bit & OP_ADDIFC;
            elsif funct(1 downto 0) = "01" then
                alu_ctrl <= comp_bit & OP_ADDIFZ;
            elsif funct(1 downto 0) = "11" then
                alu_ctrl <= comp_bit & OP_ADDWC;
            else
                alu_ctrl <= comp_bit & OP_ADD;
            end if;
            
        elsif alu_op = "011" then   -- R-Type NAND variants
            comp_bit := funct(2);   -- Extract the complement bit
            if funct(1 downto 0) = "00" then
                alu_ctrl <= comp_bit & OP_NAND;
            elsif funct(1 downto 0) = "10" then
                alu_ctrl <= comp_bit & OP_NANDIFC;
            elsif funct(1 downto 0) = "01" then
                alu_ctrl <= comp_bit & OP_NANDIFZ;
            else
                alu_ctrl <= comp_bit & OP_NAND;
            end if;
            
        else
            alu_ctrl <= '0' & OP_PASSDATA2; -- Default Pass-through
        end if;
    end process;
end Behavioral;
