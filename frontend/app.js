/**
 * Smart City Traffic Management System
 * Dynamic Routing Engine & Leaflet Visualization Controller
 * Computer Networks PBL Project
 */

// Application State
const state = {
  junctions: [],
  roads: [],
  junctionMap: new Map(),
  roadMap: new Map(),
  activeSource: null,
  activeDestination: null,
  activeRouteData: null,
  lastRouteData: null,
  map: null,
  markers: new Map(),
  polylines: new Map(),
  routeHighlightLayers: [],
  trafficChart: null,
};

// Traffic Multipliers & Visual Colors
const TRAFFIC_CONFIG = {
  LOW: { color: "#10b981", weight: 4.5, opacity: 0.85, name: "Low", multiplier: 1.0 },
  MEDIUM: { color: "#f59e0b", weight: 5.0, opacity: 0.9, name: "Medium", multiplier: 1.5 },
  HIGH: { color: "#f97316", weight: 5.5, opacity: 0.95, name: "High", multiplier: 2.5 },
  SEVERE: { color: "#ef4444", weight: 6.5, opacity: 1.0, name: "Severe", multiplier: 4.0 },
  BLOCKED: { color: "#64748b", weight: 4.0, opacity: 0.7, dashArray: "6, 8", name: "Blocked", multiplier: Infinity }
};

// DOM Elements
const elements = {
  selectSource: document.getElementById("select-source"),
  selectDestination: document.getElementById("select-destination"),
  btnFindRoute: document.getElementById("btn-find-route"),
  btnSwapEndpoints: document.getElementById("btn-swap-endpoints"),
  selectRoad: document.getElementById("select-road"),
  selectTrafficLevel: document.getElementById("select-traffic-level"),
  radioStatusOpen: document.getElementById("radio-status-open"),
  radioStatusBlocked: document.getElementById("radio-status-blocked"),
  btnApplyTraffic: document.getElementById("btn-apply-traffic"),
  btnScenario1: document.getElementById("btn-scenario-1"),
  btnScenario2: document.getElementById("btn-scenario-2"),
  btnScenario3: document.getElementById("btn-scenario-3"),
  btnResetSimulation: document.getElementById("btn-reset-simulation"),
  statJunctions: document.getElementById("stat-junctions"),
  statRoads: document.getElementById("stat-roads"),
  statCongested: document.getElementById("stat-congested"),
  statBlocked: document.getElementById("stat-blocked"),
  statFactor: document.getElementById("stat-factor"),
  resultStatusBadge: document.getElementById("result-status-badge"),
  resultPathChain: document.getElementById("result-path-chain"),
  resultDistance: document.getElementById("result-distance"),
  resultTime: document.getElementById("result-time"),
  resultCost: document.getElementById("result-cost"),
  resultRoadsCount: document.getElementById("result-roads-count"),
  resultTrafficSummary: document.getElementById("result-traffic-summary"),
  tbodySteps: document.getElementById("tbody-steps"),
  compBeforeRoute: document.getElementById("comp-before-route"),
  compBeforeDist: document.getElementById("comp-before-dist"),
  compBeforeCost: document.getElementById("comp-before-cost"),
  compBeforeTime: document.getElementById("comp-before-time"),
  compAfterRoute: document.getElementById("comp-after-route"),
  compAfterDist: document.getElementById("comp-after-dist"),
  compAfterCost: document.getElementById("comp-after-cost"),
  compAfterTime: document.getElementById("comp-after-time"),
  compReasonText: document.getElementById("comp-reason-text"),
  comparisonBadge: document.getElementById("comparison-badge"),
  btnOpenConcepts: document.getElementById("btn-open-concepts"),
  btnOpenAlgorithm: document.getElementById("btn-open-algorithm"),
  btnOpenRoutingTable: document.getElementById("btn-open-routing-table"),
  modalConcepts: document.getElementById("modal-concepts"),
  modalAlgorithm: document.getElementById("modal-algorithm"),
  modalRoutingTable: document.getElementById("modal-routing-table"),
  selectRtSource: document.getElementById("select-rt-source"),
  btnRefreshRt: document.getElementById("btn-refresh-rt"),
  tbodyRoutingTable: document.getElementById("tbody-routing-table"),
  toastContainer: document.getElementById("toast-container"),
};

// ============================================================================
// Initialization
// ============================================================================

document.addEventListener("DOMContentLoaded", async () => {
  initMap();
  initChart();
  setupEventListeners();
  await loadInitialData();
});

function initMap() {
  // Center coordinates over fictional smart-city grid
  const initialCenter = [17.4400, 78.3880];
  state.map = L.map("map-container", {
    center: initialCenter,
    zoom: 13,
    zoomControl: true,
  });

  // Standard OpenStreetMap tiles (100% free, no watermark)
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
  }).addTo(state.map);
}

function initChart() {
  const ctx = document.getElementById("traffic-chart");
  if (!ctx) return;

  state.trafficChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["Low Traffic", "Medium Traffic", "High Traffic", "Severe Traffic", "Blocked"],
      datasets: [
        {
          data: [28, 0, 0, 0, 0],
          backgroundColor: [
            "#10b981", // Low
            "#f59e0b", // Medium
            "#f97316", // High
            "#ef4444", // Severe
            "#475569", // Blocked
          ],
          borderColor: "#131b2e",
          borderWidth: 2,
          hoverOffset: 6,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            boxWidth: 12,
            font: { size: 11, family: "'Inter', sans-serif" },
            color: "#94a3b8",
            padding: 10,
          },
        },
        tooltip: {
          callbacks: {
            label: function (context) {
              const count = context.parsed;
              const total = context.dataset.data.reduce((a, b) => a + b, 0);
              const pct = total > 0 ? ((count / total) * 100).toFixed(0) : 0;
              return ` ${context.label}: ${count} roads (${pct}%)`;
            },
          },
        },
      },
      cutout: "68%",
    },
  });
}

// ============================================================================
// Data Fetching & Rendering
// ============================================================================

async function loadInitialData() {
  try {
    const [junctionsRes, roadsRes, statsRes] = await Promise.all([
      fetch("/api/junctions"),
      fetch("/api/roads"),
      fetch("/api/statistics"),
    ]);

    if (!junctionsRes.ok || !roadsRes.ok || !statsRes.ok) {
      throw new Error("Failed to load initial data from backend API.");
    }

    state.junctions = await junctionsRes.json();
    state.roads = await roadsRes.json();
    const stats = await statsRes.json();

    state.junctionMap.clear();
    state.junctions.forEach((j) => state.junctionMap.set(j.id, j));

    state.roadMap.clear();
    state.roads.forEach((r) => state.roadMap.set(r.road_id, r));

    populateJunctionDropdowns();
    populateRoadDropdown();
    renderMapElements();
    updateStatistics(stats);

    // Default select J1 and J10 for rapid demo
    if (elements.selectSource && elements.selectDestination) {
      elements.selectSource.value = "J1";
      elements.selectDestination.value = "J10";
      // Auto-compute baseline optimal route so user sees instant wow result!
      calculateRoute("J1", "J10");
    }

    showToast("Smart City network initialized successfully.", "success");
  } catch (err) {
    console.error("Initialization error:", err);
    showToast("Could not connect to backend. Please check if server is running.", "error");
  }
}

function populateJunctionDropdowns() {
  const optionsHtml = state.junctions
    .map((j) => `<option value="${j.id}">${j.id} - ${j.name} (${j.type})</option>`)
    .join("");

  elements.selectSource.innerHTML = optionsHtml;
  elements.selectDestination.innerHTML = optionsHtml;
  elements.selectRtSource.innerHTML = optionsHtml;

  if (state.junctions.length > 0) {
    elements.selectSource.value = state.junctions[0].id;
    elements.selectDestination.value = state.junctions[state.junctions.length - 1].id;
    elements.selectRtSource.value = state.junctions[0].id;
  }
}

function populateRoadDropdown() {
  elements.selectRoad.innerHTML = state.roads
    .map(
      (r) =>
        `<option value="${r.road_id}">${r.road_id}: ${r.name} (${r.source} ↔ ${r.destination}) [${r.distance_km} km]</option>`
    )
    .join("");

  // Select first road
  if (state.roads.length > 0) {
    selectRoadInControl(state.roads[0].road_id);
  }
}

function selectRoadInControl(roadId) {
  elements.selectRoad.value = roadId;
  const road = state.roadMap.get(roadId);
  if (!road) return;

  elements.selectTrafficLevel.value = road.traffic_level;
  if (road.status === "BLOCKED") {
    elements.radioStatusBlocked.checked = true;
  } else {
    elements.radioStatusOpen.checked = true;
  }
}

// ============================================================================
// Leaflet Map Network Rendering
// ============================================================================

function renderMapElements() {
  // Clear existing
  state.markers.forEach((m) => state.map.removeLayer(m));
  state.markers.clear();

  state.polylines.forEach((p) => state.map.removeLayer(p));
  state.polylines.clear();

  // 1. Render Road Polylines
  state.roads.forEach((road) => {
    const u = state.junctionMap.get(road.source);
    const v = state.junctionMap.get(road.destination);
    if (!u || !v) return;

    const latlngs = [
      [u.lat, u.lng],
      [v.lat, v.lng],
    ];

    const config =
      road.status === "BLOCKED"
        ? TRAFFIC_CONFIG.BLOCKED
        : TRAFFIC_CONFIG[road.traffic_level] || TRAFFIC_CONFIG.LOW;

    const polyline = L.polyline(latlngs, {
      color: config.color,
      weight: config.weight,
      opacity: config.opacity,
      dashArray: config.dashArray || null,
      lineCap: "round",
    }).addTo(state.map);

    // Popup
    const popupContent = `
      <div style="font-family: 'Inter', sans-serif; font-size: 12px; line-height: 1.4;">
        <strong style="font-size: 14px; color: #0284c7;">${road.name} (${road.road_id})</strong><br>
        <strong>Endpoints:</strong> ${u.name} (${u.id}) ↔ ${v.name} (${v.id})<br>
        <strong>Distance:</strong> ${road.distance_km} km | <strong>Speed:</strong> ${road.speed_limit} km/h<br>
        <strong>Traffic Level:</strong> <span style="font-weight: bold; color: ${config.color};">${road.traffic_level} (${road.traffic_factor}x)</span><br>
        <strong>Status:</strong> <span style="font-weight: bold; color: ${road.status === 'BLOCKED' ? '#ef4444' : '#10b981'};">${road.status}</span><br>
        <strong>Dynamic Cost:</strong> ${road.status === 'BLOCKED' ? 'Infinity (Blocked)' : road.dynamic_cost}<br>
        <button onclick="window.uiSelectRoad('${road.road_id}')" style="margin-top: 8px; background: #0284c7; color: white; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 11px;">
          Select in Traffic Control Panel
        </button>
      </div>
    `;
    polyline.bindPopup(popupContent);

    polyline.on("click", () => {
      selectRoadInControl(road.road_id);
    });

    state.polylines.set(road.road_id, polyline);
  });

  // 2. Render Junction Markers
  state.junctions.forEach((j) => {
    const isSource = state.activeSource === j.id;
    const isDest = state.activeDestination === j.id;

    let markerClass = "custom-junction-marker";
    if (isSource) markerClass += " is-source";
    if (isDest) markerClass += " is-destination";

    const customIcon = L.divIcon({
      className: "",
      html: `<div class="${markerClass}" style="width: 28px; height: 28px;">${j.id}</div>`,
      iconSize: [28, 28],
      iconAnchor: [14, 14],
    });

    const marker = L.marker([j.lat, j.lng], { icon: customIcon }).addTo(state.map);

    const popupHtml = `
      <div style="font-family: 'Inter', sans-serif; font-size: 12px;">
        <strong style="font-size: 14px; color: #0f172a;">${j.name} (${j.id})</strong><br>
        <em>Type: ${j.type}</em><br>
        <span style="color: #64748b;">${j.description}</span><br>
        <div style="margin-top: 8px; display: flex; gap: 6px;">
          <button onclick="window.uiSetOrigin('${j.id}')" style="background: #10b981; color: white; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 11px;">Set as Source</button>
          <button onclick="window.uiSetDest('${j.id}')" style="background: #0284c7; color: white; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 11px;">Set as Target</button>
        </div>
      </div>
    `;
    marker.bindPopup(popupHtml);

    state.markers.set(j.id, marker);
  });
}

// Global helpers for Leaflet popups
window.uiSelectRoad = (roadId) => {
  selectRoadInControl(roadId);
  showToast(`Selected road ${roadId} in Traffic Control.`, "info");
};

window.uiSetOrigin = (junctionId) => {
  elements.selectSource.value = junctionId;
  showToast(`Source set to ${junctionId}`, "info");
};

window.uiSetDest = (junctionId) => {
  elements.selectDestination.value = junctionId;
  showToast(`Destination set to ${junctionId}`, "info");
};

function updateRoadPolyline(road) {
  const polyline = state.polylines.get(road.road_id);
  if (!polyline) return;

  const config =
    road.status === "BLOCKED"
      ? TRAFFIC_CONFIG.BLOCKED
      : TRAFFIC_CONFIG[road.traffic_level] || TRAFFIC_CONFIG.LOW;

  polyline.setStyle({
    color: config.color,
    weight: config.weight,
    opacity: config.opacity,
    dashArray: config.dashArray || null,
  });
}

function highlightOptimalRoute(routeNodeIds) {
  // Clear previous route highlight layers
  state.routeHighlightLayers.forEach((layer) => state.map.removeLayer(layer));
  state.routeHighlightLayers = [];

  if (!routeNodeIds || routeNodeIds.length < 2) return;

  const routeLatLngs = [];
  for (let i = 0; i < routeNodeIds.length; i++) {
    const j = state.junctionMap.get(routeNodeIds[i]);
    if (j) routeLatLngs.push([j.lat, j.lng]);
  }

  // Outer glowing line (Cyan glow)
  const glowLine = L.polyline(routeLatLngs, {
    color: "#06b6d4",
    weight: 12,
    opacity: 0.5,
    lineCap: "round",
    lineJoin: "round",
  }).addTo(state.map);

  // Inner sharp route line (Electric Blue/Cyan)
  const coreLine = L.polyline(routeLatLngs, {
    color: "#ffffff",
    weight: 4,
    opacity: 0.95,
    lineCap: "round",
    lineJoin: "round",
  }).addTo(state.map);

  state.routeHighlightLayers.push(glowLine, coreLine);

  // Smoothly fit map view to show entire route
  const bounds = L.latLngBounds(routeLatLngs);
  state.map.fitBounds(bounds, { padding: [50, 50], maxZoom: 14 });

  // Update marker icons to emphasize source and destination
  renderMapElements();
}

// ============================================================================
// Route Calculation & Comparison Handling
// ============================================================================

async function calculateRoute(source, destination) {
  if (source === destination) {
    showToast("Source and Destination are the same junction.", "info");
    return;
  }

  state.activeSource = source;
  state.activeDestination = destination;

  try {
    elements.btnFindRoute.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Calculating...`;
    elements.btnFindRoute.disabled = true;

    const res = await fetch("/api/route", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source, destination }),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Route calculation failed.");
    }

    const { route_result, comparison } = data;
    state.activeRouteData = route_result;

    renderRouteResults(route_result);
    renderComparison(comparison);

    if (route_result.status === "success") {
      highlightOptimalRoute(route_result.route);
      showToast(`Optimal route found: ${route_result.route.join(" → ")}`, "success");
    } else {
      clearRouteHighlight();
      showToast(route_result.message, "error");
    }
  } catch (err) {
    console.error("Routing error:", err);
    showToast(err.message, "error");
  } finally {
    elements.btnFindRoute.innerHTML = `<i class="fa-solid fa-magnifying-glass-location"></i> Find Optimal Route`;
    elements.btnFindRoute.disabled = false;
  }
}

function clearRouteHighlight() {
  state.routeHighlightLayers.forEach((layer) => state.map.removeLayer(layer));
  state.routeHighlightLayers = [];
}

function renderRouteResults(routeData) {
  if (!routeData || routeData.status !== "success") {
    elements.resultStatusBadge.className = "badge-status text-danger";
    elements.resultStatusBadge.textContent = "Unreachable";
    elements.resultPathChain.innerHTML = `<span class="text-danger"><i class="fa-solid fa-triangle-exclamation"></i> ${routeData?.message || "No feasible route found."}</span>`;
    elements.resultDistance.textContent = "-- km";
    elements.resultTime.textContent = "-- min";
    elements.resultCost.textContent = "Infinity";
    elements.resultRoadsCount.textContent = "0";
    elements.resultTrafficSummary.textContent = "Blocked";
    elements.tbodySteps.innerHTML = `<tr><td colspan="8" class="text-center text-muted">Destination unreachable with current road states.</td></tr>`;
    return;
  }

  elements.resultStatusBadge.className = "badge-status badge-success";
  elements.resultStatusBadge.textContent = "Optimal";

  // Build breadcrumb path
  const pathHtml = routeData.route
    .map((nodeId, idx) => {
      const jName = routeData.route_names[idx] || nodeId;
      const isLast = idx === routeData.route.length - 1;
      return `<strong style="color: ${idx === 0 ? '#34d399' : isLast ? '#38bdf8' : '#e2e8f0'}">${nodeId}</strong> <span style="font-size: 11px; color: #94a3b8;">(${jName})</span>${!isLast ? ' <i class="fa-solid fa-arrow-right" style="color: #64748b; font-size: 10px; margin: 0 4px;"></i> ' : ''}`;
    })
    .join("");

  elements.resultPathChain.innerHTML = pathHtml;
  elements.resultDistance.textContent = `${routeData.total_distance_km} km`;
  elements.resultTime.textContent = `${routeData.estimated_time_min} min`;
  elements.resultCost.textContent = `${routeData.total_dynamic_cost}`;
  elements.resultRoadsCount.textContent = `${routeData.number_of_roads} roads`;
  elements.resultTrafficSummary.textContent = routeData.traffic_summary;

  // Render steps table
  if (routeData.steps && routeData.steps.length > 0) {
    elements.tbodySteps.innerHTML = routeData.steps
      .map(
        (step, idx) => `
        <tr>
          <td>${idx + 1}</td>
          <td><strong>${step.road_name}</strong> (${step.road_id})</td>
          <td><code>${step.from_junction} → ${step.to_junction}</code></td>
          <td>${step.distance_km} km</td>
          <td>${step.speed_limit} km/h</td>
          <td><span style="color: ${TRAFFIC_CONFIG[step.traffic_level]?.color || '#fff'}; font-weight: 600;">${step.traffic_level}</span></td>
          <td><strong>${step.dynamic_cost}</strong></td>
          <td>${step.estimated_time_min} min</td>
        </tr>
      `
      )
      .join("");
  } else {
    elements.tbodySteps.innerHTML = `<tr><td colspan="8" class="text-center text-muted">Direct or identical endpoints.</td></tr>`;
  }
}

function renderComparison(comparison) {
  if (!comparison) return;

  if (comparison.route_changed) {
    elements.comparisonBadge.className = "badge-status text-warning";
    elements.comparisonBadge.textContent = "Route Diverged";
  } else {
    elements.comparisonBadge.className = "badge-status badge-success";
    elements.comparisonBadge.textContent = "Optimal Path Retained";
  }

  // Before Box
  if (comparison.old_route && comparison.old_route.status === "success") {
    elements.compBeforeRoute.textContent = comparison.old_route.route.join(" → ");
    elements.compBeforeDist.textContent = `${comparison.old_route.total_distance_km} km`;
    elements.compBeforeCost.textContent = `${comparison.old_route.total_dynamic_cost}`;
    elements.compBeforeTime.textContent = `${comparison.old_route.estimated_time_min} min`;
  } else {
    elements.compBeforeRoute.textContent = "N/A (Baseline)";
    elements.compBeforeDist.textContent = "--";
    elements.compBeforeCost.textContent = "--";
    elements.compBeforeTime.textContent = "--";
  }

  // After Box
  if (comparison.new_route && comparison.new_route.status === "success") {
    elements.compAfterRoute.textContent = comparison.new_route.route.join(" → ");
    elements.compAfterDist.textContent = `${comparison.new_route.total_distance_km} km`;
    elements.compAfterCost.textContent = `${comparison.new_route.total_dynamic_cost}`;
    elements.compAfterTime.textContent = `${comparison.new_route.estimated_time_min} min`;
  } else {
    elements.compAfterRoute.textContent = "Unreachable (Blocked)";
    elements.compAfterDist.textContent = "--";
    elements.compAfterCost.textContent = "Infinity";
    elements.compAfterTime.textContent = "--";
  }

  // Rationale
  elements.compReasonText.textContent = comparison.reason;
}

// ============================================================================
// Traffic Mutation & Scenario Control
// ============================================================================

async function applyTrafficUpdate() {
  const roadId = elements.selectRoad.value;
  const trafficLevel = elements.selectTrafficLevel.value;
  const isBlocked = elements.radioStatusBlocked.checked;

  try {
    elements.btnApplyTraffic.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Updating...`;
    elements.btnApplyTraffic.disabled = true;

    let res;
    if (isBlocked) {
      res = await fetch("/api/road/block", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ road_id: roadId }),
      });
    } else {
      // First ensure unblocked
      await fetch("/api/road/unblock", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ road_id: roadId }),
      });

      res = await fetch("/api/traffic/update", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ road_id: roadId, traffic_level: trafficLevel }),
      });
    }

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to update traffic.");

    // Update in local state
    state.roadMap.set(roadId, data.road);
    updateRoadPolyline(data.road);
    updateStatistics(data.statistics);

    if (data.active_route) {
      state.activeRouteData = data.active_route;
      renderRouteResults(data.active_route);
      renderComparison(data.comparison);
      if (data.active_route.status === "success") {
        highlightOptimalRoute(data.active_route.route);
      } else {
        clearRouteHighlight();
      }
    }

    showToast(`Updated road ${roadId}: Level = ${trafficLevel}, Status = ${isBlocked ? 'BLOCKED' : 'OPEN'}`, "success");
  } catch (err) {
    console.error("Traffic update error:", err);
    showToast(err.message, "error");
  } finally {
    elements.btnApplyTraffic.innerHTML = `<i class="fa-solid fa-bolt"></i> Apply Traffic Update`;
    elements.btnApplyTraffic.disabled = false;
  }
}

async function applyScenario(scenarioId) {
  try {
    const res = await fetch("/api/simulation/scenario", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario_id: scenarioId }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to apply scenario.");

    await refreshAllRoads();
    updateStatistics(data.statistics);

    if (data.active_route) {
      state.activeRouteData = data.active_route;
      renderRouteResults(data.active_route);
      renderComparison(data.comparison);
      if (data.active_route.status === "success") {
        highlightOptimalRoute(data.active_route.route);
      } else {
        clearRouteHighlight();
      }
    }

    showToast(`Activated: ${data.scenario.name}`, "info");
  } catch (err) {
    console.error("Scenario error:", err);
    showToast(err.message, "error");
  }
}

async function resetSimulation() {
  try {
    const res = await fetch("/api/simulation/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to reset simulation.");

    await refreshAllRoads();
    updateStatistics(data.statistics);

    if (data.active_route) {
      state.activeRouteData = data.active_route;
      renderRouteResults(data.active_route);
      renderComparison(data.comparison);
      if (data.active_route.status === "success") {
        highlightOptimalRoute(data.active_route.route);
      } else {
        clearRouteHighlight();
      }
    }

    // Refresh selected road in panel
    selectRoadInControl(elements.selectRoad.value);
    showToast("Simulation reset to pristine baseline conditions.", "success");
  } catch (err) {
    console.error("Reset error:", err);
    showToast(err.message, "error");
  }
}

async function refreshAllRoads() {
  const roadsRes = await fetch("/api/roads");
  if (roadsRes.ok) {
    state.roads = await roadsRes.json();
    state.roadMap.clear();
    state.roads.forEach((r) => {
      state.roadMap.set(r.road_id, r);
      updateRoadPolyline(r);
    });
  }
}

function updateStatistics(stats) {
  if (!stats) return;

  elements.statJunctions.textContent = stats.total_junctions;
  elements.statRoads.textContent = stats.total_roads;
  elements.statCongested.textContent = stats.high_traffic_roads + stats.severe_traffic_roads;
  elements.statBlocked.textContent = stats.blocked_roads;
  elements.statFactor.textContent = `${stats.average_traffic_multiplier}x`;

  // Update Chart
  if (state.trafficChart) {
    state.trafficChart.data.datasets[0].data = [
      stats.low_traffic_roads,
      stats.medium_traffic_roads,
      stats.high_traffic_roads,
      stats.severe_traffic_roads,
      stats.blocked_roads,
    ];
    state.trafficChart.update();
  }
}

// ============================================================================
// Routing Table Modal Logic
// ============================================================================

async function loadRoutingTable(source) {
  try {
    elements.tbodyRoutingTable.innerHTML = `<tr><td colspan="6" class="text-center text-muted"><i class="fa-solid fa-spinner fa-spin"></i> Calculating routing table...</td></tr>`;

    const res = await fetch(`/api/routing-table/${source}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to load routing table.");

    if (!data.entries || data.entries.length === 0) {
      elements.tbodyRoutingTable.innerHTML = `<tr><td colspan="6" class="text-center text-muted">No routing entries found.</td></tr>`;
      return;
    }

    elements.tbodyRoutingTable.innerHTML = data.entries
      .map(
        (entry) => `
        <tr>
          <td><strong>${entry.destination}</strong></td>
          <td>${entry.destination_name}</td>
          <td><code style="background: rgba(6, 182, 212, 0.15); color: #38bdf8; padding: 2px 6px; border-radius: 4px;">${entry.next_hop} (${entry.next_hop_name})</code></td>
          <td>${entry.hops} hop(s)</td>
          <td><strong style="color: #38bdf8;">${entry.dynamic_cost}</strong></td>
          <td>${entry.total_distance_km} km</td>
        </tr>
      `
      )
      .join("");
  } catch (err) {
    console.error("Routing table error:", err);
    elements.tbodyRoutingTable.innerHTML = `<tr><td colspan="6" class="text-center text-danger">${err.message}</td></tr>`;
  }
}

// ============================================================================
// Event Listeners
// ============================================================================

function setupEventListeners() {
  // Find Route
  elements.btnFindRoute.addEventListener("click", () => {
    const src = elements.selectSource.value;
    const dst = elements.selectDestination.value;
    calculateRoute(src, dst);
  });

  // Swap Endpoints
  elements.btnSwapEndpoints.addEventListener("click", () => {
    const tmp = elements.selectSource.value;
    elements.selectSource.value = elements.selectDestination.value;
    elements.selectDestination.value = tmp;
    calculateRoute(elements.selectSource.value, elements.selectDestination.value);
  });

  // Road select changed in control panel
  elements.selectRoad.addEventListener("change", (e) => {
    selectRoadInControl(e.target.value);
  });

  // Apply traffic
  elements.btnApplyTraffic.addEventListener("click", applyTrafficUpdate);

  // Scenarios
  elements.btnScenario1.addEventListener("click", () => applyScenario(1));
  elements.btnScenario2.addEventListener("click", () => applyScenario(2));
  elements.btnScenario3.addEventListener("click", () => applyScenario(3));
  elements.btnResetSimulation.addEventListener("click", resetSimulation);

  // Modals
  elements.btnOpenConcepts.addEventListener("click", () => openModal("modal-concepts"));
  elements.btnOpenAlgorithm.addEventListener("click", () => openModal("modal-algorithm"));
  elements.btnOpenRoutingTable.addEventListener("click", () => {
    openModal("modal-routing-table");
    loadRoutingTable(elements.selectRtSource.value || "J1");
  });

  document.querySelectorAll(".modal-close").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const modalId = e.target.getAttribute("data-close");
      if (modalId) closeModal(modalId);
    });
  });

  document.querySelectorAll(".modal-overlay").forEach((modal) => {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) closeModal(modal.id);
    });
  });

  // Routing Table source change
  elements.selectRtSource.addEventListener("change", (e) => {
    loadRoutingTable(e.target.value);
  });

  elements.btnRefreshRt.addEventListener("click", () => {
    loadRoutingTable(elements.selectRtSource.value);
  });

  // Escape to close modals
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      document.querySelectorAll(".modal-overlay.active").forEach((m) => closeModal(m.id));
    }
  });
}

function openModal(modalId) {
  const m = document.getElementById(modalId);
  if (m) m.classList.add("active");
}

function closeModal(modalId) {
  const m = document.getElementById(modalId);
  if (m) m.classList.remove("active");
}

function showToast(message, type = "info") {
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;

  const iconClass =
    type === "success"
      ? "fa-circle-check text-emerald"
      : type === "error"
      ? "fa-circle-exclamation text-danger"
      : "fa-circle-info text-cyan";

  toast.innerHTML = `<i class="fa-solid ${iconClass}"></i> <span>${message}</span>`;
  elements.toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(30px)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}
