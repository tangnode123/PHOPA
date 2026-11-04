"""E21: scale-boundary / ground-program component analysis (iter_5 Critical #3).

Turns "the 50^3 memory wall" from an anecdote into an explained, measured
boundary. For a FIXED small object count N (so the per-pair table cost dominates
and the S-scaling is isolated), sweep S in {20,30,40,45,50} and record, for both
naive.lp and proj.lp, the ground-program components (atoms / rules / bodies /
choices) and peak RSS via ablate_one.py (fresh process, 3GB budget -> MEMKILL).

Expected: naive's vertical/distance subsystem materializes a Theta(S^3) 3-way
(DX,DY,DZ) join PER object pair, so its atom/body count and RSS grow ~S^3 and it
breaches the 3GB wall near S=50; proj shares Theta(S^2) 2D tables (az_angle/q/hd/
nd2) across all pairs and reduces the per-pair vertical/distance check to a
Theta(S) 1D zdist join, so its growth is ~S^2 and it survives further. We fit the
log-log slope of n_atoms and peak_rss vs S for each encoding to quantify the
exponent, and report WHICH component (atoms vs bodies) dominates the RSS at the
wall. This substantiates the claim "projection decomposition DELAYS, not removes,
the memory wall" and motivates lazy / per-pair on-demand table generation as the
next step.

Log: ../logs/e21_scale_boundary.jsonl
"""
import argparse, json, os, subprocess, sys, time
from math import log
import hopa3d

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "e21")
LOG = os.path.join(HERE, "..", "logs", "e21_scale_boundary.jsonl")


def run_one(S, N, n_con, enc, memlimit=3.0, timeout=120):
    seed = 210000 + S * 13 + N
    L, cs, meta = hopa3d.gen_instance(seed=seed, n_obj=N, n_con=n_con, s=S,
                                      mh=2, mv=2, ra=3, re=3, emax=0,
                                      mode="consistent")
    os.makedirs(DATA, exist_ok=True)
    base = os.path.join(DATA, f"e21_S{S}_N{N}")
    open(base + "_inst.lp", "w").write(hopa3d.emit_facts(L, cs, meta))
    open(base + "_geom.lp", "w").write(hopa3d.emit_geom(L))
    cmd = [sys.executable, os.path.join(HERE, "ablate_one.py"),
           "--inst", base + "_inst.lp", "--geom", base + "_geom.lp",
           "--enc", os.path.join(HERE, enc + ".lp"),
           "--timeout", str(timeout), "--memlimit-gb", str(memlimit)]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 90)
        last = p.stdout.strip().splitlines()[-1] if p.stdout.strip() else None
        d = json.loads(last) if last else dict(verdict="SUBPROC_FAIL",
                                               err=p.stderr[-160:])
    except subprocess.TimeoutExpired:
        d = dict(verdict="TIMEOUT")
    for suf in ("_inst.lp", "_geom.lp"):
        if os.path.exists(base + suf):
            os.remove(base + suf)
    d.update(S=S, N=N, n_con=n_con, enc=enc)
    return d


def slope(pts):
    """log-log slope of y vs S over surviving points (len>=2)."""
    pts = [(s, y) for (s, y) in pts if y and y > 0]
    if len(pts) < 2:
        return None
    xs = [log(p[0]) for p in pts]; ys = [log(p[1]) for p in pts]
    n = len(pts); mx = sum(xs) / n; my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = sum((x - mx) ** 2 for x in xs)
    return round(num / den, 2) if den else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--N", type=int, default=10)
    ap.add_argument("--ncon", type=int, default=20)
    ap.add_argument("--cells", default="20,30,40,45,50")
    a = ap.parse_args()
    Ss = [int(x) for x in a.cells.split(",")]
    rows = []
    for S in Ss:
        for enc in ("naive", "proj"):
            d = run_one(S, a.N, a.ncon, enc)
            rows.append(d)
            print(f"[S={S} {enc}] verdict={d.get('verdict')} atoms={d.get('n_atoms')} "
                  f"rules={d.get('n_rules')} bodies={d.get('n_bodies')} "
                  f"rss_kb={d.get('peak_rss_kb')} t_ground={d.get('t_ground')}",
                  flush=True)
    with open(LOG, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    # scaling fits over surviving points
    for enc in ("naive", "proj"):
        sub = [r for r in rows if r["enc"] == enc and r.get("n_atoms")]
        sa = slope([(r["S"], r["n_atoms"]) for r in sub])
        sb = slope([(r["S"], r["n_bodies"]) for r in sub])
        sr = slope([(r["S"], r["peak_rss_kb"]) for r in sub if r.get("peak_rss_kb")])
        print(f"\n{enc}: log-log slope atoms~S^{sa} bodies~S^{sb} rss~S^{sr} "
              f"(over {len(sub)} surviving S)", flush=True)
    print("E21 done ->", LOG, flush=True)


if __name__ == "__main__":
    main()
