"""HPM counter-swarm defensive simulation.

Defensive red-team tool: runs abstract swarm maneuvers against a HPM defense
configuration and reports breakthrough (leak) fraction, cost of attack, and
where the line fails. Companion to hpm-saturation-model.md / hpm-swarm-sim-design.md.

Stages implemented: 0 (single aperture, S0), 1 (P_k, n_cone, sensor/T_max,
greedy-EDF scheduler), 2 (ring of M apertures + fratricide/keep-out/zenith NoFireMask).
"""

from .config import DefenseConfig, Aperture, ThreatConfig, SimConfig
from .engine import World, simulate
from .metrics import Metrics

__all__ = [
    "DefenseConfig",
    "Aperture",
    "ThreatConfig",
    "SimConfig",
    "World",
    "simulate",
    "Metrics",
]
