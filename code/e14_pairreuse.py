"""E14: high pair-reuse workload (the n/p > 2 regime E9b never reached).

E9b increased DENSITY but random pair sampling kept constraints-per-pair n/p at
1.5-1.8, so the "share-but-don't-decompose" baseline (naive_shared) never got a
fair chance: sharing only pays when n/p exceeds ~2 (naive materializes n full
S^3 joins; naive_shared materializes 2p). This experiment fixes a SMALL pair set
and stacks r constraints on each pair, sweeping r = n/p in {2,4,8}, to test:

  - naive_shared vs naive: sharing should start winning at r >= 4;
  - proj vs both: projection decomposition (no S^3 term at all) should stay on
    top regardless of reuse, because it removes the dominant cost rather than
    amortizing it.

Design: S=30, n_obj=12, p=12 distinct ordered pairs sampled over the 12 objects
(objects recur across pairs -> genuine reuse), r constraints/pair from a
vector-consuming mix, consistent mode, 3 seeds. Variants: naive, naive_shared,
proj. Log: ../logs/e14_pairreuse.jsonl
"""
import argparse, json, os, random, subprocess, sys, time
from multiprocessing import Pool
import hopa3d
from hopa3d import Layout

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "e14")
LOG = os.path.join(HERE, "..", "logs", "e14_pairreuse.jsonl")
TIMEOUT = 150.0
VARIANTS = ["naive", "naive_shared", "proj"]
RATIOS = [2, 4, 8]                 # r = constraints per pair = n/p
S = 30
N_OBJ = 12
N_PAIRS = 12
# vector-consuming mix so n/p drives the S^3 grounding cost
MIX = ["one_sided3d", "dist_rel", "distance_range", "azim_range",
       "one_sided3d", "dist_rel"]
VEC_CONSUMERS = {"one_sided3d", "dist_rel", "distance", "distance_sq",
                 "distance_range", "azim", "azim_range"}


def gen_pairreuse(seed, s, n_obj, n_pairs, r):
    """Small pair set, r vector constraints stacked per pair -> n/p ~ r."""
    rng = random.Random(seed)
    L = Layout(s, s, s, 2, 2, 3, 3)
    Ks = list(range(1, n_obj + 1))
    for k in Ks:
        for _ in range(2000):
            x, y, z = rng.randint(1, s), rng.randint(1, s), rng.randint(1, s)
            if all((x, y, z) != L.pos[k2] for k2 in L.pos):
                break
        L.pos[k] = (x, y, z); L.ext[k] = (0, 0, 0)
        L.yaw[k] = rng.randrange(0, 360, 3)
        L.pitch[k] = rng.randrange(-90, 91, 3)
    pairs = set()
    guard = 0
    while len(pairs) < n_pairs and guard < 10000:
        guard += 1
        a, b = rng.sample(Ks, 2)
        pairs.add((a, b))
    pairs = sorted(pairs)
    cs = []; nid = 0
    for (k, l) in pairs:
        for j in range(r):
            t = MIX[j % len(MIX)]
            nid += 1
            c = hopa3d._make_basic(rng, L, nid, t, k, l, "consistent")
            if c is None:
                c = hopa3d._make_basic(rng, L, nid, "dist_rel", k, l, "consistent")
            if c is not None:
                cs.append(c)
    meta = dict(seed=seed, n_obj=n_obj, n_con=len(cs), sx=s, sy=s, sz=s,
                mh=2, mv=2, ra=3, re=3, emax=0, mode="consistent",
                pct_disj=0.0, n_disj=0)
    return L, cs, meta, len(pairs)


def run_one(spec):
    r, seed_idx = spec
    seed = 1140000 + seed_idx * 97 + r * 10007
    tag = f"e14_r{r}_s{S}_r{seed_idx}"
    meta_out = dict(cell=f"r{r}", ratio=r, s=S, n_obj=N_OBJ, n_pairs_target=N_PAIRS,
                    seed=seed, seed_idx=seed_idx, mode="consistent")
    try:
        L, cs, meta, npairs = gen_pairreuse(seed, S, N_OBJ, N_PAIRS, r)
        ok, bad = hopa3d.check_all(cs, L)
        meta_out["gen_selfcheck"] = ok
        if not ok:
            meta_out["gen_bad"] = str(bad)[:200]
            return [meta_out]
        pairs = set()
        for c in cs:
            t = c.get("t")
            if t in VEC_CONSUMERS and "k" in c and "l" in c:
                pairs.add((c["k"], c["l"]))
        meta_out["n_con"] = len(cs)
        meta_out["n_pairs"] = len(pairs)
        meta_out["realized_np"] = round(len(cs) / max(1, len(pairs)), 2)
        base = os.path.join(DATA, tag)
        hopa3d.save_instance(base, L, cs, meta)
    except MemoryError:
        meta_out["gen"] = "MEMKILL"
        return [meta_out]

    rows = []
    for v in VARIANTS:
        enc = os.path.join(HERE, v + ".lp")
        cmd = [sys.executable, os.path.join(HERE, "ablate_one.py"),
               "--inst", base + "_inst.lp", "--geom", base + "_geom.lp",
               "--enc", enc, "--timeout", str(TIMEOUT), "--memlimit-gb", "3"]
        row = dict(meta_out); row["variant"] = v
        try:
            p = subprocess.run(cmd, capture_output=True, text=True,
                               timeout=TIMEOUT + 90)
            last = p.stdout.strip().splitlines()[-1] if p.stdout.strip() else None
            if last:
                row.update(json.loads(last))
            else:
                row.update(verdict="SUBPROC_FAIL", stderr=p.stderr.strip()[-200:])
        except subprocess.TimeoutExpired:
            row.update(verdict="HARD_TIMEOUT")
        except Exception as e:
            row.update(verdict="DRIVER_ERROR", err=str(e)[:200])
        row.pop("inst", None); row.pop("enc", None)
        rows.append(row)
    for suf in ("_inst.lp", "_geom.lp"):
        pth = base + suf
        if os.path.exists(pth):
            os.remove(pth)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    os.makedirs(DATA, exist_ok=True)
    specs = [(r, si) for r in RATIOS for si in range(a.seeds)]
    print(f"E14: {len(specs)} specs x {len(VARIANTS)} variants -> {LOG}", flush=True)
    t0 = time.perf_counter(); done = 0
    with open(LOG, "a") as f:
        with Pool(a.workers) as pool:
            for rows in pool.imap_unordered(run_one, specs):
                for rr in rows:
                    f.write(json.dumps(rr) + "\n")
                f.flush(); done += 1
                print(f"[{done}/{len(specs)}] {rows[0].get('cell')} "
                      f"np={rows[0].get('realized_np')} "
                      f"({time.perf_counter()-t0:.0f}s)", flush=True)
    print("E14 done", time.perf_counter() - t0, flush=True)


if __name__ == "__main__":
    main()
