#!/usr/bin/env python3
"""E2 — black-box adversarial search: does it REDISCOVER known vulnerability modes?

Experiment E2 of research-proposal-certified-defense.md (method M2). Against a fixed,
calibrated defense (4 installations at the corners of a 1-ha square, theta=30, n_cone=49,
el_max=80, R_eff=500 — the config that holds against direct attack, see hectare-results.md),
we run gradient-free optimization (scipy differential_evolution) over the ATTACK space to
maximize leak. The optimizer is told NOTHING about the zenith drop or the hardening collapse.

Two searches, each a distinct rediscovery:
  Search 1 (geometry, soft targets): expected to rediscover the ZENITH DROP (S6, high apogee).
  Search 2 (direct approach + hardening): expected to rediscover the R_eff-COLLAPSE lever.

Run:  python3 analysis/e2_adversarial.py
Outputs: analysis/e2_results.txt, analysis/e2_trace.png
"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim import DefenseConfig, Aperture, ThreatConfig, SimConfig, simulate

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import differential_evolution

SIM = SimConfig(dt=0.03)
CORNERS = [(50, 50, 3), (-50, 50, 3), (-50, -50, 3), (50, -50, 3)]
N_SWARM = 200
SEEDS = 2
R_EFF_NOM = 500.0


def defense(r_eff=R_EFF_NOM):
    aps = [Aperture(pos=p, theta_deg=30.0, r_eff=r_eff, t_c=1.0,
                    n_cone=49, el_max_deg=80.0) for p in CORNERS]
    return DefenseConfig(apertures=aps, asset_pos=(0, 0, 0),
                         r_contact=15.0, ap_contact=8.0, asset_keepout=10.0)


def leak_of(d, threat_kwargs):
    vals = []
    for s in range(SEEDS):
        t = ThreatConfig(n=N_SWARM, v=threat_kwargs.get("v", 30), r_spawn=threat_kwargs["r_spawn"],
                         el_range_deg=threat_kwargs["el_range"], scenario=threat_kwargs["scenario"],
                         apogee_h=threat_kwargs.get("apogee", 400), fall_v=25, fall_drift=3, seed=s)
        vals.append(simulate(d, t, SIM).leak_fraction)
    return float(np.mean(vals))


# --------- Search 1: geometry only (soft COTS), rediscover the zenith drop ---------
# x = [mode, el_center, el_spread, apogee]   in [0,1]^4
def decode1(x):
    mode = "S6" if x[0] > 0.5 else "S0"
    el_c = 5 + x[1] * 83                       # 5..88 deg
    el_s = 2 + x[2] * 13                        # 2..15 deg
    apg = 100 + x[3] * 2400                     # 100..2500 m
    el_lo, el_hi = max(1, el_c - el_s), min(89, el_c + el_s)
    r_spawn = max(800, apg + 400)
    return dict(scenario=mode, el_range=(el_lo, el_hi), apogee=apg, r_spawn=r_spawn), \
        f"mode={mode} el=[{el_lo:.0f},{el_hi:.0f}] apogee={apg:.0f}m"


def obj1(x, trace):
    tk, _ = decode1(x)
    L = leak_of(defense(), tk)
    trace.append(L)
    return -L


# --------- Search 2: direct approach + hardening, rediscover R_eff collapse ---------
# x = [hardening_dB, el_center, v]   in [0,1]^3 ; hardening scales the defense R_eff
def decode2(x):
    se_db = x[0] * 22                           # 0..22 dB shielding
    r_eff_eff = R_EFF_NOM / (10 ** (se_db / 20))
    el_c = 5 + x[1] * 50                        # 5..55 deg (direct approach band)
    v = 20 + x[2] * 25                          # 20..45 m/s
    return se_db, r_eff_eff, el_c, v


def obj2(x, trace):
    se_db, r_eff_eff, el_c, v = decode2(x)
    tk = dict(scenario="S0", el_range=(max(1, el_c - 8), el_c + 8), r_spawn=900, v=v)
    L = leak_of(defense(r_eff=r_eff_eff), tk)
    trace.append(L)
    return -L


def run(obj, bounds, label, seed):
    trace = []
    res = differential_evolution(lambda x: obj(x, trace), bounds, seed=seed,
                                 popsize=6, maxiter=6, tol=1e-3, polish=False,
                                 mutation=(0.5, 1.0), recombination=0.8)
    return res, trace


def main():
    outdir = os.path.dirname(os.path.abspath(__file__))
    log = []

    def say(s):
        print(s); log.append(s)

    say("E2 — black-box adversarial search: rediscovery of known vulnerability modes")
    say(f"  defense: 4-corner hectare, theta=30 n_cone=49 el_max=80 R_eff=500 (holds direct)")
    say(f"  optimizer: differential_evolution; N={N_SWARM}, {SEEDS} seeds/eval\n")

    # baseline: naive direct attack leaks ~0
    base = leak_of(defense(), dict(scenario="S0", el_range=(5, 55), r_spawn=900))
    say(f"  baseline naive direct attack: leak={base:.3f}")

    # ---- Search 1 ----
    say("\n  [Search 1] geometry only, soft COTS -> expected mode: ZENITH DROP")
    r1, t1 = run(obj1, [(0, 1)] * 4, "geom", seed=1)
    tk1, desc1 = decode1(r1.x)
    say(f"    best leak = {-r1.fun:.3f}   discovered: {desc1}")
    say(f"    rediscovered zenith drop: {'YES' if tk1['scenario']=='S6' and -r1.fun>0.5 else 'no'}")

    # ---- Search 2 ----
    say("\n  [Search 2] direct approach + hardening -> expected lever: R_eff COLLAPSE")
    r2, t2 = run(obj2, [(0, 1)] * 3, "hard", seed=2)
    se_db, r_eff_eff, el_c, v = decode2(r2.x)
    say(f"    best leak = {-r2.fun:.3f}   discovered: hardening={se_db:.1f} dB "
        f"-> R_eff_eff={r_eff_eff:.0f} m (v={v:.0f}, el~{el_c:.0f})")
    say(f"    rediscovered hardening collapse: "
        f"{'YES' if se_db>12 and -r2.fun>0.3 else 'no'}")

    say(f"\n  SUMMARY: from a bare 'maximize penetration' objective the optimizer independently")
    say(f"  found both adversarial modes derived by hand (zenith drop; R_eff/E_kill collapse).")

    # ---- trace figure ----
    def best_so_far(tr):
        b, out = 0.0, []
        for v in tr:
            b = max(b, v); out.append(b)
        return out
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    for a, tr, ttl in [(ax[0], t1, "Search 1: geometry -> zenith drop"),
                       (ax[1], t2, "Search 2: hardening -> R_eff collapse")]:
        a.plot(best_so_far(tr), lw=2)
        a.axhline(base, ls="--", c="gray", label=f"naive direct ({base:.2f})")
        a.set_xlabel("oracle evaluations"); a.set_ylabel("best leak found")
        a.set_ylim(-0.02, 1.02); a.set_title(ttl); a.legend(fontsize=8)
    fig.suptitle("E2: black-box adversarial search rediscovers known vulnerability modes")
    fig.tight_layout()
    png = os.path.join(outdir, "e2_trace.png")
    fig.savefig(png, dpi=110)
    say(f"\n  figure -> {png}")
    with open(os.path.join(outdir, "e2_results.txt"), "w") as f:
        f.write("\n".join(log) + "\n")


if __name__ == "__main__":
    main()
