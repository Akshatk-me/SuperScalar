library ieee;
use ieee.std_logic_1164.all;

entity top is
    port (
        clk   : in std_logic;
        reset : in std_logic;

        -- debug / observation
        commit_valid : out std_logic;
        commit_reg   : out std_logic_vector(2 downto 0);
        commit_value : out std_logic_vector(15 downto 0);

        pc_out : out std_logic_vector(15 downto 0)
    );
end entity;

architecture rtl of top is
    signal pc : std_logic_vector(15 downto 0);
begin

    pc_inst: entity work.pc_unit
        port map (
            clk => clk,
            reset => reset,
            redirect_valid => '0',
            redirect_pc => (others => '0'),
            stall_fetch => '0',
            pc_out => pc,
            pc_next_out => open
        );

    pc_out <= pc;

end architecture;
