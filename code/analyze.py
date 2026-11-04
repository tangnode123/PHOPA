"""Aggregate E1a/E1b/E2/E3 JSONL logs into summary tables (paper Table-1 style)
and run pre-registered statistical checks (Wilcoxon signed-rank on paired solve
times; timeout-rate comparison)."""
import json, os, sys, argparse
import pandas as pd
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LOGS = os.path.join(HERE, "..", "logs")
RESULTS = os.path.join(HERE, "..", "results")

def load_jsonl(path):
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line: rows.append(json.loads(line))
    return rows

def e1b_table(logfiles):
    recs = []
    for lf in logfiles:
        for r in load_jsonl(lf):
            if "error" in r: continue
            for enc in ("proj", "naive"):
                e = r.get(enc, {})
                recs.append(dict(phase=r["phase"], n_obj=r["n_obj"], s=r["s"],
                                 mode=r["mode"], rep=r["rep"], seed=r["seed"],
                                 enc=enc, verdict=e.get("verdict"),
                                 t_ground=e.get("t_ground"), t_solve=e.get("t_solve"),
                                 wall=e.get("wall")))
    df = pd.DataFrame(recs)
    return df

def cell_summary(df):
    """Per (n_obj, s, mode, enc): mean/median/std/max solve time, timeout rate."""
    def agg(g):
        to = g["verdict"].isin(["TIMEOUT", "MEMKILL", "ERROR"])
        st = pd.to_numeric(g["t_solve"], errors="coerce")
        return pd.Series(dict(
            n=len(g), n_timeout=int(to.sum()), timeout_rate=to.mean(),
            mean=st.mean(), median=st.median(), std=st.std(), max=st.max(),
            mean_ground=pd.to_numeric(g["t_ground"], errors="coerce").mean()))
    return df.groupby(["phase", "n_obj", "s", "mode", "enc"]).apply(agg, include_groups=False).reset_index()

def paired_stats(df):
    """Wilcoxon signed-rank on paired solve times (proj vs naive) per cell,
    timeouts counted as the timeout cap (conservative)."""
    from scipy.stats import wilcoxon
    piv = df.copy()
    piv["t_eff"] = np.where(piv["verdict"].isin(["TIMEOUT", "MEMKILL", "ERROR"]),
                            120.0, pd.to_numeric(piv["t_solve"], errors="coerce"))
    wide = piv.pivot_table(index=["phase", "n_obj", "s", "mode", "seed"],
                           columns="enc", values="t_eff")
    out = []
    for cell, g in wide.groupby(level=[0, 1, 2, 3]):
        g = g.dropna()
        if len(g) < 8 or (g["proj"] == g["naive"]).all():
            out.append(dict(cell=cell, n=len(g), stat=None, p=None,
                            median_red=None)); continue
        try:
            st, p = wilcoxon(g["proj"], g["naive"], alternative="less")
        except ValueError:
            st, p = None, None
        med_red = (g["naive"].median() - g["proj"].median()) / max(g["naive"].median(), 1e-9)
        out.append(dict(cell=cell, n=len(g), stat=st, p=p, median_red=med_red))
    return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--out", default=os.path.join(RESULTS, "e1b_cells.csv"))
    args = ap.parse_args()
    df = e1b_table(args.logs)
    os.makedirs(RESULTS, exist_ok=True)
    df.to_csv(os.path.join(RESULTS, "e1b_raw.csv"), index=False)
    cs = cell_summary(df)
    cs.to_csv(args.out, index=False)
    pd.set_option("display.width", 200)
    print(cs.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print("\n--- paired Wilcoxon (proj < naive) ---")
    for row in paired_stats(df):
        print(row)
