import json
import os
from pathlib import Path
from typing import Dict, List, Tuple, Any
from backend.models import Junction, Road, TrafficLevel, RoadStatus, TRAFFIC_MULTIPLIERS


def get_data_dir() -> Path:
    """Resolve data directory relative to project root."""
    current_dir = Path(__file__).resolve().parent
    data_dir = current_dir.parent / "data"
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found at: {data_dir}")
    return data_dir


def load_raw_junctions() -> List[Dict[str, Any]]:
    path = get_data_dir() / "junctions.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_raw_roads() -> List[Dict[str, Any]]:
    path = get_data_dir() / "roads.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_raw_scenarios() -> Dict[str, Any]:
    path = get_data_dir() / "scenarios.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_initial_entities() -> Tuple[Dict[str, Junction], Dict[str, Road]]:
    """Loads and instantiates Junction and Road objects from JSON datasets."""
    raw_junctions = load_raw_junctions()
    raw_roads = load_raw_roads()

    junctions: Dict[str, Junction] = {}
    for j in raw_junctions:
        junctions[j["id"]] = Junction(**j)

    roads: Dict[str, Road] = {}
    for r in raw_roads:
        level = TrafficLevel(r.get("traffic_level", "LOW"))
        status = RoadStatus(r.get("status", "OPEN"))
        factor = TRAFFIC_MULTIPLIERS.get(level, 1.0)
        roads[r["road_id"]] = Road(
            road_id=r["road_id"],
            name=r["name"],
            source=r["source"],
            destination=r["destination"],
            distance_km=float(r["distance_km"]),
            speed_limit=int(r["speed_limit"]),
            traffic_level=level,
            traffic_factor=factor,
            status=status,
            lanes=int(r.get("lanes", 2)),
        )

    return junctions, roads
