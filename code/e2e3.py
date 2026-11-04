"""E2: disjunctive-constraint overhead sweep (proj vs naive, grid 20^3).
E3: extended-object (AABB extent + non-overlap) overhead sweep vs point objects.
JSONL logs to ../logs/e2_disj.jsonl / ../logs/e3_ext.jsonl."""
import json, os, sys, time, math, argparse, resource
from multiprocessing import Pool
from hopa3d import gen_instance, check_all, save_instance
from runner import solve_instance

HERE = os.path.dirname(os.path.abspath(__file__))

def init_worker(mem_gb):
    resource.setrlimit(resource.RLIMIT_AS, (mem_gb * 1024**3, mem_gb * 1024**3))

def solve_both(tag, datadir, gen_kwargs, timeout):
    base = os.path.join(datadir, tag)
    L, cs, meta = gen_instance(**gen_kwargs)
    ok, _ = check_all(cs, L)
    save_instance(base, L, cs, meta)
    res = dict(tag=tag, gen_selfcheck=ok, **{k: v for k, v in gen_kwargs.items() if k != 'seed'})
    for enc in ("proj", "naive"):
        t1 = time.perf_counter()
        try:
            r = solve_instance(base + "_inst.lp", base + "_geom.lp",
                               os.path.join(HERE, enc + ".lp"), timeout=timeout)
            res[enc] = dict(verdict=r["verdict"], t_ground=r["t_ground"], t_solve=r["t_solve"])
        except MemoryError:
            res[enc] = dict(verdict="MEMKILL")
        res[enc]["wall"] = round(time.perf_counter() - t1, 2)
    for suf in ("_inst.lp", "_geom.lp"):
        try: os.remove(base + suf)
        except OSError: pass
    return res

# ---------------- E2 ----------------
def e2_specs(reps):
    cells = [(8, 2, 0.2), (8, 4, 0.2), (16, 4, 0.2), (24, 8, 0.2),
             (8, 2, 0.4), (8, 4, 0.4), (16, 4, 0.4), (24, 8, 0.4)]
    out = []
    for (n_obj, n_disj, pct) in cells:
        for mode in ("consistent", "inconsistent"):
            for r in range(reps):
                out.append(dict(n_obj=n_obj, n_disj=n_disj, pct_disj=pct, mode=mode, rep=r,
                                seed=310000 + len(out) * 41))
    return out

def e2_case(spec, reps=None):
    tag = f"e2_n{spec['n_obj']}_d{spec['n_disj']}_p{int(spec['pct_disj']*100)}_{spec['mode'][:5]}_r{spec['rep']:02d}"
    gk = dict(seed=spec["seed"], n_obj=spec["n_obj"], n_con=math.ceil(1.5 * spec["n_obj"]),
              s=20, mh=2, mv=2, ra=3, re=3, mode=spec["mode"],
              pct_disj=spec["pct_disj"], n_disj=spec["n_disj"])
    r = solve_both(tag, os.path.join(HERE, "..", "data", "e2"), gk, timeout=120.0)
    r.update({k: spec[k] for k in ("n_obj", "n_disj", "pct_disj", "mode", "rep", "seed")})
    r["exp"] = "E2"
    return r

# ---------------- E3 ----------------
def e3_specs(reps):
    out = []
    for emax in (0, 1, 2, 3):
        for mode in ("consistent", "inconsistent"):
            for r in range(reps):
                out.append(dict(emax=emax, mode=mode, rep=r, n_obj=20, s=20,
                                seed=410000 + len(out) * 43))
    return out

def e3_case(spec):
    tag = f"e3_emax{spec['emax']}_{spec['mode'][:5]}_r{spec['rep']:02d}"
    gk = dict(seed=spec["seed"], n_obj=spec["n_obj"], n_con=math.ceil(1.5 * spec["n_obj"]),
              s=spec["s"], mh=2, mv=2, ra=3, re=3, emax=spec["emax"], mode=spec["mode"])
    r = solve_both(tag, os.path.join(HERE, "..", "data", "e3"), gk, timeout=120.0)
    r.update({k: spec[k] for k in ("emax", "mode", "rep", "seed")})
    r["exp"] = "E3"
    return r

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", choices=["E2", "E3"], required=True)
    ap.add_argument("--reps", type=int, default=15)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--mem-gb", type=int, default=3)
    args = ap.parse_args()
    datadir = os.path.join(HERE, "..", "data", args.exp.lower())
    os.makedirs(datadir, exist_ok=True)
    logpath = os.path.join(HERE, "..", "logs",
                           "e2_disj.jsonl" if args.exp == "E2" else "e3_ext.jsonl")
    specs = e2_specs(args.reps) if args.exp == "E2" else e3_specs(args.reps)
    fn = e2_case if args.exp == "E2" else e3_case
    print(f"{len(specs)} specs -> {logpath}", flush=True)
    t0 = time.perf_counter(); ndone = 0
    with open(logpath, "a") as lf, Pool(args.workers, initializer=init_worker,
                                        initargs=(args.mem_gb,)) as pool:
        for res in pool.imap_unordered(fn, specs):
            lf.write(json.dumps(res) + "\n"); lf.flush(); ndone += 1
            if ndone % 20 == 0:
                el = time.perf_counter() - t0
                print(f"  {ndone}/{len(specs)} {el:.0f}s eta {el/ndone*(len(specs)-ndone):.0f}s", flush=True)
    print(f"{args.exp} done: {ndone} specs in {time.perf_counter()-t0:.0f}s")

if __name__ == "__main__":
    main()
