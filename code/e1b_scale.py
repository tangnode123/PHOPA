"""E1b: naive vs projection-decomposed scalability sweep.

Phases:
  calib: N in {10,20,40} x s in {10,20}, C=1.5N, both modes, 20 reps  (timeout 120s)
  full : N in {40,60,80,100} x s in {20,30}, C=1.5N, both modes,
         reps 15 (N<=60) / 10 (N>=80)                                  (timeout 120s)
Per-process address-space rlimit guards the 8GB box against naive grounding blowup;
a killed grounding is logged as verdict=MEMKILL (a legitimate data point).
"""
import json, os, sys, time, math, argparse, resource, signal
from multiprocessing import Pool
import hopa3d
from hopa3d import gen_instance, check_all, save_instance
from runner import solve_instance

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "e1b")
LOGS = os.path.join(HERE, "..", "logs")

def init_worker(mem_gb):
    resource.setrlimit(resource.RLIMIT_AS, (mem_gb * 1024**3, mem_gb * 1024**3))

def specs_for(phase):
    out = []
    if phase == "calib":
        cells = [(n, s) for n in (10, 20, 40) for s in (10, 20)]
        reps = 20
    else:
        cells = [(n, s) for n in (40, 60, 80, 100) for s in (20, 30)]
        reps = 15
    idx = 0
    for (n, s) in cells:
        R = reps if phase == "calib" or n <= 60 else 10
        for mode in ("consistent", "inconsistent"):
            for r in range(R):
                idx += 1
                base_seed = 500000 if phase == "calib" else 900000
                out.append(dict(phase=phase, n_obj=n, s=s, n_con=math.ceil(1.5 * n),
                                mode=mode, rep=r, seed=base_seed + idx * 37))
    return out

def run_case(spec):
    tag = f"{spec['phase']}_n{spec['n_obj']}_s{spec['s']}_{spec['mode'][:5]}_r{spec['rep']:02d}"
    base = os.path.join(DATA, tag)
    t0 = time.perf_counter()
    try:
        L, cs, meta = gen_instance(spec["seed"], spec["n_obj"], spec["n_con"], spec["s"],
                                   mh=2, mv=2, ra=3, re=3, mode=spec["mode"])
        ok_true, _ = check_all(cs, L)
        save_instance(base, L, cs, meta)
    except MemoryError:
        return dict(tag=tag, **spec, error="GEN_MEMKILL")
    res = dict(tag=tag, **{k: spec[k] for k in ("phase","n_obj","s","n_con","mode","rep","seed")},
               gen_selfcheck=ok_true, gen_wall=round(time.perf_counter()-t0, 2))
    for enc in ("proj", "naive"):
        t1 = time.perf_counter()
        try:
            r = solve_instance(base + "_inst.lp", base + "_geom.lp", os.path.join(HERE, enc + ".lp"),
                               timeout=120.0)
            res[enc] = dict(verdict=r["verdict"], t_ground=r["t_ground"], t_solve=r["t_solve"])
        except MemoryError:
            res[enc] = dict(verdict="MEMKILL", t_ground=None, t_solve=None)
        except Exception as e:
            res[enc] = dict(verdict="ERROR", err=str(e)[:200])
        res[enc]["wall"] = round(time.perf_counter() - t1, 2)
    res["agree"] = res["proj"]["verdict"] == res["naive"]["verdict"] or \
                   "MEMKILL" in (res["proj"]["verdict"], res["naive"]["verdict"]) or \
                   "TIMEOUT" in (res["proj"]["verdict"], res["naive"]["verdict"])
    # cleanup lp files to save disk (json kept for audit)
    for suf in ("_inst.lp", "_geom.lp"):
        try: os.remove(base + suf)
        except OSError: pass
    return res

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["calib", "full"], required=True)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--mem-gb", type=int, default=3)
    ap.add_argument("--limit", type=int, default=0, help="run only first K specs (debug)")
    ap.add_argument("--only", default=None, help="filter: substring of tag")
    args = ap.parse_args()
    os.makedirs(DATA, exist_ok=True); os.makedirs(LOGS, exist_ok=True)
    specs = specs_for(args.phase)
    if args.only: specs = [s for s in specs if args.only in
                           f"{s['phase']}_n{s['n_obj']}_s{s['s']}_{s['mode'][:5]}"]
    if args.limit: specs = specs[:args.limit]
    logpath = os.path.join(LOGS, f"e1b_{args.phase}.jsonl")
    print(f"{len(specs)} specs -> {logpath}", flush=True)
    t0 = time.perf_counter(); ndone = 0; ndis = 0
    with open(logpath, "a") as lf, Pool(args.workers, initializer=init_worker,
                                        initargs=(args.mem_gb,)) as pool:
        for res in pool.imap_unordered(run_case, specs):
            lf.write(json.dumps(res) + "\n"); lf.flush(); ndone += 1
            if not res.get("agree", True): ndis += 1; print("DISAGREE", res["tag"], flush=True)
            if ndone % 20 == 0:
                el = time.perf_counter() - t0
                print(f"  {ndone}/{len(specs)} done, {el:.0f}s elapsed, "
                      f"eta {el/ndone*(len(specs)-ndone):.0f}s", flush=True)
    print(f"phase={args.phase} finished {ndone} specs in {time.perf_counter()-t0:.0f}s, disagreements={ndis}")

if __name__ == "__main__":
    main()
