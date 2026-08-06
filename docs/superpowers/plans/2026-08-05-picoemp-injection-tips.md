# PicoEMP Injection Tips Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build five EM injection tips and determine, with evidence, which of them can inject a fault into a live target.

**Architecture:** A spare Pico runs a self-checking loop and prints one line per block; a host-side analyser turns a captured log into a fault count. Tips are five off-the-shelf ferrite inductors on SMA plugs, four of them forming a diameter sweep at constant inductance so a difference in fault rate is attributable to core size alone. A baseline run with the board charged but not pulsing gates everything downstream.

**Tech Stack:** MicroPython on RP2040; `mpremote` over USB CDC; pytest for the analyser and the target's expected-value constant.

## Global Constraints

- **Spec:** `docs/superpowers/specs/2026-08-05-picoemp-injection-tips-design.md`. Section references are to it.
- **The target must be a spare Pico**, not the PicoEMP's own, and not one that matters. Flash corruption is a plausible outcome.
- **Insulate every tip face with Kapton.** With a coil fitted the SMA shell sits at essentially the full rail relative to `HV_RTN` — 261 V of floating metal that must not rest on target pins.
- **Keep the host laptop and both USB cables away from the tip.** The pulse can reset or corrupt the PicoEMP's own Pico.
- All Phase 3 bring-up rules still apply: shield in place, SW3 before contact, hands clear of J1.
- **Python via `uv` only** (`uv run --with pytest pytest`). Never bare `pip`.
- Charge PWM stays at **2500 Hz, `duty_u16(800)`**. Do not retune.

## Deviation from the spec

§3 of the spec says 3–4 tips. **This plan builds five.** A second distributor
search surfaced two more in-stock 10 µH parts at 8.5 mm and 10.0 mm, which
turns two scattered diameter points into a four-point sweep at constant
inductance — a better-sampled experiment for about $1.40 more. Build effort is
held near the spec's number by assembling the four sweep tips first and keeping
the fifth in reserve (Task 5).

## Parts

Inductors — all unshielded, through-hole, radial drum core:

| Role | MPN | Dia | L | I peak | t to peak | $1 | Stock |
|---|---|---|---|---|---|---|---|
| Sweep A | `7447462100` | 6.0 mm | 10 µH | 57 A | 3.4 µs | 0.90 | 672 |
| Sweep B | `744772100` | 7.8 mm | 10 µH | 57 A | 3.4 µs | 0.97 | 3063 |
| Sweep C | `DRC-0707-100K-UL` | 8.5 mm | 10 µH | 57 A | 3.4 µs | 0.70 | 566 |
| Sweep D | `DRC-0807-100K-UL` | 10.0 mm | 10 µH | 57 A | 3.4 µs | 0.70 | 463 |
| Reserve | `7447462022` | 6.0 mm | 2.2 µH | 121 A | 1.6 µs | 0.90 | 197 |

Currents are `V·√(C/L)` and times `(π/2)·√(LC)` with C = 0.47 µF and V = 261 V.

Connectors: **5 × Taoglas `EMPCB.SMAMST.A`**, SMA plug male, board edge, end
launch, $3.26 at qty 10.

Total about $20.

## File Structure

| File | Responsibility |
|---|---|
| `firmware/micropython/glitch_target.py` | Target: self-checking loop, one line per block. No GPIO — pure compute and print. |
| `hardware/rev2026/tools/analyze_glitch_log.py` | Host: turn a captured log into block/fault counts. |
| `hardware/rev2026/tests/test_glitch_target.py` | Host tests for both of the above. |
| `hardware/rev2026/TIP-LOG.md` | Results: baseline, per-tip fault rates, ranking. |

`glitch_target.py` deliberately imports nothing from `machine`, so its
computation is importable and testable on CPython.

---

### Task 1: The target's self-checking loop

**Files:**
- Create: `firmware/micropython/glitch_target.py`
- Create: `hardware/rev2026/tests/test_glitch_target.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `glitch_target.py` exposing `BLOCK_N` (int), `EXPECTED` (int), `compute_block()` returning int, and `format_line(seq, acc)` returning a string. Task 2's analyser parses the exact format `format_line` emits.

- [ ] **Step 1: Write the failing tests**

Create `hardware/rev2026/tests/test_glitch_target.py`:

```python
"""Host-side checks on the glitch target.

The load-bearing test is that EXPECTED actually equals what compute_block()
returns. If that constant were wrong, every block would report a fault, the
baseline control in Task 5 would be nonzero, and the whole experiment would
be measuring a typo. glitch_target.py imports nothing from `machine`
precisely so this can run on CPython.
"""

import importlib.util
import sys

import conftest

REPO = conftest.ROOT.parents[1]
TARGET = REPO / 'firmware' / 'micropython' / 'glitch_target.py'


def _load():
    spec = importlib.util.spec_from_file_location('glitch_target', TARGET)
    mod = importlib.util.module_from_spec(spec)
    sys.modules['glitch_target'] = mod
    spec.loader.exec_module(mod)
    return mod


def test_expected_matches_the_computation():
    """The constant the target compares against is the value it computes."""
    gt = _load()
    assert gt.compute_block() == gt.EXPECTED


def test_block_is_large_enough_to_be_hit():
    """The vulnerable window must be wide enough for an untriggered pulse.

    A block of a few hundred iterations would complete in microseconds and a
    hand-pressed pulse would essentially never land inside it. See spec
    section 4 -- skipping the trigger is only justified by a wide window.
    """
    gt = _load()
    assert gt.BLOCK_N >= 10000, \
        f'BLOCK_N = {gt.BLOCK_N} is too small for untriggered pulsing'


def test_line_format_is_parseable():
    """format_line emits exactly what the analyser expects."""
    gt = _load()
    assert gt.format_line(7, 12345) == 'SEQ 7 ACC 12345'


def test_target_uses_no_gpio():
    """The target must not touch hardware -- it has to run on CPython too."""
    source = TARGET.read_text()
    assert 'import machine' not in source
    assert 'from machine' not in source
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd hardware/rev2026 && uv run --with pytest pytest tests/test_glitch_target.py -v
```

Expected: all four FAIL — `glitch_target.py` does not exist, so `_load()` raises `FileNotFoundError`.

- [ ] **Step 3: Write `firmware/micropython/glitch_target.py`**

```python
# PicoEMP glitch target -- a Pico that reports on its own corruption.
#
# Runs a deterministic block of work, checks the result, and prints one line
# per block. A line whose ACC differs from EXPECTED is a data fault. If the
# capture stops, the target reset.
#
# Imports nothing from `machine` on purpose: the computation must be
# importable on CPython so tests/test_glitch_target.py can verify EXPECTED.
#
# Run with:  mpremote connect <port> run glitch_target.py
#
# THIS BOARD WILL BE DELIBERATELY GLITCHED. Use a spare Pico. Flash
# corruption is a plausible outcome.

BLOCK_N = 100000
EXPECTED = BLOCK_N


def compute_block():
    """Count to BLOCK_N the slow way.

    Deliberately the simplest possible loop. A fault that skips, repeats or
    corrupts one iteration shows up directly in the total, with nothing else
    going on to confuse the attribution.
    """
    acc = 0
    for _ in range(BLOCK_N):
        acc += 1
    return acc


def format_line(seq, acc):
    return 'SEQ %d ACC %d' % (seq, acc)


def main():
    print('GLITCH TARGET BLOCK_N %d EXPECTED %d' % (BLOCK_N, EXPECTED))
    seq = 0
    while True:
        print(format_line(seq, compute_block()))
        seq += 1


if __name__ == '__main__':
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd hardware/rev2026 && uv run --with pytest pytest tests/test_glitch_target.py -v
```

Expected: four PASS.

- [ ] **Step 5: Time one block on the actual target**

Connect the **spare** Pico. Flash MicroPython on it if it is bare, exactly as in the bring-up plan Task 4 — `RPI_PICO` build for an RP2040, confirmed via `Board-ID` in `/Volumes/RPI-RP2/INFO_UF2.TXT`.

```bash
uv run --with mpremote mpremote connect <target-port> run firmware/micropython/glitch_target.py
```

Watch the rate of `SEQ` lines. **Aim for roughly one line per second.** If blocks are much faster than that the vulnerable window is narrow and pulses will mostly miss; much slower and each trial takes too long. Adjust `BLOCK_N` and update `EXPECTED` to match, then re-run Step 4 — the test will catch a mismatch.

This step also confirms the `__name__ == '__main__'` guard fires under `mpremote run`. If nothing prints, that is why; call `main()` unconditionally and re-run the tests.

- [ ] **Step 6: Commit**

```bash
git add firmware/micropython/glitch_target.py hardware/rev2026/tests/test_glitch_target.py
git commit -m "Glitch target: self-checking loop with a host-verified expected value"
```

---

### Task 2: The log analyser

**Files:**
- Create: `hardware/rev2026/tools/analyze_glitch_log.py`
- Modify: `hardware/rev2026/tests/test_glitch_target.py`

**Interfaces:**
- Consumes: the `SEQ <n> ACC <v>` format produced by `format_line` in Task 1.
- Produces: `analyze(text, expected)` returning a dict with keys `blocks` (int), `faults` (list of `(seq, acc)` tuples), `fault_rate` (float), `last_seq` (int or None), `malformed` (int).

- [ ] **Step 1: Write the failing tests**

Append to `hardware/rev2026/tests/test_glitch_target.py`:

```python
import importlib.util as _ilu

ANALYZER = conftest.ROOT / 'tools' / 'analyze_glitch_log.py'


def _load_analyzer():
    spec = _ilu.spec_from_file_location('analyze_glitch_log', ANALYZER)
    mod = _ilu.module_from_spec(spec)
    sys.modules['analyze_glitch_log'] = mod
    spec.loader.exec_module(mod)
    return mod


CLEAN_LOG = """GLITCH TARGET BLOCK_N 100000 EXPECTED 100000
SEQ 0 ACC 100000
SEQ 1 ACC 100000
SEQ 2 ACC 100000
"""

FAULTED_LOG = """GLITCH TARGET BLOCK_N 100000 EXPECTED 100000
SEQ 0 ACC 100000
SEQ 1 ACC 99999
SEQ 2 ACC 100000
SEQ 3 ACC 100002
"""


def test_clean_log_reports_no_faults():
    a = _load_analyzer().analyze(CLEAN_LOG, 100000)
    assert a['blocks'] == 3
    assert a['faults'] == []
    assert a['fault_rate'] == 0.0
    assert a['last_seq'] == 2


def test_faulted_log_reports_both_directions():
    """Both a low and a high ACC are faults -- a glitch can skip or repeat."""
    a = _load_analyzer().analyze(FAULTED_LOG, 100000)
    assert a['blocks'] == 4
    assert a['faults'] == [(1, 99999), (3, 100002)]
    assert a['fault_rate'] == 0.5


def test_truncated_final_line_is_counted_not_crashed():
    """A capture cut off mid-line must not look like a fault.

    The target is reset by design during these runs, so the last line of a
    real log is very often a partial one. Counting that as a corrupted
    result would manufacture faults out of the capture ending.
    """
    a = _load_analyzer().analyze(CLEAN_LOG + 'SEQ 3 AC', 100000)
    assert a['blocks'] == 3
    assert a['faults'] == []
    assert a['malformed'] == 1


def test_empty_log_is_not_a_division_by_zero():
    a = _load_analyzer().analyze('', 100000)
    assert a['blocks'] == 0
    assert a['fault_rate'] == 0.0
    assert a['last_seq'] is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd hardware/rev2026 && uv run --with pytest pytest tests/test_glitch_target.py -v
```

Expected: the four new tests FAIL with `FileNotFoundError`; Task 1's four still PASS.

- [ ] **Step 3: Write `hardware/rev2026/tools/analyze_glitch_log.py`**

```python
#!/usr/bin/env python3
"""Turn a captured glitch-target log into a fault count.

Usage:  uv run tools/analyze_glitch_log.py <logfile> [expected]

A fault is any block whose ACC differs from EXPECTED, in either direction --
a glitch can skip an iteration or repeat one. A truncated final line is
counted as malformed rather than as a fault: the target gets reset on purpose
during these runs, so real logs routinely end mid-line.
"""

import re
import sys

LINE = re.compile(r'^SEQ (\d+) ACC (\d+)$')
HEADER = re.compile(r'^GLITCH TARGET BLOCK_N (\d+) EXPECTED (\d+)$')


def analyze(text, expected):
    blocks = 0
    faults = []
    malformed = 0
    last_seq = None
    for line in text.splitlines():
        line = line.strip()
        if not line or HEADER.match(line):
            continue
        m = LINE.match(line)
        if not m:
            malformed += 1
            continue
        seq, acc = int(m.group(1)), int(m.group(2))
        blocks += 1
        last_seq = seq
        if acc != expected:
            faults.append((seq, acc))
    return {
        'blocks': blocks,
        'faults': faults,
        'fault_rate': (len(faults) / blocks) if blocks else 0.0,
        'last_seq': last_seq,
        'malformed': malformed,
    }


def main(argv):
    if not 2 <= len(argv) <= 3:
        print(__doc__.strip())
        return 2
    text = open(argv[1]).read()
    if len(argv) == 3:
        expected = int(argv[2])
    else:
        m = HEADER.search(text)
        if not m:
            print('No header line in log; pass expected explicitly.')
            return 2
        expected = int(m.group(2))
    a = analyze(text, expected)
    print('blocks     %d' % a['blocks'])
    print('faults     %d' % len(a['faults']))
    print('fault rate %.4f' % a['fault_rate'])
    print('last seq   %s' % a['last_seq'])
    print('malformed  %d' % a['malformed'])
    for seq, acc in a['faults']:
        print('  SEQ %d ACC %d (delta %+d)' % (seq, acc, acc - expected))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd hardware/rev2026 && uv run --with pytest pytest tests/test_glitch_target.py -v
```

Expected: eight PASS.

- [ ] **Step 5: Run the full suite**

```bash
cd hardware/rev2026 && uv run --with pytest pytest tests/
```

Expected: 77 pre-existing plus 8 new = 85 passing.

- [ ] **Step 6: Commit**

```bash
git add hardware/rev2026/tools/analyze_glitch_log.py hardware/rev2026/tests/test_glitch_target.py
git commit -m "Glitch log analyser, with truncated captures counted as malformed not faults"
```

---

### Task 3: Order parts

**Files:** none.

**Interfaces:**
- Produces: physical parts for Tasks 4 onward.

- [ ] **Step 1: Confirm the connector's board thickness**

Open the `EMPCB.SMAMST.A` datasheet from its DigiKey page and find the slot width. It must accept the FR4 scrap you intend to use — standard scrap is 1.6 mm and the equivalent Linx part is 0.062 in (1.57 mm), so this is very likely fine, but a mismatched slot means nothing seats and the whole order is wasted.

- [ ] **Step 2: Place the order**

Five inductors from the Parts table above, plus 5 × `EMPCB.SMAMST.A`. Order spares of at least the 6.0 mm parts — tips are consumables and several of these have long lead times behind thin stock.

- [ ] **Step 3: Note what arrived**

Some of these have low stock. If any part is unavailable at order time, record the substitute and its diameter and inductance — the sweep is only interpretable if the diameters are known and the inductance is genuinely constant across A–D.

---

### Task 4: Assemble the four sweep tips

**Files:**
- Create: `hardware/rev2026/TIP-LOG.md`

**Interfaces:**
- Consumes: parts from Task 3.
- Produces: four labelled tips, and `TIP-LOG.md` with a `## Tips` section that later tasks append results to.

- [ ] **Step 1: Cut four PCB scraps**

FR4 offcuts sized to seat in the connector's slot. They only need to carry two pads — one for the SMA centre pin, one for its ground tabs.

- [ ] **Step 2: Solder connector and inductor**

For each of tips A–D: solder the `EMPCB.SMAMST.A` to the scrap, then the inductor across centre-to-ground with **leads as short as they will go**. Loop area is series inductance, and series inductance is what you are trying to keep out of the measurement.

- [ ] **Step 3: Label each tip**

Physically mark each with its letter. Four visually similar tips whose whole purpose is being told apart is an obvious way to invalidate a day's results.

- [ ] **Step 4: Kapton the tip face**

Cover the coil face on every tip. With a coil fitted the coil is a DC short from `HV_RAIL` to `HV_OUT`, so the SMA shell and everything attached to it sits at essentially the full rail relative to `HV_RTN`. It is isolated from earth and will not shock you through the target, but it must not rest on exposed target pins.

- [ ] **Step 5: Create the log**

Create `hardware/rev2026/TIP-LOG.md`:

```markdown
# Injection Tip Results — PicoEMP Rev-2026 #1

Plan: `docs/superpowers/plans/2026-08-05-picoemp-injection-tips.md`
Spec: `docs/superpowers/specs/2026-08-05-picoemp-injection-tips-design.md`

Target: spare Pico, `firmware/micropython/glitch_target.py`, BLOCK_N = 100000

## Tips

| Tip | MPN | Dia | L | I peak | t to peak | Built |
|---|---|---|---|---|---|---|
| A | 7447462100 | 6.0 mm | 10 µH | 57 A | 3.4 µs | |
| B | 744772100 | 7.8 mm | 10 µH | 57 A | 3.4 µs | |
| C | DRC-0707-100K-UL | 8.5 mm | 10 µH | 57 A | 3.4 µs | |
| D | DRC-0807-100K-UL | 10.0 mm | 10 µH | 57 A | 3.4 µs | |
| E | 7447462022 | 6.0 mm | 2.2 µH | 121 A | 1.6 µs | reserve |

Substitutions, if any:
```

Fill the `Built` column and record any substitution from Task 3 Step 3.

- [ ] **Step 6: Commit**

```bash
git add hardware/rev2026/TIP-LOG.md
git commit -m "Injection tips A-D assembled"
```

---

### Task 5: The baseline control

**Files:**
- Modify: `hardware/rev2026/TIP-LOG.md`

**Interfaces:**
- Consumes: Task 1's target, Task 2's analyser, Task 4's tips.
- Produces: a gate. Nothing downstream is interpretable without it.

- [ ] **Step 1: Set up**

Target Pico on its own USB, well away from the PicoEMP's Pico and the host. PicoEMP with tip A fitted, shield in place. Both boards powered.

- [ ] **Step 2: Charge, but do not pulse**

Arm the PicoEMP and let it charge. Leave it charged for the whole baseline run. **Do not press pulse.**

- [ ] **Step 3: Capture at least ten minutes**

```bash
mkdir -p hardware/rev2026/logs
uv run --with mpremote mpremote connect <target-port> run firmware/micropython/glitch_target.py | tee hardware/rev2026/logs/baseline.log
```

Ctrl-C to stop.

- [ ] **Step 4: Analyse**

```bash
cd hardware/rev2026 && uv run tools/analyze_glitch_log.py logs/baseline.log
```

- [ ] **Step 5: Gate**

**Faults must be zero.** A nonzero baseline means the setup produces corruptions unaided, and every per-tip number after this would be measuring that instead of the tip. Stop and find the cause — power, USB noise, a wrong `EXPECTED` (Task 1's test covers that case), or a marginal breadboard connection.

`malformed` may be 1 from the Ctrl-C cutting a line. More than that wants explaining.

- [ ] **Step 6: Record and commit**

Append to `TIP-LOG.md`:

```markdown
## Baseline control

Date:
Duration: N minutes, PicoEMP charged, not pulsing
Blocks: N
Faults: N
Malformed: N

Verdict:
```

```bash
git add hardware/rev2026/TIP-LOG.md hardware/rev2026/logs/baseline.log
git commit -m "Baseline control: zero faults with the board charged but not pulsing"
```

---

### Task 6: The diameter sweep

**Files:**
- Modify: `hardware/rev2026/TIP-LOG.md`

**Interfaces:**
- Consumes: Task 5's gate.
- Produces: a fault rate per tip.

- [ ] **Step 1: Fix the protocol before the first run**

Decide these once and hold them constant across all four tips, or the comparison is meaningless:

- **Position:** tip resting on the RP2040 package, same orientation each time.
- **Pulse count:** the same number of pulses per tip. Twenty is a reasonable start.
- **Cadence:** wait for the HV LED between pulses. The rail needs ~2.1 s to recover, and a pulse into a half-charged rail is a different experiment.

- [ ] **Step 2: Run tip A**

```bash
uv run --with mpremote mpremote connect <target-port> run firmware/micropython/glitch_target.py | tee hardware/rev2026/logs/tip-A.log
```

Pulse 20 times at the agreed cadence, then Ctrl-C.

If the capture dies on its own, **the target reset** — that is a fault event in its own right. Note it and restart.

- [ ] **Step 3: Repeat for tips B, C and D**

Same protocol, same pulse count, logging to `logs/tip-B.log`, `logs/tip-C.log`, `logs/tip-D.log`.

- [ ] **Step 4: Analyse all four**

```bash
cd hardware/rev2026 && for t in A B C D; do echo "=== tip $t ==="; uv run tools/analyze_glitch_log.py logs/tip-$t.log; done
```

- [ ] **Step 5: If every tip reads zero, build tip E**

Four zeros is a real outcome, not a failure to be explained away — but before concluding the board cannot inject, assemble tip E (`7447462022`, 6.0 mm, 2.2 µH) per Task 4's steps and run the same protocol to `logs/tip-E.log`. It doubles peak current to 121 A and halves the rise time to 1.6 µs, so it probes the one axis the sweep holds constant.

If E is also zero, record that plainly. The likely next moves are triggered injection (spec §11) and a finer probe, neither of which is in this plan's scope.

- [ ] **Step 6: Record and commit**

Append to `TIP-LOG.md`:

```markdown
## Diameter sweep

Date:
Protocol: N pulses per tip, tip resting on the RP2040 package, waiting for
the HV LED between pulses.

| Tip | Dia | Blocks | Faults | Fault rate | Target resets |
|---|---|---|---|---|---|
| A | 6.0 mm | | | | |
| B | 7.8 mm | | | | |
| C | 8.5 mm | | | | |
| D | 10.0 mm | | | | |

Ranking:
```

```bash
git add hardware/rev2026/TIP-LOG.md hardware/rev2026/logs/
git commit -m "Diameter sweep results, tips A-D"
```

---

### Task 7: Close out

**Files:**
- Modify: `hardware/rev2026/TIP-LOG.md`

- [ ] **Step 1: State what the numbers support**

Append a conclusions section. Two things belong in it and are easy to conflate:

- **Whether the board can inject a fault at all.** Any tip with a nonzero rate against a zero baseline settles this. It is the first evidence the PicoEMP works as a fault-injection tool.
- **Whether diameter mattered.** This needs the *pattern* across A–D, not just a winner. With 20 pulses per tip, a difference of one or two faults is not a result. Say so if that is what you have.

- [ ] **Step 2: Record what was not established**

At minimum: no fine probe was tested (nothing under 6.0 mm is orderable in single quantities — the 5.5 mm `DRC-0406-1R2J-UL` has a 20,000 minimum), timing was never controlled, and the rail voltage remains the derived ~261 V from bring-up rather than a probed measurement.

- [ ] **Step 3: Commit**

```bash
git add hardware/rev2026/TIP-LOG.md
git commit -m "Injection tip conclusions"
```

---

## Self-Review

**Spec coverage.** §2 no-scope constraint → Tasks 1 and 2 build the detector that replaces it. §4 no trigger → Task 1 Step 5 sizes the block so untriggered pulsing lands, and `test_block_is_large_enough_to_be_hit` enforces the floor. §5 tip set → Tasks 3 and 4, with the five-tip deviation declared up front. §6 target → Task 1. §7 the control → Task 5, written as a gate. §8 standoff and insulation → Task 4 Step 4 and Task 6 Step 1. §9 success criteria → Task 6 Step 4 and Task 7 Step 1. §10 safety → Global Constraints. §11 out of scope → Task 7 Step 2.

**Placeholders.** Empty table cells and `Date:` lines are forms filled at the bench. `<target-port>` resolves via `ls /dev/tty.usbmodem*`; it is deliberately not hardcoded, since two Picos are attached during these runs and the PicoEMP's own port is already known to be `/dev/tty.usbmodem212201`.

**Type consistency.** `analyze(text, expected)` returns the same five keys asserted in Task 2's tests and printed by its `main`. `format_line(seq, acc)` in Task 1 emits `SEQ %d ACC %d`, which is exactly the `LINE` regex in Task 2. `BLOCK_N` and `EXPECTED` are used consistently across the target, its header line, and the analyser's header fallback.

**One risk the plan carries deliberately.** Task 1 Step 5 may change `BLOCK_N`, which changes `EXPECTED`. `test_expected_matches_the_computation` catches an inconsistent pair, and `TIP-LOG.md` records the value in use, so a mid-experiment change is visible rather than silent.
