from typing import List, Tuple, Optional
import numpy as np
from .model import VRPInstance, route_demand
from .model import total_cost

def two_opt_delta(route: List[int], i: int, k: int, D: np.ndarray) -> float:
    """
    2-opt: reverse route[i:k+1]. Compute delta using only affected edges.
    route: [0, ..., 0]
    i, k are indices in the route (0-based).
    """
    if i < 1 or k >= len(route) - 1 or i >= k:
        return 0.0
    a, b = route[i - 1], route[i]
    c, d = route[k], route[k + 1]
    before = D[a, b] + D[c, d]
    after = D[a, c] + D[b, d]
    return after - before

def apply_two_opt(route: List[int], i: int, k: int) -> List[int]:
    return route[:i] + list(reversed(route[i:k+1])) + route[k+1:]

def improve_two_opt_intra(routes: List[List[int]], D: np.ndarray, max_passes: int = 1) -> Tuple[List[List[int]], bool]:
    improved = False
    for _ in range(max_passes):
        changed = False
        for r_idx, r in enumerate(routes):
            best_gain = 0.0
            best_move = None
            for i in range(1, len(r) - 2):
                for k in range(i + 1, len(r) - 1):
                    delta = two_opt_delta(r, i, k, D)
                    if delta < best_gain:
                        best_gain = delta
                        best_move = (r_idx, i, k)
            if best_move:
                rr, i, k = best_move
                routes[rr] = apply_two_opt(routes[rr], i, k)
                improved = changed = True
        if not changed:
            break
    return routes, improved

def relocate_best_improvement(routes: List[List[int]],
                              instance: VRPInstance,
                              D: np.ndarray) -> Tuple[List[List[int]], bool]:
    """
    Try moving a single customer from route A to best position in route B.
    """
    nodes = instance.all_nodes()
    best_gain = 0.0
    best_move = None  # (ra, ia, rb, jb)
    for ra in range(len(routes)):
        rA = routes[ra]
        for ia in range(1, len(rA) - 1):
            customer = rA[ia]
            # remove cost delta in A
            delta_remove = D[rA[ia - 1], rA[ia]] + D[rA[ia], rA[ia + 1]] - D[rA[ia - 1], rA[ia + 1]]

            for rb in range(len(routes)):
                if ra == rb and len(rA) <= 3:
                    continue
                rB = routes[rb]
                # capacity check: if different route
                if ra != rb:
                    loadB = route_demand(rB, nodes)
                    if loadB + nodes[customer].demand > instance.vehicle_capacity:
                        continue
                for jb in range(1, len(rB)):  # insert before index jb
                    prevB, nextB = rB[jb - 1], rB[jb]
                    delta_insert = D[prevB, customer] + D[customer, nextB] - D[prevB, nextB]
                    if ra == rb:
                        # if same route and insertion after removal, handle index shifts
                        if jb in (ia, ia + 1):
                            continue
                    gain = (delta_remove - delta_insert)
                    # gain>0 means improvement (we subtract cost)
                    if gain > best_gain:
                        best_gain = gain
                        best_move = (ra, ia, rb, jb)

    if best_move and best_gain > 1e-9:
        ra, ia, rb, jb = best_move
        customer = routes[ra][ia]
        # apply move
        del routes[ra][ia]
        routes[rb].insert(jb, customer)
        # clean empty routes
        routes[:] = [r if len(r) > 2 else r for r in routes]
        return routes, True
    return routes, False
