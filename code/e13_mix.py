"""E13: constraint-type mix robustness sweep.

Reviewer concern: performance conclusions may depend on the generator's
default constraint-type mix (one_sided3d ~40%). Sweep four mixes
(vertical-heavy / distance-heavy / azimuth-heavy / default-mixed) at fixed
cell (N=40, S=30, density 1.5N), naive vs proj, 3 seeds, consistent mode.

Records realized constraint-type histogram per instance and need_vec pair
count. Log: ../logs/e13_mix.jsonl
"""
import argparse, json, math, os, subprocess, sys, time
from multiprocessing import Pool
import hopa3d

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "e13")
LOG = os.path.join(HERE, "..", "logs", "e13_mix.jsonl")
TIMEOUT = 120.0
VARIANTS = ["proj", "naive"]
S, N_OBJ, DENS = 30, 40, 1.5
VEC_CONSUMERS = {"one_sided3d", "dist_rel", "distance", "distance_sq",
                 "distance_range", "azim", "azim_range"}

MIXES = {
    "mixed": None,  # generator default TYPE_W
    "vertical_heavy": [
        ("one_sided3d", 70), ("dist_rel", 8), ("distance_range", 5),
        ("distance", 4), ("location", 5), ("direction", 2),
        ("direction_range", 2), ("pitch", 1), ("pitch_range", 1),
        ("azim", 1), ("azim_range", 1)],
    "distance_heavy": [
        ("one_sided3d", 8), ("dist_rel", 30), ("distance_range", 25),
        ("distance", 15), ("location", 8), ("direction", 4),
        ("direction_range", 3), ("pitch", 3), ("pitch_range", 2),
        ("azim", 1), ("azim_range", 1)],
    "azimuth_heavy": [
        ("one_sided3d", 4), ("dist_rel", 3), ("distance_range", 4),
        ("distance", 2), ("location", 8), ("direction", 25),
        ("direction_range", 20), ("pitch", 8), ("pitch_range", 8),
        ("azim", 10), ("azim_range", 10)],
}


def run_one(spec):
    mix_name, seed_idx = spec
    mix_off = {"mixed": 0, "vertical_heavy": 1, "distance_heavy": 2,
               "azimuth_heavy": 3}[mix_name]
    seed = 1130000 + seed_idx * 71 + mix_off * 100003
    n_con = max(1, int(round(DENS * N_OBJ)))
    tag = f"e13_{mix_name}_r{seed_idx}"
    meta_out = dict(cell=f"{N_OBJ}x{S}", n_obj=N_OBJ, s=S, mix=mix_name,
                    dens=DENS, n_con=n_con, seed=seed, seed_idx=seed_idx,
                    mode="consistent")
    try:
        L, cs, meta = hopa3d.gen_instance(seed=seed, n_obj=N_OBJ, n_con=n_con,
                                          s=S, mh=2, mv=2, ra=3, re=3, emax=0,
                                          mode="consistent", pct_disj=0.0,
                                          n_disj=0, type_w=MIXES[mix_name])
        ok, bad = hopa3d.check_all(cs, L)
        meta_out["gen_selfcheck"] = ok
        if not ok:
            meta_out["gen_bad"] = str(bad)[:200]
            return [meta_out]
        types = {}
        pairs = set()
        for c in cs:
            t = str(c.get("t", "?"))
            types[t] = types.get(t, 0) + 1
            if t in VEC_CONSUMERS and "k" in c and "l" in c:
                pairs.add((c["k"], c["l"]))
        meta_out["con_types"] = types
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
    for suf in ("_inst.lp", "_geom.lp"):
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
    specs = [(m, r) for m in MIXES for r in range(a.seeds)]
    print(f"E13: {len(specs)} specs x {len(VARIANTS)} variants -> {LOG}", flush=True)
    t0 = time.perf_counter()
    done = 0
    with open(LOG, "a") as f:
        with Pool(a.workers) as pool:
            for rows in pool.imap_unordered(run_one, specs):
                for r in rows:
                    f.write(json.dumps(r) + "\n")
                f.flush()
                done += 1
                print(f"[{done}/{len(specs)}] {rows[0].get('mix')} "
                      f"seed_idx={rows[0].get('seed_idx')} "
                      f"({time.perf_counter()-t0:.0f}s)", flush=True)
    print("E13 done", time.perf_counter() - t0, flush=True)


if __name__ == "__main__":
    main()
