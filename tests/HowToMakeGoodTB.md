# Core principle (keep this in your head)

> A testbench is a **model of time + interactions**, not just input/output checks.

If you get this right, everything else becomes simpler.

---

# The minimal “good” structure

Don’t overcomplicate. Stick to this:

```text
ClockedTB        → owns time
Interface        → knows how to talk to DUT
Model            → defines correct behavior
Test             → drives scenarios + checks
```

That’s it. No need to jump into full driver/monitor/scoreboard separation unless complexity demands it.

---

# 1. Always start with a ClockedTB (non-negotiable)

This is your foundation.

```python
class ClockedTB:
    async def start()
    async def reset()
    async def tick()
```

### Rules:

- ALL time advances go through `tick()`
- Never sprinkle `RisingEdge` everywhere randomly
- Never mix time control across files

---

# 2. Build an Interface (this encodes timing semantics)

This is where most people mess up.

Your interface should answer:

> “How is this hardware _meant to be used over time_?”

Example pattern:

```python
class ModuleInterface:
    async def write(...)   # consumes 1 cycle
    async def read(...)    # same cycle (combinational)
```

---

### Golden rule:

Inside interface methods:

| Operation type | What to use        |
| -------------- | ------------------ |
| sequential     | `await tb.tick()`  |
| combinational  | `await Timer(...)` |

Never mix both casually.

---

# 3. Golden Model = pure logic (no timing)

```python
class Model:
    def update(...)
    def predict(...)
```

### Rules:

- No `await`
- No DUT access
- No timing assumptions

This is your **truth oracle**

---

# 4. Test = cycle-driven loop

Structure ALL tests like this:

```python
for cycle in range(N):

    # choose operation
    if condition:
        await interface.write(...)
        model.update(...)

    else:
        obs = await interface.read(...)
        gold = model.predict(...)

        assert obs == gold

        await tb.tick()
```

---

# 5. The “cycle contract” (this is the most important habit)

Every operation must clearly answer:

| Question                 | Answer            |
| ------------------------ | ----------------- |
| When are inputs sampled? | before clock edge |
| When is state updated?   | on clock edge     |
| When are outputs valid?  | after settle      |

If you can’t answer this → your TB will become unstable later.

---

# 6. When to add more structure

Don’t jump to driver/monitor/scoreboard unless:

- you have **multiple concurrent agents**
- you need **parallel stimulus**
- you’re testing **full pipeline behavior**

For your current stage:

> Interface + Model + Loop is perfect

---

# 7. Common mistakes (avoid these)

### ❌ Mixing phases

```python
await ReadOnly()
dut.signal.value = ...
```

### ❌ Random timing hacks

```python
await Timer(5, "ns")  # why 5?
```

### ❌ Calling DUT like a function

```python
write()
read()
```

(with no cycle separation)

---

# 8. Simple mental checklist (before writing TB)

Ask:

1. Is this signal **clocked or combinational?**
2. When does the DUT **observe inputs?**
3. When does it **produce outputs?**
4. Do I need **one cycle or same-cycle response?**

If you answer these → your TB will be correct.

---

# 9. How this scales to your project

### BTB (what you just did)

- write → 1 cycle
- read → combinational

---

### ROB (next level)

- dispatch → 1 cycle
- commit → 1 cycle later
- need ordering checks

---

### Pipeline

- instruction flows across multiple cycles
- you track state across time

---

# 10. A reusable template you can copy

```python
@cocotb.test()
async def test_template(dut):

    tb = ClockedTB(dut)
    await tb.start()
    await tb.reset()

    iface = ModuleInterface(tb)
    model = Model()

    for cycle in range(500):

        op = random.choice(["write", "read"])

        if op == "write":
            inp = ...
            await iface.write(inp)
            model.update(inp)

        else:
            inp = ...
            out = await iface.read(inp)
            gold = model.predict(inp)

            assert out == gold

            await tb.tick()
```

---

# 11. Philosophy (this will save you later)

Don’t try to make the TB:

- “smart”
- “clever”
- “fully abstract”

Make it:

- **predictable**
- **cycle-accurate**
- **easy to reason about**
