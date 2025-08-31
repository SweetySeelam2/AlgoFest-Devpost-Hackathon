# scripts/summarize_sweep.py
import csv, sys, statistics as st
from collections import defaultdict

def _key_any(row, *candidates, default=None):
    """Return the first present key from a list (case-insensitive)."""
    lower = {k.lower(): k for k in row.keys()}
    for cand in candidates:
        k = lower.get(cand.lower())
        if k is not None:
            return k
    return None if default is None else default

def _float_safe(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default

def read_rows(path):
    rows = []
    with open(path, newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            # Flexible column names: N/n, cost, runtime_sec/runtime, trial
            kN   = _key_any(row, "N", "n")
            kC   = _key_any(row, "cost")
            kRT  = _key_any(row, "runtime_sec", "runtime")
            kTri = _key_any(row, "trial")
            if kN is None or kC is None:
                # minimal schema: must have N and cost
                continue
            rows.append({
                "N": int(row[kN]),
                "trial": int(row[kTri]) if kTri else 0,
                "cost": _float_safe(row[kC], 0.0),
                "runtime_sec": _float_safe(row[kRT], 0.0) if kRT else 0.0,
            })
    return rows

def aggregate(rows):
    byN_cost = defaultdict(list)
    byN_rt   = defaultdict(list)
    for r in rows:
        byN_cost[r["N"]].append(r["cost"])
        byN_rt[r["N"]].append(r["runtime_sec"])

    # Build markdown lines
    lines = []
    lines.append("## Results Summary (auto-generated)\n")

    # ---- Cost table ----
    lines.append("### Cost")
    lines.append("| N (customers) | Trials | Mean Cost | Std Dev | Cost / Customer |")
    lines.append("|---:|---:|---:|---:|---:|")
    for N in sorted(byN_cost.keys()):
        arr = byN_cost[N]
        mean_c = st.mean(arr)
        sd_c   = st.pstdev(arr) if len(arr) > 1 else 0.0
        per    = mean_c / max(N, 1)
        lines.append(f"| {N} | {len(arr)} | {mean_c:.2f} | {sd_c:.2f} | {per:.2f} |")

    lines.append("")

    # ---- Runtime table ----
    lines.append("### Runtime")
    lines.append("| N (customers) | Trials | Mean Runtime (s) | Std Dev (s) |")
    lines.append("|---:|---:|---:|---:|")
    for N in sorted(byN_rt.keys()):
        arr = byN_rt[N]
        mean_rt = st.mean(arr) if arr else 0.0
        sd_rt   = st.pstdev(arr) if len(arr) > 1 else 0.0
        lines.append(f"| {N} | {len(arr)} | {mean_rt:.2f} | {sd_rt:.2f} |")

    return "\n".join(lines)

def main(in_path="results/sweep.csv", out_path="results/summary.md"):
    rows = read_rows(in_path)
    if not rows:
        print(f"[WARN] No rows parsed from {in_path}.")
        return
    md = aggregate(rows)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        f.write(md)
    print(f"[OK] wrote {out_path}")

if __name__ == "__main__":
    in_path  = sys.argv[1] if len(sys.argv) > 1 else "results/sweep.csv"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "results/summary.md"
    main(in_path, out_path)