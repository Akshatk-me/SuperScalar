library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

entity alu_arbiter is
  port (
    -- Requests from the 4 Reservation Station entries (ready_to_iss)
    req : in    std_logic_vector(3 downto 0);

    -- Individual grants sent back to the RS entries to clear their 'busy' state
    grant_bus : out   std_logic_vector(3 downto 0);

    -- Outputs for the ALU Multiplexers
    -- These tell the top-level pool WHICH RS entry won, so it can mux the data
    valid_1     : out   std_logic;
    grant_idx_1 : out   std_logic_vector(1 downto 0); -- 0 to 3

    valid_2     : out   std_logic;
    grant_idx_2 : out   std_logic_vector(1 downto 0) -- 0 to 3
  );
end entity alu_arbiter;

architecture behavioral of alu_arbiter is

begin

  process (req) is

    variable found_first  : boolean;
    variable found_second : boolean;

  begin

    -- Default assignments to prevent latches
    grant_bus   <= "0000";
    grant_idx_1 <= "00";
    grant_idx_2 <= "00";
    valid_1     <= '0';
    valid_2     <= '0';

    found_first  := false;
    found_second := false;

    -- Loop through RS entries. Lower index (0) has highest priority.
    for i in 0 to 3 loop

      if (req(i) = '1') then
        if (not found_first) then
          grant_bus(i) <= '1';
          grant_idx_1  <= std_logic_vector(to_unsigned(i, 2));
          valid_1      <= '1';
          found_first  := true;
        elsif (not found_second) then
          grant_bus(i) <= '1';
          grant_idx_2  <= std_logic_vector(to_unsigned(i, 2));
          valid_2      <= '1';
          found_second := true;
        end if;
      end if;

    end loop;

  end process;

end architecture behavioral;
