"""Paper figures from E1b raw log: scaling curves (median solve time vs N),
timeout rates, grounding time. Reads ../logs/e1b_{calib,full}.jsonl."""
import json, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FIGS = os.path.join(HERE, "..", "results", "figures")
T_EFF = 120.0  # effective time for TIMEOUT/MEMKILL (censored)

def load(paths):
    rows = []
    for p in paths:
        if os.path.exists(p):
            rows += [json.loads(l) for l in open(p)]
    return rows

def t_eff(res):
    return T_EFF if res["verdict"] in ("TIMEOUT", "MEMKILL", "ERROR") else res["t_solve"]

def main():
    logs = sys.argv[1:] or [os.path.join(HERE, "..", "logs", f"e1b_{ph}.jsonl")
                            for ph in ("calib", "full")]
    rows = load(logs)
    full = [r for r in rows if r["phase"] == "full"]
    print(f"rows total={len(rows)} full={len(full)}")
    os.makedirs(FIGS, exist_ok=True)

    # ---- fig 1: median solve time vs N, per (s, mode), full phase ----
    cells = sorted({(r["s"], r["mode"]) for r in full})
    fig, axes = plt.subplots(1, len(cells), figsize=(4.6 * len(cells), 3.8), squeeze=False)
    for ax, (s, mode) in zip(axes[0], cells):
        ns = sorted({r["n_obj"] for r in full if r["s"] == s and r["mode"] == mode})
        for enc, mk, col in (("proj", "o", "tab:blue"), ("naive", "s", "tab:red")):
            med, lo, hi = [], [], []
            for n in ns:
                ts = [t_eff(r[enc]) for r in full
                      if r["s"] == s and r["mode"] == mode and r["n_obj"] == n]
                med.append(np.median(ts))
                lo.append(np.percentile(ts, 25)); hi.append(np.percentile(ts, 75))
            ax.errorbar(ns, med, yerr=[np.array(med) - lo, np.array(hi) - med],
                        marker=mk, color=col, capsize=3, label=enc)
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_xticks(ns); ax.set_xticklabels(ns)
        ax.set_xlabel("objects N"); ax.set_ylabel("solve time [s]")
        ax.set_title(f"{mode}, grid {s}$^3$")
        ax.axhline(T_EFF, color="gray", ls=":", lw=1)
        ax.legend()
    fig.tight_layout()
    p1 = os.path.join(FIGS, "e1b_solve_time.png")
    fig.savefig(p1, dpi=150); plt.close(fig)
    print("fig1:", p1)

    # ---- fig 2: timeout rate + grounding time vs N (all full cells pooled) ----
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.5, 3.8))
    ns = sorted({r["n_obj"] for r in full})
    for enc, mk, col in (("proj", "o", "tab:blue"), ("naive", "s", "tab:red")):
        rates = [100.0 * np.mean([r[enc]["verdict"] in ("TIMEOUT", "MEMKILL")
                                  for r in full if r["n_obj"] == n]) for n in ns]
        a1.plot(ns, rates, marker=mk, color=col, label=enc)
        gmed = [np.median([r[enc]["t_ground"] for r in full if r["n_obj"] == n]) for n in ns]
        a2.plot(ns, gmed, marker=mk, color=col, label=enc)
    a1.set_xlabel("objects N"); a1.set_ylabel("timeout rate [%]")
    a1.set_title("timeout/censor rate (t=120s)"); a1.legend(); a1.set_ylim(-2, 102)
    a2.set_yscale("log"); a2.set_xlabel("objects N"); a2.set_ylabel("median grounding [s]")
    a2.set_title("grounding time"); a2.legend()
    fig.tight_layout()
    p2 = os.path.join(FIGS, "e1b_timeout_grounding.png")
    fig.savefig(p2, dpi=150); plt.close(fig)
    print("fig2:", p2)

if __name__ == "__main__":
    main()
