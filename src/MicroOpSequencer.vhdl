library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

entity micro_op_sequencer is
  port (
    clk : in    std_logic;
    rst : in    std_logic;

    -- ==========================================
    -- INPUTS FROM DECODER
    -- ==========================================
    is_complex_mem : in    std_logic;
    base_addr_in   : in    std_logic_vector(15 downto 0); -- The actual value of RA from PRF
    bitmap_in      : in    std_logic_vector(7 downto 0);  -- Imm8 field indicating R0-R7
    is_store       : in    std_logic;                     -- '1' for SM, '0' for LM

    -- ==========================================
    -- OUTPUTS TO FRONT-END & DISPATCH
    -- ==========================================
    stall_fetch : out   std_logic;

    uop_valid    : out   std_logic;
    uop_is_store : out   std_logic;
    uop_reg_idx  : out   std_logic_vector(2 downto 0); -- Which register to load/store
    uop_mem_addr : out   std_logic_vector(15 downto 0) -- The calculated memory address
  );
end entity micro_op_sequencer;

architecture behavioral of micro_op_sequencer is

  type state_type is (idle, cracking, done);

  signal state : state_type;

  -- Latched state
  signal latched_bitmap : std_logic_vector(7 downto 0);
  signal current_addr   : unsigned(15 downto 0);

  -- The Direct Index Counter (0 to 7)
  signal current_reg_idx : unsigned(2 downto 0);

  -- Helper flag to track bits processed (for early exit)
  signal bits_remaining : std_logic_vector(7 downto 0);

begin

  process (clk) is
  begin

    if rising_edge(clk) then
      if (rst = '1') then
        state       <= idle;
        stall_fetch <= '0';
        uop_valid   <= '0';
      else

        case state is

          when idle =>

            uop_valid <= '0';
            if (is_complex_mem = '1') then
              stall_fetch <= '1';

              -- Latch the incoming data
              latched_bitmap <= bitmap_in;
              bits_remaining <= bitmap_in;
              current_addr   <= unsigned(base_addr_in);

              -- Start our direct index at Register 0
              current_reg_idx <= "000";
              state           <= cracking;
            else
              stall_fetch <= '0';
            end if;

          when cracking =>

            -- EARLY EXIT: If no more bits are set in the remaining tracker, we are done!
            if (bits_remaining = "00000000") then
              uop_valid <= '0';
              state     <= done;
            else
              -- DIRECT INDEXING: Check the exact bit for the current register
              -- Note: If ISA says "R0 is left-most bit", then R0 is bit 7.
              -- If ISA says "R0 is right-most bit", then R0 is bit 0.
              -- Assuming standard Right-to-Left (Bit 0 = R0, Bit 7 = R7):

              if (latched_bitmap(to_integer(current_reg_idx)) = '1') then
                -- Output valid micro-op
                uop_valid    <= '1';
                uop_is_store <= is_store;
                uop_reg_idx  <= std_logic_vector(current_reg_idx);
                uop_mem_addr <= std_logic_vector(current_addr);

                -- Increment memory address by 2 for the next operation
                current_addr <= current_addr + 2;
              else
                -- Bit is '0', so skip this register. No valid micro-op this cycle.
                uop_valid <= '0';
              end if;

              -- Clear the bit we just checked in our "remaining" tracker
              -- This allows the "EARLY EXIT" condition to trigger faster
              bits_remaining(to_integer(current_reg_idx)) <= '0';

              -- Move to the next register index
              -- If we hit 7, the next increment naturally wraps to 0, but bits_remaining will be 00000000 anyway
              current_reg_idx <= current_reg_idx + 1;
            end if;

          when done =>

            -- De-assert everything and let the Front-End wake up
            uop_valid   <= '0';
            stall_fetch <= '0';
            state       <= idle;

        end case;

      end if;
    end if;

  end process;

end architecture behavioral;
