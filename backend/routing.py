import heapq
from typing import Dict, List, Tuple, Optional
from backend.models import (
    Road,
    Junction,
    RoadStatus,
    TrafficLevel,
    RouteResponse,
    RouteStep,
    RouteComparisonResponse,
    RoutingTableEntry,
    RoutingTableResponse,
)
from backend.graph import CityGraph


def calculate_dijkstra_route(
    graph: CityGraph, source: str, destination: str
) -> RouteResponse:
    """
    Manual implementation of Dijkstra's Algorithm with dynamic edge weights.
    
    In Computer Networks terminology:
    - Junctions are Routers/Nodes.
    - Roads are Transmission Links.
    - Dynamic Cost is Link Cost (Delay / Congestion metric).
    - Blocked roads represent Link Failures (metric = infinity).
    """
    # 1. Validation
    source_junction = graph.get_junction(source)
    dest_junction = graph.get_junction(destination)

    if not source_junction:
        return RouteResponse(
            status="error",
            source=source,
            destination=destination,
            message=f"Source junction '{source}' does not exist in the network.",
        )

    if not dest_junction:
        return RouteResponse(
            status="error",
            source=source,
            destination=destination,
            message=f"Destination junction '{destination}' does not exist in the network.",
        )

    # 2. Base case: Source is Destination
    if source == destination:
        return RouteResponse(
            status="success",
            source=source,
            destination=destination,
            route=[source],
            route_names=[source_junction.name],
            roads_used=[],
            steps=[],
            total_distance_km=0.0,
            total_dynamic_cost=0.0,
            estimated_time_min=0.0,
            number_of_roads=0,
            traffic_summary="None (Already at destination)",
            message="Source and destination are identical.",
        )

    # 3. Dijkstra Data Structures
    # distances[node] holds current minimum dynamic cost from source to node
    distances: Dict[str, float] = {j_id: float("inf") for j_id in graph.junctions}
    distances[source] = 0.0

    # previous[node] stores (predecessor_node, road_used) to backtrack optimal path
    previous: Dict[str, Optional[Tuple[str, Road]]] = {j_id: None for j_id in graph.junctions}

    # Min-Heap Priority Queue: elements are tuples of (cost, current_node)
    pq: List[Tuple[float, str]] = [(0.0, source)]

    visited = set()

    # 4. Dijkstra Main Loop
    while pq:
        current_cost, u = heapq.heappop(pq)

        if u in visited:
            continue
        visited.add(u)

        # Early exit if we reached target destination with confirmed shortest cost
        if u == destination:
            break

        # Explore all adjacent incident edges (neighboring junctions)
        for v, road in graph.get_neighbors(u):
            # If the road link is BLOCKED, treat link cost as infinite (avoid link)
            if road.status == RoadStatus.BLOCKED:
                continue

            # Calculate dynamic cost = distance * traffic_multiplier
            edge_dynamic_cost = road.dynamic_cost

            # Total tentative cost from source to v through u
            tentative_cost = current_cost + edge_dynamic_cost

            # Relaxation step: update if lower dynamic cost found
            if tentative_cost < distances[v]:
                distances[v] = tentative_cost
                previous[v] = (u, road)
                heapq.heappush(pq, (tentative_cost, v))

    # 5. Check Reachability
    if distances[destination] == float("inf") or previous[destination] is None:
        return RouteResponse(
            status="error",
            source=source,
            destination=destination,
            route=[],
            route_names=[],
            roads_used=[],
            steps=[],
            total_distance_km=0.0,
            total_dynamic_cost=0.0,
            estimated_time_min=0.0,
            number_of_roads=0,
            traffic_summary="Unreachable",
            message=f"No route found between '{source_junction.name}' ({source}) and '{dest_junction.name}' ({destination}). Connecting links are blocked or severed.",
        )

    # 6. Path Reconstruction (Backtracking from destination to source)
    path_nodes: List[str] = []
    path_roads: List[Road] = []
    curr = destination

    while curr != source:
        path_nodes.append(curr)
        prev_tuple = previous[curr]
        if prev_tuple is None:
            break
        u, road = prev_tuple
        path_roads.append(road)
        curr = u

    path_nodes.append(source)
    path_nodes.reverse()
    path_roads.reverse()

    # 7. Aggregate Route Metrics
    route_names = [graph.get_junction(n).name for n in path_nodes if graph.get_junction(n)]
    roads_used = [r.road_id for r in path_roads]

    steps: List[RouteStep] = []
    total_dist = 0.0
    total_cost = 0.0
    total_time = 0.0
    traffic_levels = []

    for i, road in enumerate(path_roads):
        u = path_nodes[i]
        v = path_nodes[i + 1]
        cost = road.dynamic_cost
        time_min = road.estimated_time_minutes

        total_dist += road.distance_km
        total_cost += cost
        total_time += time_min
        traffic_levels.append(road.traffic_level)

        steps.append(
            RouteStep(
                road_id=road.road_id,
                road_name=road.name,
                from_junction=u,
                to_junction=v,
                distance_km=road.distance_km,
                speed_limit=road.speed_limit,
                traffic_level=road.traffic_level,
                status=road.status,
                dynamic_cost=cost,
                estimated_time_min=time_min,
            )
        )

    # Determine general traffic summary
    if any(lvl == TrafficLevel.SEVERE for lvl in traffic_levels):
        traffic_summary = "Severe Delays"
    elif any(lvl == TrafficLevel.HIGH for lvl in traffic_levels):
        traffic_summary = "Heavy Congestion"
    elif any(lvl == TrafficLevel.MEDIUM for lvl in traffic_levels):
        traffic_summary = "Moderate Traffic"
    else:
        traffic_summary = "Optimal / Free Flow"

    return RouteResponse(
        status="success",
        source=source,
        destination=destination,
        route=path_nodes,
        route_names=route_names,
        roads_used=roads_used,
        steps=steps,
        total_distance_km=round(total_dist, 2),
        total_dynamic_cost=round(total_cost, 2),
        estimated_time_min=round(total_time, 1),
        number_of_roads=len(path_roads),
        traffic_summary=traffic_summary,
        message=f"Optimal dynamic route found with {len(path_roads)} road segments.",
    )


def compare_routes(
    old_route: Optional[RouteResponse], new_route: RouteResponse, graph: CityGraph
) -> RouteComparisonResponse:
    """
    Compares before & after route calculations to explain dynamic rerouting decisions.
    Essential for Computer Networks demonstration of adaptive routing convergence.
    """
    if old_route is None or old_route.status != "success":
        return RouteComparisonResponse(
            route_changed=False,
            old_route=None,
            new_route=new_route,
            cost_delta=0.0,
            distance_delta=0.0,
            time_delta=0.0,
            reason="Initial dynamic route established across network graph.",
        )

    if new_route.status != "success":
        return RouteComparisonResponse(
            route_changed=True,
            old_route=old_route,
            new_route=new_route,
            cost_delta=0.0,
            distance_delta=0.0,
            time_delta=0.0,
            reason="Destination is now unreachable due to active link blockage.",
        )

    same_path = old_route.route == new_route.route
    cost_delta = round(new_route.total_dynamic_cost - old_route.total_dynamic_cost, 2)
    dist_delta = round(new_route.total_distance_km - old_route.total_distance_km, 2)
    time_delta = round(new_route.estimated_time_min - old_route.estimated_time_min, 1)

    if same_path:
        if cost_delta > 0:
            reason = (
                f"Route unchanged ({' → '.join(new_route.route)}). Although traffic increased on segments "
                f"(cost grew by +{cost_delta}), this path remains the mathematically optimal route."
            )
        elif cost_delta < 0:
            reason = (
                f"Route unchanged ({' → '.join(new_route.route)}). Traffic conditions improved "
                f"(cost reduced by {cost_delta}), keeping this as the optimal path."
            )
        else:
            reason = "No traffic changes affected this route. Current path remains optimal."
    else:
        # Route changed! Analyze why
        old_nodes_set = set(zip(old_route.route[:-1], old_route.route[1:]))
        new_nodes_set = set(zip(new_route.route[:-1], new_route.route[1:]))
        avoided_links = old_nodes_set - new_nodes_set

        congestion_reasons = []
        for u, v in avoided_links:
            road = graph.get_road_between(u, v)
            if road:
                if road.status == RoadStatus.BLOCKED:
                    congestion_reasons.append(f"Road '{road.name}' ({u}↔{v}) is BLOCKED")
                elif road.traffic_level in (TrafficLevel.HIGH, TrafficLevel.SEVERE):
                    congestion_reasons.append(
                        f"Heavy congestion ({road.traffic_level}) on '{road.name}' ({u}↔{v})"
                    )

        reason_prefix = (
            "; ".join(congestion_reasons)
            if congestion_reasons
            else "Dynamic edge weights changed due to traffic fluctuations"
        )

        if dist_delta > 0:
            dist_desc = f"a {dist_delta} km longer bypass"
        elif dist_delta < 0:
            dist_desc = f"a {abs(dist_delta)} km shorter path"
        else:
            dist_desc = "an equal distance alternative"

        reason = (
            f"Dynamic Rerouting Triggered: {reason_prefix}. "
            f"The routing engine diverted traffic to {dist_desc} with lower dynamic cost "
            f"({new_route.total_dynamic_cost} vs previous {old_route.total_dynamic_cost})."
        )

    return RouteComparisonResponse(
        route_changed=not same_path,
        old_route=old_route,
        new_route=new_route,
        cost_delta=cost_delta,
        distance_delta=dist_delta,
        time_delta=time_delta,
        reason=reason,
    )


def generate_routing_table(graph: CityGraph, source: str) -> RoutingTableResponse:
    """
    Generates the complete routing table for a given router/junction node.
    Direct Computer Networks analogy to an IP / OSPF Routing Table.
    """
    source_j = graph.get_junction(source)
    if not source_j:
        return RoutingTableResponse(source=source, source_name="Unknown", entries=[])

    entries: List[RoutingTableEntry] = []

    for dest_id, dest_j in graph.junctions.items():
        if dest_id == source:
            continue
        route_res = calculate_dijkstra_route(graph, source, dest_id)
        if route_res.status == "success" and len(route_res.route) >= 2:
            next_hop_id = route_res.route[1]
            next_hop_j = graph.get_junction(next_hop_id)
            entries.append(
                RoutingTableEntry(
                    destination=dest_id,
                    destination_name=dest_j.name,
                    next_hop=next_hop_id,
                    next_hop_name=next_hop_j.name if next_hop_j else next_hop_id,
                    dynamic_cost=route_res.total_dynamic_cost,
                    total_distance_km=route_res.total_distance_km,
                    hops=len(route_res.route) - 1,
                )
            )

    # Sort routing table by destination ID
    entries.sort(key=lambda e: int(e.destination.replace("J", "")) if e.destination[1:].isdigit() else 999)

    return RoutingTableResponse(source=source, source_name=source_j.name, entries=entries)
