"""E8: P1/P2/P3 ablation with ground-size and memory instrumentation.

For each cell (S,N) x seed: generate ONE instance (consistent mode), then run
all 6 encodings on it in fresh subprocesses (ablate_one.py) so that peak RSS
and ground statistics are clean per variant.

Encodings: proj, naive (P1+P2+P3 all removed), naive_p1 (only P1 kept),
naive_p2 (only P2), naive_p3 (only P3), naive_p23 (P2+P3 kept).

Log: ../logs/e8_ablation.jsonl  (one line per (cell,seed,variant))
"""
import argparse, json, math, os, subprocess, sys, time
from multiprocessing import Pool
import hopa3d

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "e8")
LOG = os.path.join(HERE, "..", "logs", "e8_ablation.jsonl")
TIMEOUT = 120.0
VARIANTS = ["proj", "naive_p1", "naive_p2", "naive_p3", "naive_p23", "naive"]

# (S, N) cells: reviewer asked for S=20/30 x N=40/80/100 plus large-grid probes
CELLS = [(20, 40), (20, 80), (20, 100), (30, 40), (30, 80), (30, 100),
         (40, 40), (40, 60)]


def run_one(spec):
    s, n_obj, seed_idx = spec
    seed = 810000 + seed_idx * 61
    tag = f"e8_N{n_obj}_s{s}_r{seed_idx}"
    n_con = math.ceil(1.5 * n_obj)
    meta_out = dict(cell=f"{n_obj}x{s}", n_obj=n_obj, s=s, seed=seed,
                    seed_idx=seed_idx, mode="consistent", n_con=n_con)
    try:
        L, cs, meta = hopa3d.gen_instance(seed=seed, n_obj=n_obj, n_con=n_con,
                                          s=s, mh=2, mv=2, ra=3, re=3, emax=0,
                                          mode="consistent", pct_disj=0.0, n_disj=0)
        ok, bad = hopa3d.check_all(cs, L)
        meta_out["gen_selfcheck"] = ok
        if not ok:
            meta_out["gen_bad"] = str(bad)[:200]
            return [meta_out]
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
    for suf in ("_inst.lp", "_geom.lp"):
        p = base + suf
        if os.path.exists(p):
            os.remove(p)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=4)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--cells", default=None, help="NxS,NxS override")
    a = ap.parse_args()
    os.makedirs(DATA, exist_ok=True)
    cells = CELLS
    if a.cells:
        cells = []
        for c in a.cells.split(","):
            n, s = (int(v) for v in c.split("x"))
            cells.append((s, n))
    specs = [(s, n, r) for (s, n) in cells for r in range(a.seeds)]
    print(f"E8: {len(specs)} specs x {len(VARIANTS)} variants -> {LOG}", flush=True)
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
                      f"seed_idx={rows[0].get('seed_idx')} "
                      f"({time.perf_counter()-t0:.0f}s)", flush=True)
    print("E8 done", time.perf_counter() - t0, flush=True)


if __name__ == "__main__":
    main()
