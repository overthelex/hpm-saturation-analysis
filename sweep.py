#!/usr/bin/env python3
"""Parameter sweeps → the numbers behind the pitch-memo fixes (stages 3-5).

Run:  python3 sweep.py     (~1-2 min; Monte-Carlo over seeds)

Three results, each on a config chosen to expose the mechanism honestly:
  D. ISR value  — a SPARSE narrow-beam ring (real azimuthal gaps): knowing the seam
                  layout buys the attacker ΔL_ISR of extra breakthrough. A denser ring
                  (M>=4 here) closes the gaps outright — also shown.
  E. Mobility   — same sparse ring, orbiting: the seams the swarm aimed at drift away,
                  knocking the perfect-ISR advantage back down. Validates "mobile Leonidas".
  F. Hybrid     — a SATURATED ring (rear-leak > 0): an inner kinetic bubble closes the
                  interior HPM cannot fire into. Sizes the hybrid fix (rate × magazine).

Honest caveat: mobility only helps when the attack DEPENDS on stale seam knowledge; against
raw saturation it does nothing (see F's baseline). Numbers are order-of-magnitude on open
assumptions (hpm-saturation-model.md §10). All simplifications tighten the defensive bound.
"""
import statistics as st
from sim import DefenseConfig, ThreatConfig, SimConfig, simulate

SEEDS = range(5)
SIM = SimConfig(dt=0.03)


def mc_leak(defense_factory, threat_factory):
    return st.mean(simulate(defense_factory(), threat_factory(s), SIM).leak_fraction
                   for s in SEEDS)


def sparse_ring(M=3, **over):
    """Narrow-beam ring with genuine inter-aperture gaps (seam-exploitable)."""
    d = DefenseConfig.ring(M, r_ring=160, theta_deg=7.0, r_eff=450,
                           t_c=0.35, n_cone=2, el_max_deg=80.0)
    d.asset_keepout = 25.0
    for k, v in over.items():
        setattr(d, k, v)
    return d


def saturated_ring(**over):
    """Short-range ring driven into saturation so survivors reach the interior."""
    d = DefenseConfig.ring(6, r_ring=150, theta_deg=10.0, r_eff=250,
                           t_c=0.4, n_cone=1, el_max_deg=78.0)
    d.asset_keepout = 25.0
    for k, v in over.items():
        setattr(d, k, v)
    return d


def threat(scenario, isr, n=250, v=36, r_spawn=1000):
    return lambda s: ThreatConfig(n=n, v=v, r_spawn=r_spawn, el_range_deg=(4, 45),
                                  scenario=scenario, isr=isr, seed=s,
                                  seam_az_spread_deg=4.0, seam_zenith_frac=0.15)


def section(t): print("\n" + "=" * 70 + f"\n{t}\n" + "=" * 70)


# ---- D. Cost of knowing the configuration (ISR value) --------------------
section("D. ISR value  ΔL = leak(perfect seam-routing) − leak(blind)")
for M in (3, 4):
    tag = "sparse, has gaps" if M == 3 else "denser, gaps closed"
    blind = mc_leak(lambda M=M: sparse_ring(M), threat("S0", "blind"))
    perf = mc_leak(lambda M=M: sparse_ring(M), threat("S4", "perfect"))
    print(f"  M={M} ({tag:18s})  blind={blind:.3f}  perfect-ISR={perf:.3f}"
          f"  ΔL_ISR={perf-blind:+.3f}")
print("  -> seams are worth ΔL_ISR to an attacker that knows the layout; deny it (EMCON) "
      "or move it (E)")

# ---- E. Mobility invalidates ISR (sparse ring vs perfect-ISR swarm) -------
section("E. Mobility: leak vs ring orbit_rate, M=3 sparse ring, perfect-ISR swarm")
for w in (0.0, 0.15, 0.4, 0.8):
    leak = mc_leak(lambda w=w: sparse_ring(3, orbit_rate=w), threat("S4", "perfect"))
    print(f"  orbit_rate={w:4.2f} rad/s (~{w*160:5.1f} m/s at rim)  leak={leak:.3f}")
print("  -> rotating the ring drifts the seams away from where the swarm aimed -> edge lost")

# ---- F. Hybrid sizing: inner kinetic layer closes the rear ---------------
section("F. Hybrid: residual leak vs inner kinetic layer (saturated ring, N=300)")
base = mc_leak(lambda: saturated_ring(), threat("S0", "blind", n=300))
print(f"  baseline, no kinetic:  leak={base:.3f}  (rear-leak to be closed)")
print("  kinetic bubble radius=150 m, pk=0.9 ; sweep rate × magazine:")
for rate in (2.0, 4.0, 8.0):
    row = []
    for mag in (60, 150, 300):
        leak = mc_leak(
            lambda rate=rate, mag=mag: saturated_ring(
                kin_radius=150.0, kin_rate=rate, kin_magazine=mag, kin_pk=0.9),
            threat("S0", "blind", n=300))
        row.append(f"{leak:.3f}")
    print(f"    rate={rate:4.1f}/s  mag=60/150/300 -> " + " / ".join(row))
print("  -> HPM ring + a modest kinetic bubble drives interior rear-leak toward 0")

print("\n(D→EMCON/deny-ISR, E→mobile Leonidas, F→hybrid layer. Honest: mobility helps only "
      "where ISR-dependence exists; kinetic is the robust closer.)")
