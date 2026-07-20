#!/usr/bin/env python3
"""Export E1-E4 figure data to CSV (for unified ggplot2 rendering in figures/make_figures.R).

Reuses the functions from the e1..e4 scripts so the exported data matches the experiments.
Figure-fidelity settings (slightly reduced budgets) for speed; the precise reported numbers
live in analysis/E{1,2,3,4}-results.md.
Run:  python3 analysis/export_e_data.py
"""
import os
import sys
import importlib.util
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(os.path.dirname(HERE), "figures")
sys.path.insert(0, os.path.dirname(HERE))


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, f"{name}.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def save_csv(path, header, rows):
    import csv
    with open(path, "w", newline="") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)
    print("wrote", os.path.basename(path), len(rows), "rows")


# ---------------- E1 ----------------
def export_e1():
    e1 = load("e1_gp_surrogate")
    ths = np.linspace(*e1.THETA_RANGE, 13); tcs = np.linspace(*e1.TC_RANGE, 13)
    Ltrue = np.array([[e1.oracle(t, c) for t in ths] for c in tcs])
    gp, Xal, _ = e1.active_learn(n_init=6, n_iter=18)
    fx, fy = 41, 41
    fths = np.linspace(*e1.THETA_RANGE, fx); ftcs = np.linspace(*e1.TC_RANGE, fy)
    FT, FC = np.meshgrid(fths, ftcs)
    grid = np.column_stack([FT.ravel(), FC.ravel()])
    mu = gp.predict(e1.to_unit(grid))
    from scipy.interpolate import RegularGridInterpolator
    interp = RegularGridInterpolator((tcs, ths), Ltrue, bounds_error=False, fill_value=None)
    Lt = interp(np.column_stack([FC.ravel(), FT.ravel()]))
    rows = [[f"{t:.3f}", f"{c:.3f}", f"{m:.4f}", f"{l:.4f}"]
            for (t, c), m, l in zip(grid, mu, Lt)]
    save_csv(os.path.join(FIG, "data_e1_grid.csv"), ["theta", "t_c", "gp_mean", "L_true"], rows)
    save_csv(os.path.join(FIG, "data_e1_queries.csv"), ["theta", "t_c"],
             [[f"{x:.3f}", f"{y:.3f}"] for x, y in Xal])


# ---------------- E2 ----------------
def export_e2():
    e2 = load("e2_adversarial")
    base = e2.leak_of(e2.defense(), dict(scenario="S0", el_range=(5, 55), r_spawn=900))
    r1, t1 = e2.run(e2.obj1, [(0, 1)] * 4, "geom", seed=1)
    r2, t2 = e2.run(e2.obj2, [(0, 1)] * 3, "hard", seed=2)

    def best(tr):
        b, o = 0.0, []
        for v in tr:
            b = max(b, v); o.append(b)
        return o
    rows = []
    for i, v in enumerate(best(t1)):
        rows.append([i, "geometry -> zenith drop", f"{v:.4f}"])
    for i, v in enumerate(best(t2)):
        rows.append([i, "hardening -> R_eff collapse", f"{v:.4f}"])
    save_csv(os.path.join(FIG, "data_e2_trace.csv"), ["eval", "search", "best_leak"], rows)
    save_csv(os.path.join(FIG, "data_e2_baseline.csv"), ["baseline_leak"], [[f"{base:.4f}"]])


# ---------------- E3 ----------------
def export_e3():
    e3 = load("e3_certify")
    rng = np.random.default_rng(0)
    Xtr, ytr = e3.sample(rng, 36); gp = e3.make_gp().fit(e3.to_unit(Xtr), ytr)
    Xcal, ycal = e3.sample(rng, 36)
    q = e3.conformal_q(ycal - gp.predict(e3.to_unit(Xcal)), e3.ALPHA)
    fx, fy = 41, 41
    fths = np.linspace(*e3.THETA_RANGE, fx); ftcs = np.linspace(*e3.TC_RANGE, fy)
    FT, FC = np.meshgrid(fths, ftcs)
    grid = np.column_stack([FT.ravel(), FC.ravel()])
    mu = gp.predict(e3.to_unit(grid)); U = mu + q
    tx, ty = 13, 13
    gth = np.linspace(*e3.THETA_RANGE, tx); gtc = np.linspace(*e3.TC_RANGE, ty)
    Ltru = np.array([[e3.oracle(t, c, seeds=5) for t in gth] for c in gtc])
    from scipy.interpolate import RegularGridInterpolator
    interp = RegularGridInterpolator((gtc, gth), Ltru, bounds_error=False, fill_value=None)
    Lt = interp(np.column_stack([FC.ravel(), FT.ravel()]))
    rows = [[f"{t:.3f}", f"{c:.3f}", f"{m:.4f}", f"{u:.4f}", f"{l:.4f}",
             int(u < e3.TAU), int((u < e3.TAU) and (l >= e3.TAU))]
            for (t, c), m, u, l in zip(grid, mu, U, Lt)]
    save_csv(os.path.join(FIG, "data_e3_grid.csv"),
             ["theta", "t_c", "gp_mean", "U", "L_true", "certified", "false_safe"], rows)
    with open(os.path.join(FIG, "data_e3_meta.csv"), "w") as f:
        f.write(f"tau,alpha,q\n{e3.TAU},{e3.ALPHA},{q:.4f}\n")
    print("wrote data_e3_meta.csv")


# ---------------- E4 ----------------
def export_e4():
    e4 = load("e4_rare_event")
    gs = e4.naive_mc(3000)
    xs = np.linspace(0, max(e4.TAU_RARE * 1.6, gs.max() + 1e-3), 200)
    ccdf = [np.mean(gs >= x) for x in xs]
    save_csv(os.path.join(FIG, "data_e4_ccdf.csv"), ["x", "ccdf"],
             [[f"{x:.4f}", f"{c:.6f}"] for x, c in zip(xs, ccdf)])
    marks = []
    for name, tau in [("moderate", e4.TAU_MOD), ("rare", e4.TAU_RARE)]:
        p_mc, hits, _ = e4.naive_p(gs, tau)
        ps, p_ss, sd, _, _ = e4.ss_multi(250, tau, 3)
        marks.append([name, f"{tau:.4f}", f"{p_mc:.3e}", hits, f"{p_ss:.3e}", f"{sd:.3e}"])
    save_csv(os.path.join(FIG, "data_e4_marks.csv"),
             ["level", "tau", "p_naive", "naive_hits", "p_subset", "subset_sd"], marks)


if __name__ == "__main__":
    which = sys.argv[1:] or ["e1", "e2", "e3", "e4"]
    if "e1" in which: export_e1()
    if "e2" in which: export_e2()
    if "e3" in which: export_e3()
    if "e4" in which: export_e4()
    print("done:", which)
