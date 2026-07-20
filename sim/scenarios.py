"""Swarm spawn/guidance scenarios (abstract maneuvers).

These are POLICIES over spawn geometry and re-aim, parameterized by ISR level.
Defensive framing: they exist to find where the line fails, not to plan an attack
on a real object. Coordinates are notional; guidance is a simple heading policy.
"""
from __future__ import annotations

import numpy as np

from .config import ThreatConfig, DefenseConfig


def _sample_shell(rng, n, r_spawn, az_range_deg, el_range_deg, center):
    """Sample n points on a spherical shell sector, return positions (n,3)."""
    az0, az1 = np.radians(az_range_deg)
    el0, el1 = np.radians(el_range_deg)
    az = rng.uniform(az0, az1, n)
    # uniform in cos(el) would bias to horizon; keep uniform-in-elevation for control
    el = rng.uniform(el0, el1, n)
    x = r_spawn * np.cos(el) * np.cos(az)
    y = r_spawn * np.cos(el) * np.sin(az)
    z = r_spawn * np.sin(el)
    pos = np.stack([x, y, z], axis=1) + np.asarray(center, float)
    return pos


def _gap_azimuths(defense: DefenseConfig):
    """Azimuths (rad) of the inter-aperture gaps of a ring, from INITIAL positions.

    This is what a swarm with perfect ISR knows at launch. If the ring orbits
    (defense.orbit_rate != 0), by arrival the real gaps have rotated away — the
    staleness that mobility exploits (handled in the engine, not here).
    """
    ap = np.asarray([a.pos for a in defense.apertures], float)
    center = np.asarray(defense.asset_pos, float)
    phi = np.arctan2(ap[:, 1] - center[1], ap[:, 0] - center[0])
    phi = np.sort(phi)
    # midpoint between consecutive apertures (wrap-around included)
    mids = []
    for i in range(len(phi)):
        a0 = phi[i]
        a1 = phi[(i + 1) % len(phi)] + (2 * np.pi if i == len(phi) - 1 else 0.0)
        mids.append((a0 + a1) / 2.0)
    return np.array(mids)


def _seam_spawn(rng, threat, defense, center):
    """Perfect-ISR spawn: concentrate arrivals into the defensive seams —
    low-central corridors between apertures (→ interior blind volume) plus a
    fraction through the zenith gap. Defensive stress test of 'attacker knows config'."""
    n = threat.n
    r = threat.r_spawn
    el_max = min(a.el_max_deg for a in defense.apertures)
    gaps = _gap_azimuths(defense)

    n_zen = int(round(n * threat.seam_zenith_frac))
    n_low = n - n_zen

    # low corridors through the gaps
    g = gaps[rng.integers(0, len(gaps), n_low)]
    az_low = g + np.radians(threat.seam_az_spread_deg) * rng.standard_normal(n_low)
    el_low = np.radians(rng.uniform(threat.el_range_deg[0],
                                    threat.el_range_deg[0] + 10.0, n_low))
    # zenith gap: any azimuth, elevation just above what apertures can point to
    az_zen = rng.uniform(0, 2 * np.pi, n_zen)
    el_zen = np.radians(rng.uniform(el_max + 1.0, min(el_max + 8.0, 89.0), n_zen))

    az = np.concatenate([az_low, az_zen])
    el = np.concatenate([el_low, el_zen])
    x = r * np.cos(el) * np.cos(az)
    y = r * np.cos(el) * np.sin(az)
    z = r * np.sin(el)
    return np.stack([x, y, z], axis=1) + center


def spawn(threat: ThreatConfig, defense: DefenseConfig):
    """Return (pos[n,3], vel[n,3]) for the swarm at t=0.

    S0/S2 : uniform shell (multi-altitude via el_range_deg).
    S3/S4 : seam-routing when isr=='perfect' (concentrate into gaps + zenith);
            falls back to uniform when isr=='blind'.
    S5    : same threat as S4; mobility is a defense property (orbit_rate), applied
            in the engine — the seams the swarm aimed at drift away by arrival.
    """
    rng = np.random.default_rng(threat.seed)
    center = np.asarray(defense.asset_pos, float)
    seam = threat.scenario in ("S3", "S4", "S5") and threat.isr == "perfect"
    if seam and len(defense.apertures) >= 2:
        pos = _seam_spawn(rng, threat, defense, center)
    else:
        pos = _sample_shell(rng, threat.n, threat.r_spawn,
                            threat.az_range_deg, threat.el_range_deg, center)
    to_asset = center - pos
    dist = np.linalg.norm(to_asset, axis=1, keepdims=True)
    vel = threat.v * to_asset / np.maximum(dist, 1e-9)
    return pos.astype(float), vel.astype(float)
