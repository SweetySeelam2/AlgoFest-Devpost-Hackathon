# src/cli.py
import argparse, os, json, time
import platform
import numpy as np
import matplotlib.pyplot as plt
import datetime as _dt

from .model import generate_synthetic, VRPInstance, total_cost
from .init import clarke_wright
from .neighborhoods import improve_two_opt_intra, relocate_best_improvement
from .meta import simulated_annealing
from .viz import plot_routes


def solve_once(n, k, cap, seed, with_tw, time_budget_sa, lambda_tw, mu_fair, skip_local=False):
    """
    Single run: generate instance, CW init, optional local search, optional SA, compute cost.
    """
    inst, D = generate_synthetic(
        n_customers=n, seed=seed, capacity=cap, num_vehicles=k, with_time_windows=with_tw
    )
    inst.lambda_tw = lambda_tw
    inst.mu_fair = mu_fair

    # 1) Clarke–Wright initialization
    routes = clarke_wright(inst, D)

    # 2) Local search (optional; skip if ablation flag)
    if not skip_local:
        improved = True
        while improved:
            routes, a = improve_two_opt_intra(routes, D, max_passes=1)
            routes, b = relocate_best_improvement(routes, inst, D)
            improved = (a or b)

    # 3) Simulated Annealing (time-budgeted)
    if time_budget_sa > 0:
        routes = simulated_annealing(
            routes, inst, D, time_budget_s=time_budget_sa, T0=1.0, alpha=0.997
        )

    # 4) Cost & coords for plotting
    cost = total_cost(routes, inst, D)
    coords = np.array([(node.x, node.y) for node in inst.all_nodes()])
    return inst, D, routes, cost, coords


def _build_stem(args):
    """
    Build a filename stem that encodes settings. Used unless --outstem is provided.
    """
    parts = [f"n{args.n}", f"k{args.k}", f"cap{args.cap}", f"seed{args.seed}"]
    parts.append(f"sa{int(args.sa_time)}")
    if args.tw:
        parts.append("tw")
    if args.no_local:
        parts.append("nolocal")
    if args.tag:
        parts.append(args.tag)
    if args.stamp:
        parts.append(_dt.datetime.now().strftime("%Y%m%d-%H%M%S"))
    return "_".join(parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=250)
    parser.add_argument("--k", type=int, default=20)
    parser.add_argument("--cap", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)

    parser.add_argument("--tw", action="store_true", help="Enable time windows")
    parser.add_argument("--sa_time", type=float, default=20.0, help="SA time budget (seconds)")
    parser.add_argument("--lambda_tw", type=float, default=0.0, help="TW penalty weight")
    parser.add_argument("--mu_fair", type=float, default=0.0, help="Fairness penalty weight")

    parser.add_argument("--outdir", type=str, default="results")
    parser.add_argument("--plot", action="store_true", help="Save a route plot PNG")
    parser.add_argument("--no_local", action="store_true", help="Skip local search after Clarke–Wright init")

    # Filename controls
    parser.add_argument("--tag", type=str, default="", help="Optional label to append to output filenames")
    parser.add_argument("--stamp", action="store_true", help="Append timestamp to output filenames")
    parser.add_argument(
        "--outstem",
        type=str,
        default="",
        help="Override filename stem entirely (takes precedence over --tag/--stamp)",
    )

    # NEW: per-run environment log
    parser.add_argument("--per_run_env", action="store_true",
                        help="Write env_{stem}.json instead of env.json")

    args = parser.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    # Build stem once (so timestamp is consistent across all files for this run)
    stem = args.outstem if args.outstem else _build_stem(args)

    # Repro environment log
    env = {
        "python": platform.python_version(),
        "system": platform.platform(),
        "processor": platform.processor(),
        "seed": args.seed,
    }
    env_path = os.path.join(args.outdir, f"env_{stem}.json") if args.per_run_env \
               else os.path.join(args.outdir, "env.json")
    with open(env_path, "w") as f:
        json.dump(env, f, indent=2)

    # Solve
    t0 = time.time()
    inst, D, routes, cost, coords = solve_once(
        args.n, args.k, args.cap, args.seed,
        args.tw, args.sa_time, args.lambda_tw, args.mu_fair,
        skip_local=args.no_local,
    )
    dt = time.time() - t0

    # Result payload
    result = {
        "n": args.n, "k": args.k, "cap": args.cap, "seed": args.seed,
        "tw": bool(args.tw), "sa_time": args.sa_time,
        "lambda_tw": args.lambda_tw, "mu_fair": args.mu_fair,
        "no_local": bool(args.no_local),
        "tag": args.tag, "stamp": bool(args.stamp),
        "cost": cost, "runtime_sec": dt, "routes": routes,
    }

    # Save JSON
    json_path = os.path.join(args.outdir, f"run_{stem}.json")
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"[OK] cost={cost:.2f} runtime={dt:.2f}s  -> {json_path}")

    # Optional plot
    if args.plot:
        plot_routes(routes, coords)
        png_path = os.path.join(args.outdir, f"routes_{stem}.png")
        plt.savefig(png_path, dpi=150)
        plt.close()
        print(f"[OK] saved plot -> {png_path}")


if __name__ == "__main__":
    main()