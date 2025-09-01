import csv
import openrouteservice
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

# -----------------------------
# Load CSV
# -----------------------------
def load_students(csv_file):
    students = []
    with open(csv_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row["lat"] or not row["lon"]:  # skip empty values
                print(f"⚠️ Skipping student {row['name']} (missing coordinates)")
                continue
            students.append({
                "id": int(row["id"]),
                "name": row["name"],
                "lat": float(row["lat"]),
                "lon": float(row["lon"])
            })
    return students


def load_buses(csv_file):
    buses = []
    with open(csv_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            buses.append({
                "id": int(row["id"]),
                "capacity": int(row["capacity"])
            })
    return buses


# -----------------------------
# ORS Distance Matrix
# -----------------------------
def build_distance_matrix_ors(client, coords):
    matrix = client.distance_matrix(
        locations=coords,
        profile="driving-car",
        metrics=["distance"],
        units="m"
    )
    distances = matrix["distances"]
    return [[int(d) for d in row] for row in distances]


# -----------------------------
# OR-Tools VRP
# -----------------------------
def create_data_model(students, buses, school_coords, ors_key):
    client = openrouteservice.Client(key=ors_key)

    # Depot (school) + students
    coords = [school_coords] + [(s["lon"], s["lat"]) for s in students]

    distance_matrix = build_distance_matrix_ors(client, coords)

    return {
        "distance_matrix": distance_matrix,
        "demands": [0] + [1] * len(students),
        "vehicle_capacities": [b["capacity"] for b in buses],
        "num_vehicles": len(buses),
        "depot": 0,
        "coords": coords,
        "students": students,
        "buses": buses
    }


def print_solution(data, manager, routing, solution):
    total_dist = 0
    for v in range(data["num_vehicles"]):
        index = routing.Start(v)
        route_students = []
        route_nodes = []
        route_dist = 0

        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            route_nodes.append(node)
            if node != 0:
                route_students.append(data["students"][node-1]["name"])
            prev_index = index
            index = solution.Value(routing.NextVar(index))
            route_dist += routing.GetArcCostForVehicle(prev_index, index, v)

        route_nodes.append(0)  # back to depot

        if len(route_students) > 0:
            print(f"\nBus {data['buses'][v]['id']} (Capacity {data['buses'][v]['capacity']})")
            print("Assigned Students:", route_students)
            print("Route (coords):", [data["coords"][n] for n in route_nodes])
            print(f"Distance: {route_dist/1000:.2f} km")

        total_dist += route_dist

    print(f"\nTotal Distance (all buses): {total_dist/1000:.2f} km")


def optimize_with_ors(students_csv="students.csv", buses_csv="buses.csv",
                      school_lat=30.3565, school_lon=76.3647, ors_key="YOUR_ORS_KEY"):

    students = load_students(students_csv)
    buses = load_buses(buses_csv)
    school_coords = (school_lon, school_lat)

    data = create_data_model(students, buses, school_coords, ors_key)

    manager = pywrapcp.RoutingIndexManager(len(data["distance_matrix"]),
                                           data["num_vehicles"], data["depot"])
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        a = manager.IndexToNode(from_index)
        b = manager.IndexToNode(to_index)
        return data["distance_matrix"][a][b]

    transit_cb = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_cb)

    def demand_callback(from_index):
        node = manager.IndexToNode(from_index)
        return data["demands"][node]

    demand_cb = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_cb, 0, data["vehicle_capacities"], True, "Capacity"
    )

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.seconds = 10

    solution = routing.SolveWithParameters(params)
    if solution:
        print_solution(data, manager, routing, solution)
    else:
        print("No solution found.")


# -----------------------------
# Run
# -----------------------------
if __name__ == "__main__":
    ORS_KEY = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6ImJmNmI4YjljODBjODQ5YzZhZGRlNTk4ZWE5ZjY2M2E3IiwiaCI6Im11cm11cjY0In0="  # paste your OpenRouteService API key here
    optimize_with_ors(ors_key=ORS_KEY)
