# Rev-2026 Bring-Up Log — Board #1

Plan: `docs/superpowers/plans/2026-08-05-picoemp-rev2026-bringup.md`
Spec: `docs/superpowers/specs/2026-08-05-picoemp-rev2026-bringup-design.md`

Equipment: DMM; bench PSU with current limit. No scope, no HV probe.

---

## Phase 0 — cold checks

Date: 2026-08-05

Board had not been energized before these readings were taken.

| # | Measurement | Expected | Measured | Pass |
|---|---|---|---|---|
| 0.1 | J1 centre → J3.2 | 300 kΩ ±5 % | 299.5 kΩ | ✅ |
| 0.2 | Hold SW3, J1 centre → J3.1 | 300 kΩ ±5 % | 273 kΩ / 299.3 kΩ reversed (see note) | ✅ |
| 0.3 | GND (USB shell) → J3.1 | open > 20 MΩ | OL | ✅ |
| 0.4 | J1 centre → J1 shell | not a short | OL | ✅ |
| 0.5 | Pico 3V3(OUT) → GND | not a short | 36 kΩ | ✅ |
| 0.6 | J2.1 → J2.2 | not a short | 2.2 MΩ | ✅ |

### Note on 0.2 — 273 kΩ rather than 300 kΩ

`R2` is confirmed good by 0.1 at 299.5 kΩ, and SW3 is confirmed closing by
0.2 reading a finite value at all rather than OL. The 27 kΩ shortfall is a
second conduction path between the probe points, not a component fault:

```
J3.1 (HV_RTN) → T1 secondary (T1.3→T1.2) → HV_RECT → D2 anode→cathode → HV_RAIL (J1 centre)
```

`D2.1` is the cathode on `HV_RAIL` and `D2.2` the anode on `HV_RECT`, so this
path forward-biases when the DMM's **red** lead sits on J3.1, putting a
weakly-conducting diode branch in parallel with R2. Solving 273 ∥ 299.5 puts
that branch at ~3.0 MΩ, consistent with a silicon diode at sub-µA DMM test
current.

0.1 is unaffected because `HV_SENSE` never touches `HV_RTN`, so no D2 path
exists for that measurement — which is why it reads clean.

Reversed-polarity confirmation: **299.3 kΩ**, within 0.2 kΩ of 0.1's 299.5 kΩ.
D2 blocks in this direction and R2 is the only path, as predicted. Resolved.

**Practical consequence:** future resistance measurements between `HV_RAIL` and
`HV_RTN` must put the red lead on `HV_RAIL` (J1 centre). The other polarity
reads low through T1's secondary and D2 and does not indicate a fault.

Notes: Board had not been energized before these readings.
