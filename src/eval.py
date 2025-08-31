# src/eval.py
import argparse, os, csv, time
import datetime as _dt
import numpy as np

from .model import generate_synthetic, total_cost
from .init import clarke_wright
from .neighborhoods import improve_two_opt_intra, relocate_best_improvement
from .meta import simulated_annealing


def _solve_once(n, k, cap, seed, with_tw, sa_time, lambda_tw, mu_fair, skip_local=False):
    inst, D = generate_synthetic(
        n_customers=n, seed=seed, capacity=cap, num_vehicles=k, with_time_windows=with_tw
    )
    inst.lambda_tw = lambda_tw
    inst.mu_fair = mu_fair

    # 1) CW init
    routes = clarke_wright(inst, D)

    # 2) Local search (unless disabled)
    if not skip_local:
        improved = True
        while improved:
            routes, a = improve_two_opt_intra(routes, D, max_passes=1)
            routes, b = relocate_best_improvement(routes, inst, D)
            improved = a or b

    # 3) SA
    if sa_time > 0:
        routes = simulated_annealing(routes, inst, D, time_budget_s=sa_time, T0=1.0, alpha=0.997)

    # 4) Cost
    c = total_cost(routes, inst, D)
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", nargs="+", type=int, default=[100, 250, 500, 1000],
                    help="List of N (customers) to evaluate")
    ap.add_argument("--trials", type=int, default=3, help="Trials per N")
    ap.add_argument("--k", type=int, default=20, help="Vehicles")
    ap.add_argument("--cap", type=int, default=100, help="Vehicle capacity")
    ap.add_argument("--tw", action="store_true", help="Enable time windows")
    ap.add_argument("--sa_time", type=float, default=10.0, help="SA time budget (seconds)")
    ap.add_argument("--lambda_tw", type=float, default=0.0)
    ap.add_argument("--mu_fair", type=float, default=0.0)
    ap.add_argument("--outdir", type=str, default="results")
    # New: ablation control (match cli)
    ap.add_argument("--no_local", action="store_true", help="Skip local search after CW init")
    # New: filename controls
    ap.add_argument("--tag", type=str, default="", help="Label for this sweep")
    ap.add_argument("--stamp", action="store_true", help="Append timestamp to sweep filename")
    # New: base seed controls (seeds will be base, base+1, base+2 for trials)
    ap.add_argument("--seed_base", type=int, default=42, help="Base seed for trial 1 (t+1 for next trials)")

    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    rows = []
    for N in args.sizes:
        for t in range(args.trials):
            seed = args.seed_base + t
            t0 = time.time()
            cost = _solve_once(
                N, args.k, args.cap, seed, args.tw, args.sa_time,
                args.lambda_tw, args.mu_fair, skip_local=args.no_local
            )
            dt = time.time() - t0
            rows.append({
                "N": N,
                "trial": t + 1,
                "seed": seed,
                "k": args.k,
                "cap": args.cap,
                "tw": int(args.tw),
                "no_local": int(args.no_local),
                "sa_time": args.sa_time,
                "cost": round(cost, 4),
                "runtime_sec": round(dt, 4),
            })
            print(f"[OK] N={N} trial={t+1}/{args.trials} cost={cost:.2f} runtime={dt:.2f}s")

    # Build unique filename
    base = "sweep"
    if args.tag:
        base += f"_{args.tag}"
    if args.stamp:
        base += "_" + _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    csv_path = os.path.join(args.outdir, f"{base}.csv")

    # Write CSV
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"[OK] wrote {csv_path}")


if __name__ == "__main__":
    main()