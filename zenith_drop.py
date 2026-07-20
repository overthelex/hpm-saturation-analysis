#!/usr/bin/env python3
"""Zenith-drop attack: climb over the centre, cut power, free-fall onto the target.

Run:  python3 zenith_drop.py

The exploit combines two things the calibration exposed:
  1. Zenith gap — corner installations with elevation limit el_max cannot point straight up;
     directly over the centre there is a cone of silence above h = r_ring*tan(el_max).
  2. Soft-kill physics — HPM defeats drones by loss-of-control (E50~200 V/m). A drone that
     has ALREADY cut power for a ballistic fall is inert mass; zapping it does nothing.
     (Same class as the Shahed problem: you stop control, not mass.)

So a drone that reaches the drop point unpowered cannot be stopped by HPM. The questions:
  (a) can the swarm reach the apogee (it must CLIMB there, powered & killable)?
  (b) once dropping, does it hit? (unguided fall has drift/CEP)
  (c) what actually stops it — the kinetic layer CAN hit falling mass.

Defense: 4 installations at the corners of a 100 m hectare (calibrated theta=30, n_cone=49).
"""
import statistics as st
from sim import DefenseConfig, Aperture, ThreatConfig, SimConfig, simulate

SEEDS = range(4)
SIM = SimConfig(dt=0.03)
CORNERS = [(50, 50, 3), (-50, 50, 3), (-50, -50, 3), (50, -50, 3)]


def hectare(r_eff=500, el_max=80.0, **over):
    aps = [Aperture(pos=p, theta_deg=30.0, r_eff=r_eff, t_c=1.0,
                    n_cone=49, el_max_deg=el_max) for p in CORNERS]
    d = DefenseConfig(apertures=aps, asset_pos=(0, 0, 0),
                      r_contact=15.0, ap_contact=8.0, asset_keepout=10.0)
    for k, v in over.items():
        setattr(d, k, v)
    return d


def mc(dfac, scenario, n, apogee=450, v=30, el_range=(35, 80), r_spawn=None):
    rs = r_spawn if r_spawn is not None else max(800, apogee + 400)
    def tf(s):
        return ThreatConfig(n=n, v=v, r_spawn=rs, scenario=scenario, seed=s,
                            el_range_deg=el_range, apogee_h=apogee, fall_v=25, fall_drift=3)
    return st.mean(simulate(dfac(), tf(s), SIM).leak_fraction for s in SEEDS)


def section(t): print("\n" + "=" * 74 + f"\n{t}\n" + "=" * 74)


section("A. Direct approach vs zenith-drop (naive spread vs deliberate) — R_eff=500")
for n in (100, 300, 600):
    direct = mc(lambda: hectare(), "S0", n)
    drop_spread = mc(lambda: hectare(), "S6", n, el_range=(35, 80))
    drop_conc = mc(lambda: hectare(), "S6", n, el_range=(81, 88))
    print(f"  N={n:3d}   direct={direct:.2f}   drop(spread)={drop_spread:.2f}   "
          f"drop(concentrated in cone)={drop_conc:.2f}")
print("  -> direct fails; a naive high approach only trickles a few % into the 10deg cone;")
print("     concentrating the approach INTO the cone of silence bypasses the soft-kill wholesale")

section("B. Elevation limit vs a DELIBERATE overhead drop (concentrated just above el_max)")
import math
r_ring = math.hypot(50, 50)
for el_max in (75, 80, 85, 88):
    floor = r_ring * math.tan(math.radians(el_max))   # altitude where the cone of silence begins
    apg = max(floor + 60, 200)
    leak = mc(lambda el_max=el_max: hectare(el_max=el_max), "S6", 300,
              apogee=apg, el_range=(el_max + 0.5, min(el_max + 6, 89.5)))
    print(f"  el_max={el_max}deg -> cone floor over centre = {floor:5.0f} m, drop from {apg:.0f} m: "
          f"leak={leak:.2f}")
print("  -> a deliberate attacker always finds the residual cone; raising el_max only forces")
print("     the drop from a higher floor (264 m -> 4 km at 89deg), worsening CEP & climb exposure")

section("C. What stops the concentrated drop: kinetic layer (hits inert falling mass)")
base = mc(lambda: hectare(), "S6", 300, el_range=(81, 88))
for rate, mag in ((8, 300), (16, 600), (32, 1200)):
    leak = mc(lambda rate=rate, mag=mag: hectare(kin_radius=90, kin_rate=rate,
              kin_magazine=mag, kin_pk=0.85), "S6", 300, el_range=(81, 88))
    print(f"  + kinetic rate={rate:2d}/s mag={mag}: drop leak={leak:.2f}")
print(f"  (baseline HPM-only concentrated-drop leak = {base:.2f})")
print("  -> HPM alone cannot stop the drop; kinetic point-defense is the required counter")
