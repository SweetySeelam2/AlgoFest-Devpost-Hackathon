import math, random, time
from typing import List, Tuple
import numpy as np
from .model import VRPInstance, total_cost
from .neighborhoods import improve_two_opt_intra, relocate_best_improvement

def simulated_annealing(routes: List[List[int]],
                        instance: VRPInstance,
                        D: np.ndarray,
                        time_budget_s: float = 30.0,
                        T0: float = 1.0,
                        alpha: float = 0.995) -> List[List[int]]:
    """
    Time-budgeted SA using 2-opt/relocate proposals.
    """
    rng = random.Random(42)
    best = [r[:] for r in routes]
    best_cost = total_cost(best, instance, D)
    cur = [r[:] for r in routes]
    cur_cost = best_cost
    T = T0
    t_end = time.time() + time_budget_s
    iters = 0

    while time.time() < t_end:
        iters += 1
        # alternate move types
        if iters % 2 == 0:
            cand, _ = improve_two_opt_intra([r[:] for r in cur], D, max_passes=1)
        else:
            cand, _ = relocate_best_improvement([r[:] for r in cur], instance, D)
        cand_cost = total_cost(cand, instance, D)
        delta = cand_cost - cur_cost
        if delta <= 0 or rng.random() < math.exp(-delta / max(T, 1e-9)):
            cur, cur_cost = cand, cand_cost
            if cur_cost < best_cost:
                best, best_cost = [r[:] for r in cur], cur_cost
        T *= alpha
    return best
