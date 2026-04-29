library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

entity reorder_buffer is
  port (
    clk : in    std_logic;
    rst : in    std_logic;

    -- ==========================================
    -- DISPATCH INTERFACE (In-Order Allocation)
    -- ==========================================
    disp_en_1   : in    std_logic;
    disp_we_1   : in    std_logic;                    -- Does Inst 1 write a register?
    disp_arch_1 : in    std_logic_vector(3 downto 0); -- Dest R0-R7, C, Z
    disp_phys_1 : in    std_logic_vector(4 downto 0);

    disp_en_2   : in    std_logic;
    disp_we_2   : in    std_logic;
    disp_arch_2 : in    std_logic_vector(3 downto 0);
    disp_phys_2 : in    std_logic_vector(4 downto 0);

    rob_full : out   std_logic;

    -- ==========================================
    -- COMPLETION INTERFACE (Out-of-Order Snooping)
    -- ==========================================
    cdb1_valid : in    std_logic;
    cdb1_tag   : in    std_logic_vector(4 downto 0);

    cdb2_valid : in    std_logic;
    cdb2_tag   : in    std_logic_vector(4 downto 0);

    -- ==========================================
    -- COMMIT INTERFACE (In-Order Retirement)
    -- ==========================================
    commit_valid_1 : out   std_logic;
    commit_we_1    : out   std_logic;
    commit_arch_1  : out   std_logic_vector(3 downto 0);
    commit_phys_1  : out   std_logic_vector(4 downto 0);

    commit_valid_2 : out   std_logic;
    commit_we_2    : out   std_logic;
    commit_arch_2  : out   std_logic_vector(3 downto 0);
    commit_phys_2  : out   std_logic_vector(4 downto 0);

    -- ==========================================
    -- EXCEPTION / BRANCH RECOVERY
    -- ==========================================
    branch_flush : in    std_logic;

    -- Temporary Debug ports
    -- Add these to entity for debugging:
    debug_head_valid  : out   std_logic;
    debug_head_ready  : out   std_logic;
    debug_head1_valid : out   std_logic;
    debug_head1_ready : out   std_logic;
    -- Add to entity ports
    debug_head : out   std_logic_vector(3 downto 0);
    debug_tail : out   std_logic_vector(3 downto 0)
  );
end entity reorder_buffer;

architecture behavioral of reorder_buffer is

  -- Define a record for a single ROB entry

  type rob_entry is record
    valid     : std_logic;
    ready     : std_logic; -- '1' when execution is finished
    we        : std_logic;
    arch_dest : std_logic_vector(3 downto 0);
    phys_dest : std_logic_vector(4 downto 0);
  end record rob_entry;

  -- Array of 16 entries

  type rob_array is array (0 to 15) of rob_entry;

  signal rob : rob_array;

  -- Pointers for the circular queue
  signal head : unsigned(3 downto 0);
  signal tail : unsigned(3 downto 0);

  -- Helper signals for capacity tracking
  signal count : integer range 0 to 16;

  -- Interal signals for the output commit_valid signals
  signal commit_valid_1_int : std_logic;
  signal commit_valid_2_int : std_logic;

begin

  debug_head_valid  <= rob(to_integer(head)).valid;
  debug_head_ready  <= rob(to_integer(head)).ready;
  debug_head1_valid <= rob(to_integer(head + 1)).valid;
  debug_head1_ready <= rob(to_integer(head + 1)).ready;
  debug_head        <= std_logic_vector(head);
  debug_tail        <= std_logic_vector(tail);

  -- Output the full status (stall the front-end if we have < 2 slots left)
  rob_full <= '1' when count >= 15 else
              '0';

  -- Calculate internal signals (same logic as before)
  commit_valid_1_int <= '1' when (rob(to_integer(head)).valid = '1' and
                                   rob(to_integer(head)).ready = '1') else
                        '0';

  commit_valid_2_int <= '1' when (rob(to_integer(head)).valid = '1' and
                                   rob(to_integer(head)).ready = '1' and
                                   rob(to_integer(head + 1)).valid = '1' and
                                   rob(to_integer(head + 1)).ready = '1') else
                        '0';

  -- Drive outputs from internal signals
  commit_valid_1 <= commit_valid_1_int;
  commit_valid_2 <= commit_valid_2_int;

  -- ==========================================
  -- ASYNCHRONOUS COMMIT LOGIC (Read from Head)
  -- ==========================================
  -- Instruction 1 commits if the head is valid and ready

  commit_we_1   <= rob(to_integer(head)).we;
  commit_arch_1 <= rob(to_integer(head)).arch_dest;
  commit_phys_1 <= rob(to_integer(head)).phys_dest;

  -- Instruction 2 commits ONLY IF Instruction 1 is committing AND the next entry is also ready
  commit_we_2   <= rob(to_integer(head + 1)).we;
  commit_arch_2 <= rob(to_integer(head + 1)).arch_dest;
  commit_phys_2 <= rob(to_integer(head + 1)).phys_dest;

  -- ==========================================
  -- SYNCHRONOUS PROCESS (Dispatch, Complete, Flush)
  -- ==========================================
  process (clk) is

    variable next_head  : unsigned(3 downto 0);
    variable next_tail  : unsigned(3 downto 0);
    variable next_count : integer range -2 to 18;

  begin

    if rising_edge(clk) then
      if (rst = '1') then
        head  <= (others => '0');
        tail  <= (others => '0');
        count <= 0;

        for i in 0 to 15 loop

          rob(i).valid <= '0';
          rob(i).ready <= '0';

        end loop;

      elsif (branch_flush = '1') then
        -- On a mispredict, we wipe out all speculative instructions.
        -- Setting tail = head instantly empties the queue.
        tail  <= head;
        count <= 0;

        for i in 0 to 15 loop

          rob(i).valid <= '0';

        end loop;

      else
        next_head  := head;
        next_tail  := tail;
        next_count := count;

        -- 1. COMMIT (Pop from Head)
        if (commit_valid_1_int = '1' and commit_valid_2_int = '1') then
          rob(to_integer(next_head)).valid     <= '0';
          rob(to_integer(next_head + 1)).valid <= '0';
          next_head                            := next_head + 2;
          next_count                           := next_count - 2;
        elsif (commit_valid_1_int = '1') then
          rob(to_integer(next_head)).valid <= '0';
          next_head                        := next_head + 1;
          next_count                       := next_count - 1;
        end if;

        -- 2. DISPATCH (Push to Tail)
        if (disp_en_1 = '1' and disp_en_2 = '1') then
          rob(to_integer(next_tail)).valid     <= '1';
          rob(to_integer(next_tail)).ready     <= not disp_we_1; -- Auto-ready if it doesn't write anything
          rob(to_integer(next_tail)).we        <= disp_we_1;
          rob(to_integer(next_tail)).arch_dest <= disp_arch_1;
          rob(to_integer(next_tail)).phys_dest <= disp_phys_1;

          rob(to_integer(next_tail + 1)).valid     <= '1';
          rob(to_integer(next_tail + 1)).ready     <= not disp_we_2;
          rob(to_integer(next_tail + 1)).we        <= disp_we_2;
          rob(to_integer(next_tail + 1)).arch_dest <= disp_arch_2;
          rob(to_integer(next_tail + 1)).phys_dest <= disp_phys_2;

          next_tail  := next_tail + 2;
          next_count := next_count + 2;
        elsif (disp_en_1 = '1') then
          rob(to_integer(next_tail)).valid     <= '1';
          rob(to_integer(next_tail)).ready     <= not disp_we_1;
          rob(to_integer(next_tail)).we        <= disp_we_1;
          rob(to_integer(next_tail)).arch_dest <= disp_arch_1;
          rob(to_integer(next_tail)).phys_dest <= disp_phys_1;

          next_tail  := next_tail + 1;
          next_count := next_count + 1;
        end if;

        -- 3. COMPLETION (Snoop the CDB out-of-order)
        -- We loop through the whole ROB to find the matching physical tag
        for i in 0 to 15 loop

          if (rob(i).valid = '1' and rob(i).we = '1' and rob(i).ready = '0') then
            if ((cdb1_valid = '1' and cdb1_tag = rob(i).phys_dest) or
                (cdb2_valid = '1' and cdb2_tag = rob(i).phys_dest)) then
              report "Marking entry " & integer'image(i) & " ready"
                severity note;
              rob(i).ready <= '1';
            end if;
          end if;

        end loop;

        -- Update pointers
        head  <= next_head;
        tail  <= next_tail;
        count <= next_count;
      end if;
    end if;

  end process;

end architecture behavioral;
