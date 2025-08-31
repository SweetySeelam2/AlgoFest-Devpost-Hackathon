from typing import List
import matplotlib.pyplot as plt

def plot_routes(routes: List[List[int]], coords):
    plt.figure(figsize=(6,6))
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    plt.scatter(xs[1:], ys[1:], s=12)
    plt.scatter([xs[0]], [ys[0]], marker='s', s=60)
    for r in routes:
        for a, b in zip(r[:-1], r[1:]):
            plt.plot([xs[a], xs[b]], [ys[a], ys[b]])
    plt.title("Routes")
    plt.tight_layout()
