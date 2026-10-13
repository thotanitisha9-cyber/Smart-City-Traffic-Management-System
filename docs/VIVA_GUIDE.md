# Computer Networks PBL: Viva Voce & Presentation Guide

## Project Title
**Smart City Traffic Management System Using Dynamic Routing Algorithms**

---

## 1. Executive Summary & Problem Statement
In traditional static transportation systems, navigation systems compute routes based purely on physical Euclidean distance. During traffic bursts, accidents, or peak commute hours, static shortest paths funnel all vehicles onto the same arterial roads, causing severe bottleneck gridlock.

In **Computer Networks**, static routing (like manual routing entries) suffers from identical issues: when a link fails or buffers become full, packets are dropped or delayed unless the network employs **dynamic routing protocols** (like OSPF or IS-IS) that monitor link states and converge upon alternative least-cost paths.

This project implements a **Cyber-Physical Dynamic Routing Simulation** where:
- Road intersections are modeled as **Network Nodes / Routers ($V = 14$)**.
- Bidirectional roads are modeled as **Transmission Links / Channels ($E = 28$)**.
- Queuing delay and vehicle density are dynamically modeled via a **Traffic Multiplier ($1.0\times$ to $4.0\times$)**.
- Broken roads or construction closures are modeled as **Link Failures ($Cost = \infty$)**.
- A custom **Dijkstra Shortest Path First (SPF)** algorithm recalculates optimal routes in real-time with automated comparison and algorithmic explanation.

---

## 2. Theoretical Mapping: Smart City Traffic ↔ Computer Networks

| Smart City Traffic Domain | Computer Networks Domain | Detailed Technical Analogy |
| :--- | :--- | :--- |
| **City Junction ($J_1 \dots J_{14}$)** | **Router / Network Node** | Operates as a forwarding entity where traffic enters and exits. Maintains an adjacency state and routing table. |
| **Road Segment ($R_{01} \dots R_{28}$)** | **Transmission Link / Cable** | Physical communication medium with specific capacity (lane count) and base propagation delay (length). |
| **Road Distance ($d$)** | **Propagation Delay / Static Metric** | Distance-based link cost metric, similar to standard RIP hop count or fixed OSPF metric. |
| **Traffic Congestion Level** | **Queuing Delay / Buffer Occupancy** | Delay incurred when packet arrival rate exceeds link transmission rate ($\lambda > \mu$). |
| **Dynamic Cost Metric ($d \times m$)** | **Composite Link Metric** | Dynamically weighted link metric combining static delay and real-time load, similar to Cisco EIGRP composite metric or TE-metric in RSVP-TE. |
| **Road Blockage / Closure** | **Link Failure / Fiber Cut** | Link is disabled. Cost becomes $\infty$; the link is pruned from the graph adjacency during Dijkstra relaxation. |
| **Dynamic Rerouting** | **Routing Protocol Convergence** | Automatic calculation of an alternative loop-free path following a Link State Update. |
| **Traffic Update / Scenario Switch** | **Link State Advertisement (LSA)** | Broadcast message informing all nodes about changes in edge costs. |
| **Optimal Path Engine** | **OSPF / IS-IS SPF Process** | Centralized or distributed execution of Dijkstra’s Algorithm over the Link State Database (LSDB). |
| **Junction Forwarding Table** | **Router Forwarding Table (FIB)** | Map of `(Destination Network -> Next Hop Router, Metric, Hop Count)`. |

---

## 3. Core Algorithm: Dijkstra’s Shortest Path First (SPF)

### Dynamic Weight Formulation:
$$\text{Cost}(u, v) = \begin{cases} \infty & \text{if } \text{RoadStatus} = \text{BLOCKED} \\ \text{Distance}(u, v) \times \text{Multiplier}(\text{TrafficLevel}) & \text{if } \text{RoadStatus} = \text{OPEN} \end{cases}$$

Where the multipliers are:
- **LOW**: $1.0\times$ (Free-flow / Uncongested)
- **MEDIUM**: $1.5\times$ (Moderate queuing)
- **HIGH**: $2.5\times$ (Heavy congestion / Buffer pressure)
- **SEVERE**: $4.0\times$ (Bottleneck gridlock / Saturated buffer)

### Pseudocode Implemented in `backend/routing.py`:
```text
function Dijkstra(Graph, Source, Destination):
    Initialize dist[v] = Infinity for all v in Graph
    Initialize prev[v] = None for all v in Graph
    dist[Source] = 0
    priority_queue.push((0, Source))
    
    while priority_queue is not empty:
        (current_cost, u) = priority_queue.pop_min()
        
        if current_cost > dist[u]:
            continue
            
        if u == Destination:
            break
            
        for each neighbor v connected by edge e:
            if e.status == BLOCKED:
                continue
                
            edge_weight = e.distance_km * e.traffic_multiplier
            new_cost = dist[u] + edge_weight
            
            if new_cost < dist[v]:
                dist[v] = new_cost
                prev[v] = u
                priority_queue.push((new_cost, v))
                
    return ReconstructPath(prev, Source, Destination)
```

### Time & Space Complexity:
- **Time Complexity**: $\mathcal{O}((V + E) \log V)$ using a binary min-heap (`heapq`), where $V = 14$ and $E = 28$.
- **Space Complexity**: $\mathcal{O}(V + E)$ for adjacency list representation and predecessor tracking arrays.

---

## 4. Top 15 Computer Networks Viva Questions & Model Answers

### Q1: What is dynamic routing, and how is it superior to static routing?
**Answer**: In static routing, paths between nodes are manually configured and fixed. If a network link suffers high latency or breaks down, traffic on that link is lost until an administrator intervenes. Dynamic routing uses algorithms (such as Dijkstra in OSPF or Bellman-Ford in RIP) to adapt routing decisions automatically based on current network conditions, link status, and traffic load.

### Q2: Why did you choose Dijkstra's algorithm over Bellman-Ford?
**Answer**: Dijkstra’s algorithm operates on non-negative edge weights with a time complexity of $\mathcal{O}((V + E) \log V)$, which is significantly faster and more computationally efficient than Bellman-Ford's $\mathcal{O}(V \cdot E)$. Since road distances and traffic multipliers can never be negative, Dijkstra is the optimal choice and directly mirrors the Link State routing protocols (OSPF, IS-IS) used in modern enterprise and Internet core backbones.

### Q3: How is traffic congestion analogous to queuing delay in computer networks?
**Answer**: In a computer network, packet delay consists of four components: Nodal Processing Delay, Queuing Delay, Transmission Delay, and Propagation Delay. When the packet arrival rate exceeds the link capacity, packets queue up in router memory buffers. In our smart city model, traffic congestion represents this queuing delay—the physical road length is constant (propagation delay), but high density multiplies the traversal cost.

### Q4: How does your system handle a blocked road or link failure?
**Answer**: When a road is marked `BLOCKED`, its dynamic weight is set to $\infty$. During the priority queue relaxation step of Dijkstra's algorithm, blocked edges are pruned from graph traversal. The algorithm automatically finds the next least-cost reachable path without causing routing loops.

### Q5: What is the difference between Link State and Distance Vector routing?
**Answer**:
- **Link State (OSPF, IS-IS)**: Every router maintains a complete, identical map of the entire network topology (Link State Database). Each node independently runs Dijkstra’s algorithm to calculate the shortest path tree to all destinations.
- **Distance Vector (RIP)**: Routers only know the distance (vector) and next hop to each destination from their immediate neighbors ("routing by rumor"), which converges slower and is vulnerable to the Count-to-Infinity problem.
Our project implements the **Link State** philosophy.

### Q6: What does the "Next Hop" mean in a routing table?
**Answer**: In packet forwarding, routers do not store the entire path to the final destination in the IP packet header. Instead, each router uses its forwarding table to look up the final destination IP and determines the immediate adjacent node (the *Next Hop*) to which the packet should be transmitted across the local link.

### Q7: What metric does your system use for route calculation?
**Answer**: We use a dynamic composite metric:
$$\text{Cost} = \text{Distance (km)} \times \text{Traffic Multiplier}$$
This mirrors how advanced protocols like Cisco EIGRP calculate composite metrics using bandwidth and delay, or how traffic-engineered MPLS networks assign weights based on link utilization.

### Q8: What is routing convergence time?
**Answer**: Convergence time is the time taken by all routers in an autonomous system to update their routing tables and reach a consistent state after a topology change or link failure. In our system, convergence occurs instantly in single-digit milliseconds because the centralized FastAPI graph manager recalculates Dijkstra and updates the client UI within $\approx 5$ ms.

### Q9: Can dynamic routing ever produce suboptimal paths?
**Answer**: If all routes become congested or if routing updates are delayed, temporary routing oscillations or flap can occur in real-world protocols. In our implementation, because graph state updates are atomic and Dijkstra evaluates the global Link State Database, the returned path is mathematically optimal for the current timestamp's edge weights.

### Q10: How does the system compute estimated travel time?
**Answer**:
$$\text{Travel Time (hours)} = \frac{\text{Distance (km)}}{\text{Speed Limit (km/h)} \times \frac{1}{\text{Traffic Multiplier}}}$$
$$\text{Travel Time (min)} = \text{Travel Time (hours)} \times 60$$
When traffic is severe ($4.0\times$), effective vehicular speed drops to $25\%$ of the posted speed limit, increasing travel time proportionately.

### Q11: What is a Link State Advertisement (LSA)?
**Answer**: An LSA is a packet used in Link State protocols that describes the local state of a router's links, interface IP addresses, and configured costs. In our system, triggering a scenario or updating a road's congestion via `POST /api/traffic/update` acts as an LSA that updates the global graph representation.

### Q12: How are routing loops prevented in this system?
**Answer**: Dijkstra's algorithm builds a directed Shortest Path Tree (SPT) originating from the source vertex. Because each node's shortest distance is permanently finalized upon extraction from the min-heap, no cycles can be introduced into the tree, guaranteeing a strictly loop-free path.

### Q13: What happens when the destination node is completely unreachable?
**Answer**: If all incoming edges to the destination node are blocked or disconnected, the priority queue terminates without reaching the destination. The system returns an HTTP 200 response with `status: "unreachable"` and an informative message: *"Destination is unreachable with current road closures."*

### Q14: How does the frontend communicate with the backend?
**Answer**: The frontend communicates asynchronously using the modern JavaScript `fetch()` API making JSON requests over HTTP to RESTful FastAPI endpoints (`/api/route`, `/api/traffic/update`, `/api/simulation/scenario`, `/api/routing-table/{source}`). Leaflet.js renders the geospatial graph and Chart.js renders the live traffic distribution.

### Q15: Why is this system offline-first?
**Answer**: In lab evaluations and viva examinations, third-party internet APIs can introduce rate limits, latency, or authentication failures. Our system embeds synthetic geographic coordinates and topology in local JSON files and includes fallback CSS/JS rendering, ensuring 100% reliable local demonstrations on `http://127.0.0.1:8000`.

---

## 5. Live Demonstration Script for Viva Examiners

1. **Step 1: Introduction & Baseline State**
   - *"Good morning, examiners. Our project is titled 'Smart City Traffic Management System Using Dynamic Routing Algorithms.' We have modeled 14 smart city junctions as network routers and 28 arterial roads as bidirectional transmission channels."*
   - Show the 5 metric cards: 14 Junctions, 28 Roads, 0 Congested, 0 Blocked, 1.0x factor.

2. **Step 2: Baseline Route Calculation**
   - Source: `J1 - Central Plaza`, Destination: `J10 - Industrial Zone`.
   - Click **Find Optimal Route**.
   - Show path: `J1 → J4 → J10` (5.5 km, cost 5.5).

3. **Step 3: Trigger Dynamic Congestion**
   - *"Now, we simulate heavy rush-hour traffic on the East Express Corridor (R03, connecting J1 and J4)."*
   - Select Road `R03`, set traffic to `SEVERE` ($4.0\times$ multiplier), click **Apply Traffic Update**.
   - Point out the **Dynamic Rerouting Analysis card**:
     - Before: `J1 → J4 → J10` (Cost 5.5)
     - After: `J1 → J11 → J4 → J10` (Cost 5.6)
     - Explain: *"Even though the new path is 0.1 km physically longer, the dynamic cost through the bypass is lower than the heavily congested R03 segment."*

4. **Step 4: Demonstrate Link Failure Avoidance**
   - Set Road `R03` status to `BLOCKED` (Link Failure).
   - Show that the path bypasses R03 completely, and the blocked road counter increments to 1.

5. **Step 5: Predefined Scenarios & Reset**
   - Click **Scenario 2: Peak Congestion** to show multi-road simultaneous queuing.
   - Click **Reset Simulation** to show instant convergence back to baseline.

6. **Step 6: Viva Modals (CN Concepts & Routing Table)**
   - Open **CN Concepts** to show theoretical mapping.
   - Open **Routing Table** to show Next-Hop router forwarding entries for router $J_1$.
