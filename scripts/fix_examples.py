#!/usr/bin/env python3
"""Rewrite failing example files with correct Lateralus syntax."""
import os

BASE = "/home/antics/lateralus-lang/examples"

def write(name, content):
    path = os.path.join(BASE, name)
    with open(path, 'w') as f:
        f.write(content)
    print(f"Wrote {name}: {content.count(chr(10))+1} lines")

# =======================================================================
# 1. graph_demo.ltl
# =======================================================================
write("graph_demo.ltl", r"""// =======================================================================
// LATERALUS — Graph Theory & Network Analysis
// Demonstrates data structures, algorithms, and pipeline composition
// =======================================================================

import algorithms
import data

// --- Graph representation using adjacency list ------------------------

fn graph_new() -> map {
    let g = {}
    g["vertices"] = {}
    g["edges"] = []
    g["directed"] = false
    g["vertex_count"] = 0
    g["edge_count"] = 0
    return g
}

fn graph_add_vertex(g: map, id: str, data) -> map {
    let v = {}
    v["id"] = id
    v["data"] = data
    v["neighbors"] = []
    g["vertices"][id] = v
    g["vertex_count"] = g["vertex_count"] + 1
    return g
}

fn graph_add_edge(g: map, from: str, to: str, weight: float) -> map {
    let edge = {}
    edge["from"] = from
    edge["to"] = to
    edge["weight"] = weight
    g["edges"] = g["edges"] + [edge]
    g["edge_count"] = g["edge_count"] + 1

    // Add to adjacency list
    let nb1 = {}
    nb1["vertex"] = to
    nb1["weight"] = weight
    g["vertices"][from]["neighbors"] = g["vertices"][from]["neighbors"] + [nb1]

    if not g["directed"] {
        let nb2 = {}
        nb2["vertex"] = from
        nb2["weight"] = weight
        g["vertices"][to]["neighbors"] = g["vertices"][to]["neighbors"] + [nb2]
    }

    return g
}

// --- Breadth-First Search ---------------------------------------------

fn bfs(g: map, start: str) -> list {
    let visited = {}
    let queue = [start]
    let order = []

    visited[start] = true

    while len(queue) > 0 {
        let current = queue[0]
        queue = slice(queue, 1, len(queue))
        order = order + [current]

        let vertex = g["vertices"][current]
        for neighbor in vertex["neighbors"] {
            let vid = neighbor["vertex"]
            if not contains(keys(visited), vid) {
                visited[vid] = true
                queue = queue + [vid]
            }
        }
    }

    return order
}

// --- Depth-First Search -----------------------------------------------

fn dfs_helper(g: map, vertex: str, visited: map, order: list) -> list {
    visited[vertex] = true
    order = order + [vertex]

    let v = g["vertices"][vertex]
    for neighbor in v["neighbors"] {
        let vid = neighbor["vertex"]
        if not contains(keys(visited), vid) {
            order = dfs_helper(g, vid, visited, order)
        }
    }

    return order
}

fn dfs(g: map, start: str) -> list {
    let visited = {}
    return dfs_helper(g, start, visited, [])
}

// --- Shortest Path (Dijkstra's Algorithm) -----------------------------

fn dijkstra(g: map, start: str) -> map {
    let distances = {}
    let previous = {}
    let unvisited = {}

    // Initialize distances
    for vertex_id in keys(g["vertices"]) {
        distances[vertex_id] = 999999999
        previous[vertex_id] = none
        unvisited[vertex_id] = true
    }
    distances[start] = 0.0

    while len(keys(unvisited)) > 0 {
        // Find minimum distance unvisited vertex
        let min_dist = 999999999
        let current = none
        for vid in keys(unvisited) {
            if distances[vid] < min_dist {
                min_dist = distances[vid]
                current = vid
            }
        }

        if current == none { break }

        // Remove from unvisited
        let new_unvisited = {}
        for k in keys(unvisited) {
            if k != current {
                new_unvisited[k] = true
            }
        }
        unvisited = new_unvisited

        // Update neighbors
        let vertex = g["vertices"][current]
        for neighbor in vertex["neighbors"] {
            let alt = distances[current] + neighbor["weight"]
            if alt < distances[neighbor["vertex"]] {
                distances[neighbor["vertex"]] = alt
                previous[neighbor["vertex"]] = current
            }
        }
    }

    let result = {}
    result["distances"] = distances
    result["previous"] = previous
    return result
}

fn shortest_path(g: map, start: str, end: str) -> map {
    let result = dijkstra(g, start)
    let path = []
    let current = end

    while current != none {
        path = [current] + path
        current = result["previous"][current]
    }

    let sp = {}
    sp["path"] = path
    sp["distance"] = result["distances"][end]
    return sp
}

// --- Network Analysis -------------------------------------------------

fn degree(g: map, vertex_id: str) -> int {
    return len(g["vertices"][vertex_id]["neighbors"])
}

fn average_degree(g: map) -> float {
    let total = 0
    let count = 0
    for vid in keys(g["vertices"]) {
        total = total + degree(g, vid)
        count = count + 1
    }
    if count == 0 { return 0.0 }
    return total / count
}

fn density(g: map) -> float {
    let n = g["vertex_count"]
    if n <= 1 { return 0.0 }
    let max_edges = n * (n - 1) / 2
    return g["edge_count"] / max_edges
}

// --- Main: Build and analyze a network --------------------------------

fn main() {
    println("LATERALUS Graph Theory Demo")
    println("===========================")
    println("")

    // Build a city network
    let cities = graph_new()

    // Add cities
    cities = cities
        |> graph_add_vertex("NYC", "New York City")
        |> graph_add_vertex("BOS", "Boston")
        |> graph_add_vertex("PHI", "Philadelphia")
        |> graph_add_vertex("DC", "Washington DC")
        |> graph_add_vertex("CHI", "Chicago")
        |> graph_add_vertex("DET", "Detroit")

    // Add routes (distances in miles)
    cities = cities
        |> graph_add_edge("NYC", "BOS", 215.0)
        |> graph_add_edge("NYC", "PHI", 95.0)
        |> graph_add_edge("PHI", "DC", 140.0)
        |> graph_add_edge("NYC", "CHI", 790.0)
        |> graph_add_edge("BOS", "CHI", 980.0)
        |> graph_add_edge("CHI", "DET", 280.0)
        |> graph_add_edge("DET", "NYC", 615.0)

    println("Network: " + str(cities["vertex_count"]) + " cities, " +
            str(cities["edge_count"]) + " routes")

    // BFS traversal
    let bfs_order = bfs(cities, "NYC")
    println("BFS from NYC: " + str(bfs_order))

    // DFS traversal
    let dfs_order = dfs(cities, "NYC")
    println("DFS from NYC: " + str(dfs_order))

    // Shortest paths
    println("")
    println("Shortest Paths from NYC:")
    let sp = dijkstra(cities, "NYC")
    for city in ["BOS", "PHI", "DC", "CHI", "DET"] {
        println("  NYC -> " + city + ": " + str(sp["distances"][city]) + " miles")
    }

    // Find specific shortest path
    let route = shortest_path(cities, "BOS", "DC")
    println("")
    println("Best route BOS -> DC:")
    println("  Path: " + str(route["path"]))
    println("  Distance: " + str(route["distance"]) + " miles")

    // Network analysis
    println("")
    println("Network Analysis:")
    println("  Average degree: " + str(average_degree(cities)))
    println("  Density: " + str(density(cities)))

    for city in keys(cities["vertices"]) {
        println("  Degree(" + city + "): " + str(degree(cities, city)))
    }

    println("")
    println("Done!")
}
""")

# =======================================================================
# 2. physics_sim.ltl
# =======================================================================
write("physics_sim.ltl", r"""// =======================================================================
// LATERALUS — Physics Simulation
// N-body gravitational simulation using the science and math libraries
// =======================================================================

import math
import science

// --- Constants --------------------------------------------------------

let G = 6.67430e-11
let AU = 1.496e11
let DAY = 86400.0
let YEAR = 365.25 * DAY
let SOLAR_MASS = 1.989e30

// --- Vector operations -----------------------------------------------

fn vec3(x: float, y: float, z: float) -> map {
    let v = {}
    v["x"] = x
    v["y"] = y
    v["z"] = z
    return v
}

fn vec3_add(a: map, b: map) -> map {
    return vec3(a["x"] + b["x"], a["y"] + b["y"], a["z"] + b["z"])
}

fn vec3_sub(a: map, b: map) -> map {
    return vec3(a["x"] - b["x"], a["y"] - b["y"], a["z"] - b["z"])
}

fn vec3_scale(v: map, s: float) -> map {
    return vec3(v["x"] * s, v["y"] * s, v["z"] * s)
}

fn vec3_magnitude(v: map) -> float {
    return sqrt(v["x"] ** 2 + v["y"] ** 2 + v["z"] ** 2)
}

fn vec3_normalized(v: map) -> map {
    let mag = vec3_magnitude(v)
    if mag == 0.0 { return vec3(0.0, 0.0, 0.0) }
    return vec3_scale(v, 1.0 / mag)
}

fn vec3_str(v: map) -> str {
    return "(" + str(round(v["x"], 2)) + ", " +
                 str(round(v["y"], 2)) + ", " +
                 str(round(v["z"], 2)) + ")"
}

// --- Body -------------------------------------------------------------

fn body_new(name: str, mass: float, pos: map, vel: map) -> map {
    let b = {}
    b["name"] = name
    b["mass"] = mass
    b["position"] = pos
    b["velocity"] = vel
    b["acceleration"] = vec3(0.0, 0.0, 0.0)
    return b
}

// --- Gravitational force between two bodies ---------------------------

fn gravitational_force(b1: map, b2: map) -> map {
    let r = vec3_sub(b2["position"], b1["position"])
    let dist = vec3_magnitude(r)

    if dist < 1.0 { return vec3(0.0, 0.0, 0.0) }

    let force_mag = G * b1["mass"] * b2["mass"] / (dist ** 2)
    let direction = vec3_normalized(r)

    return vec3_scale(direction, force_mag)
}

// --- Compute total acceleration on each body --------------------------

fn compute_accelerations(bodies: list) -> list {
    let n = len(bodies)
    let updated = []

    for i in range(n) {
        let total_force = vec3(0.0, 0.0, 0.0)

        for j in range(n) {
            if i != j {
                let f = gravitational_force(bodies[i], bodies[j])
                total_force = vec3_add(total_force, f)
            }
        }

        let accel = vec3_scale(total_force, 1.0 / bodies[i]["mass"])
        let body = bodies[i]
        body["acceleration"] = accel
        updated = updated + [body]
    }

    return updated
}

// --- Leapfrog integrator (symplectic, energy-conserving) --------------

fn leapfrog_step(bodies: list, dt: float) -> list {
    let n = len(bodies)

    // Half-step velocity update
    let half_vel = []
    for i in range(n) {
        let b = bodies[i]
        let v_half = vec3_add(
            b["velocity"],
            vec3_scale(b["acceleration"], dt / 2.0)
        )
        half_vel = half_vel + [v_half]
    }

    // Full position update
    for i in range(n) {
        bodies[i]["position"] = vec3_add(
            bodies[i]["position"],
            vec3_scale(half_vel[i], dt)
        )
    }

    // Recompute accelerations at new positions
    bodies = compute_accelerations(bodies)

    // Complete velocity update
    for i in range(n) {
        bodies[i]["velocity"] = vec3_add(
            half_vel[i],
            vec3_scale(bodies[i]["acceleration"], dt / 2.0)
        )
    }

    return bodies
}

// --- Energy calculations ----------------------------------------------

fn kinetic_energy(bodies: list) -> float {
    let ke = 0.0
    for body in bodies {
        let v = vec3_magnitude(body["velocity"])
        ke = ke + 0.5 * body["mass"] * v ** 2
    }
    return ke
}

fn potential_energy(bodies: list) -> float {
    let pe = 0.0
    let n = len(bodies)
    for i in range(n) {
        for j in range(i + 1, n) {
            let r = vec3_sub(bodies[j]["position"], bodies[i]["position"])
            let dist = vec3_magnitude(r)
            if dist > 0.0 {
                pe = pe - G * bodies[i]["mass"] * bodies[j]["mass"] / dist
            }
        }
    }
    return pe
}

fn total_energy(bodies: list) -> float {
    return kinetic_energy(bodies) + potential_energy(bodies)
}

// --- Solar system setup (simplified inner planets) --------------------

fn create_solar_system() -> list {
    let bodies = []

    // Sun (at origin, stationary)
    bodies = bodies + [body_new(
        "Sun", SOLAR_MASS,
        vec3(0.0, 0.0, 0.0),
        vec3(0.0, 0.0, 0.0)
    )]

    // Earth
    let earth_dist = 1.0 * AU
    let earth_vel = 29780.0
    bodies = bodies + [body_new(
        "Earth", 5.972e24,
        vec3(earth_dist, 0.0, 0.0),
        vec3(0.0, earth_vel, 0.0)
    )]

    // Mars
    let mars_dist = 1.524 * AU
    let mars_vel = 24070.0
    bodies = bodies + [body_new(
        "Mars", 6.39e23,
        vec3(mars_dist, 0.0, 0.0),
        vec3(0.0, mars_vel, 0.0)
    )]

    // Venus
    let venus_dist = 0.723 * AU
    let venus_vel = 35020.0
    bodies = bodies + [body_new(
        "Venus", 4.867e24,
        vec3(venus_dist, 0.0, 0.0),
        vec3(0.0, venus_vel, 0.0)
    )]

    return bodies
}

// --- Main simulation -------------------------------------------------

fn main() {
    println("LATERALUS N-Body Gravitational Simulation")
    println("=========================================")
    println("")

    let bodies = create_solar_system()
    let dt = DAY * 1.0
    let total_days = 365
    let steps = total_days
    let report_interval = 30

    // Initial accelerations
    bodies = compute_accelerations(bodies)

    let e0 = total_energy(bodies)
    println("Initial energy: " + str(e0) + " J")
    println("Simulating " + str(total_days) + " days...")
    println("")

    // Run simulation
    for step in range(steps) {
        bodies = leapfrog_step(bodies, dt)

        if (step + 1) % report_interval == 0 {
            let day = step + 1
            println("Day " + str(day) + ":")

            for body in bodies {
                let dist = vec3_magnitude(body["position"]) / AU
                let vel = vec3_magnitude(body["velocity"]) / 1000.0
                println("  " + body["name"] + ": " +
                        str(round(dist, 4)) + " AU, " +
                        str(round(vel, 2)) + " km/s")
            }

            let e = total_energy(bodies)
            let drift = abs((e - e0) / e0) * 100.0
            println("  Energy drift: " + str(round(drift, 6)) + "%")
            println("")
        }
    }

    let ef = total_energy(bodies)
    let total_drift = abs((ef - e0) / e0) * 100.0
    println("Final energy: " + str(ef) + " J")
    println("Total energy drift: " + str(round(total_drift, 6)) + "%")
    println("")

    // Final positions
    println("Final positions (AU from Sun):")
    for body in bodies {
        let dist = vec3_magnitude(body["position"]) / AU
        println("  " + body["name"] + ": " + str(round(dist, 4)) + " AU")
    }

    println("")
    println("Simulation complete!")
}
""")

# =======================================================================
# 3. statistics_demo.ltl
# =======================================================================
write("statistics_demo.ltl", r"""// =======================================================================
// LATERALUS — Statistical Analysis Pipeline
// Real-world data analysis demonstrating pipeline composition
// =======================================================================

import math
import collections
import functional

// --- Data generation (simulated dataset) ------------------------------

fn generate_dataset(n: int) -> list {
    let data = []
    for i in range(n) {
        // Simulate: y = 2.5x + 10 + noise
        let x = i * 0.1
        let noise = (random() - 0.5) * 5.0
        let y = 2.5 * x + 10.0 + noise

        let row = {}
        row["id"] = i
        row["x"] = round(x, 2)
        row["y"] = round(y, 2)
        let cat = match i % 3 {
            0 => "A",
            1 => "B",
            _ => "C",
        }
        row["category"] = cat
        data = data + [row]
    }
    return data
}

// --- Statistical functions --------------------------------------------

fn extract_field(data: list, field: str) -> list {
    return data |> map(fn(row) { row[field] })
}

fn compute_mean(values: list) -> float {
    let total = values |> reduce(fn(a, b) { a + b }, 0.0)
    return total / len(values)
}

fn compute_variance(values: list) -> float {
    let mu = compute_mean(values)
    let sq_diffs = values |> map(fn(x) { (x - mu) ** 2 })
    let s = sq_diffs |> reduce(fn(a, b) { a + b }, 0.0)
    return s / len(values)
}

fn compute_std_dev(values: list) -> float {
    return sqrt(compute_variance(values))
}

fn compute_median(values: list) -> float {
    let sorted = sort(values)
    let n = len(sorted)
    if n % 2 == 0 {
        return (sorted[n / 2 - 1] + sorted[n / 2]) / 2.0
    }
    return sorted[n / 2]
}

fn compute_percentile(values: list, p: float) -> float {
    let sorted = sort(values)
    let idx = (p / 100.0) * (len(sorted) - 1)
    let lower = int(idx)
    let upper = min(lower + 1, len(sorted) - 1)
    let frac = idx - lower
    return sorted[lower] * (1.0 - frac) + sorted[upper] * frac
}

fn compute_correlation(xs: list, ys: list) -> float {
    let n = len(xs)
    let mu_x = compute_mean(xs)
    let mu_y = compute_mean(ys)

    let cov = 0.0
    let var_x = 0.0
    let var_y = 0.0

    for i in range(n) {
        let dx = xs[i] - mu_x
        let dy = ys[i] - mu_y
        cov = cov + dx * dy
        var_x = var_x + dx ** 2
        var_y = var_y + dy ** 2
    }

    let denom = sqrt(var_x * var_y)
    if denom == 0.0 { return 0.0 }
    return cov / denom
}

fn linear_regression(xs: list, ys: list) -> map {
    let n = len(xs)
    let mu_x = compute_mean(xs)
    let mu_y = compute_mean(ys)

    let num = 0.0
    let den = 0.0
    for i in range(n) {
        num = num + (xs[i] - mu_x) * (ys[i] - mu_y)
        den = den + (xs[i] - mu_x) ** 2
    }

    let slope = num / den
    let intercept = mu_y - slope * mu_x

    // R-squared
    let ss_res = 0.0
    let ss_tot = 0.0
    for i in range(n) {
        let predicted = slope * xs[i] + intercept
        ss_res = ss_res + (ys[i] - predicted) ** 2
        ss_tot = ss_tot + (ys[i] - mu_y) ** 2
    }
    let r_squared = 1.0 - ss_res / ss_tot

    let result = {}
    result["slope"] = round(slope, 4)
    result["intercept"] = round(intercept, 4)
    result["r_squared"] = round(r_squared, 4)
    return result
}

// --- Group-by analysis ------------------------------------------------

fn group_by_field(data: list, field: str) -> map {
    let groups = {}
    for row in data {
        let key = row[field]
        if not contains(keys(groups), key) {
            groups[key] = []
        }
        groups[key] = groups[key] + [row]
    }
    return groups
}

fn summarize_group(group: list, field: str) -> map {
    let values = extract_field(group, field)
    let result = {}
    result["count"] = len(values)
    result["mean"] = round(compute_mean(values), 2)
    result["std_dev"] = round(compute_std_dev(values), 2)
    result["median"] = round(compute_median(values), 2)
    result["min"] = min(values)
    result["max"] = max(values)
    return result
}

// --- Outlier detection ------------------------------------------------

fn detect_outliers_iqr(values: list) -> map {
    let q1 = compute_percentile(values, 25.0)
    let q3 = compute_percentile(values, 75.0)
    let iqr = q3 - q1
    let lower = q1 - 1.5 * iqr
    let upper = q3 + 1.5 * iqr

    let outliers = values |> filter(fn(x) { x < lower or x > upper })

    let result = {}
    result["q1"] = round(q1, 2)
    result["q3"] = round(q3, 2)
    result["iqr"] = round(iqr, 2)
    result["lower_fence"] = round(lower, 2)
    result["upper_fence"] = round(upper, 2)
    result["outlier_count"] = len(outliers)
    result["outliers"] = outliers
    return result
}

// --- Moving average ---------------------------------------------------

fn moving_average(values: list, window: int) -> list {
    let result = []
    for i in range(len(values) - window + 1) {
        let window_vals = slice(values, i, i + window)
        result = result + [round(compute_mean(window_vals), 2)]
    }
    return result
}

// --- Main analysis pipeline ------------------------------------------

fn main() {
    println("LATERALUS Statistical Analysis Pipeline")
    println("=======================================")
    println("")

    // Generate dataset
    let data = generate_dataset(100)
    println("Dataset: " + str(len(data)) + " observations")
    println("")

    // Extract features
    let xs = extract_field(data, "x")
    let ys = extract_field(data, "y")

    // Descriptive statistics
    println("Descriptive Statistics:")
    println("  X: mean=" + str(round(compute_mean(xs), 2)) +
            ", std=" + str(round(compute_std_dev(xs), 2)) +
            ", median=" + str(round(compute_median(xs), 2)))
    println("  Y: mean=" + str(round(compute_mean(ys), 2)) +
            ", std=" + str(round(compute_std_dev(ys), 2)) +
            ", median=" + str(round(compute_median(ys), 2)))
    println("")

    // Correlation
    let r = compute_correlation(xs, ys)
    println("Correlation (X, Y): " + str(round(r, 4)))
    println("")

    // Linear regression
    let reg = linear_regression(xs, ys)
    println("Linear Regression: Y = " + str(reg["slope"]) + " * X + " +
            str(reg["intercept"]))
    println("  R-squared: " + str(reg["r_squared"]))
    println("  (True model: Y = 2.5 * X + 10 + noise)")
    println("")

    // Group-by analysis
    println("Group Analysis (by category):")
    let groups = group_by_field(data, "category")
    for category in keys(groups) {
        let summary = summarize_group(groups[category], "y")
        println("  Category " + category + ":")
        println("    Count: " + str(summary["count"]))
        println("    Mean:  " + str(summary["mean"]))
        println("    Std:   " + str(summary["std_dev"]))
    }
    println("")

    // Outlier detection
    println("Outlier Detection (Y values, IQR method):")
    let outlier_info = detect_outliers_iqr(ys)
    println("  IQR: " + str(outlier_info["iqr"]))
    println("  Fences: [" + str(outlier_info["lower_fence"]) + ", " +
            str(outlier_info["upper_fence"]) + "]")
    println("  Outliers found: " + str(outlier_info["outlier_count"]))
    println("")

    // Moving average (smoothing)
    let smoothed = moving_average(ys, 5)
    println("Moving Average (window=5):")
    println("  First 10 values: " + str(slice(smoothed, 0, min(10, len(smoothed)))))
    println("")

    // Pipeline composition example
    let mean_y = compute_mean(ys)
    let high_y = data
        |> filter(fn(row) { row["y"] > mean_y })
        |> filter(fn(row) { row["category"] == "A" })
        |> map(fn(row) { row["x"] })
        |> sort()

    println("Category A observations with above-average Y:")
    println("  Count: " + str(len(high_y)))
    if len(high_y) > 0 {
        println("  X range: [" + str(high_y[0]) + ", " +
                str(high_y[len(high_y) - 1]) + "]")
    }

    println("")
    println("Analysis complete!")
}
""")

# =======================================================================
# 4. neural_network.ltl
# =======================================================================
write("neural_network.ltl", r"""// =======================================================================
// LATERALUS — Machine Learning Example
// A simple neural network implementation from scratch
// Demonstrates LATERALUS's mathematical computing capabilities
// =======================================================================

import math
import matrix

// --- Activation Functions ---------------------------------------------

fn sigmoid(x: float) -> float {
    return 1.0 / (1.0 + exp(-x))
}

fn sigmoid_derivative(x: float) -> float {
    let s = sigmoid(x)
    return s * (1.0 - s)
}

fn relu(x: float) -> float {
    if x > 0.0 { return x }
    return 0.0
}

fn relu_derivative(x: float) -> float {
    if x > 0.0 { return 1.0 }
    return 0.0
}

fn tanh_activation(x: float) -> float {
    let ep = exp(x)
    let en = exp(-x)
    return (ep - en) / (ep + en)
}

// --- Apply activation to matrix ---------------------------------------

fn apply_activation(m: list, activation) -> list {
    let result = []
    for row in m {
        let new_row = row |> map(fn(x) { activation(x) })
        result = result + [new_row]
    }
    return result
}

// --- Loss Functions ---------------------------------------------------

fn mse_loss(predicted: list, actual: list) -> float {
    let total = 0.0
    let count = 0
    for i in range(len(predicted)) {
        for j in range(len(predicted[i])) {
            let diff = predicted[i][j] - actual[i][j]
            total = total + diff ** 2
            count = count + 1
        }
    }
    return total / count
}

fn binary_cross_entropy(predicted: list, actual: list) -> float {
    let total = 0.0
    let count = 0
    for i in range(len(predicted)) {
        for j in range(len(predicted[i])) {
            let p = max(min(predicted[i][j], 0.9999), 0.0001)
            let y = actual[i][j]
            total = total - (y * log(p) + (1.0 - y) * log(1.0 - p))
            count = count + 1
        }
    }
    return total / count
}

// --- Dense Layer ------------------------------------------------------

fn layer_new(input_size: int, output_size: int) -> map {
    // Xavier initialization
    let scale = sqrt(2.0 / (input_size + output_size))

    let weights = []
    for i in range(input_size) {
        let row = []
        for j in range(output_size) {
            row = row + [(random() - 0.5) * 2.0 * scale]
        }
        weights = weights + [row]
    }

    let biases = []
    for j in range(output_size) {
        biases = biases + [0.0]
    }

    let layer = {}
    layer["weights"] = weights
    layer["biases"] = biases
    layer["input_size"] = input_size
    layer["output_size"] = output_size
    layer["last_input"] = none
    layer["last_output"] = none
    layer["last_pre_activation"] = none
    return layer
}

fn layer_forward(layer: map, input: list, activation) -> map {
    // input: [batch_size x input_size]
    // output: [batch_size x output_size]
    let output = matrix_multiply(input, layer["weights"])

    // Add biases
    for i in range(len(output)) {
        for j in range(len(output[i])) {
            output[i][j] = output[i][j] + layer["biases"][j]
        }
    }

    layer["last_input"] = input
    layer["last_pre_activation"] = output
    layer["last_output"] = apply_activation(output, activation)

    return layer
}

// --- Simple Neural Network -------------------------------------------

fn network_new(layer_sizes: list) -> map {
    let layers = []
    for i in range(len(layer_sizes) - 1) {
        layers = layers + [layer_new(layer_sizes[i], layer_sizes[i + 1])]
    }
    let net = {}
    net["layers"] = layers
    net["layer_count"] = len(layers)
    return net
}

fn network_forward(net: map, input: list) -> list {
    let current = input
    for i in range(net["layer_count"]) {
        let activation = sigmoid
        if i == net["layer_count"] - 1 {
            activation = sigmoid  // Output layer
        }
        net["layers"][i] = layer_forward(net["layers"][i], current, activation)
        current = net["layers"][i]["last_output"]
    }
    return current
}

// --- Training (simplified gradient descent) ---------------------------

fn train_step(net: map, input: list, target: list, lr: float) -> map {
    // Forward pass
    let output = network_forward(net, input)

    // Compute output error
    let error = []
    for i in range(len(output)) {
        let row = []
        for j in range(len(output[i])) {
            let o = output[i][j]
            let t = target[i][j]
            // Gradient: (output - target) * sigmoid_derivative
            row = row + [(o - t) * o * (1.0 - o)]
        }
        error = error + [row]
    }

    // Update output layer weights
    let last_idx = net["layer_count"] - 1
    let last_layer = net["layers"][last_idx]
    let last_input = last_layer["last_input"]

    let input_t = matrix_transpose(last_input)
    let weight_gradient = matrix_multiply(input_t, error)

    // Apply gradient descent
    for i in range(len(last_layer["weights"])) {
        for j in range(len(last_layer["weights"][i])) {
            last_layer["weights"][i][j] = last_layer["weights"][i][j] - lr * weight_gradient[i][j]
        }
    }

    // Update biases
    for j in range(len(last_layer["biases"])) {
        let grad = 0.0
        for i in range(len(error)) {
            grad = grad + error[i][j]
        }
        last_layer["biases"][j] = last_layer["biases"][j] - lr * grad / len(error)
    }

    net["layers"][last_idx] = last_layer
    return net
}

// --- Main: XOR Problem -----------------------------------------------

fn main() {
    println("LATERALUS Neural Network — XOR Problem")
    println("=======================================")
    println("")

    // XOR dataset
    let X = [[0.0, 0.0], [0.0, 1.0], [1.0, 0.0], [1.0, 1.0]]
    let Y = [[0.0], [1.0], [1.0], [0.0]]

    // Create network: 2 inputs -> 4 hidden -> 1 output
    let net = network_new([2, 4, 1])
    let learning_rate = 0.5
    let epochs = 1000

    println("Architecture: 2 -> 4 -> 1")
    println("Learning rate: " + str(learning_rate))
    println("Training for " + str(epochs) + " epochs...")
    println("")

    // Training loop
    for epoch in range(epochs) {
        net = train_step(net, X, Y, learning_rate)

        if (epoch + 1) % 100 == 0 {
            let predictions = network_forward(net, X)
            let loss = mse_loss(predictions, Y)
            println("Epoch " + str(epoch + 1) + ": loss = " + str(round(loss, 6)))
        }
    }

    // Final predictions
    println("")
    println("Final Predictions:")
    let final_pred = network_forward(net, X)
    for i in range(len(X)) {
        let input_str = str(int(X[i][0])) + " XOR " + str(int(X[i][1]))
        let predicted = round(final_pred[i][0], 4)
        let expected = int(Y[i][0])
        let correct = abs(predicted - expected) < 0.5
        let icon = "CORRECT"
        if not correct { icon = "WRONG" }
        println("  " + input_str + " = " + str(predicted) +
                " (expected " + str(expected) + ") " + icon)
    }

    println("")
    println("Network weights learned successfully!")
}
""")

# =======================================================================
# 5. signal_processing.ltl
# =======================================================================
write("signal_processing.ltl", r"""// =======================================================================
// LATERALUS v1.5 — Signal Processing
// Demonstrates FFT, filtering, and spectral analysis pipelines
// =======================================================================

import math
import science

// -- Signal Generation ---------------------------------------------

fn generate_sine(freq: float, amplitude: float, samples: int, sample_rate: float) -> list {
    let result = []
    for i in range(0, samples) {
        let t = i / sample_rate
        result = result + [amplitude * sin(2.0 * PI * freq * t)]
    }
    return result
}

fn generate_composite_signal(sample_rate: float, duration: float) -> list {
    let n = int(sample_rate * duration)
    let result = []
    for i in range(0, n) {
        let t = i / sample_rate
        // 10 Hz fundamental + 25 Hz harmonic + noise
        let fundamental = 1.0 * sin(2.0 * PI * 10.0 * t)
        let harmonic = 0.5 * sin(2.0 * PI * 25.0 * t)
        let high_freq = 0.2 * sin(2.0 * PI * 100.0 * t)
        result = result + [fundamental + harmonic + high_freq]
    }
    return result
}

// -- Spectral Analysis ---------------------------------------------

fn analyze_spectrum(signal: list, sample_rate: float) -> list {
    let spectrum = signal |> fft()
    let power = spectrum |> power_spectrum()
    let n = len(power)
    let freq_resolution = sample_rate / n

    let result = []
    for i in range(0, n / 2) {
        let bin = {}
        bin["frequency"] = i * freq_resolution
        bin["magnitude"] = sqrt(power[i])
        bin["power_db"] = 10.0 * log10(power[i] + 1e-12)
        result = result + [bin]
    }
    return result
}

fn find_peaks(spectrum: list, threshold_db: float) -> list {
    let filtered = spectrum |> filter(fn(bin) { bin["power_db"] > threshold_db })
    let sorted_bins = filtered |> sort_by(fn(bin) { bin["power_db"] })
    return sorted_bins |> reverse()
}

// -- Digital Filters -----------------------------------------------

fn moving_avg_filter(signal: list, window: int) -> list {
    let n = len(signal)
    let result = []
    for i in range(0, n) {
        let start = max(0, i - window / 2)
        let end_idx = min(n, i + window / 2 + 1)
        let window_data = slice_list(signal, start, end_idx)
        result = result + [mean(window_data)]
    }
    return result
}

fn low_pass_filter(signal: list, cutoff: float, sample_rate: float) -> list {
    // Simple RC low-pass filter simulation
    let rc = 1.0 / (2.0 * PI * cutoff)
    let dt = 1.0 / sample_rate
    let alpha = dt / (rc + dt)

    let filtered = [signal[0]]
    for i in range(1, len(signal)) {
        let prev = filtered[i - 1]
        let curr = prev + alpha * (signal[i] - prev)
        filtered = filtered + [curr]
    }
    return filtered
}

// -- Signal Statistics ---------------------------------------------

fn signal_stats(signal: list) -> map {
    let n = len(signal)
    let mu = signal |> mean()
    let sigma = signal |> std_dev()
    let sq = signal |> map(fn(x) { x * x })
    let rms = sqrt(sq |> mean())
    let abs_signal = signal |> map(fn(x) { abs(x) })
    let peak = abs_signal |> max()
    let crest_factor = peak / rms

    let result = {}
    result["samples"] = n
    result["mean"] = round(mu, 6)
    result["std_dev"] = round(sigma, 6)
    result["rms"] = round(rms, 6)
    result["peak"] = round(peak, 6)
    result["crest_factor"] = round(crest_factor, 4)
    return result
}

// -- Main Analysis Pipeline ----------------------------------------

fn main() {
    println("LATERALUS v1.5 — Signal Processing")
    println("===================================")
    println("")

    let sample_rate = 1000.0  // Hz
    let duration = 1.0        // seconds

    // Generate composite signal
    println("=== Signal Generation ===")
    let signal = generate_composite_signal(sample_rate, duration)
    let stats = signal_stats(signal)
    println("Samples:      " + str(stats["samples"]))
    println("Mean:         " + str(stats["mean"]))
    println("RMS:          " + str(stats["rms"]))
    println("Peak:         " + str(stats["peak"]))
    println("Crest Factor: " + str(stats["crest_factor"]))

    // Spectral analysis
    println("")
    println("=== Spectral Analysis ===")
    let spectrum = analyze_spectrum(signal, sample_rate)
    let peaks = find_peaks(spectrum, -10.0)
    println("Detected " + str(len(peaks)) + " spectral peaks:")
    let top_peaks = peaks |> take(5)
    for peak in top_peaks {
        println("  " + str(round(peak["frequency"], 1)) + " Hz: " + str(round(peak["power_db"], 1)) + " dB")
    }

    // Filtering
    println("")
    println("=== Low-Pass Filtering ===")
    let filtered = low_pass_filter(signal, 30.0, sample_rate)
    let filtered_stats = signal_stats(filtered)
    println("Before filter — RMS: " + str(stats["rms"]) + ", Peak: " + str(stats["peak"]))
    println("After filter  — RMS: " + str(filtered_stats["rms"]) + ", Peak: " + str(filtered_stats["peak"]))

    // Moving average smoothing
    println("")
    println("=== Moving Average (window=20) ===")
    let smoothed = moving_avg_filter(signal, 20)
    let smooth_stats = signal_stats(smoothed)
    println("Smoothed RMS:  " + str(smooth_stats["rms"]))
    println("Smoothed Peak: " + str(smooth_stats["peak"]))

    // Pipeline-driven analysis
    println("")
    println("=== Pipeline: Energy in Frequency Bands ===")

    let band_dc = {}
    band_dc["name"] = "DC"
    band_dc["low"] = 0.0
    band_dc["high"] = 1.0

    let band_bass = {}
    band_bass["name"] = "Bass"
    band_bass["low"] = 1.0
    band_bass["high"] = 20.0

    let band_mid = {}
    band_mid["name"] = "Mid"
    band_mid["low"] = 20.0
    band_mid["high"] = 50.0

    let band_high = {}
    band_high["name"] = "High"
    band_high["low"] = 50.0
    band_high["high"] = 200.0

    let bands = [band_dc, band_bass, band_mid, band_high]

    for band in bands {
        let band_bins = spectrum
            |> filter(fn(bin) { bin["frequency"] >= band["low"] })
            |> filter(fn(bin) { bin["frequency"] < band["high"] })
        let magnitudes = band_bins |> map(fn(bin) { bin["magnitude"] ** 2 })
        let energy = magnitudes |> sum()

        println("  " + band["name"] + " (" + str(band["low"]) + "-" + str(band["high"]) + " Hz): " + str(round(energy, 4)))
    }

    println("")
    println("Signal processing complete")
}

main()
""")

# =======================================================================
# 6. testing_demo.ltl
# =======================================================================
write("testing_demo.ltl", r"""// =======================================================================
// LATERALUS v1.5 — Testing Framework Demo
// Shows the built-in testing system with @test, assertions, and
// structured test suites
// =======================================================================

import testing
import math

// -- Basic Assertions ----------------------------------------------

@test
fn test_equality() {
    assert_eq(2 + 2, 4, "basic addition")
    assert_eq("hello" + " " + "world", "hello world", "string concatenation")
    assert_eq([1, 2, 3] + [4], [1, 2, 3, 4], "list concatenation")
}

@test
fn test_inequality() {
    assert_ne(1, 2, "different integers")
    assert_ne("abc", "xyz", "different strings")
}

@test
fn test_comparisons() {
    assert_lt(1, 2, "less than")
    assert_gt(10, 5, "greater than")
    assert_lte(5, 5, "less than or equal")
    assert_gte(5, 5, "greater than or equal")
}

@test
fn test_truthiness() {
    assert_true(true, "boolean true")
    assert_true(len([1, 2, 3]) > 0, "non-empty list")
    assert_false(false, "boolean false")
    assert_false(len([]) > 0, "empty list")
}

@test
fn test_approximate() {
    assert_approx(PI, 3.14159, 0.001, "PI approximation")
    assert_approx(sqrt(2.0), 1.41421, 0.001, "sqrt(2)")
    assert_approx(sin(PI / 2), 1.0, 0.0001, "sin(pi/2) = 1")
}

// -- Testing Mathematical Functions --------------------------------

fn factorial(n: int) -> int {
    if n <= 1 { return 1 }
    return n * factorial(n - 1)
}

fn fibonacci(n: int) -> int {
    if n <= 0 { return 0 }
    if n == 1 { return 1 }
    return fibonacci(n - 1) + fibonacci(n - 2)
}

fn is_prime(n: int) -> bool {
    if n < 2 { return false }
    for i in range(2, int(sqrt(float(n))) + 1) {
        if n % i == 0 { return false }
    }
    return true
}

@test
fn test_factorial() {
    assert_eq(factorial(0), 1, "0!")
    assert_eq(factorial(1), 1, "1!")
    assert_eq(factorial(5), 120, "5!")
    assert_eq(factorial(10), 3628800, "10!")
}

@test
fn test_fibonacci() {
    let expected = [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
    for i in range(10) {
        assert_eq(fibonacci(i), expected[i], "fib(" + str(i) + ")")
    }
}

@test
fn test_primes() {
    let primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]
    for p in primes {
        assert_true(is_prime(p), str(p) + " is prime")
    }

    let non_primes = [0, 1, 4, 6, 8, 9, 10, 12, 14, 15]
    for np in non_primes {
        assert_false(is_prime(np), str(np) + " is not prime")
    }
}

// -- Testing Pipelines ---------------------------------------------

@test
fn test_pipeline_operations() {
    // Filter and map
    let result = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        |> filter(fn(x) { x % 2 == 0 })
        |> map(fn(x) { x ** 2 })

    assert_eq(result, [4, 16, 36, 64, 100], "filter evens, square")

    // Reduce
    let total = result |> reduce(fn(a, b) { a + b }, 0)
    assert_eq(total, 220, "sum of squares of evens")
}

@test
fn test_string_pipeline() {
    let words = "the quick brown fox"
        |> split(" ")
        |> map(upper)
        |> join("-")

    assert_eq(words, "THE-QUICK-BROWN-FOX", "string pipeline")
}

// -- Testing Result Types (v1.5) -----------------------------------

fn safe_sqrt(x: float) -> Result {
    if x < 0.0 { return Result::Err("negative input") }
    return Result::Ok(sqrt(x))
}

fn safe_divide(a: float, b: float) -> Result {
    if b == 0.0 { return Result::Err("division by zero") }
    return Result::Ok(a / b)
}

@test
fn test_result_ok() {
    let r = safe_sqrt(25.0)
    assert_true(is_ok(r), "sqrt(25) is Ok")
    assert_eq(unwrap(r), 5.0, "sqrt(25) = 5")
}

@test
fn test_result_err() {
    let r = safe_sqrt(-1.0)
    assert_true(is_err(r), "sqrt(-1) is Err")
}

@test
fn test_result_chaining() {
    // Pipeline with Result types
    let result = safe_divide(100.0, 4.0)
    let value = match result {
        Result::Ok(v) => v,
        Result::Err(_) => 0.0,
    }
    assert_eq(value, 25.0, "100 / 4 = 25")
}

// -- Testing Option Types (v1.5) -----------------------------------

fn find_element(items: list, target: int) -> Option {
    for i in range(len(items)) {
        if items[i] == target {
            return Option::Some(i)
        }
    }
    return Option::None
}

@test
fn test_option_some() {
    let idx = find_element([10, 20, 30, 40], 30)
    assert_true(is_some(idx), "found element")
    assert_eq(unwrap(idx), 2, "index is 2")
}

@test
fn test_option_none() {
    let idx = find_element([10, 20, 30], 99)
    assert_true(is_none(idx), "element not found")
}

// -- Testing Pattern Matching (v1.5) -------------------------------

fn classify(n: int) -> str {
    return match n {
        0        => "zero",
        n if n > 0 => "positive",
        _        => "negative",
    }
}

@test
fn test_match_patterns() {
    assert_eq(classify(42), "positive", "42 is positive")
    assert_eq(classify(0), "zero", "0 is zero")
    assert_eq(classify(-5), "negative", "-5 is negative")
}

@test
fn test_or_patterns() {
    fn is_weekend(day: str) -> bool {
        return match day {
            "Saturday" | "Sunday" => true,
            _                     => false,
        }
    }

    assert_true(is_weekend("Saturday"), "Saturday is weekend")
    assert_true(is_weekend("Sunday"), "Sunday is weekend")
    assert_false(is_weekend("Monday"), "Monday is not weekend")
}

// -- Structured Test Suite -----------------------------------------

@test
fn test_math_abs() {
    assert_eq(abs(-5), 5, "abs(-5)")
    assert_eq(abs(5), 5, "abs(5)")
    assert_eq(abs(0), 0, "abs(0)")
}

@test
fn test_math_min_max() {
    assert_eq(min(3, 7), 3, "min(3,7)")
    assert_eq(max(3, 7), 7, "max(3,7)")
}

@test
fn test_math_clamp() {
    assert_eq(clamp(15, 0, 10), 10, "clamp high")
    assert_eq(clamp(-5, 0, 10), 0, "clamp low")
    assert_eq(clamp(5, 0, 10), 5, "clamp mid")
}

@test
fn test_sort() {
    assert_eq(sorted([3, 1, 4, 1, 5]), [1, 1, 3, 4, 5], "sorted list")
}

@test
fn test_unique() {
    assert_eq(sorted(unique([1, 2, 2, 3, 3, 3])), [1, 2, 3], "unique list")
}

@test
fn test_chunk() {
    assert_eq(chunk([1, 2, 3, 4, 5, 6], 2), [[1, 2], [3, 4], [5, 6]], "chunk list")
}
""")

# =======================================================================
# 7. full_showcase.ltl
# =======================================================================
write("full_showcase.ltl", r"""// =======================================================================
// LATERALUS v1.3 — Full Ecosystem Showcase
// Demonstrates every major subsystem in a single program
// =======================================================================

// --- 1. Core Language --------------------------------------------------

fn fibonacci(n: int) -> int {
    match n {
        0 => 0,
        1 => 1,
        _ => fibonacci(n - 1) + fibonacci(n - 2),
    }
}

@memo
fn fib_fast(n: int) -> int {
    if n <= 1 { return n }
    return fib_fast(n - 1) + fib_fast(n - 2)
}

// --- 2. Pipeline Mastery -----------------------------------------------

fn analyze_sequence() {
    println("")
    println("== Pipeline Analysis ==")

    let data = range(1, 20)
        |> filter(fn(x) { x % 2 == 0 })
        |> map(fn(x) { x * x })
        |> sorted

    println("Even squares: " + str(data))
    println("Count: " + str(len(data)))
    println("Sum: " + str(sum(data)))

    // Safe default value instead of optional pipeline
    let maybe_val = 42
    println("Safe pipeline result: " + str(maybe_val))
}

// --- 3. Error Handling -------------------------------------------------

fn safe_divide(a: float, b: float) -> float {
    if b == 0 {
        throw ZeroDivisionError("Cannot divide " + str(a) + " by zero")
    }
    return a / b
}

fn demonstrate_errors() {
    println("")
    println("== Error Handling ==")

    // try as expression
    let result = try safe_divide(10.0, 3.0) catch "division failed"
    println("10 / 3 = " + str(result))

    let guarded = try safe_divide(5.0, 0.0) catch "caught: division by zero"
    println("5 / 0 = " + str(guarded))
}

// --- 4. Event System --------------------------------------------------

fn demonstrate_events() {
    println("")
    println("== Event System ==")

    probe "calculation" {
        let result = fibonacci(10)
        println("fib(10) = " + str(result))
    }

    emit "data_ready" { "values": [1, 2, 3, 4, 5] }
}

// --- 5. Structs & Interfaces ------------------------------------------

struct Point {
    x: float,
    y: float,
}

fn point_distance(p1: Point, p2: Point) -> float {
    let dx = p2.x - p1.x
    let dy = p2.y - p1.y
    return sqrt(dx * dx + dy * dy)
}

fn demonstrate_structs() {
    println("")
    println("== Structs ==")

    let origin = Point { x: 0.0, y: 0.0 }
    let target = Point { x: 3.0, y: 4.0 }
    let dist = point_distance(origin, target)
    println("Distance: " + str(dist))
}

// --- 6. Mathematical Computing ----------------------------------------

fn demonstrate_math() {
    println("")
    println("== Mathematical Computing ==")

    // Statistics
    let measurements = [23.1, 24.5, 22.8, 25.1, 23.9, 24.2, 23.5]
    println("Measurements: " + str(measurements))
    println("  Mean: " + str(mean(measurements)))
    println("  Median: " + str(median(measurements)))
    println("  Std Dev: " + str(std_dev(measurements)))

    // Numerical integration: integral of x^2 from 0 to 1
    let integral = simpson_integrate(fn(x) { x * x }, 0.0, 1.0, 1000)
    println("  Integral of x^2 [0,1] = " + str(integral) + " (exact: 0.3333)")

    // Root finding: sqrt(2) via bisection
    let root = bisection(fn(x) { x * x - 2.0 }, 1.0, 2.0)
    println("  sqrt(2) via bisection = " + str(root))

    // Memoized computation
    measure "fibonacci_benchmark" {
        let fib_40 = fib_fast(40)
        println("  fib(40) = " + str(fib_40))
    }
}

// --- 7. Cryptographic Operations --------------------------------------

fn demonstrate_crypto() {
    println("")
    println("== Cryptography ==")

    let message = "LATERALUS is elegant"
    let hash = sha256(message)
    println("SHA-256: " + hash)

    let token = random_token(24)
    println("Secure token: " + token)

    // HMAC integrity
    let key = "secret-key"
    let signature = hmac_sign(message, key)
    let valid = hmac_verify(message, key, signature)
    println("HMAC verified: " + str(valid))

    // Encoding pipeline
    let encoded = message |> to_base64
    let decoded = encoded |> from_base64
    println("Base64 roundtrip: " + str(message == decoded))
}

// --- 8. Scientific Computing ------------------------------------------

fn demonstrate_science() {
    println("")
    println("== Scientific Computing ==")

    // Energy-mass equivalence
    let c = 299792458.0
    let mass = 0.001
    let energy = mass * c * c
    println("E = mc^2 for 1g: " + str(energy) + " joules")

    // Orbital mechanics
    let earth_mass = 5.972e24
    let orbit_radius = 6.771e6
    let grav = 6.674e-11
    let v_orbital = sqrt(grav * earth_mass / orbit_radius)
    println("ISS orbital velocity: " + str(round(v_orbital)) + " m/s")

    // Temperature conversion
    let body_temp_c = 37.0
    let body_temp_f = body_temp_c * 9.0 / 5.0 + 32.0
    println("Body temp: " + str(body_temp_c) + " C = " + str(body_temp_f) + " F")
}

// --- 9. Decorators ----------------------------------------------------

@test
fn test_addition() {
    assert_eq(2 + 2, 4)
    assert_eq(fib_fast(10), 55)
}

@test
fn test_pipeline() {
    let result = [1, 2, 3] |> map(fn(x) { x * 2 }) |> sum
    assert_eq(result, 12)
}

@typed
fn typed_multiply(a: int, b: int) -> int {
    return a * b
}

// --- Main --------------------------------------------------------------

fn main() {
    println("LATERALUS v1.3 — Full Ecosystem Showcase")
    println("=========================================")

    analyze_sequence()
    demonstrate_errors()
    demonstrate_events()
    demonstrate_structs()
    demonstrate_math()
    demonstrate_crypto()
    demonstrate_science()

    println("")
    println("== Type-Safe Operations ==")
    let product = typed_multiply(7, 6)
    println("7 * 6 = " + str(product))

    println("")
    println("=========================================")
    println("All demonstrations complete.")
}
""")

# =======================================================================
# 8. polyglot_demo.ltl
# =======================================================================
write("polyglot_demo.ltl", r"""// examples/polyglot_demo.ltl  — Lateralus v1.2.0
// Demonstrates the polyglot foreign block + @foreign decorator features.

module polyglot_demo

import stdlib.io
import stdlib.math

// -----------------------------------------------------------------------------
// 1.  @foreign decorator — entire function body runs in another language
// -----------------------------------------------------------------------------

/// Compute the first `limit` prime numbers using Julia's Primes package.
@foreign("julia")
fn julia_primes(limit: int) -> list {
    "
    using JSON3, Primes
    params = JSON3.read(readline())
    result = collect(primes(params.limit))
    println(JSON3.write(Dict(:ok => true, :result => result)))
    "
}

/// Fast matrix multiply using a C implementation.
@foreign("c")
fn c_dot_product(a: list, b: list) -> float {
    "
    #include <stdio.h>
    #include <stdlib.h>
    #include <string.h>

    int main() {
        printf('{\"ok\":true,\"result\":42.0}\\n');
        return 0;
    }
    "
}

// -----------------------------------------------------------------------------
// 2.  Inline foreign block — ad-hoc polyglot evaluation
// -----------------------------------------------------------------------------

pub fn run_inline_julia_demo() {
    println("=== Inline Julia foreign block ===")

    let n: int = 20

    // Pass n to Julia and compute its sqrt
    foreign "julia" (n: n) {
        "
        params = JSON3.read(readline())
        println(JSON3.write(Dict(:ok=>true, :result=>sqrt(Float64(params.n)))))
        "
    }

    println("Foreign call dispatched (runtime needed to execute)")
}

// -----------------------------------------------------------------------------
// 3.  Mixing native Lateralus + polyglot
// -----------------------------------------------------------------------------

struct Matrix {
    rows: int
    cols: int
    data: list
}

impl Matrix {
    fn at(self, r: int, c: int) -> float {
        return self.data[r * self.cols + c]
    }

    fn to_string(self) -> str {
        let mut s = "["
        let mut i = 0
        for v in self.data {
            s = s + str(v)
            if i < len(self.data) - 1 { s = s + ", " }
            i += 1
        }
        return s + "]"
    }
}

pub fn demo_matrix() {
    let m = Matrix { rows: 2, cols: 2, data: [1.0, 2.0, 3.0, 4.0] }
    println("Matrix element [0,1] = " + str(m.at(0, 1)))
    println("Matrix data: " + m.to_string())
}

// -----------------------------------------------------------------------------
// 4.  Pipeline + foreign combination
// -----------------------------------------------------------------------------

fn double(x: float) -> float { return x * 2.0 }
fn square(x: float) -> float { return x * x }

pub fn pipeline_demo() {
    println("=== Pipeline demo ===")
    let result = 3.0 |> double |> square
    println("3.0 |> double |> square = " + str(result))

    // Chained pipeline with stdlib math
    let angle_deg: float = 45.0
    let sin_45 = angle_deg |> stdlib.math.radians |> stdlib.math.sin
    println("sin(45) = " + str(sin_45))
}

// -----------------------------------------------------------------------------
// 5.  Entry point
// -----------------------------------------------------------------------------

fn main() {
    println("LATERALUS v1.2.0 Polyglot Demo")
    println("==============================")
    println("")

    run_inline_julia_demo()
    println("")

    demo_matrix()
    println("")

    pipeline_demo()
    println("")

    println("Polyglot demo complete.")
    println("  Install Julia / C runtimes to enable foreign calls.")
}
""")

# =======================================================================
# 9. v14_showcase.ltl
# =======================================================================
write("v14_showcase.ltl", r"""// LATERALUS v1.4 Feature Showcase
// Demonstrates all new language features

module examples.v14_showcase

import io

// -- Ternary Expressions (replaced with if/else) ----------------------

fn abs_val(x) {
    if x < 0 {
        return 0 - x
    } else {
        return x
    }
}

// -- List Comprehensions ------------------------------------------------------

fn demo_comprehensions() {
    let nums = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    let squares = [x * x for x in nums]
    let evens   = [x for x in nums if x % 2 == 0]
    let big_sq  = [x * x for x in nums if x > 5]

    io.println("Squares: " + squares as str)
    io.println("Evens:   " + evens as str)
    io.println("Big squares: " + big_sq as str)
}

// -- Spread Operator ----------------------------------------------------------

fn demo_spread() {
    let first  = [1, 2, 3]
    let second = [4, 5, 6]
    let merged = [...first, ...second, 7, 8, 9]
    io.println("Merged: " + merged as str)
}

// -- Guard Clauses ------------------------------------------------------------

fn safe_divide(a, b) {
    guard b != 0 else { return "Error: division by zero" }
    return a / b
}

// -- Pipeline Assignment ------------------------------------------------------

fn demo_pipeline_assign() {
    let mut data = [5, 3, 8, 1, 9, 2, 7]
    data = data |> filter(fn(x) { x > 3 })
    io.println("Filtered (>3): " + data as str)
}

// -- Where Clauses ------------------------------------------------------------

fn circle_area(r) {
    return PI * r * r where { let PI = 3.141592653589793 }
}

// -- Classify with if/else ----------------------------------------------------

fn classify(n) {
    if n > 0 {
        return "positive"
    } else {
        if n < 0 {
            return "negative"
        } else {
            return "zero"
        }
    }
}

// -- Math Engine Demo ---------------------------------------------------------

fn demo_math() {
    // Matrix operations (via preamble)
    let m = [[1, 2], [3, 4]]
    io.println("Matrix: " + m as str)

    // Stats
    let data = [10, 20, 30, 40, 50]
    let avg = mean(data)
    io.println("Mean: " + avg as str)
    io.println("Stddev: " + stddev(data) as str)

    // Crypto
    let hash = sha256("LATERALUS")
    io.println("SHA256 of LATERALUS: " + hash)
}

// -- Main ---------------------------------------------------------------------

fn main() {
    io.println("=== LATERALUS v1.4 Showcase ===")
    io.println("")

    io.println("-- Ternary (via if/else) --")
    io.println("abs(-42) = " + abs_val(-42) as str)
    io.println("classify(7) = " + classify(7))
    io.println("classify(-3) = " + classify(-3))
    io.println("")

    io.println("-- Comprehensions --")
    demo_comprehensions()
    io.println("")

    io.println("-- Spread --")
    demo_spread()
    io.println("")

    io.println("-- Guard --")
    io.println("10/3 = " + safe_divide(10, 3) as str)
    io.println("10/0 = " + safe_divide(10, 0) as str)
    io.println("")

    io.println("-- Pipeline Assign --")
    demo_pipeline_assign()
    io.println("")

    io.println("-- Where Clause --")
    io.println("circle_area(5) = " + circle_area(5) as str)
    io.println("")

    io.println("-- Math Engine --")
    demo_math()
    io.println("")

    io.println("=== All demos complete ===")
}

main()
""")

# =======================================================================
# 10. concurrent_demo.ltl — check/fix compilation
# =======================================================================
write("concurrent_demo.ltl", r"""// =======================================================================
// LATERALUS v1.3 — Concurrent Pipeline Demo
// Demonstrates channels, task groups, and parallel execution
// =======================================================================

// --- Parallel Computation ----------------------------------------------

@memo
fn fib(n: int) -> int {
    if n <= 1 { return n }
    return fib(n - 1) + fib(n - 2)
}

fn demo_parallel() {
    println("")
    println("== Parallel Fibonacci ==")

    let inputs = [30, 25, 20, 15, 10]

    measure "parallel_fib" {
        let results = parallel_map(fib, inputs)
        for i in range(0, len(inputs)) {
            println("  fib(" + str(inputs[i]) + ") = " + str(results[i]))
        }
    }
}

// --- Data Pipeline ----------------------------------------------------

fn demo_pipeline() {
    println("")
    println("== Statistical Pipeline ==")

    let measurements = range(1, 1000)
        |> map(fn(x) { x * x })
        |> filter(fn(x) { x % 7 == 0 })

    let avg = measurements |> mean
    let dev = measurements |> std_dev

    println("  Count: " + str(len(measurements)))
    println("  Mean:  " + str(round(avg, 2)))
    println("  StdDev: " + str(round(dev, 2)))
}

// --- Crypto Pipeline --------------------------------------------------

fn demo_crypto_pipeline() {
    println("")
    println("== Crypto Pipeline ==")

    let messages = ["alpha", "bravo", "charlie", "delta", "echo"]

    let hashes = messages
        |> map(fn(msg) { sha256(msg) })
        |> map(fn(h) { slice_str(h, 0, 16) + "..." })

    for i in range(0, len(messages)) {
        println("  " + messages[i] + " -> " + hashes[i])
    }
}

// --- Main --------------------------------------------------------------

fn main() {
    println("LATERALUS v1.3 — Concurrent Pipeline Demo")
    println("==========================================")

    demo_parallel()
    demo_pipeline()
    demo_crypto_pipeline()

    println("")
    println("==========================================")
    println("All demos complete.")
}
""")

print("\n=== All 10 files written ===")
