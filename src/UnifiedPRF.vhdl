library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

entity unified_prf is
  port (
    clk : in    std_logic;
    rst : in    std_logic; -- Active high synchronous reset

    -- ==========================================
    -- 8 ASYNCHRONOUS READ PORTS (4 per Instruction)
    -- ==========================================
    -- Instruction 1 Reads (Rs1, Rs2, C_flag_addr, Z_flag_addr)
    rd_addr_1 : in    std_logic_vector(4 downto 0);
    rd_data_1 : out   std_logic_vector(17 downto 0);

    rd_addr_2 : in    std_logic_vector(4 downto 0);
    rd_data_2 : out   std_logic_vector(17 downto 0);

    rd_addr_3 : in    std_logic_vector(4 downto 0);
    rd_data_3 : out   std_logic_vector(17 downto 0);

    rd_addr_4 : in    std_logic_vector(4 downto 0);
    rd_data_4 : out   std_logic_vector(17 downto 0);

    -- Instruction 2 Reads (Rs1, Rs2, C_flag_addr, Z_flag_addr)
    rd_addr_5 : in    std_logic_vector(4 downto 0);
    rd_data_5 : out   std_logic_vector(17 downto 0);

    rd_addr_6 : in    std_logic_vector(4 downto 0);
    rd_data_6 : out   std_logic_vector(17 downto 0);

    rd_addr_7 : in    std_logic_vector(4 downto 0);
    rd_data_7 : out   std_logic_vector(17 downto 0);

    rd_addr_8 : in    std_logic_vector(4 downto 0);
    rd_data_8 : out   std_logic_vector(17 downto 0);

    -- ==========================================
    -- 2 SYNCHRONOUS WRITE PORTS
    -- (For up to 2 instructions completing per cycle)
    -- Width is 18 bits: [17] Z, [16] C, [15:0] Data
    -- ==========================================
    wr_en_1   : in    std_logic;
    wr_addr_1 : in    std_logic_vector(4 downto 0);
    wr_data_1 : in    std_logic_vector(17 downto 0);

    wr_en_2   : in    std_logic;
    wr_addr_2 : in    std_logic_vector(4 downto 0);
    wr_data_2 : in    std_logic_vector(17 downto 0)
  );
end entity unified_prf;

architecture behavioral of unified_prf is

  -- Define an array of 32 elements, each 18 bits wide

  type prf_array_type is array (0 to 31) of std_logic_vector(17 downto 0);

  signal prf_reg : prf_array_type;

begin

  -- ==========================================
  -- ASYNCHRONOUS READ LOGIC
  -- ==========================================
  -- In an OoO processor, reads must be asynchronous so instructions waking up
  -- in the Reservation Station can grab their data and execute in the same cycle.
  rd_data_1 <= prf_reg(to_integer(unsigned(rd_addr_1)));
  rd_data_2 <= prf_reg(to_integer(unsigned(rd_addr_2)));
  rd_data_3 <= prf_reg(to_integer(unsigned(rd_addr_3)));
  rd_data_4 <= prf_reg(to_integer(unsigned(rd_addr_4)));

  rd_data_5 <= prf_reg(to_integer(unsigned(rd_addr_5)));
  rd_data_6 <= prf_reg(to_integer(unsigned(rd_addr_6)));
  rd_data_7 <= prf_reg(to_integer(unsigned(rd_addr_7)));
  rd_data_8 <= prf_reg(to_integer(unsigned(rd_addr_8)));

  -- ==========================================
  -- SYNCHRONOUS WRITE LOGIC
  -- ==========================================
  sync_writes : process (clk) is
  begin

    if rising_edge(clk) then
      if (rst = '1') then
        -- Clear all physical registers on reset
        for i in 0 to 31 loop

          prf_reg(i) <= (others => '0');

        end loop;

      else
        -- Port 1 Write
        if (wr_en_1 = '1') then
          prf_reg(to_integer(unsigned(wr_addr_1))) <= wr_data_1;
        end if;

        -- Port 2 Write
        -- Note: If both ports try to write to the exact same physical register
        -- simultaneously, Port 2 will overwrite Port 1 in VHDL simulation.
        -- However, in Tomasulo's algorithm, the Free List guarantees unique
        -- physical register allocation, so this collision should never happen.
        if (wr_en_2 = '1') then
          prf_reg(to_integer(unsigned(wr_addr_2))) <= wr_data_2;
        end if;
      end if;
    end if;

  end process sync_writes;

end architecture behavioral;
