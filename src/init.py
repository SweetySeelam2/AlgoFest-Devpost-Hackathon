# Clarke–Wright savings heuristic (Clarke & Wright, 1964) – custom implementation here.
from typing import List, Tuple
import numpy as np
from .model import VRPInstance, route_demand

def clarke_wright(instance: VRPInstance, D: np.ndarray) -> List[List[int]]:
    """
    Classic Clarke–Wright (sequential) for CVRP.
    Start with routes [0, i, 0] and merge by savings if capacity-feasible and endpoints align.
    """
    N = len(instance.customers)
    nodes_idx = list(range(1, N + 1))

    # ---- Initial routes: each customer alone ----
    # routes is 0-indexed: route 0 owns customer 1, route 1 owns customer 2, ...
    routes = [[0, i, 0] for i in nodes_idx]

    # Map each customer -> current route index (0..N-1), NOT the customer id
    route_of = {cust: (cust - 1) for cust in nodes_idx}

    # For each route index, track (first_customer, last_customer)
    ends = {ri: (nodes_idx[ri], nodes_idx[ri]) for ri in range(N)}

    # ---- Savings list ----
    s_list: List[Tuple[float, int, int]] = []
    for i in nodes_idx:
        for j in nodes_idx:
            if i < j:
                s = D[0, i] + D[0, j] - D[i, j]
                s_list.append((s, i, j))
    s_list.sort(reverse=True, key=lambda x: x[0])

    def feasible_merge(ri_idx: int, rj_idx: int, i: int, j: int) -> bool:
        # index guards (paranoia)
        if not (0 <= ri_idx < len(routes)) or not (0 <= rj_idx < len(routes)):
            return False
        ri = routes[ri_idx]
        rj = routes[rj_idx]
        # Skip "dead" routes
        if ri == [0, 0] or rj == [0, 0]:
            return False

        # i must be at an end of ri; j at an end of rj
        ei0, ei1 = ends[ri_idx]
        ej0, ej1 = ends[rj_idx]
        if i not in (ei0, ei1) or j not in (ej0, ej1):
            return False

        # capacity feasibility
        load_i = route_demand(ri, instance.all_nodes())
        load_j = route_demand(rj, instance.all_nodes())
        if load_i + load_j > instance.vehicle_capacity:
            return False
        return True

    for s, i, j in s_list:
        ri_idx = route_of[i]
        rj_idx = route_of[j]
        if ri_idx == rj_idx:
            continue
        if not feasible_merge(ri_idx, rj_idx, i, j):
            continue

        ri = routes[ri_idx]
        rj = routes[rj_idx]
        ei0, ei1 = ends[ri_idx]
        ej0, ej1 = ends[rj_idx]

        # ---- Normalize orientation ----
        # We want i to be the TAIL (last customer) of ri, and j to be the HEAD (first customer) of rj.
        # If i is the FIRST of ri, reverse ri; if j is the LAST of rj, reverse rj.
        if ei0 == i:
            ri = ri[::-1]
        if ej1 == j:
            rj = rj[::-1]

        # Merge by dropping the depot in the middle: [ ... i, 0] + [0, j ... ] -> [ ... i, j ... ]
        new_route = ri[:-1] + rj[1:]

        # Update structures
        routes[ri_idx] = new_route
        routes[rj_idx] = [0, 0]  # mark rj as dead

        # New ends for ri_idx: first and last customers of the merged route
        # (route always starts/ends with depot, so customers are at 1..-2)
        new_first = new_route[1] if len(new_route) > 2 else 0
        new_last  = new_route[-2] if len(new_route) > 2 else 0
        ends[ri_idx] = (new_first, new_last)
        ends[rj_idx] = (0, 0)

        # Update route_of mapping for all customers in the merged route
        for c in new_route:
            if c != 0:
                route_of[c] = ri_idx

    # ---- Prune dead routes and enforce vehicle limit ----
    alive = [r for r in routes if r != [0, 0]]
    if len(alive) > instance.num_vehicles:
        # Keep the heaviest routes first to reduce future merges need (simple heuristic)
        alive.sort(key=lambda r: -route_demand(r, instance.all_nodes()))
        alive = alive[:instance.num_vehicles]

    return alive