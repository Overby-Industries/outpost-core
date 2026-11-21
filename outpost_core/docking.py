"""Docking / handoff coordination -- the first piece every outpost variant
needs (docs/subsystems-draft.md).

Scheduling is deterministic. A request that outranks the others simply wins
(priority >= EMERGENCY_PRIORITY is Tier 0: it pre-empts and is never routed
to an AI advisory). When two *equal-priority* requests compete for the same
port, the scheduler still picks one deterministically (earliest ETA, then
id) so the outpost is never blocked waiting on a deliberation -- but it also
records a `Contention`, which is the hook for a Tier 1 roundtable
(ai-roundtable) to recommend a better ordering for a human to review.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List

EMERGENCY_PRIORITY = 10


@dataclass(frozen=True)
class Port:
    id: str
    services: frozenset = frozenset({"dock", "cargo", "repair"})


@dataclass(frozen=True)
class DockRequest:
    vehicle_id: str
    service: str                 # "dock" | "cargo" | "repair"
    priority: int                # 0..10; 10 = emergency (Tier 0)
    eta_s: float                 # seconds from schedule epoch
    duration_s: float
    cargo_kg: float = 0.0


@dataclass(frozen=True)
class Slot:
    vehicle_id: str
    port_id: str
    service: str
    start_s: float
    end_s: float


@dataclass(frozen=True)
class Contention:
    winner: str
    loser: str
    port_id: str
    priority: int
    loser_delay_s: float

    @property
    def advisory_eligible(self) -> bool:
        return self.priority < EMERGENCY_PRIORITY


@dataclass
class Schedule:
    slots: List[Slot] = field(default_factory=list)
    unserved: List[DockRequest] = field(default_factory=list)
    contentions: List[Contention] = field(default_factory=list)


class DockingCoordinator:
    def __init__(self, ports: Iterable[Port]):
        self.ports: List[Port] = sorted(ports, key=lambda p: p.id)
        if not self.ports:
            raise ValueError("an outpost needs at least one port")

    def schedule(self, requests: Iterable[DockRequest]) -> Schedule:
        order = sorted(requests, key=lambda r: (-r.priority, r.eta_s, r.vehicle_id))
        free_at: Dict[str, float] = {p.id: 0.0 for p in self.ports}
        last_user: Dict[str, Slot] = {}
        last_prio: Dict[str, int] = {}
        out = Schedule()

        for req in order:
            candidates = [p for p in self.ports if req.service in p.services]
            if not candidates:
                out.unserved.append(req)
                continue
            # Earliest possible start across compatible ports; ties -> port id.
            port = min(candidates, key=lambda p: (max(req.eta_s, free_at[p.id]), p.id))
            start = max(req.eta_s, free_at[port.id])
            slot = Slot(req.vehicle_id, port.id, req.service, start, start + req.duration_s)
            delay = start - req.eta_s
            prev = last_user.get(port.id)
            if delay > 0 and prev is not None and last_prio[port.id] == req.priority:
                out.contentions.append(
                    Contention(prev.vehicle_id, req.vehicle_id, port.id, req.priority, delay)
                )
            out.slots.append(slot)
            free_at[port.id] = slot.end_s
            last_user[port.id] = slot
            last_prio[port.id] = req.priority

        out.slots.sort(key=lambda s: (s.start_s, s.port_id))
        return out
