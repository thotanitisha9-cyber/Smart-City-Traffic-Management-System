import pytest
from backend.traffic import TrafficManager
from backend.models import TrafficLevel, RoadStatus


@pytest.fixture
def manager():
    return TrafficManager()


def test_traffic_manager_init(manager):
    assert len(manager.junctions) == 14
    assert len(manager.roads) == 28
    stats = manager.get_statistics()
    assert stats.total_junctions == 14
    assert stats.total_roads == 28
    assert stats.blocked_roads == 0
    assert stats.low_traffic_roads == 28


def test_update_road_traffic(manager):
    updated = manager.update_road_traffic("R01", TrafficLevel.HIGH)
    assert updated.traffic_level == TrafficLevel.HIGH
    assert updated.traffic_factor == 2.5
    assert updated.dynamic_cost == round(2.1 * 2.5, 2)

    stats = manager.get_statistics()
    assert stats.high_traffic_roads == 1
    assert stats.low_traffic_roads == 27


def test_block_and_unblock_road(manager):
    road = manager.set_road_status("R05", RoadStatus.BLOCKED)
    assert road.status == RoadStatus.BLOCKED
    assert road.dynamic_cost == float("inf")

    stats = manager.get_statistics()
    assert stats.blocked_roads == 1
    assert stats.open_roads == 27

    road2 = manager.set_road_status("R05", RoadStatus.OPEN)
    assert road2.status == RoadStatus.OPEN
    stats2 = manager.get_statistics()
    assert stats2.blocked_roads == 0


def test_apply_scenarios(manager):
    # Scenario 2: Peak congestion
    scenario = manager.apply_scenario(2)
    assert scenario["id"] == 2
    assert manager.roads["R01"].traffic_level == TrafficLevel.SEVERE
    assert manager.roads["R03"].traffic_level == TrafficLevel.HIGH

    stats = manager.get_statistics()
    assert stats.severe_traffic_roads >= 1
    assert stats.high_traffic_roads >= 1

    # Scenario 3: Road blockage
    scenario3 = manager.apply_scenario(3)
    assert scenario3["id"] == 3
    assert manager.roads["R03"].status == RoadStatus.BLOCKED

    stats3 = manager.get_statistics()
    assert stats3.blocked_roads >= 1


def test_reset_network(manager):
    manager.update_road_traffic("R01", TrafficLevel.SEVERE)
    manager.set_road_status("R02", RoadStatus.BLOCKED)
    assert manager.roads["R01"].traffic_level == TrafficLevel.SEVERE
    assert manager.roads["R02"].status == RoadStatus.BLOCKED

    # Reset
    manager.reset_network()
    assert manager.roads["R01"].traffic_level == TrafficLevel.LOW
    assert manager.roads["R02"].status == RoadStatus.OPEN
    stats = manager.get_statistics()
    assert stats.blocked_roads == 0
    assert stats.low_traffic_roads == 28
