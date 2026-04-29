
-- This is deprecated, shifted to fetch_unit.vhdl

library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

entity pc_unit is
  port (
    clk   : in    std_logic;
    reset : in    std_logic;

    -- redirect (branch / R0 write / flush)
    redirect_valid : in    std_logic;
    redirect_pc    : in    std_logic_vector(15 downto 0);

    -- stall (optional)
    stall_fetch : in    std_logic;

    -- outputs
    pc_out      : out   std_logic_vector(15 downto 0);
    pc_next_out : out   std_logic_vector(15 downto 0)
  );
end entity pc_unit;

architecture rtl of pc_unit is

  signal pc_reg : std_logic_vector(15 downto 0);

begin

  process (clk, reset) is
  begin

    if (reset = '1') then
      pc_reg <= (others => '0');
    elsif rising_edge(clk) then
      if (redirect_valid = '1') then
        pc_reg <= redirect_pc;
      elsif (stall_fetch = '1') then
        pc_reg <= pc_reg;
      else
        pc_reg <= std_logic_vector(unsigned(pc_reg) + 2);
      end if;
    end if;

  end process;

  -- outputs
  pc_out      <= pc_reg;
  pc_next_out <= std_logic_vector(unsigned(pc_reg) + 2);

end architecture rtl;
