library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity regfile is
    port (
        clk : in std_logic;

        -- Reads
        raddr1, raddr2, raddr3, raddr4 : in std_logic_vector(2 downto 0);
        rdata1, rdata2, rdata3, rdata4 : out std_logic_vector(15 downto 0);

        -- Writes
        we1, we2       : in std_logic;
        waddr1, waddr2 : in std_logic_vector(2 downto 0);
        wdata1, wdata2 : in std_logic_vector(15 downto 0);

        -- PC input
        pc_value : in std_logic_vector(15 downto 0)
    );
end entity;

architecture rtl of regfile is

    type reg_file_t is array (1 to 7) of std_logic_vector(15 downto 0);
    signal rf : reg_file_t := (others => (others => '0'));

    function read_port(
        raddr : std_logic_vector(2 downto 0)
    ) return std_logic_vector is
    begin
        if raddr = "000" then
            return pc_value;

        elsif (we2 = '1' and waddr2 = raddr) then
            return wdata2;

        elsif (we1 = '1' and waddr1 = raddr) then
            return wdata1;

        else
            return rf(to_integer(unsigned(raddr)));
        end if;
    end function;

begin

    -- Write logic
    process(clk)
    begin
        if rising_edge(clk) then

            if we1 = '1' and waddr1 /= "000" then
                rf(to_integer(unsigned(waddr1))) <= wdata1;
            end if;

            if we2 = '1' and waddr2 /= "000" then
                rf(to_integer(unsigned(waddr2))) <= wdata2;
            end if;

        end if;
    end process;

    -- Read ports
    rdata1 <= read_port(raddr1);
    rdata2 <= read_port(raddr2);
    rdata3 <= read_port(raddr3);
    rdata4 <= read_port(raddr4);

end architecture;
