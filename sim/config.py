"""Configuration dataclasses for the HPM counter-swarm simulation.

All distances in meters, times in seconds, angles in degrees (converted at use).
Every default carries a [assumption] tag in hpm-saturation-model.md §10.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple
import math


@dataclass
class Aperture:
    """A single HPM effector.

    pos       : (x, y, z) position, meters. Ring apertures sit on a circle; z is height.
    theta_deg : beam half-angle (cone). Pencil ~5-10, shield ~30.
    r_eff     : kill range from the aperture, meters.
    t_c       : full engagement cycle per aim-point (slew+dwell+confirm), seconds.
    n_cone    : max targets neutralized per pulse (one-to-many within the cone).
    el_max_deg: max elevation the aperture can point to (zenith gap = 90 - el_max).
    hardened  : if True, friendly apertures may fire toward it (relaxes fratricide).
    velocity  : (vx, vy, vz) reposition velocity for mobile apertures, m/s.
    """
    pos: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    theta_deg: float = 10.0
    r_eff: float = 500.0
    t_c: float = 0.3
    n_cone: int = 1
    el_max_deg: float = 85.0
    hardened: bool = False
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass
class DefenseConfig:
    """The full defensive line.

    asset_pos      : protected object position (drones aim here).
    asset_keepout  : rho — radius of protected electronics; sets fratricide arc.
    apertures      : list of Aperture.
    r_contact      : R_c — a live drone within this of the asset counts as a LEAKER.
    r_detect       : sensor detection range (from asset); None = unlimited.
    t_max_tracks   : max simultaneous fire-control tracks; None = unlimited.
    p_k_soft       : softness of the P_k(r) rolloff at r_eff, meters (0 = hard step).
    fratricide     : master switch; False disables the NoFireMask (validation).
    neighbor_margin_deg : extra angular guard around a friendly aperture direction.
    """
    asset_pos: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    asset_keepout: float = 20.0
    apertures: List[Aperture] = field(default_factory=lambda: [Aperture()])
    r_contact: float = 50.0
    ap_contact: float = 0.0        # if >0, a live drone within this of ANY aperture is a
    #                                LEAKER (it reached an installation "вплотную")
    r_detect: float | None = None
    t_max_tracks: int | None = None
    p_k_soft: float = 0.0
    fratricide: bool = True
    neighbor_margin_deg: float = 3.0

    # Mobility (stage 4): the ring orbits the asset about the vertical axis at this rate.
    # A swarm that seam-routed against the initial layout finds the seams have moved by
    # orbit_rate * (time-to-arrive) — this is how mobility invalidates the attacker's ISR.
    orbit_rate: float = 0.0        # rad/s

    # Inner kinetic layer (stage 4): the point-defense bubble that owns the interior HPM
    # cannot fire into (no fratricide problem for kinetics). Sizes the hybrid fix.
    kin_radius: float = 0.0        # 0 disables the layer
    kin_rate: float = 0.0          # engagements per second
    kin_magazine: int = 0          # total interceptors before depletion
    kin_pk: float = 0.9            # per-engagement kill probability

    @staticmethod
    def ring(m: int, r_ring: float, height: float = 0.0, **ap_kwargs) -> "DefenseConfig":
        """Build a ring of m identical apertures on a circle of radius r_ring."""
        aps = []
        for i in range(m):
            ang = 2 * math.pi * i / m
            pos = (r_ring * math.cos(ang), r_ring * math.sin(ang), height)
            aps.append(Aperture(pos=pos, **ap_kwargs))
        return DefenseConfig(apertures=aps)


@dataclass
class ThreatConfig:
    """The attacking swarm (abstract kinematics — points with velocity)."""
    n: int = 100
    v: float = 30.0                 # approach speed, m/s
    r_spawn: float = 1500.0         # start radius (shell), meters
    # angular distribution over the upper hemisphere the swarm spawns from:
    az_range_deg: Tuple[float, float] = (0.0, 360.0)
    el_range_deg: Tuple[float, float] = (5.0, 60.0)   # multi-altitude via el spread
    scenario: str = "S0"           # S0 uniform shell; S3/S4 seam-routing; per design doc
    isr: str = "blind"             # blind | perfect (seam-routing) — used by S3/S4/S5
    seed: int = 0
    # seam-routing knobs (used when scenario in {S3,S4} and isr=='perfect')
    seam_az_spread_deg: float = 6.0   # concentration of azimuth around inter-aperture gaps
    seam_zenith_frac: float = 0.25    # fraction routed through the zenith gap (above el_max)
    # zenith-drop attack (scenario 'S6'): climb over the centre, then cut power and free-fall.
    # Once falling with electronics OFF the drone is INERT MASS -> immune to a soft-kill HPM.
    apogee_h: float = 400.0           # altitude of the drop point over the asset, m
    fall_v: float = 25.0              # descent speed once unpowered, m/s
    fall_drift: float = 3.0           # 1-sigma horizontal drift while falling (CEP driver), m/s


@dataclass
class SimConfig:
    dt: float = 0.02               # timestep, s
    t_max: float | None = None     # hard stop, s; None = auto from geometry (slowest transit)
    hemisphere: bool = True        # Omega_def = 2pi (ground-based, upper hemisphere)
