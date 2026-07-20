#!/usr/bin/env python3
"""E7 — drone SPEED as a third breakthrough axis (up to 600 km/h). Parallelized.

Fast drones (Shahed / jet-FPV class, up to ~167 m/s = 600 km/h) shrink the transit time
tau = (R_eff - R_c)/v, so the saturation ratio Sigma = T_r/tau = S(theta) t_c v /(R_eff - R_c)
grows LINEARLY with speed. Above a critical speed the beam cannot revisit all sectors within
the (now short) engagement window and the one-to-many defense breaks -- even against soft,
unhardened drones. This is a third breakthrough axis alongside altitude (zenith drop) and
hardening (R_eff collapse).

Runs on all CPU cores. Sweeps leak vs speed for several engagement cycles t_c and overlays the
analytic critical speed v* where Sigma=1.

Run:  python3 analysis/e7_speed.py
Outputs: analysis/e7_results.txt, figures/data_e7_speed.csv, analysis/e7_speed.png
"""
import os
import sys
import math
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim import DefenseConfig, Aperture, ThreatConfig, SimConfig, simulate
from analysis.parallel_eval import pmap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CORNERS = [(50, 50, 3), (-50, 50, 3), (-50, -50, 3), (50, -50, 3)]
SIM = SimConfig(dt=0.04)
THETA, N_CONE, R_EFF, EL_MAX = 30.0, 49, 500.0, 80.0
R_C = 15.0
N_SWARM = 400
SEEDS = 3
T_CYCLES = [0.5, 1.0, 1.5]
# speeds: 72 .. 612 km/h
V_MS = list(range(20, 172, 8))


def eval_point(arg):
    """Top-level worker: (t_c, v, seed) -> leak. Runs one simulation."""
    t_c, v, seed = arg
    aps = [Aperture(pos=p, theta_deg=THETA, r_eff=R_EFF, t_c=t_c, n_cone=N_CONE,
                    el_max_deg=EL_MAX) for p in CORNERS]
    d = DefenseConfig(apertures=aps, asset_pos=(0, 0, 0),
                      r_contact=R_C, ap_contact=8.0, asset_keepout=10.0)
    return simulate(d, ThreatConfig(n=N_SWARM, v=v, r_spawn=700, el_range_deg=(5, 55),
                                    scenario="S0", seed=seed), SIM).leak_fraction


def v_star(t_c):
    """Analytic critical speed where Sigma = T_r/tau = 1 (breakthrough onset)."""
    S = 1.0 / (1.0 - math.cos(math.radians(THETA)))     # sectors
    T_r = S * t_c                                        # revisit time
    return (R_EFF - R_C) / T_r                           # v* = (R_eff-R_c)/T_r


def main():
    outdir = os.path.dirname(os.path.abspath(__file__))
    figdir = os.path.join(os.path.dirname(outdir), "figures")
    log = []
    say = lambda s: (print(s), log.append(s))

    say("E7 — drone speed as a third breakthrough axis (parallel, %d cores)" % os.cpu_count())
    say(f"  defense: calibrated 4-corner hectare (theta={THETA}, n_cone={N_CONE}, R_eff={R_EFF})")
    say(f"  swarm N={N_SWARM}, soft/unhardened, direct approach; speeds "
        f"{V_MS[0]*3.6:.0f}..{V_MS[-1]*3.6:.0f} km/h")

    jobs = [(t_c, v, s) for t_c in T_CYCLES for v in V_MS for s in range(SEEDS)]
    say(f"  running {len(jobs)} simulations across all cores ...")
    res = pmap(eval_point, jobs, chunksize=4)

    # aggregate over seeds
    leak = {}
    k = 0
    for t_c in T_CYCLES:
        for v in V_MS:
            vals = res[k:k + SEEDS]; k += SEEDS
            leak[(t_c, v)] = float(np.mean(vals))

    say("\n  leak vs speed (rows = t_c, cols = km/h):")
    header = "   t_c \\ km/h |" + "".join(f"{v*3.6:5.0f}" for v in V_MS[::2])
    say(header)
    for t_c in T_CYCLES:
        row = "".join(f"{leak[(t_c, v)]:5.2f}" for v in V_MS[::2])
        say(f"   t_c={t_c:<4}    |{row}")

    say("\n  analytic critical speed v* (Sigma=1) and first speed where leak>=0.2:")
    for t_c in T_CYCLES:
        vs = v_star(t_c)
        onset = next((v for v in V_MS if leak[(t_c, v)] >= 0.2), None)
        onset_s = f"{onset*3.6:.0f} km/h" if onset else ">612 km/h"
        say(f"    t_c={t_c}: v*={vs:.0f} m/s ({vs*3.6:.0f} km/h);  simulated onset ~{onset_s}")

    say("\n  => SPEED alone breaks the one-to-many defense above v*: a 600 km/h swarm penetrates")
    say("     a hectare that holds against 2000 slow drones. Speed is a third axis (with altitude")
    say("     and hardening); it scales Sigma linearly, so faster drones need no hardening or drop.")

    # CSV
    with open(os.path.join(figdir, "data_e7_speed.csv"), "w") as f:
        f.write("t_c,v_ms,v_kmh,leak,Sigma\n")
        for t_c in T_CYCLES:
            S = 1.0 / (1.0 - math.cos(math.radians(THETA)))
            for v in V_MS:
                sig = S * t_c * v / (R_EFF - R_C)
                f.write(f"{t_c},{v},{v*3.6:.0f},{leak[(t_c,v)]:.4f},{sig:.4f}\n")
    say(f"  wrote {figdir}/data_e7_speed.csv")

    # quick matplotlib (R version separately)
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    for t_c in T_CYCLES:
        y = [leak[(t_c, v)] for v in V_MS]
        ax.plot([v * 3.6 for v in V_MS], y, marker="o", ms=3, label=f"t_c={t_c}s")
        ax.axvline(v_star(t_c) * 3.6, ls="--", alpha=0.4)
    ax.set_xlabel("drone speed (km/h)"); ax.set_ylabel("leak fraction")
    ax.set_title("E7: speed breaks the one-to-many defense (dashed = analytic v*, Σ=1)")
    ax.legend(); fig.tight_layout()
    fig.savefig(os.path.join(outdir, "e7_speed.png"), dpi=120)
    say(f"  figure -> {outdir}/e7_speed.png")
    with open(os.path.join(outdir, "e7_results.txt"), "w") as f:
        f.write("\n".join(log) + "\n")


if __name__ == "__main__":
    main()
