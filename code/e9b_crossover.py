"""E9b: naive_shared vs naive vs proj crossover sweep.

E9 showed naive_shared (share the full 3-way join per needed pair) is DOMINATED
by naive at the standard density n=ceil(1.5N): it pays p*S^3 twice (v3 and d3)
while naive pays (n_v+n_d)*S^3 inline. Sharing should start paying off only when
constraints-per-pair n/p exceeds ~2. This sweep increases density (and shrinks
N so pairs saturate faster) to locate the crossover empirically -- and to test
whether proj remains on top everywhere (projection decomposition eliminates the
S^3 term regardless of density).

Design: S=20 (naive_shared MEMKILLs at S>=30), N in {20,40},
dens in {1.5,3,5,10} x N, 3 seeds, consistent mode.
Variants: naive, naive_shared, proj.

Log: ../logs/e9b_crossover.jsonl
"""
import argparse, json, math, os, subprocess, sys, time
from multiprocessing import Pool
import hopa3d

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "e9b")
LOG = os.path.join(HERE, "..", "logs", "e9b_crossover.jsonl")
TIMEOUT = 120.0
VARIANTS = ["naive", "naive_shared", "proj"]
DENSITIES = [1.5, 3.0, 5.0, 10.0]
CELLS = [(20, 20), (20, 40)]          # (S, N)
VEC_CONSUMERS = {"one_sided3d", "dist_rel", "distance", "distance_sq",
                 "distance_range", "azim", "azim_range"}


def run_one(spec):
    s, n_obj, dens, seed_idx = spec
    seed = 1090000 + seed_idx * 71 + int(dens * 10) * 1000
    n_con = max(1, int(round(dens * n_obj)))
    tag = f"e9b_N{n_obj}_s{s}_d{dens}_r{seed_idx}"
    meta_out = dict(cell=f"{n_obj}x{s}", n_obj=n_obj, s=s, dens=dens,
                    n_con=n_con, seed=seed, seed_idx=seed_idx,
                    mode="consistent")
    try:
        L, cs, meta = hopa3d.gen_instance(seed=seed, n_obj=n_obj, n_con=n_con,
                                          s=s, mh=2, mv=2, ra=3, re=3, emax=0,
                                          mode="consistent", pct_disj=0.0, n_disj=0)
        ok, bad = hopa3d.check_all(cs, L)
        meta_out["gen_selfcheck"] = ok
        if not ok:
            meta_out["gen_bad"] = str(bad)[:200]
            return [meta_out]
        pairs = set()
        for c in cs:
            t = str(c.get("t", "?")) if isinstance(c, dict) else str(c[0])
            if t in VEC_CONSUMERS and "k" in c and "l" in c:
                pairs.add((c["k"], c["l"]))
        meta_out["n_pairs"] = len(pairs)
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
        row = dict(meta_out)
        row["variant"] = v
        try:
            p = subprocess.run(cmd, capture_output=True, text=True,
                               timeout=TIMEOUT + 90)
            last = p.stdout.strip().splitlines()[-1] if p.stdout.strip() else None
            if last:
                row.update(json.loads(last))
            else:
                row.update(verdict="SUBPROC_FAIL",
                           stderr=p.stderr.strip()[-200:])
        except subprocess.TimeoutExpired:
            row.update(verdict="HARD_TIMEOUT")
        except Exception as e:
            row.update(verdict="DRIVER_ERROR", err=str(e)[:200])
        row.pop("inst", None); row.pop("enc", None)
        rows.append(row)
    for suf in ("_inst.lp", "__geom.lp", "_geom.lp"):
        p = base + suf
        if os.path.exists(p):
            os.remove(p)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    os.makedirs(DATA, exist_ok=True)
    specs = [(s, n, d, r) for (s, n) in CELLS for d in DENSITIES
             for r in range(a.seeds)]
    print(f"E9b: {len(specs)} specs x {len(VARIANTS)} variants -> {LOG}", flush=True)
    t0 = time.perf_counter()
    done = 0
    with open(LOG, "a") as f:
        with Pool(a.workers) as pool:
            for rows in pool.imap_unordered(run_one, specs):
                for r in rows:
                    f.write(json.dumps(r) + "\n")
                f.flush()
                done += 1
                print(f"[{done}/{len(specs)}] {rows[0].get('cell')} "
                      f"d={rows[0].get('dens')} seed_idx={rows[0].get('seed_idx')} "
                      f"({time.perf_counter()-t0:.0f}s)", flush=True)
    print("E9b done", time.perf_counter() - t0, flush=True)


if __name__ == "__main__":
    main()
