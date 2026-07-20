#!/usr/bin/env python3
"""Export real simulator trajectories to JSON for the Three.js 3D viewer (viz/index.html).

Runs several scenarios on the calibrated hectare defense, records drone positions + states
per subsampled frame, and writes viz/trajectories.json. The viewer plays these back in 3D.
Run:  python3 viz/export_trajectories.py
"""
import os
import sys
import json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from sim import DefenseConfig, Aperture, ThreatConfig, SimConfig
from sim.engine import World, ALIVE, KILLED, LEAKER, ESCAPED

CORNERS = [(50, 50, 3), (-50, 50, 3), (-50, -50, 3), (50, -50, 3)]
N = 120
DT = 0.04
REC = 4                      # record every REC ticks (~0.16 s)


def defense(r_eff=500.0, t_c=1.0, el_max=80.0):
    aps = [Aperture(pos=p, theta_deg=30.0, r_eff=r_eff, t_c=t_c, n_cone=49, el_max_deg=el_max)
           for p in CORNERS]
    return DefenseConfig(apertures=aps, asset_pos=(0, 0, 0),
                         r_contact=15.0, ap_contact=8.0, asset_keepout=10.0)


def record(defense_cfg, threat):
    w = World(defense_cfg, threat, SimConfig(dt=DT))
    d0 = np.linalg.norm(w.pos - w.asset, axis=1).max()
    t_max = (d0 - defense_cfg.r_contact) / max(threat.v, 1e-6) * 1.35
    nsteps = int(t_max / DT)
    frames = []
    prev = w.status.copy()
    for k in range(nsteps):
        if not np.any(w.status == ALIVE):
            break
        w.step()
        if k % REC == 0:
            killed_now = np.flatnonzero((w.status == KILLED) & (prev != KILLED))
            frames.append({
                "t": round(w.time, 2),
                "pos": [[round(float(x), 1) for x in p] for p in w.pos],
                "st": [int(s) for s in w.status],
                "killed": [int(i) for i in killed_now],
            })
            prev = w.status.copy()
    # final frame (resolve leftovers as run() does)
    d_asset = np.linalg.norm(w.pos - w.asset, axis=1)
    leftover = (w.status == ALIVE) & (d_asset < float(max(a.r_eff for a in defense_cfg.apertures)))
    w.status[leftover] = LEAKER
    w.status[w.status == ALIVE] = ESCAPED
    frames.append({"t": round(w.time, 2),
                   "pos": [[round(float(x), 1) for x in p] for p in w.pos],
                   "st": [int(s) for s in w.status], "killed": []})
    killed = int(np.sum(w.status == KILLED))
    leaked = int(np.sum(w.status == LEAKER))
    return frames, killed, leaked


SCENARIOS = [
    ("Direct — defense holds", defense(),
     dict(scenario="S0", v=32, el_range=(5, 55), r_spawn=700)),
    ("Zenith drop — top attack", defense(),
     dict(scenario="S6", v=30, el_range=(80, 87), apogee_h=550, r_spawn=1000)),
    ("Hardened swarm — R_eff collapse", defense(r_eff=60.0),
     dict(scenario="S0", v=30, el_range=(5, 55), r_spawn=700)),
    ("High-speed 600 km/h", defense(t_c=1.3),
     dict(scenario="S0", v=167, el_range=(5, 55), r_spawn=700)),
]


def main():
    out = {"meta": {"asset": [0, 0, 0], "apertures": [list(c) for c in CORNERS],
                    "r_contact": 15, "ap_contact": 8, "hectare": 100, "n": N},
           "scenarios": []}
    for name, dcfg, tk in SCENARIOS:
        threat = ThreatConfig(n=N, v=tk["v"], r_spawn=tk["r_spawn"], scenario=tk["scenario"],
                              el_range_deg=tk["el_range"], apogee_h=tk.get("apogee_h", 400),
                              isr="blind", seed=1)
        frames, killed, leaked = record(dcfg, threat)
        out["scenarios"].append({"name": name, "frames": frames,
                                 "killed": killed, "leaked": leaked, "n": N})
        print(f"{name:36s} frames={len(frames):3d} killed={killed} leaked={leaked}")
    path = os.path.join(HERE, "trajectories.json")
    with open(path, "w") as f:
        json.dump(out, f, separators=(",", ":"))
    print("wrote", path, f"({os.path.getsize(path)//1024} KB)")


if __name__ == "__main__":
    main()
