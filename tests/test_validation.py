"""Validation: the sim MUST reproduce the closed-form model before we trust it.

Run:  python3 -m pytest tests/ -q      (from ~/epirus/)
  or: python3 tests/test_validation.py  (prints a report, no pytest needed)

Checks (hpm-swarm-sim-design.md §7):
  1. Single aperture, S0: leak boundary matches T_r/tau (Sigma>1 -> leak; Sigma<1 -> ~0)
  2. Limit cases: v->0 => leak->0 ; theta->90 => S->1 no angular saturation
  3. Fratricide-off on a ring => interior blind volume closes (rear leak -> 0)
  4. Determinism: same seed => identical result
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sim import DefenseConfig, Aperture, ThreatConfig, SimConfig, simulate


def sectors(theta_deg):
    return 1.0 / (1.0 - math.cos(math.radians(theta_deg)))


def sigma(theta_deg, t_c, v, r_eff, r_c):
    S = sectors(theta_deg)
    T_r = S * t_c
    tau = (r_eff - r_c) / v
    return T_r / tau


def _single(theta_deg, t_c, v, n, seed=0, n_cone=1, r_eff=500, r_c=50):
    d = DefenseConfig(
        asset_keepout=0.0,          # isolate angular effect (no fratricide for 1 aperture)
        r_contact=r_c,
        apertures=[Aperture(pos=(0, 0, 0), theta_deg=theta_deg, r_eff=r_eff,
                            t_c=t_c, n_cone=n_cone, el_max_deg=90.0)],
        fratricide=False,
    )
    t = ThreatConfig(n=n, v=v, r_spawn=r_eff * 1.6,
                     el_range_deg=(5.0, 85.0), az_range_deg=(0.0, 360.0), seed=seed)
    return simulate(d, t, SimConfig(dt=0.02))


def test_angular_boundary():
    """Isolate the ANGULAR regime: pulse clears the whole cone (one-to-many),
    so the only limit is beam revisit. Sigma>1 must leak; Sigma<1 must hold.
    n_cone=n removes the service (temporal) limit so §5 is tested cleanly."""
    th = 8.0
    S = sectors(th)
    n = int(round(S))
    sig = sigma(th, t_c=0.5, v=30, r_eff=500, r_c=50)
    m_sat = _single(th, t_c=0.5, v=30, n=n, n_cone=n)
    # non-saturating wide shield, same load, same one-to-many
    sig2 = sigma(40.0, t_c=0.5, v=30, r_eff=500, r_c=50)
    m_hold = _single(40.0, t_c=0.5, v=30, n=n, n_cone=n)
    assert sig > 1.0 and m_sat.leak_fraction > 0.1, (sig, m_sat)
    assert sig2 < 1.0 and m_hold.leak_fraction < 0.05, (sig2, m_hold)
    return sig, m_sat, sig2, m_hold


def test_limit_slow_targets():
    """v->0 : transit time huge => everything serviced => leak ~ 0."""
    m = _single(8.0, t_c=0.5, v=2.0, n=int(round(sectors(8.0))))
    assert m.leak_fraction < 0.05, m
    return m


def test_limit_wide_beam():
    """theta->90 : S->1, one shot covers the hemisphere => no angular saturation."""
    m = _single(80.0, t_c=0.5, v=30, n=60, n_cone=60)
    assert m.leak_fraction < 0.05, m
    return m


def test_fratricide_off_closes_interior():
    """Interior blind volume (§8.2 / scenario S4): drones that have already crossed the
    ring sit in the rear of every aperture. Firing at them means firing across the asset
    (fratricide) -> with the mask ON they cannot be engaged and leak; with the mask OFF
    (idealized: friendlies hardened) they are engaged and killed. This isolates the
    mechanism by spawning the swarm INSIDE the ring."""
    common = dict(theta_deg=20.0, r_eff=600, t_c=0.3, n_cone=2, el_max_deg=85.0)
    # r_spawn=120 is inside the ring radius 200 -> swarm starts in the rear
    threat = ThreatConfig(n=40, v=25, r_spawn=120, el_range_deg=(3, 18), seed=1)
    ring_on = DefenseConfig.ring(6, r_ring=200, **common)
    ring_on.fratricide = True
    ring_on.asset_keepout = 25.0
    ring_off = DefenseConfig.ring(6, r_ring=200, **common)
    ring_off.fratricide = False
    ring_off.asset_keepout = 25.0
    m_on = simulate(ring_on, threat, SimConfig(dt=0.02))
    m_off = simulate(ring_off, threat, SimConfig(dt=0.02))
    # ON: low-central interior is a blind volume -> substantial leak; OFF: engageable -> ~0.
    # (High-altitude interior drones can be hit from the far side at an upward angle that
    #  clears the asset, so the blind volume is the low, central sector — not the whole interior.)
    assert m_off.leak_fraction < 0.1, m_off
    assert m_on.leak_fraction > m_off.leak_fraction + 0.15, (m_on, m_off)
    assert m_off.holds_fratricide == 0, m_off
    assert m_on.holds_fratricide > 0, m_on   # mask actually blocked engageable targets
    return m_on, m_off


def test_determinism():
    a = _single(8.0, 0.5, 30, 40, seed=7)
    b = _single(8.0, 0.5, 30, 40, seed=7)
    assert (a.killed, a.leaked) == (b.killed, b.leaked)
    return a, b


# ---- stage 3-4 mechanisms -------------------------------------------------
def _sparse(M=3, **over):
    d = DefenseConfig.ring(M, r_ring=160, theta_deg=7.0, r_eff=450,
                           t_c=0.35, n_cone=2, el_max_deg=80.0)
    d.asset_keepout = 25.0
    for k, v in over.items():
        setattr(d, k, v)
    return d


def _mc(dfac, scenario, isr, seeds=5, n=250):
    import statistics as stat
    return stat.mean(
        simulate(dfac(),
                 ThreatConfig(n=n, v=36, r_spawn=1000, el_range_deg=(4, 45),
                              scenario=scenario, isr=isr, seed=s, seam_az_spread_deg=4.0,
                              seam_zenith_frac=0.15),
                 SimConfig(dt=0.03)).leak_fraction
        for s in range(seeds))


def test_isr_value_positive():
    """Perfect seam-routing must beat blind on a sparse ring with real gaps (§8 / S3)."""
    blind = _mc(lambda: _sparse(3), "S0", "blind")
    perfect = _mc(lambda: _sparse(3), "S4", "perfect")
    assert perfect > blind, (blind, perfect)
    return blind, perfect


def test_mobility_reduces_leak():
    """Orbiting the ring invalidates the swarm's stale seam knowledge -> leak falls."""
    still = _mc(lambda: _sparse(3, orbit_rate=0.0), "S4", "perfect")
    moving = _mc(lambda: _sparse(3, orbit_rate=0.8), "S4", "perfect")
    assert moving < still, (still, moving)
    return still, moving


def test_kinetic_closes_rear():
    """An inner kinetic bubble drives interior rear-leak down (hybrid fix, §8 lock 3)."""
    def sat(**o):
        d = DefenseConfig.ring(6, r_ring=150, theta_deg=10.0, r_eff=250,
                               t_c=0.4, n_cone=1, el_max_deg=78.0)
        d.asset_keepout = 25.0
        for k, v in o.items():
            setattr(d, k, v)
        return d
    base = _mc(lambda: sat(), "S0", "blind", n=300)
    hybrid = _mc(lambda: sat(kin_radius=150.0, kin_rate=8.0, kin_magazine=300, kin_pk=0.9),
                 "S0", "blind", n=300)
    assert hybrid < base - 0.15, (base, hybrid)
    return base, hybrid


if __name__ == "__main__":
    print("== angular boundary (Sigma>1 leaks, Sigma<1 holds) ==")
    sig, msat, sig2, mhold = test_angular_boundary()
    print(f"  pencil 8deg  Sigma={sig:.2f}  {msat}")
    print(f"  shield 40deg Sigma={sig2:.2f}  {mhold}")
    print("== limit: slow targets v=2 ==")
    print("  ", test_limit_slow_targets())
    print("== limit: wide beam theta=80 ==")
    print("  ", test_limit_wide_beam())
    print("== fratricide off closes interior (ring M=6) ==")
    on, off = test_fratricide_off_closes_interior()
    print("  ON :", on)
    print("  OFF:", off)
    print("== determinism ==")
    a, b = test_determinism()
    print(f"  {a.killed},{a.leaked} == {b.killed},{b.leaked}")
    print("== ISR value (perfect seam-routing > blind, sparse ring) ==")
    bl, pf = test_isr_value_positive()
    print(f"  blind={bl:.3f}  perfect-ISR={pf:.3f}")
    print("== mobility reduces leak (orbiting invalidates ISR) ==")
    stll, mov = test_mobility_reduces_leak()
    print(f"  static={stll:.3f}  orbiting={mov:.3f}")
    print("== kinetic layer closes the rear ==")
    base, hyb = test_kinetic_closes_rear()
    print(f"  base={base:.3f}  hybrid={hyb:.3f}")
    print("\nALL VALIDATION CHECKS PASSED")
