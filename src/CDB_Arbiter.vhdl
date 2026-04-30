library ieee;
  use ieee.std_logic_1164.all;

entity cdb_arbiter is
  port (
    -- Requests from Functional Units
    req_alu1  : in    std_logic;
    tag_alu1  : in    std_logic_vector(4 downto 0);
    data_alu1 : in    std_logic_vector(17 downto 0);

    req_alu2  : in    std_logic;
    tag_alu2  : in    std_logic_vector(4 downto 0);
    data_alu2 : in    std_logic_vector(17 downto 0);

    req_lsu  : in    std_logic;
    tag_lsu  : in    std_logic_vector(4 downto 0);
    data_lsu : in    std_logic_vector(17 downto 0);

    -- Grants back to Functional Units (tells them they successfully broadcasted)
    grant_alu1 : out   std_logic;
    grant_alu2 : out   std_logic;
    grant_lsu  : out   std_logic;

    -- The 2 Common Data Buses (To ROB, RS, and PRF Write Ports)
    cdb1_valid : out   std_logic;
    cdb1_tag   : out   std_logic_vector(4 downto 0);
    cdb1_data  : out   std_logic_vector(17 downto 0);

    cdb2_valid : out   std_logic;
    cdb2_tag   : out   std_logic_vector(4 downto 0);
    cdb2_data  : out   std_logic_vector(17 downto 0)
  );
end entity cdb_arbiter;

architecture behavioral of cdb_arbiter is

begin

  process (req_alu1, req_alu2, req_lsu, tag_alu1, tag_alu2, tag_lsu, data_alu1, data_alu2, data_lsu) is
  begin

    -- Default assignments to prevent latches
    grant_alu1 <= '0';
    grant_alu2 <= '0';
    grant_lsu  <= '0';
    cdb1_valid <= '0';
    cdb1_tag   <= (others => '0');
    cdb1_data  <= (others => '0');
    cdb2_valid <= '0';
    cdb2_tag   <= (others => '0');
    cdb2_data  <= (others => '0');

    -- Priority 1: LSU (Memory loads usually block dependents, so rush them out)
    if (req_lsu = '1') then
      cdb1_valid <= '1';
      cdb1_tag   <= tag_lsu;
      cdb1_data  <= data_lsu;
      grant_lsu  <= '1';

      -- Route second priority to CDB2
      if (req_alu1 = '1') then
        cdb2_valid <= '1';
        cdb2_tag   <= tag_alu1;
        cdb2_data  <= data_alu1;
        grant_alu1 <= '1';
      -- ALU2 gets denied this cycle if all 3 request
      elsif (req_alu2 = '1') then
        cdb2_valid <= '1';
        cdb2_tag   <= tag_alu2;
        cdb2_data  <= data_alu2;
        grant_alu2 <= '1';
      end if;

    -- Priority 2 & 3: ALU1 and ALU2 (No LSU request)
    else
      if (req_alu1 = '1') then
        cdb1_valid <= '1';
        cdb1_tag   <= tag_alu1;
        cdb1_data  <= data_alu1;
        grant_alu1 <= '1';

        if (req_alu2 = '1') then
          cdb2_valid <= '1';
          cdb2_tag   <= tag_alu2;
          cdb2_data  <= data_alu2;
          grant_alu2 <= '1';
        end if;
      elsif (req_alu2 = '1') then
        -- Only ALU2 requested
        cdb1_valid <= '1';
        cdb1_tag   <= tag_alu2;
        cdb1_data  <= data_alu2;
        grant_alu2 <= '1';
      end if;
    end if;

  end process;

end architecture behavioral;
