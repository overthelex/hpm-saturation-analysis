# HPM counter-swarm simulation — engine

Defensive red-team tool. Runs abstract swarm maneuvers against a HPM defense
configuration and reports breakthrough (leak) fraction, cost of attack, and where the
line fails. Companion to `hpm-saturation-model.md` and `hpm-swarm-sim-design.md`.

> **Scope (unchanged from the model):** evaluates the *defense*. Kinematics are abstract,
> coordinates notional; output is "where the line fails", not an attack plan. See design
> doc §9.

## Run

```bash
cd ~/epirus
python3 run_sim.py                 # three headline demos (A pencil/shield, B leak(N), C interior)
python3 tests/test_validation.py   # validation report (no pytest needed)
python3 -m pytest tests/ -q        # same, under pytest
```

Requires `numpy` (and `scipy` later for the Hungarian scheduler). No other deps.

## What's implemented (stages 0-2 of the design)

- **Stage 0** — 3D time-stepped engine, drone kinematics, single static aperture, S0 shell.
- **Stage 1** — `P_k(r)` (hard step or logistic rolloff), `n_cone` one-to-many, sensor with
  `T_max` track cap, greedy earliest-deadline-first scheduler.
- **Stage 2** — ring of `M` apertures + `NoFireMask` (fratricide: asset keep-out cone +
  unhardened-friendly arcs), elevation limit / zenith gap, mobile-aperture hook.

## Validated (design §7 — all pass)

| Check | Result |
|---|---|
| Angular boundary reproduces `Σ = T_r/τ` | breach at θ=8° (Σ=3.4), holds at θ≥15° (Σ≤1) |
| Limit `v→0` | leak→0 (all serviced) |
| Limit `θ→90°` (S→1) | leak→0 (no angular saturation) |
| Fratricide OFF closes interior | rear swarm: ON 100% leak / OFF 0% (mask isolated) |
| Determinism | same seed → identical result |

The θ=15° knife-edge (Σ≈0.98 → leak≈0.01) is the sim independently landing on the model's
`Σ=1` threshold — the core cross-check.

## Structure

```
sim/config.py     dataclasses: Aperture, DefenseConfig (+.ring), ThreatConfig, SimConfig
sim/scenarios.py  spawn policies (S0 shell, multi-altitude via el_range)
sim/engine.py     World: step loop, NoFireMask/legality, greedy-EDF scheduler, run()
sim/metrics.py    Metrics: leak_fraction, kills_before_first_leak, holds_fratricide
run_sim.py        demo driver (headline A/B/C)
tests/            validation suite
```

## Not yet implemented (stages 3-6)

- S3/S4/S5 guidance policies (seam-routing with ISR levels; mobility invalidating ISR).
- Inner kinetic layer (the interior bubble that closes the fratricide blind volume).
- Explicit slew-rate model (currently slew folded into `t_c`).
- Hungarian optimal scheduler (upper bound on best-possible defense).
- Sweep driver + Monte-Carlo + heatmap artifacts (leak vs M/hardening/altitude; ISR value).

## Caveats

Order-of-magnitude on open assumptions (`hpm-saturation-model.md` §10). All simplifications
tighten the defensive bound (real thresholds ≤ computed). With classified parameters the
model re-solves quickly.
