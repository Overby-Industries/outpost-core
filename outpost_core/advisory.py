"""Build a Tier 1 advisory request (ai-roundtable) from a docking contention.

Only equal-priority contentions are eligible; emergencies are Tier 0 and are
resolved deterministically with no advisory step. The schema is
ai-roundtable's schemas/advisory-request.schema.json (ADV-1).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from .docking import Contention
from .timeutil import fmt

MIN_DELIBERATION_S = 600  # below this there is no time to deliberate; stay deterministic


def contention_to_advisory(c: Contention, source_id: str, now: datetime,
                           decide_by: datetime) -> Optional[Dict[str, Any]]:
    if not c.advisory_eligible:
        return None
    if (decide_by - now).total_seconds() < MIN_DELIBERATION_S:
        return None
    return {
        "version": "ADV-1",
        "kind": "advisory-request",
        "timestamp": fmt(now),
        "source": {"id": source_id, "role": "node"},
        "id": f"{source_id}-dock-{c.winner}-{c.loser}",
        "topic": "resource-allocation",
        "urgency": "deliberative",
        "question": (f"Vehicles {c.winner} and {c.loser} have equal priority ({c.priority}) "
                     f"for port {c.port_id}; the default ordering delays {c.loser} by "
                     f"{int(c.loser_delay_s)} s. Is a different ordering better?"),
        "context": {"port": c.port_id, "priority": c.priority, "loserDelayS": c.loser_delay_s},
        "options": [
            {"id": "default", "summary": f"{c.winner} first (earliest ETA)"},
            {"id": "swap", "summary": f"{c.loser} first"},
        ],
        "defaultChoice": "default",
        "decideBy": fmt(decide_by),
    }
