library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

entity free_list is
  port (
    clk : in    std_logic;
    rst : in    std_logic;

    -- ==========================================
    -- ALLOCATION (Pops from the queue to the RAT)
    -- ==========================================
    req_1 : in    std_logic; -- Instruction 1 needs a register
    req_2 : in    std_logic; -- Instruction 2 needs a register

    alloc_phys_1 : out   std_logic_vector(4 downto 0);
    alloc_phys_2 : out   std_logic_vector(4 downto 0);

    empty : out   std_logic; -- Stall fetch/decode if no registers available

    -- ==========================================
    -- FREED REGISTERS (Pushes from the RRAT/Commit)
    -- ==========================================
    free_en_1   : in    std_logic;
    free_phys_1 : in    std_logic_vector(4 downto 0);

    free_en_2   : in    std_logic;
    free_phys_2 : in    std_logic_vector(4 downto 0);

    -- ==========================================
    -- BRANCH RECOVERY
    -- ==========================================
    -- In a real processor, you take a snapshot of the read pointer
    -- when a branch is dispatched. If it mispredicts, you restore it.
    recover_en  : in    std_logic;
    recover_ptr : in    std_logic_vector(4 downto 0)
  );
end entity free_list;

architecture behavioral of free_list is

  type fifo_array is array (0 to 31) of std_logic_vector(4 downto 0);

  signal queue : fifo_array;

  -- 5-bit pointers for a 32-entry circular buffer
  signal head_ptr : unsigned(4 downto 0);
  signal tail_ptr : unsigned(4 downto 0);

begin

  -- Asynchronous read logic for allocation
  -- Head pointer gives the first available, Head + 1 gives the second.
  alloc_phys_1 <= queue(to_integer(head_ptr));
  alloc_phys_2 <= queue(to_integer(head_ptr + 1));

  -- Basic empty logic (can be refined to check for exactly 0 or 1 left)
  empty <= '1' when head_ptr = tail_ptr else
           '0';

  process (clk) is

    variable next_head : unsigned(4 downto 0);
    variable next_tail : unsigned(4 downto 0);

  begin

    if rising_edge(clk) then
      if (rst = '1') then
        -- INITIAL STATE:
        -- R0-R7, C, and Z take up Physical Registers 0 through 9.
        -- Therefore, the Free List starts with P10 through P31.
        for i in 0 to 21 loop

          queue(i) <= std_logic_vector(to_unsigned(i + 10, 5));

        end loop;

        head_ptr <= to_unsigned(0, 5);
        tail_ptr <= to_unsigned(22, 5); -- Next write goes to index 22
      elsif (recover_en = '1') then
        -- On branch mispredict, we revert the head pointer back to the snapshot.
        -- The tail pointer remains where it is (freed registers are still free).
        head_ptr <= unsigned(recover_ptr);
      else
        next_head := head_ptr;
        next_tail := tail_ptr;

        -- 1. Handle Pops (Allocations)
        if (req_1 = '1' and req_2 = '1') then
          next_head := next_head + 2;
        elsif (req_1 = '1' or req_2 = '1') then
          next_head := next_head + 1;
        end if;

        -- 2. Handle Pushes (Freed from RRAT)
        if (free_en_1 = '1' and free_en_2 = '1') then
          queue(to_integer(next_tail))     <= free_phys_1;
          queue(to_integer(next_tail + 1)) <= free_phys_2;
          next_tail                        := next_tail + 2;
        elsif (free_en_1 = '1') then
          queue(to_integer(next_tail)) <= free_phys_1;
          next_tail                    := next_tail + 1;
        elsif (free_en_2 = '1') then
          queue(to_integer(next_tail)) <= free_phys_2;
          next_tail                    := next_tail + 1;
        end if;

        head_ptr <= next_head;
        tail_ptr <= next_tail;
      end if;
    end if;

  end process;

end architecture behavioral;
