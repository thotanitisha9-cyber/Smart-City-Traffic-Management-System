import pytest
from fastapi.testclient import TestClient
from backend.main import app, traffic_manager, active_state


@pytest.fixture
def client():
    traffic_manager.reset_network()
    active_state["active_source"] = None
    active_state["active_destination"] = None
    active_state["last_route"] = None
    return TestClient(app)


def test_api_junctions(client):
    res = client.get("/api/junctions")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 14
    ids = [j["id"] for j in data]
    assert "J1" in ids
    assert "J10" in ids


def test_api_roads(client):
    res = client.get("/api/roads")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 28
    assert "dynamic_cost" in data[0]


def test_api_statistics(client):
    res = client.get("/api/statistics")
    assert res.status_code == 200
    data = res.json()
    assert data["total_junctions"] == 14
    assert data["total_roads"] == 28
    assert data["blocked_roads"] == 0


def test_api_route_calculation(client):
    # Valid route calculation
    res = client.post("/api/route", json={"source": "J1", "destination": "J10"})
    assert res.status_code == 200
    data = res.json()
    assert "route_result" in data
    assert "comparison" in data
    route = data["route_result"]
    assert route["status"] == "success"
    assert route["source"] == "J1"
    assert route["destination"] == "J10"
    assert route["total_distance_km"] > 0
    assert len(route["route"]) >= 2


def test_api_route_invalid_junction(client):
    res = client.post("/api/route", json={"source": "J999", "destination": "J10"})
    assert res.status_code == 404
    assert "does not exist" in res.json()["detail"]


def test_api_traffic_update_and_reroute(client):
    # 1. Establish initial route J1 -> J6
    res1 = client.post("/api/route", json={"source": "J1", "destination": "J6"})
    assert res1.status_code == 200

    # 2. Update traffic on R01 (Central-North) to SEVERE
    res2 = client.post("/api/traffic/update", json={"road_id": "R01", "traffic_level": "SEVERE"})
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "success"
    assert data2["road"]["traffic_level"] == "SEVERE"
    assert data2["active_route"] is not None
    assert data2["comparison"] is not None


def test_api_road_block_and_unblock(client):
    # Block R01
    res_block = client.post("/api/road/block", json={"road_id": "R01"})
    assert res_block.status_code == 200
    assert res_block.json()["road"]["status"] == "BLOCKED"

    # Unblock R01
    res_unblock = client.post("/api/road/unblock", json={"road_id": "R01"})
    assert res_unblock.status_code == 200
    assert res_unblock.json()["road"]["status"] == "OPEN"


def test_api_scenarios(client):
    res = client.post("/api/simulation/scenario", json={"scenario_id": 2})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["scenario"]["id"] == 2

    # Invalid scenario
    res_err = client.post("/api/simulation/scenario", json={"scenario_id": 99})
    assert res_err.status_code == 400


def test_api_reset(client):
    client.post("/api/road/block", json={"road_id": "R01"})
    res = client.post("/api/simulation/reset")
    assert res.status_code == 200
    stats = client.get("/api/statistics").json()
    assert stats["blocked_roads"] == 0


def test_api_routing_table(client):
    res = client.get("/api/routing-table/J1")
    assert res.status_code == 200
    data = res.json()
    assert data["source"] == "J1"
    assert len(data["entries"]) == 13

    # Invalid source
    res_err = client.get("/api/routing-table/J999")
    assert res_err.status_code == 404
