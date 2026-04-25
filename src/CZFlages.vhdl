library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity Condition_Code_Register is
    Port (
        clk      : in  STD_LOGIC;
        reset    : in  STD_LOGIC;
        
        -- Raw flags coming from the ALU
        C_in     : in  STD_LOGIC;
        Z_in     : in  STD_LOGIC;
        
        -- Control signals from the Decode Stage
        Update_C : in  STD_LOGIC;
        Update_Z : in  STD_LOGIC;
        
        -- Saved flags going to the ALU and Control Logic
        C_out    : out STD_LOGIC;
        Z_out    : out STD_LOGIC
    );
end Condition_Code_Register;

architecture Behavioral of Condition_Code_Register is
    signal reg_C : STD_LOGIC := '0';
    signal reg_Z : STD_LOGIC := '0';
begin
    process(clk, reset)
    begin
        if reset = '1' then
            reg_C <= '0';
            reg_Z <= '0';
        elsif rising_edge(clk) then
            if Update_C = '1' then
                reg_C <= C_in;
            end if;
            if Update_Z = '1' then
                reg_Z <= Z_in;
            end if;
        end if;
    end process;

    C_out <= reg_C;
    Z_out <= reg_Z;
end Behavioral;
