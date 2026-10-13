import os
from pathlib import Path
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.models import (
    TrafficLevel,
    RoadStatus,
    RouteRequest,
    RouteResponse,
    TrafficUpdateRequest,
    RoadBlockRequest,
    ScenarioRequest,
    RouteComparisonResponse,
    NetworkStatistics,
    RoutingTableResponse,
)
from backend.traffic import TrafficManager
from backend.routing import calculate_dijkstra_route, compare_routes, generate_routing_table

# Initialize FastAPI application
app = FastAPI(
    title="Smart City Traffic Management System API",
    description="Dynamic Routing and Traffic Optimization Engine for Computer Networks PBL",
    version="1.0.0",
)

# Enable CORS for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Traffic Manager singleton
traffic_manager = TrafficManager()

# State tracker for current active route (for dynamic reroute comparisons)
active_state: Dict[str, Any] = {
    "active_source": None,
    "active_destination": None,
    "last_route": None,
}


@app.get("/api/junctions")
def get_junctions():
    """Returns list of all smart city junctions."""
    return [j.model_dump() for j in traffic_manager.junctions.values()]


@app.get("/api/roads")
def get_roads():
    """Returns all roads with real-time dynamic costs and congestion multipliers."""
    return [r.to_dict() for r in traffic_manager.roads.values()]


@app.get("/api/traffic")
def get_traffic():
    """Returns traffic summary status for all roads."""
    return [
        {
            "road_id": r.road_id,
            "name": r.name,
            "source": r.source,
            "destination": r.destination,
            "traffic_level": r.traffic_level.value,
            "traffic_factor": r.traffic_factor,
            "status": r.status.value,
            "dynamic_cost": r.dynamic_cost if r.status == RoadStatus.OPEN else None,
        }
        for r in traffic_manager.roads.values()
    ]


@app.get("/api/statistics", response_model=NetworkStatistics)
def get_statistics():
    """Returns aggregated traffic and network health metrics."""
    return traffic_manager.get_statistics()


@app.post("/api/route")
def compute_route(req: RouteRequest):
    """
    Computes optimal route between source and destination using manual Dijkstra.
    If an existing route was active, generates route comparison.
    """
    source = req.source.strip().upper()
    destination = req.destination.strip().upper()

    if source not in traffic_manager.junctions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source junction '{source}' does not exist.",
        )
    if destination not in traffic_manager.junctions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Destination junction '{destination}' does not exist.",
        )

    # Compute new route
    new_route = calculate_dijkstra_route(traffic_manager.graph, source, destination)

    # Check if we should compare with previous route
    prev_route = None
    if (
        active_state["active_source"] == source
        and active_state["active_destination"] == destination
        and active_state["last_route"] is not None
    ):
        prev_route = active_state["last_route"]

    comparison = compare_routes(prev_route, new_route, traffic_manager.graph)

    # Update active state
    active_state["active_source"] = source
    active_state["active_destination"] = destination
    active_state["last_route"] = new_route

    return {
        "route_result": new_route,
        "comparison": comparison,
    }


@app.post("/api/traffic/update")
def update_traffic(req: TrafficUpdateRequest):
    """
    Updates the traffic congestion level on a specific road segment.
    Automatically triggers dynamic route recalculation if an active route exists.
    """
    try:
        updated_road = traffic_manager.update_road_traffic(req.road_id, req.traffic_level)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    comparison = None
    new_route = None
    if active_state["active_source"] and active_state["active_destination"]:
        new_route = calculate_dijkstra_route(
            traffic_manager.graph,
            active_state["active_source"],
            active_state["active_destination"],
        )
        comparison = compare_routes(
            active_state["last_route"], new_route, traffic_manager.graph
        )
        active_state["last_route"] = new_route

    return {
        "status": "success",
        "road": updated_road.to_dict(),
        "active_route": new_route,
        "comparison": comparison,
        "statistics": traffic_manager.get_statistics(),
    }


@app.post("/api/road/block")
def block_road(req: RoadBlockRequest):
    """
    Blocks a road link (simulating link failure or construction cut).
    Triggers dynamic network rerouting.
    """
    try:
        blocked_road = traffic_manager.set_road_status(req.road_id, RoadStatus.BLOCKED)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    comparison = None
    new_route = None
    if active_state["active_source"] and active_state["active_destination"]:
        new_route = calculate_dijkstra_route(
            traffic_manager.graph,
            active_state["active_source"],
            active_state["active_destination"],
        )
        comparison = compare_routes(
            active_state["last_route"], new_route, traffic_manager.graph
        )
        active_state["last_route"] = new_route

    return {
        "status": "success",
        "road": blocked_road.to_dict(),
        "active_route": new_route,
        "comparison": comparison,
        "statistics": traffic_manager.get_statistics(),
    }


@app.post("/api/road/unblock")
def unblock_road(req: RoadBlockRequest):
    """Unblocks a previously closed road segment."""
    try:
        unblocked_road = traffic_manager.set_road_status(req.road_id, RoadStatus.OPEN)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    comparison = None
    new_route = None
    if active_state["active_source"] and active_state["active_destination"]:
        new_route = calculate_dijkstra_route(
            traffic_manager.graph,
            active_state["active_source"],
            active_state["active_destination"],
        )
        comparison = compare_routes(
            active_state["last_route"], new_route, traffic_manager.graph
        )
        active_state["last_route"] = new_route

    return {
        "status": "success",
        "road": unblocked_road.to_dict(),
        "active_route": new_route,
        "comparison": comparison,
        "statistics": traffic_manager.get_statistics(),
    }


@app.post("/api/simulation/scenario")
def set_scenario(req: ScenarioRequest):
    """Applies a preset simulation scenario (Normal, Congestion, Road Closure)."""
    try:
        scenario = traffic_manager.apply_scenario(req.scenario_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    comparison = None
    new_route = None
    if active_state["active_source"] and active_state["active_destination"]:
        new_route = calculate_dijkstra_route(
            traffic_manager.graph,
            active_state["active_source"],
            active_state["active_destination"],
        )
        comparison = compare_routes(
            active_state["last_route"], new_route, traffic_manager.graph
        )
        active_state["last_route"] = new_route

    return {
        "status": "success",
        "scenario": scenario,
        "active_route": new_route,
        "comparison": comparison,
        "statistics": traffic_manager.get_statistics(),
    }


@app.post("/api/simulation/reset")
def reset_simulation():
    """Resets the entire transportation network back to default baseline state."""
    traffic_manager.reset_network()

    comparison = None
    new_route = None
    if active_state["active_source"] and active_state["active_destination"]:
        new_route = calculate_dijkstra_route(
            traffic_manager.graph,
            active_state["active_source"],
            active_state["active_destination"],
        )
        comparison = compare_routes(
            active_state["last_route"], new_route, traffic_manager.graph
        )
        active_state["last_route"] = new_route

    return {
        "status": "success",
        "message": "Network restored to baseline normal state.",
        "active_route": new_route,
        "comparison": comparison,
        "statistics": traffic_manager.get_statistics(),
    }


@app.get("/api/routing-table/{source}", response_model=RoutingTableResponse)
def get_routing_table(source: str):
    """
    Returns the complete IP/Link-State style routing table for a given router/junction.
    Essential for Computer Networks viva demonstration.
    """
    source_clean = source.strip().upper()
    if source_clean not in traffic_manager.junctions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Junction '{source}' not found.",
        )
    return generate_routing_table(traffic_manager.graph, source_clean)


# Mount Static Files (Frontend UI)
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
