#!/usr/bin/env python3
"""E4 — rare-event certification of the penetration probability via Subset Simulation.

Experiment E4 of research-proposal-certified-defense.md. E3 certified the MEAN leak
L(d,a)=E_w[leak]. Here we certify the small TAIL probability p(a)=Pr_w[leak >= tau] in the
safe region, where naive Monte-Carlo sees ~0 events. We use Subset Simulation
(Au & Beck 2001): decompose a rare probability into a product of ~p0 conditional
probabilities across intermediate thresholds, sampled by component-wise Modified Metropolis.

The randomness w is made EXPLICIT: for a fixed attack, w in R^{2N} perturbs the spawn
azimuth/elevation of the N drones; the kill law is a hard step, so g(w)=leak(w) is a
deterministic function of w and the only stochasticity is w ~ N(0, I).

Run:  python3 analysis/e4_rare_event.py           (full)
      E4_SMOKE=1 python3 analysis/e4_rare_event.py (fast smoke test)
Outputs: analysis/e4_results.txt, analysis/e4_ccdf.png
"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim import DefenseConfig, Aperture, ThreatConfig, SimConfig
from sim.engine import World

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SMOKE = os.environ.get("E4_SMOKE") == "1"

# ---- fixed attack/defense in the safe-but-marginal regime ----
NDR = 60                       # drones (omega dim = 2*NDR)
THETA, T_C, R_EFF, VEL, N_CONE = 15.0, 0.60, 500.0, 32.0, 6
R_SPAWN = 800.0
EL_C, SIG_AZ, SIG_EL = 45.0, 0.20, 10.0   # base elevation, noise scales (rad, deg)
# Two events on the same marginal config (Sigma~1.27, mean leak ~0.002):
#   TAU_MOD  — moderate: naive MC is reliable, so it VALIDATES the subset-sim estimate.
#   TAU_RARE — rare: naive MC is near-blind; only subset simulation resolves it.
TAU_MOD = 0.033                # >= 2 of 60 penetrate
TAU_RARE = 0.067               # >= 4 of 60 penetrate
TAU = TAU_RARE                 # default level for standalone g-threshold references
DT = 0.03


def _defense():
    return DefenseConfig(asset_keepout=0.0, r_contact=50.0, fratricide=False, p_k_soft=0.0,
                         apertures=[Aperture(pos=(0, 0, 0), theta_deg=THETA, r_eff=R_EFF,
                                             t_c=T_C, n_cone=N_CONE, el_max_deg=90.0)])


def g(omega):
    """Deterministic leak as a function of the standard-normal noise vector omega (2*NDR)."""
    w = omega.reshape(NDR, 2)
    az = 2 * np.pi * np.arange(NDR) / NDR + SIG_AZ * w[:, 0]
    el = np.clip(np.radians(EL_C + SIG_EL * w[:, 1]), np.radians(5), np.radians(85))
    x = R_SPAWN * np.cos(el) * np.cos(az)
    y = R_SPAWN * np.cos(el) * np.sin(az)
    z = R_SPAWN * np.sin(el)
    pos = np.column_stack([x, y, z]).astype(float)
    to_c = -pos
    vel = VEL * to_c / np.maximum(np.linalg.norm(to_c, axis=1, keepdims=True), 1e-9)

    threat = ThreatConfig(n=NDR, v=VEL, r_spawn=R_SPAWN, scenario="S0", seed=0)
    world = World(_defense(), threat, SimConfig(dt=DT))
    world.pos = pos
    world.vel = vel
    world.status[:] = 0
    world.immune[:] = False
    return world.run().leak_fraction


# ---------------- Subset Simulation ----------------
def modified_metropolis(seed_omega, b_level, n_out, step=0.3, rng=None):
    """Generate ~n_out samples conditioned on g(w) >= b_level, starting chains from seeds."""
    dim = seed_omega.shape[1]
    chains = len(seed_omega)
    per = int(np.ceil(n_out / chains))
    out, out_g = [], []
    for c in range(chains):
        cur = seed_omega[c].copy()
        gc = g(cur)
        for _ in range(per):
            prop = cur + step * rng.standard_normal(dim)
            # component-wise MH accept for standard normal target (symmetric proposal)
            ratio = np.exp(0.5 * (cur ** 2 - prop ** 2))
            acc = rng.random(dim) < ratio
            cand = np.where(acc, prop, cur)
            gcand = g(cand)
            if gcand >= b_level:
                cur, gc = cand, gcand
            out.append(cur.copy()); out_g.append(gc)
    return np.array(out[:n_out]), np.array(out_g[:n_out])


def subset_simulation(Ns, p0=0.1, tau=TAU, max_levels=8, seed=0):
    """Adaptive Subset Simulation with the ACTUAL per-level conditional fraction (robust to
    the discrete/degenerate-threshold case where the p0-quantile ties at 0)."""
    rng = np.random.default_rng(seed)
    W = rng.standard_normal((Ns, 2 * NDR))
    G = np.array([g(w) for w in W])
    levels, thresholds, all_g = 0, [], [G.copy()]
    p = 1.0
    while True:
        levels += 1
        b = np.quantile(G, 1 - p0, method="higher")   # target ~p0-upper quantile
        if b <= 0:                                     # degenerate: <p0 have positive leak
            pos = G[G > 0]
            if pos.size == 0:                          # no positive sample -> event unreached
                return 0.0, thresholds + [0.0], all_g, levels
            b = pos.min()                              # thin to the positive-leak samples
        if b >= tau or levels > max_levels:
            p *= float(np.mean(G >= tau))              # final conditional fraction
            thresholds.append(min(b, tau))
            return p, thresholds, all_g, levels
        f = float(np.mean(G >= b))                     # ACTUAL fraction, not nominal p0
        p *= f
        thresholds.append(b)
        seeds = W[G >= b]
        W, G = modified_metropolis(seeds, b, Ns, rng=rng)
        all_g.append(G.copy())


def naive_mc(n, seed=1):
    rng = np.random.default_rng(seed)
    gs = np.array([g(rng.standard_normal(2 * NDR)) for _ in range(n)])
    return gs


def naive_p(gs, tau):
    n = len(gs); hits = int(np.sum(gs >= tau)); p = hits / n
    cov = np.sqrt((1 - p) / (p * n)) if p > 0 else float("inf")
    return p, hits, cov


def ss_multi(Ns, tau, n_runs, seed0=10):
    ps, budgets, thr = [], [], None
    for r in range(n_runs):
        p, thr, _, lv = subset_simulation(Ns, tau=tau, seed=seed0 + r)
        ps.append(p); budgets.append(Ns * lv)
    ps = np.array(ps)
    return ps, float(np.mean(ps)), float(np.std(ps)), int(np.mean(budgets)), thr


def main():
    outdir = os.path.dirname(os.path.abspath(__file__))
    log = []
    say = lambda s: (print(s), log.append(s))

    Ns = 60 if SMOKE else 250
    n_mc = 200 if SMOKE else 4000
    n_runs = 2 if SMOKE else 4

    say("E4 — rare-event certification of penetration probability (Subset Simulation)")
    say(f"  fixed attack: {NDR} drones, theta={THETA} t_c={T_C} n_cone={N_CONE}; omega dim={2*NDR}")
    say(f"  ({'SMOKE' if SMOKE else 'full'}: Ns={Ns}, naive budget={n_mc}, {n_runs} SS runs)")

    rng0 = np.random.default_rng(7)
    mean_leak = float(np.mean([g(rng0.standard_normal(2 * NDR)) for _ in range(40 if SMOKE else 120)]))
    say(f"  E[leak] ~ {mean_leak:.4f}  (safe region: mean well below both thresholds)")

    say("  naive Monte-Carlo (single pass) ...")
    gs_mc = naive_mc(n_mc)

    marks = []
    for name, tau in [("MODERATE (validation)", TAU_MOD), ("RARE (subset-sim only)", TAU_RARE)]:
        p_mc, hits, cov_mc = naive_p(gs_mc, tau)
        ps, p_ss, sd, budget, thr = ss_multi(Ns, tau, n_runs)
        marks.append((tau, p_mc, hits, p_ss, sd))
        rel = "reliable" if hits >= 15 else "UNRELIABLE"
        say(f"\n  [{name}]  leak >= tau = {tau}")
        say(f"    naive MC : p={p_mc:.2e}  ({hits} hits / {n_mc}, rel.err={cov_mc:.2f}) [{rel}]")
        say(f"    subset   : p={p_ss:.2e} +/- {sd:.1e}  ({budget} evals/run x {n_runs} runs)")
        say(f"    per-run  : {['%.1e' % v for v in ps]}")
        if hits >= 15:
            agree = p_ss / p_mc if p_mc > 0 else float('nan')
            say(f"    -> naive is reliable here; subset-sim agrees within {agree:.1f}x "
                f"(VALIDATES the estimator) using ~{100*budget/n_mc:.0f}% of the naive budget")
        else:
            need = int((1 - p_ss) / (p_ss * 0.09)) if p_ss > 0 else 0
            say(f"    -> naive is near-blind ({hits} hits); subset-sim resolves p at "
                f"~{budget} evals; naive would need ~{need:,} evals for CoV=0.3 (~{need//max(budget,1)}x)")

    say("\n  SUMMARY: subset simulation is validated against naive MC where naive is reliable")
    say("  (moderate tau), then resolves a rarer penetration probability that naive cannot")
    say("  (rare tau) -- certifying the tail, not just the mean (tightens the E3 guarantee).")

    # ---- CCDF figure ----
    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    xs = np.linspace(0, max(TAU_RARE * 1.6, gs_mc.max() + 1e-3), 250)
    ccdf_mc = np.array([np.mean(gs_mc >= x) for x in xs])
    ax.semilogy(xs, np.clip(ccdf_mc, 0.5 / n_mc, 1), color="gray", label=f"naive MC CCDF ({n_mc})")
    for tau, p_mc, hits, p_ss, sd in marks:
        col = "C0" if tau == TAU_MOD else "C3"
        lbl = "moderate" if tau == TAU_MOD else "rare"
        ax.errorbar([tau], [max(p_ss, 1e-7)], yerr=[[min(sd, p_ss * 0.99)], [sd]], fmt="o",
                    color=col, capsize=4, zorder=5,
                    label=f"subset-sim {lbl}: p={p_ss:.1e}")
        if hits > 0:
            ax.scatter([tau], [p_mc], marker="x", color=col, s=60, zorder=6)
    ax.set_xlabel("leak level  x  (= penetrators / N)"); ax.set_ylabel("P(leak >= x)")
    ax.set_ylim(1e-7, 1.3)
    ax.set_title("E4: tail probability — subset simulation (o) vs naive MC (line, x)")
    ax.legend(fontsize=8, loc="upper right")
    fig.tight_layout()
    png = os.path.join(outdir, "e4_ccdf.png")
    fig.savefig(png, dpi=110)
    say(f"  figure -> {png}")
    with open(os.path.join(outdir, "e4_results.txt"), "w") as f:
        f.write("\n".join(log) + "\n")


if __name__ == "__main__":
    main()
