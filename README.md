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
| `hpm-open-source-intel.md` | OSINT + peer-reviewed physics used to calibrate the model: disclosed Leonidas TTX, analog range envelope, HPM field-kill thresholds (E₅₀≈200 V/m), P_k(r) derivation. |
| `hpm-swarm-sim-design.md` | Design of the 3D agent simulation (method, scenarios, validation, roadmap). |
| `epirus-pitch-memo.md` | One-page technical memo (envelope + 3 lead numbers + 3 fixes). |
| `hectare-results.md` | Worked case: 1 hectare defended by 4 installations. |
| `zenith-drop-results.md` | Over-the-top attack: drop into the zenith cone of silence; soft-kill can't stop inert falling mass ("hail" of dead-but-detonating drones). |
| `leonidas-video-summary.md` | Section summary of the source video. |
| `research-proposal-certified-defense.md` | Research proposal: certified penetration-safety envelopes for area defense (adversarial-robustness / certification transfer from ML). |
| `paper.pdf` / `paper.tex` | **Compiled LaTeX paper** (E1–E4, unified ggplot2 figures) — the submission draft. |
| `paper-draft.md` | Markdown working draft (source for the LaTeX paper). |
| `figures/` | R/ggplot2 publication figures (SVG + PNG) + the data CSVs and build scripts. |
| `analysis/E1-results.md` | Preliminary E1: GP surrogate + level-set active learning recovers the failure boundary to 0.038 s using 14% of a dense grid, +79% vs random. |
| `analysis/E2-results.md` | Preliminary E2: black-box adversarial search autonomously rediscovers both hand-derived modes (zenith drop; hardening/R_eff collapse), leak 0→1.0. |
| `analysis/E3-results.md` | Preliminary E3 (core): conformal penetration-safety certificate — 94% coverage, 0 false-safe, 93% tight, and holds against an active adversary (worst leak in Â = 0.125 < τ). |
| `analysis/E4-results.md` | Preliminary E4: subset-simulation certifies the tail probability Pr[leak≥τ]≈1e-3 where naive MC is blind; validated within 0.9× where naive is reliable. |
| `analysis/E5-results.md` | Preliminary E5: Sobol sensitivity — one-to-many capacity n_cone and effective range R_eff co-dominate penetration; design guidance. |
| `analysis/E6-results.md` | E6: MAP-Elites joint mode search — two full-breakthrough ridges (drop, hardening), no cheap third full mode. |
| `analysis/E7-results.md` | E7: drone **speed** (to 600 km/h) is a partial third breakthrough axis; parallelized across all cores. |
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
- **1 hectare / 4 installations (calibrated `n_cone=49`, `θ=30°`):** against unshielded COTS
  the one-to-many pulse makes the site robust to **raw numbers** — it holds absolutely even
  at N=2000. The swarm's real lever is **hardening**: `R_eff ∝ 1/E_kill`, so +20 dB of drone
  shielding collapses effective range ~10× and breaks the defense (leak 0.67 at N=600). ISR
  value and the mobility/kinetic fixes matter only in that short-effective-range regime.
