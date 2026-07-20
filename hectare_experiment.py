#!/usr/bin/env python3
"""Concrete case: 1 hectare (100 x 100 m) defended by 4 HPM installations.

Run:  python3 hectare_experiment.py

Geometry: asset (vital point) at centre; 4 apertures at the corners of the 100 m square
(ring radius = 70.7 m). A drone is a LEAKER if it reaches the vital point (r<15 m) OR
comes within 8 m of any installation ("подлететь вплотную к установке"). Swarm surrounds
from all sides (S0) and, worst case, with perfect knowledge of the layout (S4 seam-routing).

Sweeps the one parameter that dominates and is classified — per-installation range r_eff —
against swarm size N. Numbers are order-of-magnitude on open assumptions (model §10).
"""
import statistics as st
from sim import DefenseConfig, Aperture, ThreatConfig, SimConfig, simulate

SEEDS = range(4)
SIM = SimConfig(dt=0.03)
CORNERS = [(50, 50, 3), (-50, 50, 3), (-50, -50, 3), (50, -50, 3)]  # 100x100 m, 3 m mast


def hectare(r_eff, theta=10.0, t_c=0.3, n_cone=2, **over):
    aps = [Aperture(pos=p, theta_deg=theta, r_eff=r_eff, t_c=t_c,
                    n_cone=n_cone, el_max_deg=80.0) for p in CORNERS]
    d = DefenseConfig(apertures=aps, asset_pos=(0, 0, 0),
                      r_contact=15.0, ap_contact=8.0, asset_keepout=10.0)
    for k, v in over.items():
        setattr(d, k, v)
    return d


def mc(dfac, scenario, isr, n, v=32):
    def tf(s):
        return ThreatConfig(n=n, v=v, r_spawn=700, el_range_deg=(4, 55),
                            scenario=scenario, isr=isr, seed=s,
                            seam_az_spread_deg=4.0, seam_zenith_frac=0.15)
    res = [simulate(dfac(), tf(s), SIM) for s in SEEDS]
    return (st.mean(r.leak_fraction for r in res),
            st.mean(r.kills_before_first_leak for r in res))


def section(t): print("\n" + "=" * 72 + f"\n{t}\n" + "=" * 72)


section("1 hectare, 4 installations at the corners — breakthrough vs range & swarm size")
print("  leak = fraction of swarm reaching the vital point or an installation")
print("  (blind = surround from all sides; ISR = attacker knows the 4 positions)\n")
header = f"  {'r_eff':>6} | " + " | ".join(f"N={n:<4d}" for n in (100, 300, 600, 1000))
for r_eff in (120, 200, 350, 500):
    cells = []
    for n in (100, 300, 600, 1000):
        lb, _ = mc(lambda r_eff=r_eff: hectare(r_eff), "S0", "blind", n)
        lp, _ = mc(lambda r_eff=r_eff: hectare(r_eff), "S4", "perfect", n)
        cells.append(f"{lb:.2f}/{lp:.2f}")
    if r_eff == 120:
        print(header)
        print("  " + "-" * (len(header) - 2))
    print(f"  {r_eff:>6} | " + " | ".join(f"{c:>9}" for c in cells))
print("\n  cell = leak(blind) / leak(perfect-ISR).  r_eff in meters.")

section("Same site + the two fixes (r_eff=200, N=600, perfect-ISR worst case)")
base, cost = mc(lambda: hectare(200), "S4", "perfect", 600)
mob, _ = mc(lambda: hectare(200, orbit_rate=0.4), "S4", "perfect", 600)
kin, _ = mc(lambda: hectare(200, kin_radius=60, kin_rate=6, kin_magazine=200, kin_pk=0.9),
            "S4", "perfect", 600)
both, _ = mc(lambda: hectare(200, orbit_rate=0.4, kin_radius=60, kin_rate=6,
                             kin_magazine=200, kin_pk=0.9), "S4", "perfect", 600)
print(f"  baseline (static, HPM only) : leak={base:.3f}   kills_before_1st_leak={cost:.0f}")
print(f"  + rotating installations    : leak={mob:.3f}")
print(f"  + inner kinetic bubble      : leak={kin:.3f}")
print(f"  + both fixes                : leak={both:.3f}")
print("\n(Interpretation printed by the script is descriptive; see model §8 for the mechanism.)")
