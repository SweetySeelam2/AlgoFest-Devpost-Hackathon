## Ablations (N=250, K=20, Cap=100, seed=42)

| Stage                          | Cost   | Runtime (s) | Δ vs CW (%) | JSON |
|-------------------------------:|-------:|------------:|-----------:|------|
| CW + Local (2-opt + relocate)  | 2,390.44 |       0.18 |       0.12 | results\run_ablation_local_only.json |
| CW + Local + SA (10s)          | 2,390.44 |      10.22 |       0.12 | results\run_ablation_local_sa10.json |
| Init only (Clarke–Wright)      | 2,393.36 |       0.15 |       0.00 | results\run_ablation_cw_only.json |

*Interpretation*

CW → CW+Local removes edge crossings and balances load (small cost drop). Adding SA (10s) ties local on this instance, showing CW+Local already reached a strong local optimum.
