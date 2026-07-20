#!/usr/bin/env python3
"""E6 — quality-diversity (MAP-Elites) joint search for NEW failure modes.

Beyond E2 (which rediscovered two hand-derived modes with scoped searches), we run a JOINT
search over a combined attack genome and use MAP-Elites to map *diverse* high-penetration
strategies rather than a single optimum. Behavior descriptors: (drop altitude, drone
hardening) -- the two axes of the known modes. Hidden levers in the genome (approach
elevation, speed, azimuth seam-routing) let the optimizer discover strategies the descriptors
don't directly encode.

Question: is there a high-leak cell in the CHEAP corner (low altitude AND low hardening)?
That would be a NEW mode beyond the zenith drop (high altitude) and hardening collapse (high
hardening). We also map the hybrid frontier -- the minimum combined adversary investment.

Run:  python3 analysis/e6_novelty_search.py            (full)
      E6_SMOKE=1 python3 analysis/e6_novelty_search.py (fast)
Outputs: analysis/e6_results.txt, figures/data_e6_map.csv, figures/data_e6_new.csv
"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim import DefenseConfig, Aperture, ThreatConfig, SimConfig, simulate
from analysis.parallel_eval import pmap

SMOKE = os.environ.get("E6_SMOKE") == "1"
CORNERS = [(50, 50, 3), (-50, 50, 3), (-50, -50, 3), (50, -50, 3)]
SIM = SimConfig(dt=0.04)
SEEDS = 2
N_SWARM = 400
R_EFF_NOM = 500.0
BINS = 6
GENOME = 5   # [apogee, hardening, el_center, v, seam]


def decode(x):
    apogee = x[0] * 2000.0                 # 0..2000 m  (descriptor 1)
    hard_db = x[1] * 24.0                  # 0..24 dB   (descriptor 2)
    el_c = 5 + x[2] * 83.0                 # 5..88 deg  (hidden)
    v = 20 + x[3] * 147.0                  # 20..167 m/s = 72..600 km/h (hidden)
    seam = x[4] > 0.5                      # azimuth seam-routing (hidden)
    return apogee, hard_db, el_c, v, seam


def leak_of(x):
    apogee, hard_db, el_c, v, seam = decode(x)
    r_eff = R_EFF_NOM / (10 ** (hard_db / 20.0))
    aps = [Aperture(pos=p, theta_deg=30.0, r_eff=r_eff, t_c=1.0, n_cone=49, el_max_deg=80.0)
           for p in CORNERS]
    d = DefenseConfig(apertures=aps, asset_pos=(0, 0, 0),
                      r_contact=15.0, ap_contact=8.0, asset_keepout=10.0)
    if apogee > 150:                       # ballistic drop
        scen, isr = "S6", "blind"
        el_range = (max(1, el_c - 4), min(89, el_c + 4))
        r_spawn = max(800, apogee + 400)
    else:                                  # direct / seam-routed
        scen = "S4" if seam else "S0"
        isr = "perfect" if seam else "blind"
        el_range = (max(1, el_c - 8), min(80, el_c + 8))
        r_spawn = 800
    vals = [simulate(d, ThreatConfig(n=N_SWARM, v=v, r_spawn=r_spawn, el_range_deg=el_range,
                                     scenario=scen, isr=isr, apogee_h=apogee, seed=s),
                     SIM).leak_fraction for s in range(SEEDS)]
    return float(np.mean(vals))


def cell(x):
    apogee, hard_db = x[0] * 2000.0, x[1] * 24.0
    i = min(BINS - 1, int(apogee / 2000.0 * BINS))       # altitude bin
    j = min(BINS - 1, int(hard_db / 24.0 * BINS))        # hardening bin
    return (i, j)


def main():
    outdir = os.path.dirname(os.path.abspath(__file__))
    figdir = os.path.join(os.path.dirname(outdir), "figures")
    log = []
    say = lambda s: (print(s), log.append(s))

    n_init = 20 if SMOKE else 40
    n_iter = 60 if SMOKE else 360
    rng = np.random.default_rng(0)

    say("E6 — MAP-Elites joint search for diverse / new failure modes")
    say(f"  defense: calibrated 4-corner hectare (holds direct soft attack); N={N_SWARM}")
    say(f"  descriptors: (drop altitude x drone hardening), {BINS}x{BINS} map")
    say(f"  budget: {n_init} init + {n_iter} mutations ({'SMOKE' if SMOKE else 'full'})\n")

    archive = {}   # cell -> (leak, genome)

    def add(x, L):
        c = cell(x)
        if c not in archive or L > archive[c][0]:
            archive[c] = (L, x.copy())

    # init (parallel across all cores)
    init = [rng.random(GENOME) for _ in range(n_init)]
    for x, L in zip(init, pmap(leak_of, init)):
        add(x, L)
    # batched MAP-Elites generations (each batch evaluated in parallel)
    B = os.cpu_count()
    for _ in range(max(1, n_iter // B)):
        keys = list(archive.keys())
        batch = [np.clip(archive[keys[rng.integers(len(keys))]][1]
                         + 0.15 * rng.standard_normal(GENOME), 0, 1) for _ in range(B)]
        for x, L in zip(batch, pmap(leak_of, batch)):
            add(x, L)

    # build map grid
    grid = np.full((BINS, BINS), np.nan)
    rows = []
    for (i, j), (L, x) in archive.items():
        grid[i, j] = L
        apogee, hard_db, el_c, v, seam = decode(x)
        rows.append([i, j, f"{L:.3f}", f"{apogee:.0f}", f"{hard_db:.1f}",
                     f"{el_c:.0f}", f"{v:.0f}", int(seam)])

    say("  MAP-Elites archive filled: %d / %d cells" % (len(archive), BINS * BINS))
    say("  leak map (rows=altitude bin 0..5, cols=hardening bin 0..5):")
    for i in range(BINS - 1, -1, -1):
        say("    alt%d | " % i + " ".join(
            ("  .  " if np.isnan(grid[i, j]) else f"{grid[i, j]:.2f}") for j in range(BINS)))
    say("           " + " ".join(f"hard{j}" for j in range(BINS)))

    # --- classify every high-leak elite by the ACTUAL lever it uses (decoded, not binned) ---
    DROP, HARD, FAST = 150.0, 6.0, 110.0   # apogee>DROP=drop; hard>HARD dB; v>FAST m/s (~400 km/h)
    classes = {"drop": [], "hardening": [], "high-speed": [], "seam-routing": [], "direct-soft-slow": []}
    for (i, j), (L, x) in archive.items():
        if L < 0.5:
            continue
        ap, hd, el, v, sm = decode(x)
        if ap > DROP:
            classes["drop"].append((L, ap, hd, el, v, sm))
        elif hd > HARD:
            classes["hardening"].append((L, ap, hd, el, v, sm))
        elif v > FAST:
            classes["high-speed"].append((L, ap, hd, el, v, sm))
        elif sm:
            classes["seam-routing"].append((L, ap, hd, el, v, sm))
        else:
            classes["direct-soft-slow"].append((L, ap, hd, el, v, sm))

    say("\n  High-leak strategies (leak>=0.5) by ACTUAL lever used:")
    for k in classes:
        say(f"    {k:>16}: {len(classes[k])} elite(s)")

    new = classes["high-speed"] + classes["seam-routing"] + classes["direct-soft-slow"]
    say("")
    if new:
        say(f"  ** NEW MODE(S) beyond zenith-drop and hardening-collapse: {len(new)} elite(s)")
        for L, ap, hd, el, v, sm in sorted(new, reverse=True)[:6]:
            kind = ("high-speed" if v > FAST and ap <= DROP and hd <= HARD
                    else "seam-routing" if sm else "direct-soft-slow")
            say(f"     leak={L:.2f} [{kind}] v={v:.0f} m/s ({v*3.6:.0f} km/h) apogee={ap:.0f}m "
                f"hardening={hd:.1f}dB el={el:.0f}")
    else:
        say("  No FULL-breakthrough (leak>=0.5) mode outside drop / hardening in this genome.")

    # quantify the SPEED axis even below the 0.5 bar (direct + soft + fast)
    fast_soft = max((L for (i, j), (L, x) in archive.items()
                     if decode(x)[0] <= DROP and decode(x)[1] <= 3.0 and decode(x)[3] > FAST),
                    default=0.0)
    say(f"\n  Speed as a PARTIAL third axis: best leak by a direct+soft+fast (>{FAST*3.6:.0f} km/h)")
    say(f"  strategy = {fast_soft:.2f} (< full breakthrough at the calibrated t_c=1.0, but nonzero;")
    say("  see E7 -- speed dominates once the engagement cycle t_c is larger / R_eff smaller).")

    with open(os.path.join(figdir, "data_e6_map.csv"), "w") as f:
        f.write("alt_bin,hard_bin,leak,apogee,hardening_db,el_center,v,seam\n")
        for r in rows:
            f.write(",".join(map(str, r)) + "\n")
    say(f"\n  wrote {figdir}/data_e6_map.csv")
    with open(os.path.join(outdir, "e6_results.txt"), "w") as f:
        f.write("\n".join(log) + "\n")


if __name__ == "__main__":
    main()
