"""E7: stress probe at large grids (s=40/50) -- find the crossover where the
naive 3-way join grounding explodes (time/MEMKILL) while the projection-
decomposed encoding (shared 2D tables) still solves. Consistent mode only
(SAT instances are the hard ones; UNSAT proofs are fast for both).

Phases:
  probe : 4 configs x 1 rep, both encodings, timeout 300 -- feasibility check
  main  : configs that survived probe x more reps (set --reps)
"""
import argparse, json, math, os, resource, sys, time
from multiprocessing import Pool
import hopa3d
from runner import solve_instance

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "e7")
LOG = os.path.join(HERE, "..", "logs", "e7_stress.jsonl")
TIMEOUT = 300.0

PROBE = [(60, 40), (100, 40), (60, 50), (100, 50)]

def init_worker(mem_gb):
    if mem_gb > 0:
        resource.setrlimit(resource.RLIMIT_AS,
                           (mem_gb * 1024**3, mem_gb * 1024**3))

def run_case(spec):
    phase, n_obj, s, rep, seed = spec
    tag = f"e7_{phase}_N{n_obj}_s{s}_r{rep}"
    out = dict(phase=phase, n_obj=n_obj, s=s, rep=rep, seed=seed, tag=tag,
               mode="consistent", n_con=math.ceil(1.5 * n_obj))
    t0 = time.perf_counter()
    try:
        L, cs, meta = hopa3d.gen_instance(seed=seed, n_obj=n_obj,
                                          n_con=out["n_con"], s=s, mh=2, mv=2,
                                          ra=3, re=3, emax=0, mode="consistent",
                                          pct_disj=0.0, n_disj=0)
        ok, bad = hopa3d.check_all(cs, L)
        out["gen_selfcheck"] = ok
        if not ok:
            out["gen_bad"] = str(bad)[:200]
            return out
        base = os.path.join(DATA, tag)
        hopa3d.save_instance(base, L, cs, meta)
    except MemoryError:
        out["gen"] = "MEMKILL"; return out
    out["gen_wall"] = round(time.perf_counter() - t0, 2)
    for enc in ("proj", "naive"):
        try:
            r = solve_instance(base + "_inst.lp", base + "_geom.lp",
                               os.path.join(HERE, enc + ".lp"), timeout=TIMEOUT)
            r.pop("model", None)
        except MemoryError:
            r = dict(verdict="MEMKILL", t_ground=None, t_solve=None, t_total=None)
        out[enc] = r
    out["agree"] = out["proj"]["verdict"] == out["naive"]["verdict"] or \
        "MEMKILL" in (out["proj"]["verdict"], out["naive"]["verdict"])
    for suf in ("_inst.lp", "_geom.lp"):
        p = base + suf
        if os.path.exists(p): os.remove(p)
    return out

def specs_for(phase, reps, configs=None):
    if phase == "probe":
        cfgs, nr = PROBE, 1
    else:
        cfgs, nr = configs or PROBE, reps
    out = []
    i = 0
    for rep in range(nr):
        for (n, s) in cfgs:
            out.append((phase, n, s, rep, 700000 + i * 53)); i += 1
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["probe", "main"], default="probe")
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--mem-gb", type=int, default=3)
    ap.add_argument("--configs", default=None, help="NxS,NxS,... override for main phase")
    a = ap.parse_args()
    os.makedirs(DATA, exist_ok=True)
    cfgs = None
    if a.configs:
        cfgs = [tuple(int(v) for v in c.split("x")) for c in a.configs.split(",")]
    specs = specs_for(a.phase, a.reps, cfgs)
    print(f"{len(specs)} specs -> {LOG}", flush=True)
    done = 0; t0 = time.perf_counter()
    with open(LOG, "a") as f, Pool(a.workers, initializer=init_worker,
                                   initargs=(a.mem_gb,)) as pool:
        for r in pool.imap_unordered(run_case, specs):
            f.write(json.dumps(r) + "\n"); f.flush()
            done += 1
            el = time.perf_counter() - t0
            pv = r.get("proj", {}).get("verdict"); nv = r.get("naive", {}).get("verdict")
            flag = "" if r.get("agree", True) else "  <<DISAGREE>>"
            print(f"{done}/{len(specs)} {r['tag']} proj={pv} naive={nv} "
                  f"({el:.0f}s){flag}", flush=True)
    print(f"phase={a.phase} finished {done} specs in {time.perf_counter()-t0:.0f}s")

if __name__ == "__main__":
    main()
