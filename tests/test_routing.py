import pytest
from backend.data_loader import load_initial_entities
from backend.graph import CityGraph
from backend.models import TrafficLevel, RoadStatus
from backend.routing import calculate_dijkstra_route, compare_routes, generate_routing_table


@pytest.fixture
def fresh_graph():
    junctions, roads = load_initial_entities()
    return CityGraph(junctions, roads)


def test_dijkstra_direct_path(fresh_graph):
    """Test routing between directly connected adjacent nodes."""
    res = calculate_dijkstra_route(fresh_graph, "J1", "J2")
    assert res.status == "success"
    assert res.route == ["J1", "J2"]
    assert res.total_distance_km == 2.1
    assert res.total_dynamic_cost == 2.1
    assert len(res.steps) == 1
    assert res.roads_used == ["R01"]


def test_dijkstra_multi_hop(fresh_graph):
    """Test routing across multiple hops under baseline low traffic."""
    res = calculate_dijkstra_route(fresh_graph, "J1", "J10")
    assert res.status == "success"
    assert res.route[0] == "J1"
    assert res.route[-1] == "J10"
    assert res.total_distance_km > 0
    assert res.total_dynamic_cost > 0
    assert len(res.route) >= 3


def test_same_source_and_destination(fresh_graph):
    """Test zero distance when source equals destination."""
    res = calculate_dijkstra_route(fresh_graph, "J1", "J1")
    assert res.status == "success"
    assert res.route == ["J1"]
    assert res.total_distance_km == 0.0
    assert res.total_dynamic_cost == 0.0
    assert res.number_of_roads == 0


def test_invalid_nodes(fresh_graph):
    """Test error handling when node does not exist."""
    res1 = calculate_dijkstra_route(fresh_graph, "INVALID", "J2")
    assert res1.status == "error"
    assert "INVALID" in res1.message

    res2 = calculate_dijkstra_route(fresh_graph, "J1", "INVALID")
    assert res2.status == "error"
    assert "INVALID" in res2.message


def test_dynamic_rerouting_due_to_congestion(fresh_graph):
    """
    Test that increasing traffic multiplier on an active road forces Dijkstra
    to find an alternative route with lower dynamic cost.
    """
    # 1. Baseline route from J1 to J6
    baseline_res = calculate_dijkstra_route(fresh_graph, "J1", "J6")
    assert baseline_res.status == "success"
    initial_route = baseline_res.route
    assert "J2" in initial_route  # Baseline typically goes J1 -> J2 -> J6

    # 2. Introduce SEVERE congestion on R01 (J1-J2)
    road_r01 = fresh_graph.get_road("R01")
    road_r01.traffic_level = TrafficLevel.SEVERE
    road_r01.traffic_factor = 4.0

    # 3. Recalculate route
    congested_res = calculate_dijkstra_route(fresh_graph, "J1", "J6")
    assert congested_res.status == "success"

    # Route should avoid R01 or use an alternative like J1 -> J11 -> J12 -> J6 or J1 -> J5 -> J8
    comparison = compare_routes(baseline_res, congested_res, fresh_graph)
    assert comparison.route_changed is True
    assert "R01" not in congested_res.roads_used or congested_res.route != initial_route
    assert "Dynamic Rerouting Triggered" in comparison.reason


def test_blocked_road_avoidance(fresh_graph):
    """Test that blocked road is avoided by routing engine."""
    # 1. Baseline route from J1 to J2
    res_before = calculate_dijkstra_route(fresh_graph, "J1", "J2")
    assert res_before.roads_used == ["R01"]

    # 2. Block R01
    road_r01 = fresh_graph.get_road("R01")
    road_r01.status = RoadStatus.BLOCKED

    # 3. Recalculate route
    res_after = calculate_dijkstra_route(fresh_graph, "J1", "J2")
    assert res_after.status == "success"
    assert "R01" not in res_after.roads_used
    assert res_after.route[0] == "J1"
    assert res_after.route[-1] == "J2"
    assert len(res_after.route) > 2  # Takes detour via J11/J12 or similar


def test_unreachable_destination(fresh_graph):
    """Test that when all connecting links to a node are blocked, it reports unreachable."""
    # Block all roads connecting to J6 (R08, R21, R22)
    for r_id in ["R08", "R21", "R22"]:
        fresh_graph.get_road(r_id).status = RoadStatus.BLOCKED

    res = calculate_dijkstra_route(fresh_graph, "J1", "J6")
    assert res.status == "error"
    assert res.traffic_summary == "Unreachable"
    assert "No route found" in res.message


def test_generate_routing_table(fresh_graph):
    """Test that full routing table can be generated for a router node."""
    table = generate_routing_table(fresh_graph, "J1")
    assert table.source == "J1"
    assert len(table.entries) == len(fresh_graph.junctions) - 1
    # Check that all entries have valid next hops
    for entry in table.entries:
        assert entry.next_hop in fresh_graph.junctions
        assert entry.dynamic_cost > 0
        assert entry.hops >= 1
