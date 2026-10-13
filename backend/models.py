from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class TrafficLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    SEVERE = "SEVERE"


class RoadStatus(str, Enum):
    OPEN = "OPEN"
    BLOCKED = "BLOCKED"


TRAFFIC_MULTIPLIERS = {
    TrafficLevel.LOW: 1.0,
    TrafficLevel.MEDIUM: 1.5,
    TrafficLevel.HIGH: 2.5,
    TrafficLevel.SEVERE: 4.0,
}


class Junction(BaseModel):
    id: str
    name: str
    lat: float
    lng: float
    type: str = "Junction"
    description: str = ""


class Road(BaseModel):
    road_id: str
    name: str
    source: str
    destination: str
    distance_km: float
    speed_limit: int
    traffic_level: TrafficLevel = TrafficLevel.LOW
    traffic_factor: float = 1.0
    status: RoadStatus = RoadStatus.OPEN
    lanes: int = 2

    @property
    def dynamic_cost(self) -> float:
        """Dynamic cost formulation: distance * traffic_multiplier, or infinity if blocked."""
        if self.status == RoadStatus.BLOCKED:
            return float("inf")
        multiplier = TRAFFIC_MULTIPLIERS.get(self.traffic_level, 1.0)
        return round(self.distance_km * multiplier, 2)

    @property
    def estimated_time_minutes(self) -> float:
        """Estimated travel time in minutes based on distance, speed limit, and congestion multiplier."""
        if self.status == RoadStatus.BLOCKED or self.speed_limit <= 0:
            return float("inf")
        multiplier = TRAFFIC_MULTIPLIERS.get(self.traffic_level, 1.0)
        base_hours = self.distance_km / self.speed_limit
        total_minutes = base_hours * multiplier * 60
        return round(total_minutes, 1)

    def to_dict(self) -> Dict[str, Any]:
        data = self.model_dump()
        data["dynamic_cost"] = self.dynamic_cost if self.status == RoadStatus.OPEN else 999999.0
        data["estimated_time_min"] = self.estimated_time_minutes if self.status == RoadStatus.OPEN else 999999.0
        return data


class RouteRequest(BaseModel):
    source: str = Field(..., description="Source junction ID (e.g. J1)")
    destination: str = Field(..., description="Destination junction ID (e.g. J10)")


class RouteStep(BaseModel):
    road_id: str
    road_name: str
    from_junction: str
    to_junction: str
    distance_km: float
    speed_limit: int
    traffic_level: TrafficLevel
    status: RoadStatus
    dynamic_cost: float
    estimated_time_min: float


class RouteResponse(BaseModel):
    status: str
    source: str
    destination: str
    route: List[str] = []
    route_names: List[str] = []
    roads_used: List[str] = []
    steps: List[RouteStep] = []
    total_distance_km: float = 0.0
    total_dynamic_cost: float = 0.0
    estimated_time_min: float = 0.0
    number_of_roads: int = 0
    traffic_summary: str = "Normal"
    message: Optional[str] = None


class TrafficUpdateRequest(BaseModel):
    road_id: str
    traffic_level: TrafficLevel


class RoadBlockRequest(BaseModel):
    road_id: str


class ScenarioRequest(BaseModel):
    scenario_id: int


class RouteComparisonResponse(BaseModel):
    route_changed: bool
    old_route: Optional[RouteResponse] = None
    new_route: Optional[RouteResponse] = None
    cost_delta: float = 0.0
    distance_delta: float = 0.0
    time_delta: float = 0.0
    reason: str


class NetworkStatistics(BaseModel):
    total_junctions: int
    total_roads: int
    low_traffic_roads: int
    medium_traffic_roads: int
    high_traffic_roads: int
    severe_traffic_roads: int
    blocked_roads: int
    open_roads: int
    average_traffic_multiplier: float


class RoutingTableEntry(BaseModel):
    destination: str
    destination_name: str
    next_hop: str
    next_hop_name: str
    dynamic_cost: float
    total_distance_km: float
    hops: int


class RoutingTableResponse(BaseModel):
    source: str
    source_name: str
    entries: List[RoutingTableEntry]
