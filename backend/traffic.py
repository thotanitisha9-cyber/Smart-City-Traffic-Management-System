from typing import Dict, Optional, List, Any
from backend.models import (
    Road,
    Junction,
    TrafficLevel,
    RoadStatus,
    TRAFFIC_MULTIPLIERS,
    NetworkStatistics,
)
from backend.graph import CityGraph
from backend.data_loader import load_initial_entities, load_raw_scenarios


class TrafficManager:
    """
    Manages live state of the Smart City road network, handles dynamic traffic
    modifications, scenarios, and resets.
    """

    def __init__(self):
        self.junctions, self.roads = load_initial_entities()
        self.graph = CityGraph(self.junctions, self.roads)
        self.scenarios_data = load_raw_scenarios()
        self.current_scenario_id = 1

    def reset_network(self) -> None:
        """Restores all roads and junctions to original baseline dataset."""
        self.junctions, self.roads = load_initial_entities()
        self.graph = CityGraph(self.junctions, self.roads)
        self.current_scenario_id = 1

    def update_road_traffic(self, road_id: str, traffic_level: TrafficLevel) -> Road:
        """Modifies traffic level and updates traffic factor accordingly."""
        road = self.roads.get(road_id)
        if not road:
            raise KeyError(f"Road ID '{road_id}' not found.")

        road.traffic_level = traffic_level
        road.traffic_factor = TRAFFIC_MULTIPLIERS.get(traffic_level, 1.0)
        self.graph.rebuild_adjacency()
        return road

    def set_road_status(self, road_id: str, status: RoadStatus) -> Road:
        """Blocks or unblocks a road."""
        road = self.roads.get(road_id)
        if not road:
            raise KeyError(f"Road ID '{road_id}' not found.")

        road.status = status
        self.graph.rebuild_adjacency()
        return road

    def apply_scenario(self, scenario_id: int) -> Dict[str, Any]:
        """Applies a preset simulation scenario."""
        scenarios = self.scenarios_data.get("scenarios", [])
        selected = next((s for s in scenarios if s["id"] == scenario_id), None)
        if not selected:
            raise ValueError(f"Scenario ID '{scenario_id}' not found.")

        # Always start from clean baseline before applying scenario overrides
        self.reset_network()
        self.current_scenario_id = scenario_id

        for update in selected.get("updates", []):
            r_id = update["road_id"]
            if r_id in self.roads:
                road = self.roads[r_id]
                level = TrafficLevel(update.get("traffic_level", road.traffic_level.value))
                status = RoadStatus(update.get("status", road.status.value))
                road.traffic_level = level
                road.traffic_factor = TRAFFIC_MULTIPLIERS.get(level, 1.0)
                road.status = status

        self.graph.rebuild_adjacency()
        return selected

    def get_statistics(self) -> NetworkStatistics:
        """Computes live network statistics across all roads."""
        total_j = len(self.junctions)
        total_r = len(self.roads)

        low_count = sum(1 for r in self.roads.values() if r.traffic_level == TrafficLevel.LOW and r.status == RoadStatus.OPEN)
        med_count = sum(1 for r in self.roads.values() if r.traffic_level == TrafficLevel.MEDIUM and r.status == RoadStatus.OPEN)
        high_count = sum(1 for r in self.roads.values() if r.traffic_level == TrafficLevel.HIGH and r.status == RoadStatus.OPEN)
        severe_count = sum(1 for r in self.roads.values() if r.traffic_level == TrafficLevel.SEVERE and r.status == RoadStatus.OPEN)
        blocked_count = sum(1 for r in self.roads.values() if r.status == RoadStatus.BLOCKED)
        open_count = total_r - blocked_count

        open_multipliers = [r.traffic_factor for r in self.roads.values() if r.status == RoadStatus.OPEN]
        avg_factor = round(sum(open_multipliers) / len(open_multipliers), 2) if open_multipliers else 1.0

        return NetworkStatistics(
            total_junctions=total_j,
            total_roads=total_r,
            low_traffic_roads=low_count,
            medium_traffic_roads=med_count,
            high_traffic_roads=high_count,
            severe_traffic_roads=severe_count,
            blocked_roads=blocked_count,
            open_roads=open_count,
            average_traffic_multiplier=avg_factor,
        )
