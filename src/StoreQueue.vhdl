library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

entity store_queue is
  port (
    clk : in    std_logic;
    rst : in    std_logic;

    -- ==========================================
    -- DISPATCH (In-Order Allocation from Decode/Rename)
    -- ==========================================
    alloc_en : in    std_logic;
    sq_full  : out   std_logic;

    -- ==========================================
    -- EXECUTION (Address & Data arrive out-of-order)
    -- ==========================================
    -- From the Address Generation Unit (AGU)
    agu_valid  : in    std_logic;
    agu_sq_idx : in    std_logic_vector(2 downto 0); -- Which SQ entry?
    agu_addr   : in    std_logic_vector(15 downto 0);

    -- From the Common Data Bus (CDB - Data to be stored)
    data_valid  : in    std_logic;
    data_sq_idx : in    std_logic_vector(2 downto 0);
    data_val    : in    std_logic_vector(15 downto 0);

    -- ==========================================
    -- STORE-TO-LOAD FORWARDING (Snooped by Loads)
    -- ==========================================
    load_req_valid : in    std_logic;
    load_req_addr  : in    std_logic_vector(15 downto 0);

    forward_hit  : out   std_logic;
    forward_data : out   std_logic_vector(15 downto 0);

    -- ==========================================
    -- COMMIT (In-Order Write to Actual Data Memory)
    -- ==========================================
    commit_en : in    std_logic; -- Fired by the ROB

    mem_write_en   : out   std_logic;
    mem_write_addr : out   std_logic_vector(15 downto 0);
    mem_write_data : out   std_logic_vector(15 downto 0);

    -- ==========================================
    -- BRANCH RECOVERY
    -- ==========================================
    branch_flush : in    std_logic
  );
end entity store_queue;

architecture behavioral of store_queue is

  -- 8-entry Store Queue

  type sq_entry is record
    valid      : std_logic;
    addr_ready : std_logic;
    data_ready : std_logic;
    addr       : std_logic_vector(15 downto 0);
    data       : std_logic_vector(15 downto 0);
  end record sq_entry;

  type sq_array is array (0 to 7) of sq_entry;

  signal sq : sq_array;

  signal head  : unsigned(2 downto 0);
  signal tail  : unsigned(2 downto 0);
  signal count : integer range 0 to 8;

begin

  sq_full <= '1' when count >= 7 else
             '0';

  -- ==========================================
  -- STORE-TO-LOAD FORWARDING LOGIC (Combinational CAM)
  -- ==========================================
  process (load_req_valid, load_req_addr, sq) is

    variable match_found : boolean;
    variable match_data  : std_logic_vector(15 downto 0);

  begin

    forward_hit  <= '0';
    forward_data <= (others => '0');
    match_found  := false;

    if (load_req_valid = '1') then
      -- Search the queue. In a real superscalar, we search from youngest to oldest.
      -- For simplicity, we check all valid entries with ready addresses and data.
      for i in 0 to 7 loop

        if (sq(i).valid = '1' and sq(i).addr_ready = '1' and sq(i).data_ready = '1') then
          if (sq(i).addr = load_req_addr) then
            match_found := true;
            match_data  := sq(i).data;
          end if;
        end if;

      end loop;

      if (match_found) then
        forward_hit  <= '1';
        forward_data <= match_data;
      end if;
    end if;

  end process;

  -- ==========================================
  -- COMMIT TO DATA MEMORY (Combinational output from Head)
  -- ==========================================
  mem_write_en   <= '1' when (commit_en = '1' and sq(to_integer(head)).valid = '1' and sq(to_integer(head)).addr_ready = '1' and sq(to_integer(head)).data_ready = '1') else
                    '0';
  mem_write_addr <= sq(to_integer(head)).addr;
  mem_write_data <= sq(to_integer(head)).data;

  -- ==========================================
  -- SYNCHRONOUS UPDATES (Dispatch, Execute, Flush, Commit)
  -- ==========================================
  process (clk) is

    variable next_tail  : unsigned(2 downto 0);
    variable next_head  : unsigned(2 downto 0);
    variable next_count : integer range -1 to 9;

  begin

    if rising_edge(clk) then
      if (rst = '1' or branch_flush = '1') then
        -- On mispredict, flush the whole speculative SQ
        head  <= (others => '0');
        tail  <= (others => '0');
        count <= 0;

        for i in 0 to 7 loop

          sq(i).valid <= '0';

        end loop;

      else
        next_tail  := tail;
        next_head  := head;
        next_count := count;

        -- 1. COMMIT (Pop from Head to Memory)
        if (commit_en = '1' and sq(to_integer(next_head)).valid = '1') then
          sq(to_integer(next_head)).valid <= '0';
          next_head                       := next_head + 1;
          next_count                      := next_count - 1;
        end if;

        -- 2. DISPATCH (Allocate at Tail)
        if (alloc_en = '1') then
          sq(to_integer(next_tail)).valid      <= '1';
          sq(to_integer(next_tail)).addr_ready <= '0';
          sq(to_integer(next_tail)).data_ready <= '0';
          next_tail                            := next_tail + 1;
          next_count                           := next_count + 1;
        end if;

        -- 3. EXECUTE: Address Calculation arrives
        if (agu_valid = '1') then
          sq(to_integer(unsigned(agu_sq_idx))).addr       <= agu_addr;
          sq(to_integer(unsigned(agu_sq_idx))).addr_ready <= '1';
        end if;

        -- 4. EXECUTE: Store Data arrives from CDB
        if (data_valid = '1') then
          sq(to_integer(unsigned(data_sq_idx))).data       <= data_val;
          sq(to_integer(unsigned(data_sq_idx))).data_ready <= '1';
        end if;

        head  <= next_head;
        tail  <= next_tail;
        count <= next_count;
      end if;
    end if;

  end process;

end architecture behavioral;
