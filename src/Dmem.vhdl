library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

entity data_memory is
  port (
    clk : in    std_logic;

    -- ==========================================
    -- READ PORT (For Load Instructions executing)
    -- ==========================================
    rd_addr : in    std_logic_vector(15 downto 0);
    rd_data : out   std_logic_vector(15 downto 0);

    -- ==========================================
    -- WRITE PORT (For Store Instructions committing)
    -- ==========================================
    wr_en   : in    std_logic;
    wr_addr : in    std_logic_vector(15 downto 0);
    wr_data : in    std_logic_vector(15 downto 0)
  );
end entity data_memory;

architecture behavioral of data_memory is

  -- Define RAM: 1024 words (16-bit), equals 2048 bytes of data space

  type ram_type is array (0 to 1023) of std_logic_vector(15 downto 0);

  signal ram : ram_type;

begin

  -- Asynchronous Read for Loads (allows single-cycle execution)
  process (rd_addr, ram) is

    variable rd_idx : integer;

  begin

    rd_idx := to_integer(unsigned(rd_addr(15 downto 1)));

    if (rd_idx < 1024) then
      rd_data <= ram(rd_idx);
    else
      rd_data <= (others => '0');
    end if;

  end process;

  -- Synchronous Write for Committing Stores
  process (clk) is

    variable wr_idx : integer;

  begin

    if rising_edge(clk) then
      if (wr_en = '1') then
        wr_idx := to_integer(unsigned(wr_addr(15 downto 1)));
        if (wr_idx < 1024) then
          ram(wr_idx) <= wr_data;
        end if;
      end if;
    end if;

  end process;

end architecture behavioral;
