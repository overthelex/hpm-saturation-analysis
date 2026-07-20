#!/usr/bin/env python3
"""E1 — GP surrogate + level-set active learning of the defense failure boundary.

Prototype for research-proposal-certified-defense.md, experiment E1 (surrogate fidelity).

Slice: single aperture, 2-D attack/defense slice (beam half-angle theta, engagement cycle
t_c) at fixed R_eff, R_c, v, N. The angular-saturation model gives a CLOSED-FORM boundary
Sigma = S(theta)*t_c*v/(R_eff-R_c) = 1, i.e. t_c* = (R_eff-R_c)/v * (1-cos theta). We:
  1. treat the simulator as the stochastic oracle L(theta,t_c) = E[leak];
  2. learn L with a GP surrogate under LEVEL-SET ACTIVE LEARNING (straddle acquisition
     targeting the level L = tau);
  3. validate against a dense Monte-Carlo grid (surrogate RMSE), against the analytic
     boundary, and against a same-budget RANDOM design (does active learning win?).

Run:  python3 analysis/e1_gp_surrogate.py
Outputs: analysis/e1_results.txt  and  analysis/e1_surrogate.png
"""
import os
import sys
import math
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim import DefenseConfig, Aperture, ThreatConfig, SimConfig, simulate

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel as C, WhiteKernel

# ---------------- oracle ----------------
R_EFF, R_C, V, N = 500.0, 50.0, 30.0, 80
TAU_TRANSIT = (R_EFF - R_C) / V
SEEDS = 3
DT = 0.03
TAU = 0.15                      # level of interest (meaningful penetration)

THETA_RANGE = (8.0, 32.0)       # deg
TC_RANGE = (0.10, 1.60)         # s


def oracle(theta, t_c, seeds=SEEDS):
    """Stochastic leak oracle at (theta, t_c). n_cone=N clears the cone -> isolate the
    ANGULAR regime, so the boundary is the closed-form Sigma=1."""
    d = DefenseConfig(
        asset_keepout=0.0, r_contact=R_C, fratricide=False,
        apertures=[Aperture(pos=(0, 0, 0), theta_deg=theta, r_eff=R_EFF,
                            t_c=t_c, n_cone=N, el_max_deg=90.0)])
    vals = []
    for s in range(seeds):
        t = ThreatConfig(n=N, v=V, r_spawn=R_EFF * 1.6, el_range_deg=(5, 85),
                         az_range_deg=(0, 360), seed=s)
        vals.append(simulate(d, t, SimConfig(dt=DT)).leak_fraction)
    return float(np.mean(vals))


def analytic_tc(theta_deg):
    """t_c on the Sigma=1 boundary for a given theta (closed form)."""
    return TAU_TRANSIT * (1.0 - math.cos(math.radians(theta_deg)))


# ---------------- normalization ----------------
def to_unit(X):
    x = np.atleast_2d(X).astype(float).copy()
    x[:, 0] = (x[:, 0] - THETA_RANGE[0]) / (THETA_RANGE[1] - THETA_RANGE[0])
    x[:, 1] = (x[:, 1] - TC_RANGE[0]) / (TC_RANGE[1] - TC_RANGE[0])
    return x


def make_gp():
    kernel = C(0.1, (1e-3, 1e1)) * RBF([0.2, 0.2], (1e-2, 5.0)) \
        + WhiteKernel(1e-2, (1e-4, 5e-1))
    return GaussianProcessRegressor(kernel=kernel, normalize_y=True,
                                    n_restarts_optimizer=3, alpha=1e-6)


# ---------------- active learning ----------------
def candidate_grid(nx=41, ny=41):
    th = np.linspace(*THETA_RANGE, nx)
    tc = np.linspace(*TC_RANGE, ny)
    TH, TC = np.meshgrid(th, tc)
    return np.column_stack([TH.ravel(), TC.ravel()])


def active_learn(n_init=8, n_iter=40, seed=0):
    rng = np.random.default_rng(seed)
    cand = candidate_grid()
    # space-filling init (random Latin-ish)
    idx = rng.choice(len(cand), n_init, replace=False)
    X = cand[idx].tolist()
    y = [oracle(*p) for p in X]
    hist = []
    for it in range(n_iter):
        gp = make_gp().fit(to_unit(np.array(X)), np.array(y))
        mu, sd = gp.predict(to_unit(cand), return_std=True)
        # LSE straddle: prefer high uncertainty near the tau level set
        score = 1.96 * sd - np.abs(mu - TAU)
        # avoid re-querying near existing points
        Xa = np.array(X)
        for j, c in enumerate(cand):
            if np.min(np.linalg.norm(to_unit([c]) - to_unit(Xa), axis=1)) < 0.03:
                score[j] = -1e9
        pick = int(np.argmax(score))
        X.append(cand[pick].tolist())
        y.append(oracle(*cand[pick]))
        hist.append(len(X))
    gp = make_gp().fit(to_unit(np.array(X)), np.array(y))
    return gp, np.array(X), np.array(y)


def random_design(n_pts, seed=1):
    rng = np.random.default_rng(seed)
    cand = candidate_grid()
    idx = rng.choice(len(cand), n_pts, replace=False)
    X = cand[idx]
    y = np.array([oracle(*p) for p in X])
    return make_gp().fit(to_unit(X), y), X, y


# ---------------- boundary extraction ----------------
def boundary_tc(pred_fn, thetas, tc_axis):
    """For each theta, the smallest t_c where predicted L crosses TAU (or nan)."""
    out = []
    for th in thetas:
        col = pred_fn(np.column_stack([np.full_like(tc_axis, th), tc_axis]))
        above = np.where(col >= TAU)[0]
        out.append(tc_axis[above[0]] if above.size else np.nan)
    return np.array(out)


def main():
    outdir = os.path.dirname(os.path.abspath(__file__))
    log = []

    def say(s):
        print(s); log.append(s)

    say("E1 — GP surrogate + level-set active learning")
    say(f"  slice: theta in {THETA_RANGE} deg x t_c in {TC_RANGE} s; "
        f"R_eff={R_EFF} v={V} N={N} tau={TAU}")

    # ---- dense MC ground truth ----
    nx, ny = 13, 13
    ths = np.linspace(*THETA_RANGE, nx)
    tcs = np.linspace(*TC_RANGE, ny)
    say(f"  dense MC ground truth: {nx}x{ny}={nx*ny} points x {SEEDS} seeds ...")
    L_true = np.array([[oracle(th, tc) for th in ths] for tc in tcs])  # [tc, theta]

    # fine grid + interpolated MC truth (shared by all evaluations)
    fx, fy = 41, 41
    fths = np.linspace(*THETA_RANGE, fx)
    ftcs = np.linspace(*TC_RANGE, fy)
    FT, FC = np.meshgrid(fths, ftcs)
    grid = np.column_stack([FT.ravel(), FC.ravel()])
    from scipy.interpolate import RegularGridInterpolator
    interp = RegularGridInterpolator((tcs, ths), L_true, bounds_error=False, fill_value=None)
    L_true_fine = interp(np.column_stack([FC.ravel(), FT.ravel()])).reshape(fy, fx)
    tc_analytic = np.array([analytic_tc(t) for t in fths])
    b_true = boundary_tc(lambda P: interp(np.column_stack([P[:, 1], P[:, 0]])), fths, ftcs)

    def eval_gp(gp):
        mu = gp.predict(to_unit(grid)).reshape(fy, fx)
        rmse = float(np.sqrt(np.nanmean((mu - L_true_fine) ** 2)))
        b = boundary_tc(lambda P: gp.predict(to_unit(P)), fths, ftcs)
        m = ~np.isnan(b) & ~np.isnan(b_true)
        b_rmse = float(np.sqrt(np.mean((b[m] - b_true[m]) ** 2))) if m.any() else float("nan")
        return mu, rmse, b_rmse

    # ---- TIGHT budget: this is where level-set targeting should matter ----
    BUDGET = 24
    say(f"  active learning: tight budget = {BUDGET} queries (6 init + 18 straddle) ...")
    gp_al, Xal, yal = active_learn(n_init=6, n_iter=BUDGET - 6)
    mu_al, rmse_al, bnd_al = eval_gp(gp_al)

    say(f"  random baseline: {BUDGET} points x 4 seeds (averaged) ...")
    rnd_rmse, rnd_bnd = [], []
    for sd in range(4):
        gp_r, _, _ = random_design(BUDGET, seed=100 + sd)
        _, rr, br = eval_gp(gp_r)
        rnd_rmse.append(rr); rnd_bnd.append(br)
    rmse_rnd, bnd_rnd = float(np.mean(rnd_rmse)), float(np.nanmean(rnd_bnd))

    say("")
    say(f"  RESULTS (budget = {BUDGET} oracle queries; dense-MC grid = {nx*ny})")
    say(f"    global surrogate RMSE (leak) : AL={rmse_al:.4f}   random={rmse_rnd:.4f}")
    say(f"    BOUNDARY RMSE vs MC (t_c, s) : AL={bnd_al:.3f}    random={bnd_rnd:.3f}   "
        f"<-- level-set metric")
    say(f"    active-learning wins on boundary: {'YES' if bnd_al < bnd_rnd else 'no'} "
        f"(AL is {100*(bnd_rnd-bnd_al)/bnd_rnd:+.0f}% vs random)")
    say(f"    sample efficiency            : {BUDGET} queries vs {nx*ny} dense grid "
        f"({100*BUDGET/(nx*ny):.0f}%), boundary recovered to {bnd_al:.3f}s")

    # ---- figure ----
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.4))
    ext = [THETA_RANGE[0], THETA_RANGE[1], TC_RANGE[0], TC_RANGE[1]]
    for a, (Z, ttl) in zip(ax, [(L_true_fine, "MC ground truth L"),
                                (mu_al, "GP mean (active learning)"),
                                (np.abs(mu_al - L_true_fine), "|GP - MC|")]):
        im = a.imshow(Z, origin="lower", extent=ext, aspect="auto",
                      cmap="viridis", vmin=0, vmax=1 if "err" not in ttl.lower() else None)
        a.plot(fths, tc_analytic, "w--", lw=2, label="analytic Sigma=1")
        a.set_xlabel("theta (deg)"); a.set_ylabel("t_c (s)"); a.set_title(ttl)
        fig.colorbar(im, ax=a, fraction=0.046)
    ax[1].scatter(Xal[:, 0], Xal[:, 1], c="red", s=14, edgecolor="k",
                  lw=0.3, label="AL queries")
    ax[1].legend(loc="upper left", fontsize=7)
    ax[0].legend(loc="upper left", fontsize=7)
    fig.suptitle("E1: level-set active learning of the failure boundary (single-aperture slice)")
    fig.tight_layout()
    png = os.path.join(outdir, "e1_surrogate.png")
    fig.savefig(png, dpi=110)
    say(f"  figure -> {png}")

    with open(os.path.join(outdir, "e1_results.txt"), "w") as f:
        f.write("\n".join(log) + "\n")


if __name__ == "__main__":
    main()
