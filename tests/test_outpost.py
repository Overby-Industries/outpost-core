from datetime import datetime, timedelta, timezone

import pytest

from outpost_core import (DockRequest, DockingCoordinator, Load, OutpostNode, Port,
                          PowerBudget, contention_to_advisory)

NOW = datetime(2026, 11, 21, 12, 0, 0, tzinfo=timezone.utc)


def coordinator(n=1):
    return DockingCoordinator(Port(f"P{i}") for i in range(n))


def test_higher_priority_wins_without_contention_record():
    s = coordinator().schedule([
        DockRequest("low", "dock", 2, eta_s=0, duration_s=100),
        DockRequest("high", "dock", 8, eta_s=0, duration_s=100),
    ])
    assert [x.vehicle_id for x in s.slots] == ["high", "low"]
    assert s.contentions == []          # outranked, not a tie


def test_equal_priority_is_deterministic_and_recorded():
    reqs = [DockRequest("B", "dock", 5, eta_s=10, duration_s=100),
            DockRequest("A", "dock", 5, eta_s=0, duration_s=100)]
    s = coordinator().schedule(reqs)
    assert [x.vehicle_id for x in s.slots] == ["A", "B"]
    (c,) = s.contentions
    assert (c.winner, c.loser, c.loser_delay_s) == ("A", "B", 90)
    assert c.advisory_eligible
    assert coordinator().schedule(reversed(reqs)).slots == s.slots   # input order irrelevant


def test_second_port_removes_contention():
    s = coordinator(2).schedule([DockRequest("A", "dock", 5, 0, 100),
                                 DockRequest("B", "dock", 5, 0, 100)])
    assert s.contentions == [] and {x.port_id for x in s.slots} == {"P0", "P1"}


def test_unservable_request_reported():
    dc = DockingCoordinator([Port("P0", frozenset({"dock"}))])
    s = dc.schedule([DockRequest("A", "repair", 5, 0, 10)])
    assert s.slots == [] and len(s.unserved) == 1


def test_emergency_never_goes_to_advisory():
    s = coordinator().schedule([DockRequest("A", "dock", 10, 0, 100),
                                DockRequest("B", "dock", 10, 0, 100)])
    (c,) = s.contentions
    assert not c.advisory_eligible
    assert contention_to_advisory(c, "depot-1", NOW, NOW + timedelta(hours=2)) is None


def test_advisory_requires_time_to_deliberate():
    s = coordinator().schedule([DockRequest("A", "dock", 5, 0, 100),
                                DockRequest("B", "dock", 5, 0, 100)])
    c = s.contentions[0]
    assert contention_to_advisory(c, "depot-1", NOW, NOW + timedelta(seconds=60)) is None
    adv = contention_to_advisory(c, "depot-1", NOW, NOW + timedelta(hours=1))
    assert adv["urgency"] == "deliberative" and adv["defaultChoice"] == "default"


def test_power_sheds_lowest_priority_first():
    pb = PowerBudget(capacity_wh=1000, soc_wh=250)       # floor is 200 Wh
    loads = [Load("telemetry", 20, 9, sheddable=False), Load("docking", 100, 8),
             Load("processing", 400, 1)]
    shed = pb.step(3600, solar_w=0, loads=loads)
    assert [l.name for l in shed] == ["processing", "docking"]
    assert pb.soc_wh == pytest.approx(230)


def test_power_mode_thresholds():
    assert PowerBudget(1000, 900).mode == "nominal"
    assert PowerBudget(1000, 400).mode == "degraded"
    assert PowerBudget(1000, 150).mode == "safe"


def test_node_status_and_assignment_flow():
    node = OutpostNode("depot-1", PowerBudget(1000, 900))
    st = node.status(NOW)
    assert st["node"]["capabilities"] == ["process", "store"] and st["seq"] == 0

    offer = {"source": {"id": "fleet-coordinator", "role": "coordinator"},
             "task": {"id": "T-1", "action": "process"},
             "acceptBy": "2026-11-21T12:00:10Z"}
    ack = node.handle_assignment(offer, NOW)
    assert ack["result"] == "accepted" and node.status(NOW)["task"]["state"] == "active"

    busy = node.handle_assignment({**offer, "task": {"id": "T-2", "action": "store"}}, NOW)
    assert (busy["result"], busy["reason"]) == ("rejected", "busy")

    late = node.handle_assignment({**offer, "task": {"id": "T-3", "action": "store"}},
                                  NOW + timedelta(seconds=30))
    assert late["reason"] == "expired"

    unsupported = OutpostNode("d2", PowerBudget(1000, 900)).handle_assignment(
        {**offer, "task": {"id": "T-4", "action": "capture"}}, NOW)
    assert unsupported["reason"] == "unsupported"


def test_node_rejects_when_power_low():
    offer = {"source": {"id": "c", "role": "coordinator"},
             "task": {"id": "T", "action": "process"}, "acceptBy": "2026-11-21T12:00:10Z"}
    assert OutpostNode("a", PowerBudget(1000, 400)).handle_assignment(offer, NOW)["reason"] == "degraded"
    assert OutpostNode("a", PowerBudget(1000, 100)).handle_assignment(offer, NOW)["reason"] == "safe-mode"


def test_ingest_capture_event_updates_inventory():
    node = OutpostNode("depot-1", PowerBudget(1000, 900))
    ev = {"version": "OTF-1", "outcome": {"processedKg": 5.0, "repurposedAs": "shield_block",
                                          "status": "stored"}}
    assert node.ingest_event(ev) == 5.0
    assert node.inventory_kg["shield_block"] == 5.0
    ev["outcome"]["status"] = "failed"
    assert node.ingest_event(ev) == 0.0
