# HPM Saturation Analysis

Defensive counter-UAS red-team of a single/layered high-power-microwave (HPM) line,
using Epirus Leonidas as the open-source reference. Quantifies **where a HPM defense
saturates, at what swarm size, and how to close the seams** — from the defender's side.

> Scope: strictly defensive evaluation. Kinematics are abstract, coordinates notional;
> the output is "where the line fails and what to fix", not an attack plan. All figures
> are order-of-magnitude on open-source assumptions; classified parameters re-solve the
> model in minutes.

## Documents

| File | What |
|---|---|
| `hpm-saturation-model.md` | The analytical model: angular/temporal saturation, fratricide & interior blind volume, three defensive locks. |
| `hpm-swarm-sim-design.md` | Design of the 3D agent simulation (method, scenarios, validation, roadmap). |
| `epirus-pitch-memo.md` | One-page technical memo (envelope + 3 lead numbers + 3 fixes). |
| `hectare-results.md` | Worked case: 1 hectare defended by 4 installations. |
| `leonidas-video-summary.md` | Section summary of the source video. |
| `README-sim.md` | Simulation engine status & how to run. |

## Simulation

3D time-stepped agent model (Python + NumPy). Stages 0–4 implemented:
angular saturation, `P_k`/`n_cone`/sensor, ring + fratricide `NoFireMask`,
seam-routing by ISR level, orbiting apertures (mobility), inner kinetic layer.

```bash
python3 tests/test_validation.py   # 8 validation checks (reproduce the closed-form model)
python3 run_sim.py                 # headline demos A/B/C
python3 sweep.py                   # ISR value, mobility, hybrid sizing
python3 hectare_experiment.py      # 1 ha / 4 installations breakthrough table
```

Requires `numpy` (`scipy` reserved for the future Hungarian scheduler).

## Key results

- A single aperture saturates by **beam-revisit geometry**, not power: breakthrough when
  `T_r = S·t_c > τ = (R_eff−R_c)/v`, independent of N. The sim lands on the `Σ=1` threshold.
- A ring has a **by-design interior blind volume** (firing inward = fratricide); a rear
  swarm leaks 100% with the mask on, 0% off.
- **1 hectare / 4 installations:** holds absolutely below a range-dependent threshold
  `N_min ≈ 150–500`, then breaks; a ~600–1000 swarm exceeds the ceiling at any realistic
  range. Mobility helps only against ISR-dependent attacks; a kinetic bubble is the robust
  closer near threshold — deep saturation needs more mass, not refinement.
