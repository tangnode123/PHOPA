"""E1a pilot: three-way cross-validation (generator label <-> proj <-> naive),
plus independent Python-verifier check on every SAT model.

Gate: 100% agreement on >=200 instances before main experiments.
"""
import json, os, re, sys, time, argparse
from multiprocessing import Pool
import hopa3d
from hopa3d import gen_instance, check_all, save_instance, Layout
from runner import solve_instance

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "pilot")
LOGS = os.path.join(HERE, "..", "logs")

VARIANTS = [
    dict(name="plain",  mh=2, mv=2, ra=3, re=3, emax=0, pct_disj=0.0),
    dict(name="disj",   mh=2, mv=2, ra=3, re=3, emax=0, pct_disj=0.25),
    dict(name="ext",    mh=2, mv=2, ra=3, re=3, emax=1, pct_disj=0.0),
    dict(name="gran3",  mh=3, mv=3, ra=3, re=3, emax=0, pct_disj=0.0),
]

def model_to_layout(model_atoms, jd):
    meta = jd["meta"]; gl = jd["layout"]
    L = Layout(meta["sx"], meta["sy"], meta["sz"], meta["mh"], meta["mv"], meta["ra"], meta["re"])
    pos = {}
    for a in model_atoms:
        m = re.match(r"(xloc|yloc|zloc)\((\d+),(-?\d+)\)", a)
        if m: pos.setdefault(int(m.group(2)), {})[m.group(1)[0]] = int(m.group(3))
        m = re.match(r"yaw\((\d+),(-?\d+)\)", a)
        if m: L.yaw[int(m.group(1))] = int(m.group(2))
        m = re.match(r"pitch\((\d+),(-?\d+)\)", a)
        if m: L.pitch[int(m.group(1))] = int(m.group(2))
    for k, d in pos.items(): L.pos[k] = (d["x"], d["y"], d["z"])
    for k in L.pos:
        L.yaw.setdefault(k, 0); L.pitch.setdefault(k, 0)
        L.ext[k] = tuple(gl["ext"].get(str(k), (0, 0, 0)))
    return L

def make_case(idx):
    """Deterministic case spec for pilot instance #idx."""
    seed = 10000 + idx
    mode = "consistent" if idx % 2 == 0 else "inconsistent"
    n_obj = [5, 10, 20][idx % 3]
    s = [8, 12][idx % 2] if idx % 5 else [10, 16][idx % 2]
    var = VARIANTS[(idx // 2) % len(VARIANTS)]
    n_con = max(4, int(n_obj * 1.5))
    return dict(idx=idx, seed=seed, mode=mode, n_obj=n_obj, s=s, n_con=n_con, **var)

def run_case(spec):
    idx = spec["idx"]
    base = os.path.join(DATA, f"p{idx:04d}")
    # generate (retry seeds until generator selfcheck passes for consistent mode)
    seed = spec["seed"]; attempt = 0
    while True:
        L, cs, meta = gen_instance(seed, spec["n_obj"], spec["n_con"], spec["s"],
                                   mh=spec["mh"], mv=spec["mv"], ra=spec["ra"], re=spec["re"],
                                   emax=spec["emax"], mode=spec["mode"], pct_disj=spec["pct_disj"])
        ok_true, bad_true = check_all(cs, L)
        if spec["mode"] == "consistent" and not ok_true:
            seed += 77777; attempt += 1
            if attempt > 20: return dict(spec=spec, error="generator failed selfcheck")
            continue
        break
    save_instance(base, L, cs, meta)
    jd = json.load(open(base + ".json"))
    out = dict(spec={k: spec[k] for k in ("idx","seed","mode","n_obj","s","n_con","name")},
               gen_selfcheck=ok_true, attempt=attempt)
    for enc in ("proj.lp", "naive.lp"):
        t0 = time.perf_counter()
        r = solve_instance(base + "_inst.lp", base + "_geom.lp", os.path.join(HERE, enc),
                           timeout=60.0)
        e = dict(verdict=r["verdict"], t_ground=r["t_ground"], t_solve=r["t_solve"],
                 t_wall=round(time.perf_counter() - t0, 3))
        if r["verdict"] == "SAT":
            Lm = model_to_layout(r["model"], jd)
            vok, vbad = check_all(cs, Lm)
            e["model_valid"] = vok
            if not vok: e["model_bad"] = str(vbad)[:200]
        out[enc[:-3]] = e
    # agreement checks
    p, n = out["proj"], out["naive"]
    agree = p["verdict"] == n["verdict"]
    label_ok = True
    if spec["mode"] == "consistent":
        label_ok = p["verdict"] == "SAT" and p.get("model_valid") and n.get("model_valid")
    else:
        label_ok = (p["verdict"] != "SAT" or p.get("model_valid")) and \
                   (n["verdict"] != "SAT" or n.get("model_valid"))
    out["agree"] = agree; out["pass"] = bool(agree and label_ok)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=240)
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    os.makedirs(DATA, exist_ok=True); os.makedirs(LOGS, exist_ok=True)
    specs = [make_case(i) for i in range(args.n)]
    logpath = os.path.join(LOGS, "e1a_pilot.jsonl")
    t0 = time.perf_counter()
    npass = nfail = nerr = 0
    with open(logpath, "w") as lf, Pool(args.workers) as pool:
        for res in pool.imap_unordered(run_case, specs):
            lf.write(json.dumps(res) + "\n"); lf.flush()
            if "error" in res: nerr += 1; print("ERR", res["spec"]["idx"], res["error"])
            elif res["pass"]: npass += 1
            else:
                nfail += 1
                print("FAIL", json.dumps(res)[:400])
    print(f"pilot done in {time.perf_counter()-t0:.1f}s: pass={npass} fail={nfail} err={nerr} "
          f"(total={args.n}) log={logpath}")
    sys.exit(0 if (nfail == 0 and nerr == 0) else 1)

if __name__ == "__main__":
    main()
