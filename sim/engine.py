"""3D time-stepped agent engine for HPM counter-swarm simulation.

Vectorized over drones (numpy); apertures looped (M is small). Deterministic per seed.

Core fratricide invariant (heart of the model): a drone is ENGAGEABLE by aperture a
only if it is within the beam cone reachable direction, within r_eff, within el_max,
tracked, AND not in NoFireMask[a] (firing there would wash the asset or an unhardened
friendly aperture). A drone illegal for ALL apertures and past the ring is a guaranteed
leaker unless an inner kinetic layer takes it (stage 4, not yet implemented).
"""
from __future__ import annotations

import math
import numpy as np

from .config import DefenseConfig, ThreatConfig, SimConfig
from .metrics import Metrics
from . import scenarios

# drone status codes
ALIVE, KILLED, LEAKER, ESCAPED = 0, 1, 2, 3


def _unit(v, axis=-1):
    n = np.linalg.norm(v, axis=axis, keepdims=True)
    return v / np.maximum(n, 1e-12)


def _angle_between(u, v):
    """Angle (rad) between two (…,3) unit-or-not vectors, broadcasting."""
    uu = _unit(u)
    vv = _unit(v)
    dot = np.clip(np.sum(uu * vv, axis=-1), -1.0, 1.0)
    return np.arccos(dot)


class World:
    def __init__(self, defense: DefenseConfig, threat: ThreatConfig, sim: SimConfig):
        self.d = defense
        self.t = threat
        self.s = sim
        self.rng = np.random.default_rng(threat.seed + 10007)  # separate stream from spawn

        pos, vel = scenarios.spawn(threat, defense)
        self.pos = pos                      # (N,3)
        self.vel = vel                      # (N,3)
        self.status = np.zeros(len(pos), dtype=np.int8)
        self.asset = np.asarray(defense.asset_pos, float)

        self.ap_pos = np.array([a.pos for a in defense.apertures], float)   # (M,3)
        self.ap_vel = np.array([a.velocity for a in defense.apertures], float)
        self.ap_busy = np.zeros(len(defense.apertures))                     # busy-until time
        self.theta = np.array([math.radians(a.theta_deg) for a in defense.apertures])
        self.r_eff = np.array([a.r_eff for a in defense.apertures])
        self.t_c = np.array([a.t_c for a in defense.apertures])
        self.n_cone = np.array([a.n_cone for a in defense.apertures])
        self.el_max = np.array([math.radians(a.el_max_deg) for a in defense.apertures])
        self.hardened = np.array([a.hardened for a in defense.apertures])

        self.time = 0.0
        self.kills_before_first_leak = 0
        self._first_leak_seen = False
        # inner kinetic layer state
        self.kin_credit = 0.0
        self.kin_mag_left = defense.kin_magazine
        self.kin_kills = 0
        # diagnostics
        self.leak_via_seam = 0   # leakers that were illegal for all apertures at contact
        self.holds_fratricide = 0  # aperture-ticks idled with tracks present but all no-fire

    # ---- geometry / legality -------------------------------------------------
    def _asset_subtend(self, ai):
        """Half-angle subtended by the asset keep-out sphere from aperture ai."""
        d = np.linalg.norm(self.ap_pos[ai] - self.asset)
        return math.asin(min(1.0, self.d.asset_keepout / max(d, 1e-6)))

    def _legal_mask(self, ai, alive_idx):
        """Return (legal, geometric, dist, u) masks over alive_idx for aperture ai.

        geometric : within r_eff, el_max, above horizon (physically reachable)
        legal     : geometric AND not in NoFireMask (fratricide/keep-out)
        The gap (geometric & ~legal) is what fratricide costs — used for hold diagnostics.
        """
        a = self.ap_pos[ai]
        P = self.pos[alive_idx]                       # (k,3)
        rel = P - a
        dist = np.linalg.norm(rel, axis=1)
        u = rel / np.maximum(dist[:, None], 1e-12)    # aim directions

        geometric = dist <= self.r_eff[ai]
        el = np.arcsin(np.clip(u[:, 2], -1.0, 1.0))
        geometric &= el <= self.el_max[ai]
        geometric &= el >= 0.0                         # cannot fire below horizon

        if not self.d.fratricide:
            return geometric.copy(), geometric, dist, u

        th = self.theta[ai]
        # (a) no-fire if beam would wash the protected asset
        to_asset = self.asset - a
        ang_asset = _angle_between(u, to_asset[None, :])
        forbid = ang_asset < (th + self._asset_subtend(ai))
        # (b) no-fire toward each unhardened friendly aperture
        margin = math.radians(self.d.neighbor_margin_deg)
        for bi in range(len(self.ap_pos)):
            if bi == ai or self.hardened[bi]:
                continue
            to_b = self.ap_pos[bi] - a
            ang_b = _angle_between(u, to_b[None, :])
            forbid |= ang_b < (th + margin)

        legal = geometric & ~forbid
        return legal, geometric, dist, u

    # ---- one tick ------------------------------------------------------------
    def step(self):
        dt = self.s.dt
        self.time += dt

        # move drones (alive only) and mobile apertures
        alive = self.status == ALIVE
        self.pos[alive] += self.vel[alive] * dt
        self.ap_pos += self.ap_vel * dt
        # orbit the ring about the asset's vertical axis (mobility invalidates ISR)
        if self.d.orbit_rate != 0.0:
            ang = self.d.orbit_rate * dt
            c, s = math.cos(ang), math.sin(ang)
            rel = self.ap_pos - self.asset
            x = rel[:, 0] * c - rel[:, 1] * s
            y = rel[:, 0] * s + rel[:, 1] * c
            self.ap_pos[:, 0] = x + self.asset[0]
            self.ap_pos[:, 1] = y + self.asset[1]

        # distances to asset
        d_asset = np.linalg.norm(self.pos - self.asset, axis=1)

        # leaker check: reached the vital point, or reached an installation "вплотную"
        newly_leak = alive & (d_asset < self.d.r_contact)
        if self.d.ap_contact > 0.0:
            # min distance from each drone to any aperture
            diff = self.pos[:, None, :] - self.ap_pos[None, :, :]
            d_ap = np.sqrt((diff * diff).sum(axis=2)).min(axis=1)
            newly_leak = newly_leak | (alive & (d_ap < self.d.ap_contact))
        if np.any(newly_leak):
            self.status[newly_leak] = LEAKER

        # escaped (moved well past spawn and receding) — rare for radial-in, guard anyway
        escaped = (self.status == ALIVE) & (d_asset > self.t.r_spawn * 1.3)
        self.status[escaped] = ESCAPED

        # ---- sensor: build track set (alive, within detect, up to T_max urgent) ----
        alive_idx = np.flatnonzero(self.status == ALIVE)
        if alive_idx.size == 0:
            return
        if self.d.r_detect is not None:
            alive_idx = alive_idx[d_asset[alive_idx] <= self.d.r_detect]
        # urgency = time-to-contact
        ttc = (d_asset[alive_idx] - self.d.r_contact) / max(self.t.v, 1e-6)
        if self.d.t_max_tracks is not None and alive_idx.size > self.d.t_max_tracks:
            keep = np.argsort(ttc)[: self.d.t_max_tracks]
            alive_idx = alive_idx[keep]
            ttc = ttc[keep]
        tracked = set(alive_idx.tolist())

        # ---- scheduler: greedy earliest-deadline-first per free aperture ----
        for ai in range(len(self.ap_pos)):
            if self.ap_busy[ai] > self.time:
                continue
            cur = np.array(sorted(tracked), dtype=int)
            if cur.size == 0:
                break
            legal, geometric, dist, u = self._legal_mask(ai, cur)
            if not np.any(legal):
                # a hold is fratricide-caused only if a geometrically-reachable target
                # existed but was blocked by the NoFireMask
                if np.any(geometric):
                    self.holds_fratricide += 1
                continue
            cand = cur[legal]
            cand_u = u[legal]
            cand_ttc = (np.linalg.norm(self.pos[cand] - self.asset, axis=1)
                        - self.d.r_contact) / max(self.t.v, 1e-6)
            pick = int(np.argmin(cand_ttc))
            aim = cand_u[pick]

            # everything within the cone of `aim` that is also legal is a co-kill candidate
            in_cone = _angle_between(cand_u, aim[None, :]) <= self.theta[ai]
            cluster = cand[in_cone]
            # order by urgency, keep up to n_cone
            order = np.argsort((np.linalg.norm(self.pos[cluster] - self.asset, axis=1)
                                - self.d.r_contact))
            cluster = cluster[order][: int(self.n_cone[ai])]

            # apply P_k(r)
            for di in cluster.tolist():
                r = float(np.linalg.norm(self.pos[di] - self.ap_pos[ai]))
                pk = self._p_k(r, ai)
                if self.rng.random() < pk:
                    self.status[di] = KILLED
                    tracked.discard(di)
                    if not self._first_leak_seen:
                        self.kills_before_first_leak += 1
            self.ap_busy[ai] = self.time + self.t_c[ai]

        # ---- inner kinetic layer: engages the interior HPM cannot fire into ----
        if self.d.kin_radius > 0.0 and self.kin_mag_left > 0:
            self.kin_credit += self.d.kin_rate * dt
            n_shots = int(self.kin_credit)
            if n_shots > 0:
                d_now = np.linalg.norm(self.pos - self.asset, axis=1)
                inzone = (self.status == ALIVE) & (d_now <= self.d.kin_radius)
                cand = np.flatnonzero(inzone)
                if cand.size:
                    # most urgent first (closest to asset)
                    cand = cand[np.argsort(d_now[cand])]
                    for di in cand[:n_shots].tolist():
                        if self.kin_mag_left <= 0:
                            break
                        self.kin_mag_left -= 1
                        self.kin_credit -= 1.0
                        if self.rng.random() < self.d.kin_pk:
                            self.status[di] = KILLED
                            self.kin_kills += 1
                            if not self._first_leak_seen:
                                self.kills_before_first_leak += 1

        if (not self._first_leak_seen) and np.any(self.status == LEAKER):
            self._first_leak_seen = True

    def _p_k(self, r, ai):
        if r > self.r_eff[ai] and self.d.p_k_soft == 0.0:
            return 0.0
        if self.d.p_k_soft == 0.0:
            return 1.0
        # logistic rolloff centered at r_eff
        return 1.0 / (1.0 + math.exp((r - self.r_eff[ai]) / self.d.p_k_soft))

    def run(self) -> Metrics:
        n = len(self.pos)
        if self.s.t_max is not None:
            t_max = self.s.t_max
        else:
            # auto: let the slowest drone complete its transit to contact, +30% margin
            d0 = np.linalg.norm(self.pos - self.asset, axis=1).max()
            t_max = (d0 - self.d.r_contact) / max(self.t.v, 1e-6) * 1.3
        nsteps = int(t_max / self.s.dt)
        for _ in range(nsteps):
            if not np.any(self.status == ALIVE):
                break
            self.step()
        # With sufficient run time a radial-in drone is either killed or reached contact.
        # Any still-alive that penetrated the engagement zone counts as leaked; those still
        # en route beyond r_eff are not (they simply had not arrived).
        d_asset = np.linalg.norm(self.pos - self.asset, axis=1)
        max_r_eff = float(self.r_eff.max())
        leftover_pen = (self.status == ALIVE) & (d_asset < max_r_eff)
        self.status[leftover_pen] = LEAKER
        leftover_enroute = self.status == ALIVE
        self.status[leftover_enroute] = ESCAPED
        killed = int(np.sum(self.status == KILLED))
        leaked = int(np.sum(self.status == LEAKER))
        escaped = int(np.sum(self.status == ESCAPED))
        return Metrics(
            n=n, killed=killed, leaked=leaked, escaped=escaped,
            leak_fraction=leaked / n if n else 0.0,
            kills_before_first_leak=self.kills_before_first_leak,
            holds_fratricide=self.holds_fratricide,
            kin_kills=self.kin_kills,
        )


def simulate(defense: DefenseConfig, threat: ThreatConfig, sim: SimConfig | None = None) -> Metrics:
    return World(defense, threat, sim or SimConfig()).run()
