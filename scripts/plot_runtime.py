# scripts/plot_runtime.py
import csv, sys
from collections import defaultdict
import matplotlib.pyplot as plt

def main(in_path="results/sweep.csv", out_path="results/runtime_vs_n.png"):
    with open(in_path, newline="") as f:
        r = csv.DictReader(f)
        rows = list(r)

    # Robust header access (support 'n' or 'N', 'runtime_sec' or 'runtime', etc.)
    def get_key(row, *candidates):
        for k in candidates:
            if k in row:
                return k
        raise KeyError(f"None of {candidates} found in CSV headers: {list(row.keys())}")

    by_n = defaultdict(list)
    for row in rows:
        n_key = get_key(row, "n", "N")
        rt_key = get_key(row, "runtime_sec", "runtime", "Runtime(s)", "runtime (s)")
        by_n[int(float(row[n_key]))].append(float(row[rt_key]))

    xs, ys = [], []
    for n in sorted(by_n.keys()):
        arr = by_n[n]
        xs.append(n)
        ys.append(sum(arr)/len(arr))

    plt.figure()
    plt.plot(xs, ys, marker="o")  # no explicit colors/styles
    plt.xlabel("N (customers)")
    plt.ylabel("Mean runtime (s)")
    plt.title("Runtime vs N")
    plt.grid(True)
    plt.savefig(out_path, dpi=150)
    print(f"[OK] wrote {out_path}")

if __name__ == "__main__":
    in_path = sys.argv[1] if len(sys.argv) > 1 else "results/sweep.csv"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "results/runtime_vs_n.png"
    main(in_path, out_path)