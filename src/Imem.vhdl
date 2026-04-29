library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

entity instruction_memory is
  port (
    -- The PC is byte-addressed, but we fetch 16-bit words
    pc_addr : in    std_logic_vector(15 downto 0);

    -- Outputs two 16-bit instructions for the 2-way superscalar decode
    inst_1 : out   std_logic_vector(15 downto 0);
    inst_2 : out   std_logic_vector(15 downto 0)
  );
end entity instruction_memory;

architecture behavioral of instruction_memory is

  -- Define ROM: 1024 words (16-bit), which equals 2048 bytes of instruction space

  type rom_type is array (0 to 1023) of std_logic_vector(15 downto 0);

  -- You can initialize your compiled machine code here!
  constant rom : rom_type :=
  (
    0 => x"C000", -- Example: LHI R0, 0
    1 => x"0000", -- Example: ADD R0, R0, R0
    -- ... add more initializations or use a .mif file
    others => x"0000"
  );

begin

  -- Asynchronous Read (standard for simple university project instruction fetches)
  process (pc_addr) is

    variable word_idx : integer;

  begin

    -- Shift right by 1 to convert byte address to word index
    word_idx := to_integer(unsigned(pc_addr(15 downto 1)));

    if (word_idx < 1023) then
      inst_1 <= ROM(word_idx);
      inst_2 <= ROM(word_idx + 1); -- Fetch the very next 16-bit word
    else
      inst_1 <= x"0000";
      inst_2 <= x"0000";
    end if;

  end process;

end architecture behavioral;
