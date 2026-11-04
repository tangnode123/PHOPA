"""E15: MV (vertical granularity) impact on application inference quality.

Reviewer concern (iter_3 High-Risk #1 / P0): the recommended config MV<=2 may
be too coarse for 3D applications; MV>=3 introduces integer-vs-real semantic
divergence. This experiment runs the E11 semi-real harbor case at MV in
{1,2,3,5} and records, per granularity:

  (a) integer-vs-real elevation-sector divergence rate over all one_sided3d
      labels derived from the TRUE layout (real-valued reference uses exact
      sqrt/tan, no isqrt floor and no fixed-point TB rounding);
  (b) T1 consistency verdict (unique valid model?);
  (c) T2 fault-localization correctness (does the optimum drop exactly the
      corrupted perception?);
  (d) T3 missing-position candidate-set size (does finer MV shrink it?);
  (e) T5 disjunctive-perception discrimination (ghost excluded?).

The point is to show WHERE the MV<=2 recommendation comes from: coarser MV
loses discriminative power (larger candidate sets), finer MV gains little but
introduces boundary divergence. Log: ../logs/e15_mv.json
"""
import json, math, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import e11_case
from e11_case import (OBJ, EXT, true_layout, build_constraints, derive_os3d,
                      task_facts, run_task, GHOST_27)
from hopa3d import elev_sector
from math import isqrt

LOG = os.path.join(HERE, "..", "logs", "e15_mv.json")
MVS = [1, 2, 3, 5]


def real_elev_sector(dz, dx, dy, mv):
    """Exact real-valued elevation sector (no isqrt floor, no TB rounding).
    Mirrors elev_sector's linear/angular partition with real arithmetic."""
    q = math.sqrt(dx * dx + dy * dy)
    if q == 0:
        if dz > 0: return 2 * mv
        if dz < 0: return 0
        return None
    w = 90.0 / mv
    for j in range(0, 2 * mv + 1):
        if j % 2 == 0:
            if j == 0 or j == 2 * mv: continue
            c = -90.0 + j * w
            if abs(dz - math.tan(math.radians(c)) * q) < 1e-9: return j
        else:
            clo = -90.0 + (j - 1) * w
            chi = -90.0 + (j + 1) * w
            lo = math.tan(math.radians(clo))
            hi = math.tan(math.radians(chi))
            if dz > lo * q and dz < hi * q: return j
    return None


def divergence_for_mv(mv):
    """Over the TRUE harbor layout, derive every one_sided3d elevation label
    with (i) canonical integer semantics and (ii) real-valued reference; report
    disagreement count/rate and max |angle error| at boundaries."""
    e11_case.META = dict(sx=50, sy=50, sz=24, mh=2, mv=mv, ra=3, re=3)
    L = true_layout()
    # scan ALL ordered object pairs (representative, not just the 10 observed)
    ks = sorted(OBJ.keys())
    pairs = [(K, V) for K in ks for V in ks if K != V]
    n = 0; dis = 0; details = []
    for (K, V) in pairs:
        dx, dy, dz, q, dsq, az = L.geom(K, V)   # vector V->K
        if dz == 0 and q == 0: continue          # coincident: undefined
        n += 1
        j_int = elev_sector(dz, q, mv, L.tb)               # integer (isqrt q, TB)
        j_real = real_elev_sector(dz, dx, dy, mv)          # exact
        if j_int != j_real:
            dis += 1
            if len(details) < 8:
                details.append(dict(K=K, V=V, dz=dz, q_int=q,
                                    q_real=round(math.sqrt(dx*dx+dy*dy), 3),
                                    j_int=j_int, j_real=j_real))
    return dict(mv=mv, n_pairs=n, n_diverge=dis,
                rate=round(dis / max(1, n), 4), details=details)


def run_case_for_mv(mv):
    e11_case.META = dict(sx=50, sy=50, sz=24, mh=2, mv=mv, ra=3, re=3)
    L = true_layout()
    cs = build_constraints(L)
    out = dict(mv=mv, n_con=len(cs))

    # T1 consistency
    (f1, k1), = [task_facts(L, cs, "T1")]
    r1 = run_task("T1", f1, k1, e11_case.META, max_models=50, timeout=120.0)
    out["T1_n_models"] = r1["n_models"]
    out["T1_unique_valid"] = (r1["n_valid"] == 1 and r1["n_models"] == 1)

    # T2 fault localization
    (f2, k2), cid = task_facts(L, cs, "T2")
    r2 = run_task("T2", f2, k2, e11_case.META, corrupt_id=cid, max_models=50, timeout=120.0)
    out["T2_corrupt_id"] = cid
    out["T2_drops"] = r2["drops"]
    out["T2_localized_correctly"] = (r2["drops"] and all(d == [cid] for d in r2["drops"])
                                     and r2["n_valid"] == r2["n_optimal"] and r2["n_optimal"] >= 1)

    # T3 missing position (ship_transit 21)
    (f3, k3), = [task_facts(L, cs, "T3")]
    r3 = run_task("T3", f3, k3, e11_case.META, max_models=3000, timeout=180.0)
    out["T3_n_cand_pos_21"] = r3.get("n_cand_pos_21", 0)
    out["T3_true_in_cand"] = (OBJ[21][1] in set(map(tuple, r3.get("cand_pos_21", []))))

    # T5 disjunctive perception (small_boat 27 vs ghost)
    (f5, k5), = [task_facts(L, cs, "T5")]
    r5 = run_task("T5", f5, k5, e11_case.META, max_models=3000, timeout=180.0)
    out["T5_n_cand_pos_27"] = r5.get("n_cand_pos_27", 0)
    out["T5_chosen"] = r5.get("chosen", [])
    ghost_in = GHOST_27 in set(map(tuple, r5.get("cand_pos_27", [])))
    out["T5_ghost_excluded"] = (not ghost_in)
    return out


def main():
    res = dict(mvs=MVS, divergence=[], cases=[])
    for mv in MVS:
        d = divergence_for_mv(mv)
        res["divergence"].append(d)
        print(f"[MV={mv}] divergence {d['n_diverge']}/{d['n_pairs']} "
              f"({d['rate']*100:.1f}%)", flush=True)
    for mv in MVS:
        c = run_case_for_mv(mv)
        res["cases"].append(c)
        print(f"[MV={mv}] T1uniq={c['T1_unique_valid']} "
              f"T2ok={c['T2_localized_correctly']} "
              f"T3cand={c['T3_n_cand_pos_21']} "
              f"T5cand={c['T5_n_cand_pos_27']} ghostExcl={c['T5_ghost_excluded']}",
              flush=True)
    with open(LOG, "w") as f:
        json.dump(res, f, indent=1)
    print("E15 done ->", LOG, flush=True)


if __name__ == "__main__":
    main()
