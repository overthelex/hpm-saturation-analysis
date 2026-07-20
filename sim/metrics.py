"""Result metrics (aligned with hpm-saturation-model.md §6)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Metrics:
    n: int
    killed: int
    leaked: int
    escaped: int
    leak_fraction: float             # master output: fraction of swarm reaching contact
    kills_before_first_leak: int     # cost of attack (§6.3)
    holds_fratricide: int            # aperture-ticks idled by NoFireMask (diagnoses §8)
    kin_kills: int = 0               # drones killed by the inner kinetic layer

    def __str__(self):
        return (f"N={self.n} killed={self.killed} leaked={self.leaked} "
                f"escaped={self.escaped} leak={self.leak_fraction:.3f} "
                f"cost(kills_before_1st_leak)={self.kills_before_first_leak} "
                f"fratricide_holds={self.holds_fratricide} kin_kills={self.kin_kills}")
