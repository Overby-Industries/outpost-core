"""The outpost as an OTF-1 fleet node.

From the coordinator's view an outpost is a stationary node (README). OTF-1
has no `outpost` nodeType yet, so it advertises as `refinery` -- the closest
existing type, since a depot's job is process/store -- in the `surface`
zone. See docs/otf1-gap.md for the proposed schema addition.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, Optional

from .power import PowerBudget
from .timeutil import fmt, parse

CAPABILITIES = ["process", "store"]


class OutpostNode:
    def __init__(self, node_id: str, power: PowerBudget):
        self.node_id = node_id
        self.power = power
        self._seq = 0
        self.task: Optional[Dict[str, Any]] = None  # {"id", "state", "progress"}
        self.link = "connected"
        self.inventory_kg: Dict[str, float] = defaultdict(float)

    def _next_seq(self) -> int:
        n = self._seq
        self._seq += 1
        return n

    # -- outbound ---------------------------------------------------------
    def status(self, now: datetime) -> Dict[str, Any]:
        pkt: Dict[str, Any] = {
            "version": "OTF-1",
            "kind": "status",
            "timestamp": fmt(now),
            "source": {"id": self.node_id, "role": "node"},
            "seq": self._next_seq(),
            "node": {
                "type": "refinery",
                "mode": self.power.mode,
                "phase": "Depot",
                "link": self.link,
                "capabilities": list(CAPABILITIES),
            },
            "location": {"zone": "surface"},
        }
        if self.task:
            pkt["task"] = dict(self.task)
        return pkt

    # -- inbound ----------------------------------------------------------
    def handle_assignment(self, pkt: Dict[str, Any], now: datetime) -> Dict[str, Any]:
        """Answer a coordinator offer with an ack. The node always has the
        final say (OTF-1: an assignment is an offer, not a command)."""
        task = pkt["task"]
        reason = None
        if self.power.mode == "safe":
            reason = "safe-mode"
        elif now > parse(pkt["acceptBy"]):
            reason = "expired"
        elif task["action"] not in CAPABILITIES:
            reason = "unsupported"
        elif self.power.mode == "degraded":
            reason = "degraded"
        elif self.task and self.task["state"] == "active" and self.task["id"] != task["id"]:
            reason = "busy"

        ack: Dict[str, Any] = {
            "version": "OTF-1",
            "kind": "ack",
            "timestamp": fmt(now),
            "source": {"id": self.node_id, "role": "node"},
            "destination": pkt["source"]["id"],
            "seq": self._next_seq(),
            "taskId": task["id"],
            "result": "rejected" if reason else "accepted",
        }
        if reason:
            ack["reason"] = reason
        else:
            self.task = {"id": task["id"], "state": "active", "progress": 0.0}
        return ack

    def complete_task(self, progress: float = 1.0, failed: bool = False) -> None:
        if self.task:
            self.task["state"] = "failed" if failed else "completed"
            self.task["progress"] = progress

    def ingest_event(self, event: Dict[str, Any]) -> float:
        """Accept an OTF-1 `event` (e.g. a reclaimer's capture) handed off to
        this depot; returns kg added to inventory. Only events whose outcome
        is stored or delivered are counted."""
        if event.get("kind", "event") != "event":
            raise ValueError("ingest_event expects an OTF-1 event packet")
        outcome = event["outcome"]
        if outcome["status"] not in ("stored", "delivered"):
            return 0.0
        kg = float(outcome.get("processedKg", 0.0))
        self.inventory_kg[outcome.get("repurposedAs", "none")] += kg
        return kg
