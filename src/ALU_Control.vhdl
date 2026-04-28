library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

entity alu_control is
  port (
    alu_op   : in    std_logic_vector(3 downto 0); -- 4-bit opcode
    funct    : in    std_logic_vector(2 downto 0); -- {COMPL, CZ(1 downto 0)}
    alu_ctrl : out   std_logic_vector(4 downto 0)  -- [COMPL][OPCODE(4)]
  );
end entity alu_control;

architecture behavioral of alu_control is

  -- Base ALU operations (4 bits)
  constant op_add     : std_logic_vector(3 downto 0) := "0000";
  constant op_addifc  : std_logic_vector(3 downto 0) := "0001";
  constant op_addifz  : std_logic_vector(3 downto 0) := "0010";
  constant op_addwc   : std_logic_vector(3 downto 0) := "0011";
  constant op_nand    : std_logic_vector(3 downto 0) := "0100";
  constant op_nandifc : std_logic_vector(3 downto 0) := "0101";
  constant op_nandifz : std_logic_vector(3 downto 0) := "0110";
  constant op_compare : std_logic_vector(3 downto 0) := "0111";
  constant op_pass    : std_logic_vector(3 downto 0) := "1000";
  constant op_lli     : std_logic_vector(3 downto 0) := "1001";

begin

  process (alu_op, funct) is

    variable comp_bit : std_logic;
    variable cz_bits  : std_logic_vector(1 downto 0);

  begin

    comp_bit := funct(2);                      -- COMPL bit
    cz_bits  := funct(1 downto 0);             -- CZ bits

    case alu_op is

      -- ADI: Add Immediate (I-Type)
      when "0000" =>

        alu_ctrl <= '0' & op_add;

      -- ADD Family (R-Type with complement)
      when "0001" =>

        case cz_bits is

          when "00" =>                         -- ADA (Add) or ACA (Add Complement)

            alu_ctrl <= comp_bit & op_add;

          when "01" =>                         -- ADZ (Add if Zero) or ACZ (Add Complement if Zero)

            -- FIXED: CZ="01" maps to ADDIFZ (Zero flag)
            alu_ctrl <= comp_bit & op_addifz;

          when "10" =>                         -- ADC (Add if Carry) or ACC (Add Complement if Carry)

            -- FIXED: CZ="10" maps to ADDIFC (Carry flag)
            alu_ctrl <= comp_bit & op_addifc;

          when "11" =>                         -- AWC (Add with Carry) or ACW (Add Complement with Carry)

            alu_ctrl <= comp_bit & op_addwc;

          when others =>

            alu_ctrl <= comp_bit & op_add;

        end case;

      -- NAND Family (R-Type with complement)
      when "0010" =>

        case cz_bits is

          when "00" =>                         -- NDU (NAND) or NCU (NAND Complement)

            alu_ctrl <= comp_bit & op_nand;

          when "01" =>                         -- NDZ (NAND if Zero) or NCZ (NAND Complement if Zero)

            -- FIXED: CZ="01" maps to NANDIFZ (Zero flag)
            alu_ctrl <= comp_bit & op_nandifz;

          when "10" =>                         -- NDC (NAND if Carry) or NCC (NAND Complement if Carry)

            -- FIXED: CZ="10" maps to NANDIFC (Carry flag)
            alu_ctrl <= comp_bit & op_nandifc;

          when others =>                       -- "11" - default to NAND

            alu_ctrl <= comp_bit & op_nand;

        end case;

      -- LLI: Load Lower Immediate (J-Type)
      when "0011" =>

        alu_ctrl <= '0' & op_lli;

      -- LW: Load Word (I-Type)
      when "0100" =>

        alu_ctrl <= '0' & op_pass;

      -- SW: Store Word (I-Type)
      when "0101" =>

        alu_ctrl <= '0' & op_pass;

      -- LM/LMF: Load Multiple (J-Type)
      when "0110" =>

        alu_ctrl <= '0' & op_pass;

      -- SM/SMF: Store Multiple (J-Type)
      when "0111" =>

        alu_ctrl <= '0' & op_pass;

      -- BEQ: Branch if Equal (I-Type)
      when "1000" =>

        alu_ctrl <= '0' & op_compare;

      -- BLT/BLE: Branch if Less Than/Equal (I-Type)
      when "1001" =>

        alu_ctrl <= '0' & op_compare;

      -- JAL: Jump and Link (J-Type)
      when "1100" =>

        alu_ctrl <= '0' & op_pass;

      -- JLR: Jump and Link Register (I-Type)
      when "1101" =>

        alu_ctrl <= '0' & op_pass;

      -- JRI: Jump Register Immediate (J-Type)
      when "1111" =>

        alu_ctrl <= '0' & op_add;              -- RA + Imm*2

      -- Default for undefined opcodes
      when others =>

        alu_ctrl <= '0' & op_pass;

    end case;

  end process;

end architecture behavioral;
