"""Solar + battery energy ledger with priority-ordered load shedding.

Deliberately hardware-agnostic (README: power hardware is undecided). Loads
are shed lowest-priority-first, so docking and telemetry survive and
processing is what gives way first.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence


@dataclass(frozen=True)
class Load:
    name: str
    watts: float
    priority: int            # higher = more important
    sheddable: bool = True


class PowerBudget:
    def __init__(self, capacity_wh: float, soc_wh: float, reserve_fraction: float = 0.2,
                 degraded_fraction: float = 0.5):
        if not 0 <= soc_wh <= capacity_wh:
            raise ValueError("state of charge must be within capacity")
        self.capacity_wh = capacity_wh
        self.soc_wh = soc_wh
        self.reserve_fraction = reserve_fraction
        self.degraded_fraction = degraded_fraction

    @property
    def soc_fraction(self) -> float:
        return self.soc_wh / self.capacity_wh

    @property
    def mode(self) -> str:
        """OTF-1 node mode: nominal / degraded / safe."""
        if self.soc_fraction <= self.reserve_fraction:
            return "safe"
        if self.soc_fraction < self.degraded_fraction:
            return "degraded"
        return "nominal"

    def step(self, dt_s: float, solar_w: float, loads: Sequence[Load]) -> List[Load]:
        """Advance dt_s seconds; returns the loads shed this step.

        Sheds lowest-priority sheddable loads until the battery would not
        cross the reserve floor within this step.
        """
        hours = dt_s / 3600.0
        floor = self.capacity_wh * self.reserve_fraction
        active = sorted(loads, key=lambda l: (l.priority, l.name))
        shed: List[Load] = []

        def projected(ls: Sequence[Load]) -> float:
            return self.soc_wh + (solar_w - sum(l.watts for l in ls)) * hours

        while projected(active) < floor:
            victim = next((l for l in active if l.sheddable), None)
            if victim is None:
                break
            active.remove(victim)
            shed.append(victim)

        self.soc_wh = min(self.capacity_wh, max(0.0, projected(active)))
        return shed
