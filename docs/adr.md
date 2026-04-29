# Architecture Decision Record

## Sizing of ROB, PRFs

So going with PRF holds ARF as well, we'll need 8 (R0 to R7) + (CZ Flags) = 10 minimum

Now say memory latency is 10 cycles (due to whatever, in real systems cache miss or whatever), we'll have our fetch and decode stage actively writing to the ROB and PRF,
thus there'll be 10 \* 2 = 20 instructions that'll be fetched.

So having these 20 speculative instructions, we get Total PRF = 10 (Architectural) + 20 (speculative) = 30

Let's choose PRF size = 32 (now tag can be 5 bits long and efficiently used)

## RRAT construction

The RRAT Flattened Array: VHDL ports don't love custom 2D arrays unless you declare them in a separate package file. To make this file plug-and-play, I passed the RRAT state in as a flat 50-bit vector (rrat_state).

Prioritization Cascade (The If-Elsif): Look at the synchronous write block. It asks "Is Inst 2 writing to this register?" first. If yes, it assigns alloc_phys_2. The elsif means Inst 1 is ignored for that specific register. This perfectly handles the collision.

The Intra-cycle Forwarding: Look at phys_rs1_2. It uses a when...else statement. This creates a combinatorial multiplexer in front of Instruction 2. If it detects a hazard with Instruction 1, the multiplexer routes the new allocation to Instruction 2 instantly.
