from dataclasses import dataclass
import numpy as np
from typing import List, Tuple, Dict, Optional

@dataclass
class Node:
    idx: int
    x: float
    y: float
    demand: int = 0
    tw_open: Optional[float] = None
    tw_close: Optional[float] = None
    service: float = 0.0

@dataclass
class VRPInstance:
    depot: Node
    customers: List[Node]
    vehicle_capacity: int
    num_vehicles: int
    lambda_tw: float = 0.0   # time-window penalty multiplier
    mu_fair: float = 0.0     # fairness penalty multiplier (optional hook)

    def all_nodes(self) -> List[Node]:
        return [self.depot] + self.customers

def euclidean_matrix(nodes: List[Node]) -> np.ndarray:
    coords = np.array([(n.x, n.y) for n in nodes], dtype=float)
    diff = coords[:, None, :] - coords[None, :, :]
    return np.sqrt((diff ** 2).sum(axis=2))

def route_distance(route: List[int], D: np.ndarray) -> float:
    """Route is a sequence of node indices including depot at start and end."""
    if len(route) < 2:
        return 0.0
    return float(np.sum(D[route[:-1], route[1:]]))

def route_demand(route: List[int], nodes: List[Node]) -> int:
    # Expects route includes depot at start/end; customers are 1..N
    return sum(nodes[i].demand for i in route if i != 0)

def time_window_penalty(route: List[int], nodes: List[Node], D: np.ndarray) -> float:
    """Simple TW model: travel time == distance; waiting allowed; penalize lateness linearly."""
    t = 0.0
    penalty = 0.0
    for a, b in zip(route[:-1], route[1:]):
        t += D[a, b]
        node = nodes[b]
        if node.tw_open is not None and node.tw_close is not None:
            if t < node.tw_open:
                t = node.tw_open  # wait
            if t > node.tw_close:
                penalty += (t - node.tw_close)
        t += node.service
    return penalty

def fairness_penalty(routes: List[List[int]], nodes: List[Node], num_zones: int = 4) -> float:
    """
    Optional: grid zones to discourage starving far zones.
    Simple proxy: count visits per zone and penalize variance.
    """
    if num_zones <= 1:
        return 0.0
    xs = np.array([n.x for n in nodes])
    ys = np.array([n.y for n in nodes])
    x_edges = np.linspace(xs.min(), xs.max(), num_zones + 1)
    y_edges = np.linspace(ys.min(), ys.max(), num_zones + 1)

    def zone_id(i: int) -> int:
        xz = np.searchsorted(x_edges, nodes[i].x, side="right") - 1
        yz = np.searchsorted(y_edges, nodes[i].y, side="right") - 1
        xz = min(max(xz, 0), num_zones - 1)
        yz = min(max(yz, 0), num_zones - 1)
        return yz * num_zones + xz

    counts: Dict[int, int] = {}
    for r in routes:
        for i in r:
            if i == 0:  # skip depot
                continue
            z = zone_id(i)
            counts[z] = counts.get(z, 0) + 1
    if not counts:
        return 0.0
    arr = np.array(list(counts.values()), dtype=float)
    return float(np.var(arr))

def total_cost(routes: List[List[int]],
               instance: VRPInstance,
               D: np.ndarray) -> float:
    nodes = instance.all_nodes()
    dist = sum(route_distance(r, D) for r in routes)
    tw_pen = 0.0
    if instance.lambda_tw > 0:
        tw_pen = sum(time_window_penalty(r, nodes, D) for r in routes)
    fair_pen = 0.0
    if instance.mu_fair > 0:
        fair_pen = fairness_penalty(routes, nodes)
    return dist + instance.lambda_tw * tw_pen + instance.mu_fair * fair_pen

def generate_synthetic(n_customers: int,
                       seed: int = 42,
                       capacity: int = 100,
                       num_vehicles: int = 10,
                       with_time_windows: bool = False) -> Tuple[VRPInstance, np.ndarray]:
    rng = np.random.default_rng(seed)
    depot = Node(0, 50.0, 50.0, demand=0)
    customers = []
    for i in range(1, n_customers + 1):
        x, y = rng.uniform(0, 100, size=2)
        demand = int(rng.integers(1, max(2, capacity // 5)))
        if with_time_windows:
            base = rng.uniform(0, 200)
            tw_open = base
            tw_close = base + rng.uniform(20, 60)
            service = rng.uniform(0.5, 2.0)
        else:
            tw_open = tw_close = None
            service = 0.0
        customers.append(Node(i, x, y, demand, tw_open, tw_close, service))
    inst = VRPInstance(depot, customers, capacity, num_vehicles)
    nodes = inst.all_nodes()
    D = euclidean_matrix(nodes)
    return inst, D
