library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

entity instruction_decoder is
  port (
    instruction : in    std_logic_vector(15 downto 0);

    -- Extracted Fields
    opcode_out  : out   std_logic_vector(3 downto 0);
    ra_out      : out   std_logic_vector(2 downto 0);
    rb_out      : out   std_logic_vector(2 downto 0);
    rc_out      : out   std_logic_vector(2 downto 0);
    imm6_ext    : out   std_logic_vector(15 downto 0);
    imm9_ext    : out   std_logic_vector(15 downto 0);
    complet_bit : out   std_logic; -- COMPL bit for ALU_Control
    cz_flags    : out   std_logic_vector(1 downto 0);

    -- Destination Resolution
    dest_valid : out   std_logic;
    dest_reg   : out   std_logic_vector(2 downto 0);
    dest_is_c  : out   std_logic; -- Destination is C flag
    dest_is_z  : out   std_logic; -- Destination is Z flag

    -- OoO Control Signals
    is_branch          : out   std_logic;
    is_implicit_branch : out   std_logic;
    wants_c_flag       : out   std_logic;
    wants_z_flag       : out   std_logic;
    wants_flags        : out   std_logic; -- Needs old C and Z (for ADD/NAND)
    writes_c_flag      : out   std_logic; -- Instruction modifies C flag
    writes_z_flag      : out   std_logic; -- Instruction modifies Z flag
    is_complex_mem     : out   std_logic;
    is_load_multiple   : out   std_logic;
    is_store_multiple  : out   std_logic
  );
end entity instruction_decoder;

architecture behavioral of instruction_decoder is

  signal opcode : std_logic_vector(3 downto 0);
  signal ra     : std_logic_vector(2 downto 0);
  signal rb     : std_logic_vector(2 downto 0);
  signal rc     : std_logic_vector(2 downto 0);
  signal imm6   : std_logic_vector(5 downto 0);
  signal imm9   : std_logic_vector(8 downto 0);
  signal compl  : std_logic;
  signal cz     : std_logic_vector(1 downto 0);

  -- Internal
  signal is_r_type      : std_logic;
  signal is_i_type      : std_logic;
  signal is_j_type      : std_logic;
  signal dest_valid_int : std_logic;
  signal dest_reg_int   : std_logic_vector(2 downto 0);

begin

  -- Field Extraction
  opcode <= instruction(15 downto 12);
  ra     <= instruction(11 downto 9);
  rb     <= instruction(8 downto 6);
  rc     <= instruction(5 downto 3);
  compl  <= instruction(2);
  cz     <= instruction(1 downto 0);
  imm6   <= instruction(5 downto 0);
  imm9   <= instruction(8 downto 0);

  opcode_out  <= opcode;
  ra_out      <= ra;
  rb_out      <= rb;
  rc_out      <= rc;
  complet_bit <= compl;
  cz_flags    <= cz;

  -- Sign Extension
  imm6_ext <= std_logic_vector(resize(signed(imm6), 16));
  imm9_ext <= std_logic_vector(resize(signed(imm9), 16));

  -- Instruction Type Detection
  is_r_type <= '1' when opcode = "0001" or opcode = "0010" else
               '0';
  is_i_type <= '1' when opcode = "0000" or opcode = "0100" or opcode = "0101" or
                        opcode = "1000" or opcode = "1001" or opcode = "1010" or
                        opcode = "1101" else
               '0';
  is_j_type <= '1' when opcode = "0011" or opcode = "0110" or opcode = "0111" or
                        opcode = "1100" or opcode = "1111" else
               '0';

  -- Main Decode Process
  process (opcode, ra, rb, rc, compl, cz, is_r_type, is_i_type, is_j_type) is
  begin

    -- Defaults
    dest_valid_int    <= '1';
    dest_reg_int      <= rc;
    dest_is_c         <= '0';
    dest_is_z         <= '0';
    is_branch         <= '0';
    wants_c_flag      <= '0';
    wants_z_flag      <= '0';
    wants_flags       <= '0';
    writes_c_flag     <= '0';
    writes_z_flag     <= '0';
    is_complex_mem    <= '0';
    is_load_multiple  <= '0';
    is_store_multiple <= '0';

    case opcode is

      -- ==========================================
      -- ADI: Add Immediate (I-Type)
      -- Format: ADI rb, ra, imm6
      -- dst = rb, src = ra
      -- ==========================================
      when "0000" =>

        dest_reg_int  <= rb;
        writes_c_flag <= '1';
        writes_z_flag <= '1';
        wants_flags   <= '0';

      -- ==========================================
      -- ADD Family (R-Type)
      -- ADA, ADC, ADZ, AWC, ACA, ACC, ACZ, ACW
      -- Format: ADD rc, ra, rb
      -- dst = rc
      -- ==========================================
      when "0001" =>

        dest_reg_int  <= rc;
        writes_c_flag <= '1';
        writes_z_flag <= '1';
        wants_flags   <= '1';            -- May need old flags for conditional
        -- Condition flags needed
        if (cz = "10") then              -- ADC / ACC
          wants_c_flag <= '1';
        end if;

        if (cz = "01") then              -- ADZ / ACZ
          wants_z_flag <= '1';
        end if;

      -- ==========================================
      -- NAND Family (R-Type)
      -- NDU, NDC, NDZ, NCU, NCC, NCZ
      -- Format: NAND rc, ra, rb
      -- dst = rc, only modifies Z flag
      -- ==========================================
      when "0010" =>

        dest_reg_int  <= rc;
        writes_c_flag <= '0';            -- NAND doesn't modify C
        writes_z_flag <= '1';
        wants_flags   <= '1';

        if (cz = "10") then              -- NDC / NCC
          wants_c_flag <= '1';
        end if;

        if (cz = "01") then              -- NDZ / NCZ
          wants_z_flag <= '1';
        end if;

      -- ==========================================
      -- LLI: Load Lower Immediate (J-Type)
      -- Format: LLI ra, imm9
      -- dst = ra
      -- ==========================================
      when "0011" =>

        dest_reg_int  <= ra;
        writes_c_flag <= '0';
        writes_z_flag <= '1';

      -- ==========================================
      -- LW: Load Word (I-Type)
      -- Format: LW ra, rb, imm6
      -- dst = ra
      -- ==========================================
      when "0100" =>

        dest_reg_int  <= rb;
        writes_c_flag <= '0';
        writes_z_flag <= '1';

      -- ==========================================
      -- SW: Store Word (I-Type)
      -- Format: SW ra, rb, imm6
      -- No destination
      -- ==========================================
      when "0101" =>

        dest_valid_int <= '0';
        writes_c_flag  <= '0';
        writes_z_flag  <= '0';

      -- ==========================================
      -- LM / LMF: Load Multiple (J-Type)
      -- Format: LM/LMF ra, imm8 (bitmap)
      -- ==========================================
      when "0110" =>

        is_complex_mem   <= '1';
        is_load_multiple <= '1';
        dest_valid_int   <= '0';         -- Destinations handled by sequencer
        writes_c_flag    <= '0';
        writes_z_flag    <= '0';

      -- CZ flags are written by the sequencer

      -- ==========================================
      -- SM / SMF: Store Multiple (J-Type)
      -- Format: SM/SMF ra, imm8 (bitmap)
      -- ==========================================
      when "0111" =>

        is_complex_mem    <= '1';
        is_store_multiple <= '1';
        dest_valid_int    <= '0';
        writes_c_flag     <= '0';
        writes_z_flag     <= '0';
      -- CZ flags are written by the sequencer

      -- ==========================================
      -- BEQ: Branch if Equal (I-Type)
      -- Format: BEQ ra, rb, imm6
      -- ==========================================
      when "1000" =>

        dest_valid_int <= '0';
        is_branch      <= '1';
        wants_flags    <= '0';           -- Uses comparison, not flags
        writes_c_flag  <= '0';
        writes_z_flag  <= '0';

      -- ==========================================
      -- BLT: Branch if Less Than (I-Type)
      -- Format: BLT ra, rb, imm6
      -- ==========================================
      when "1001" =>

        dest_valid_int <= '0';
        is_branch      <= '1';
        wants_flags    <= '0';
        writes_c_flag  <= '0';
        writes_z_flag  <= '0';

      -- ==========================================
      -- BLE: Branch if Less or Equal (I-Type)
      -- Format: BLE ra, rb, imm6
      -- ==========================================
      when "1010" =>

        dest_valid_int <= '0';
        is_branch      <= '1';
        wants_flags    <= '0';
        writes_c_flag  <= '0';
        writes_z_flag  <= '0';

      -- ==========================================
      -- JAL: Jump and Link (J-Type)
      -- Format: JAL ra, imm9
      -- dst = ra (PC+2)
      -- ==========================================
      when "1100" =>

        dest_reg_int  <= ra;
        is_branch     <= '1';
        writes_c_flag <= '0';
        writes_z_flag <= '0';

      -- ==========================================
      -- JLR: Jump and Link Register (I-Type)
      -- Format: JLR ra, rb
      -- dst = ra (PC+2)
      -- ==========================================
      when "1101" =>

        dest_reg_int  <= ra;
        is_branch     <= '1';
        writes_c_flag <= '0';
        writes_z_flag <= '0';

      -- ==========================================
      -- JRI: Jump Register Immediate (J-Type)
      -- Format: JRI ra, imm9
      -- No destination
      -- ==========================================
      when "1111" =>

        dest_valid_int <= '0';
        is_branch      <= '1';
        writes_c_flag  <= '0';
        writes_z_flag  <= '0';

      -- ==========================================
      -- Default
      -- ==========================================
      when others =>

        dest_valid_int <= '0';
        writes_c_flag  <= '0';
        writes_z_flag  <= '0';

    end case;

  end process;

  -- Implicit Branch Check (Writing to R0 = PC)
  is_implicit_branch <= '1' when (dest_valid_int = '1' and dest_reg_int = "000") else
                        '0';

  dest_valid <= dest_valid_int;
  dest_reg   <= dest_reg_int;

end architecture behavioral;
