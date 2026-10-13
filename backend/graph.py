from typing import Dict, List, Tuple, Optional
from backend.models import Junction, Road, RoadStatus


class CityGraph:
    """
    Graph representation of the Smart City transportation network.
    Junctions correspond to vertices (network routers/nodes).
    Roads correspond to bidirectional edges (network links).
    """

    def __init__(self, junctions: Dict[str, Junction], roads: Dict[str, Road]):
        self.junctions: Dict[str, Junction] = junctions
        self.roads: Dict[str, Road] = roads
        self.adjacency: Dict[str, List[Tuple[str, Road]]] = {j_id: [] for j_id in junctions}
        self._build_adjacency()

    def _build_adjacency(self) -> None:
        """Constructs adjacency list for bidirectional roads."""
        for j_id in self.junctions:
            self.adjacency[j_id] = []

        for road in self.roads.values():
            u = road.source
            v = road.destination
            if u in self.adjacency and v in self.adjacency:
                self.adjacency[u].append((v, road))
                self.adjacency[v].append((u, road))

    def rebuild_adjacency(self) -> None:
        """Re-evaluates adjacency when roads or junctions change."""
        self._build_adjacency()

    def get_neighbors(self, junction_id: str) -> List[Tuple[str, Road]]:
        """Returns list of (neighbor_junction_id, road_object)."""
        return self.adjacency.get(junction_id, [])

    def get_road_between(self, u: str, v: str) -> Optional[Road]:
        """Finds the Road object connecting u and v."""
        for neighbor, road in self.get_neighbors(u):
            if neighbor == v:
                return road
        return None

    def get_junction(self, junction_id: str) -> Optional[Junction]:
        return self.junctions.get(junction_id)

    def get_road(self, road_id: str) -> Optional[Road]:
        return self.roads.get(road_id)

    def clone(self) -> "CityGraph":
        """Creates a detached deep copy of the graph."""
        cloned_junctions = {k: v.model_copy() for k, v in self.junctions.items()}
        cloned_roads = {k: v.model_copy() for k, v in self.roads.items()}
        return CityGraph(cloned_junctions, cloned_roads)
