#!/usr/bin/env python3
"""Demo driver for the HPM counter-swarm simulation (stages 0-2).

Run:  python3 run_sim.py

Prints three headline results that map to hpm-saturation-model.md and the pitch memo:
  A. Pencil vs shield  — angular saturation (Sigma = T_r/tau), the beam-width lever.
  B. Leak-rate curve    — leak(N) for a pencil aperture, with N_min / N_10%.
  C. Interior blind volume — ring, fratricide ON vs OFF (the §8 rear-attack).
"""
import math
from sim import DefenseConfig, Aperture, ThreatConfig, SimConfig, simulate


def sectors(th):      return 1.0 / (1.0 - math.cos(math.radians(th)))
def sigma(th, tc, v, reff, rc): return sectors(th) * tc / ((reff - rc) / v)


def single(theta, tc, v, n, n_cone=1, reff=500, rc=50, seed=0):
    d = DefenseConfig(asset_keepout=0.0, r_contact=rc, fratricide=False,
                      apertures=[Aperture(theta_deg=theta, r_eff=reff, t_c=tc,
                                          n_cone=n_cone, el_max_deg=90.0)])
    t = ThreatConfig(n=n, v=v, r_spawn=reff * 1.6, el_range_deg=(5, 85), seed=seed)
    return simulate(d, t, SimConfig(dt=0.02))


def section(title): print("\n" + "=" * 68 + f"\n{title}\n" + "=" * 68)


# ---- A. pencil vs shield --------------------------------------------------
section("A. Angular saturation: pencil vs shield (one-to-many pulse)")
N = int(round(sectors(8)))
for th in (8, 15, 25, 40):
    m = single(th, tc=0.5, v=30, n=N, n_cone=N)
    print(f"  theta={th:2d}deg  S={sectors(th):5.1f}  Sigma={sigma(th,0.5,30,500,50):4.2f}"
          f"  -> leak={m.leak_fraction:.2f}  ({'BREACH' if m.leak_fraction>0.05 else 'holds'})")

# ---- B. leak-rate curve over N -------------------------------------------
section("B. Leak-rate curve leak(N): pencil theta=8, t_c=0.3, n_cone=3, v=30")
prev = 0.0
n_min = n_10 = None
for n in (20, 40, 60, 80, 100, 150, 200, 300):
    m = single(8, tc=0.3, v=30, n=n, n_cone=3)
    if n_min is None and m.leaked >= 1:  n_min = n
    if n_10 is None and m.leak_fraction >= 0.10:  n_10 = n
    print(f"  N={n:3d}  leak={m.leak_fraction:.3f}  killed_before_1st_leak={m.kills_before_first_leak}")
print(f"  -> N_min(>=1 leaker) ~ {n_min};  N_10% ~ {n_10}")

# ---- C. interior blind volume (ring, fratricide) -------------------------
section("C. Interior blind volume: ring M=6, rear-spawned swarm, fratricide ON vs OFF")
common = dict(theta_deg=20.0, r_eff=600, t_c=0.3, n_cone=2, el_max_deg=85.0)
threat = ThreatConfig(n=40, v=25, r_spawn=120, el_range_deg=(3, 18), seed=1)
for label, frat in (("ON  (unhardened, static)", True), ("OFF (hardened friendlies)", False)):
    ring = DefenseConfig.ring(6, r_ring=200, **common)
    ring.fratricide = frat
    ring.asset_keepout = 25.0
    m = simulate(ring, threat, SimConfig(dt=0.02))
    print(f"  fratricide {label}: leak={m.leak_fraction:.2f}  killed={m.killed}"
          f"  fratricide_holds={m.holds_fratricide}")

print("\n(These map to model §5/§7 (A), §6 (B), §8 (C). Numbers are order-of-magnitude "
      "on open assumptions — see hpm-saturation-model.md §10.)")
