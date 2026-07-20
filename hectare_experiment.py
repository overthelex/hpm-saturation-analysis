#!/usr/bin/env python3
"""Concrete case: 1 hectare (100 x 100 m) defended by 4 HPM installations.

Run:  python3 hectare_experiment.py

CALIBRATED to open-source data (see hpm-open-source-intel.md):
  theta = 30 deg (public "~60-degree arc" wide/sector mode)
  n_cone = 49    (one pulse defeated a 49-drone swarm, 26 Aug 2025)
  t_c   = 1.0 s  (swarm burst-mode sector-clear cycle; a single isolated drone is ~4 s)
  R_eff : swept as EFFECTIVE range, which encodes both nominal range AND target hardening.
          Physics: E(r)=sqrt(30*ERP)/r, so R_eff ∝ 1/E_kill -> +20 dB drone shielding
          shrinks effective R_eff by ~10x. That is the real exploitable axis, not raw N.

Geometry: vital point at centre; 4 apertures at the corners of the 100 m square
(ring radius 70.7 m). A LEAKER reaches the vital point (r<15 m) OR comes within 8 m of any
installation. Swarm surrounds from all sides (S0) and, worst case, with perfect knowledge
of the layout (S4 seam-routing). Numbers are order-of-magnitude (model §10).
"""
import statistics as st
from sim import DefenseConfig, Aperture, ThreatConfig, SimConfig, simulate

SEEDS = range(3)
SIM = SimConfig(dt=0.03)
CORNERS = [(50, 50, 3), (-50, 50, 3), (-50, -50, 3), (50, -50, 3)]

# calibrated defense
THETA, N_CONE, T_C, EL_MAX = 30.0, 49, 1.0, 80.0

# effective range rows, labelled by what shrinks/extends them (target hardening)
R_ROWS = [
    (1000, "soft COTS, long range"),
    (500,  "soft COTS, mid range"),
    (200,  "+14 dB hardened  (R_eff/5)"),
    (50,   "+20 dB hardened  (R_eff/10)"),
]
N_COLS = (100, 300, 600, 1000, 2000)


def hectare(r_eff, **over):
    aps = [Aperture(pos=p, theta_deg=THETA, r_eff=r_eff, t_c=T_C,
                    n_cone=N_CONE, el_max_deg=EL_MAX) for p in CORNERS]
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


def section(t): print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)


section("1 hectare, 4 installations — CALIBRATED (theta=30, n_cone=49, t_c=1s)")
print("  leak = fraction of swarm reaching the vital point or an installation")
print("  cell = leak(blind) / leak(perfect-ISR).  R_eff = EFFECTIVE range (m).\n")
print(f"  {'R_eff (effective)':<28} | " + " | ".join(f"N={n:<4d}" for n in N_COLS))
print("  " + "-" * 76)
for r_eff, label in R_ROWS:
    cells = []
    for n in N_COLS:
        lb, _ = mc(lambda r_eff=r_eff: hectare(r_eff), "S0", "blind", n)
        lp, _ = mc(lambda r_eff=r_eff: hectare(r_eff), "S4", "perfect", n)
        cells.append(f"{lb:.2f}/{lp:.2f}")
    print(f"  {r_eff:>4} m  {label:<19} | " + " | ".join(f"{c:>9}" for c in cells))

section("The hardening axis: same site, N=600 blind, sweep effective range")
for r_eff, label in R_ROWS:
    lb, cost = mc(lambda r_eff=r_eff: hectare(r_eff), "S0", "blind", 600)
    print(f"  R_eff={r_eff:>4} m ({label:<26}) leak={lb:.3f}  kills_before_1st_leak={cost:.0f}")
print("\n  -> against unshielded COTS the one-to-many pulse (n_cone=49) makes 4 units very")
print("     robust to raw numbers; the swarm's real lever is HARDENING, which collapses")
print("     effective R_eff (physics: R_eff ∝ 1/E_kill) — not fielding more drones.")

section("Fixes at the contested point (R_eff=200 m, N=1000, perfect-ISR)")
base, _ = mc(lambda: hectare(200), "S4", "perfect", 1000)
mob, _ = mc(lambda: hectare(200, orbit_rate=0.4), "S4", "perfect", 1000)
kin, _ = mc(lambda: hectare(200, kin_radius=60, kin_rate=6, kin_magazine=300, kin_pk=0.9),
            "S4", "perfect", 1000)
both, _ = mc(lambda: hectare(200, orbit_rate=0.4, kin_radius=60, kin_rate=6,
                             kin_magazine=300, kin_pk=0.9), "S4", "perfect", 1000)
print(f"  baseline (static, HPM only) : leak={base:.3f}")
print(f"  + rotating installations    : leak={mob:.3f}")
print(f"  + inner kinetic bubble      : leak={kin:.3f}")
print(f"  + both fixes                : leak={both:.3f}")
