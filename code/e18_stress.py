"""E18: NON-CIRCULAR stress test of the E11 harbor case (iter_4 Critical #4).

Reviewer concern: E11 derives constraints from a true layout then recovers that
layout -- internally consistent but externally weak. A credible spatial task must
degrade gracefully under realistic noise: missing observations, faulty labels,
multiple simultaneous errors. E18 perturbs the INPUT constraint set randomly
(seeded, NOT derived from the layout) and measures the framework against ground
truth.

Part A -- multi-error fault localization (layout anchored by mandatory surveyed
  infrastructure). ALL perception constraints (one_sided3d / dist_rel /
  azim_range / distance_range) are made defeasible (droppable); world knowledge
  (location / direction / min_gap) is mandatory. We randomly corrupt k in {1,2,3}
  perceptions and run explain_mode (optN, minimize drops). Metrics: precision,
  recall, exact-match rate of the optimal drop set vs the truly-corrupted ids,
  minimal repair size, solve time. The solver must IDENTIFY which k of the ~22
  droppable perceptions to drop -- a genuine search, not a forced answer.

Part A2 -- identifiability probe. Same as A with k=1, but the target object's
  position is ALSO freed (toinfer_pos). Tests whether a single faulty bearing is
  still localized, or absorbed by relocating the now-free object (cost-0). This
  is an honest probe of WHEN fault localization is identifiable.

Part B -- missing-position inference under random observation dropout. The transit
  ship's location is removed (toinfer_pos); additionally a random x% of the other
  perceptions is dropped (x in {0,25,50}). Metrics: candidate-set size and
  true-position coverage (is ground truth still among the inferred candidates?).
  Pure dropout cannot exclude the true layout, so coverage should stay 100% while
  the candidate set grows -- graceful degradation.

Grid/qualitative resolution variation is covered by E15 (MV sweep on this same
harbor case) and E1b (S in {20,30,40,50}); E18 holds the recommended config
(MH=MV=2, RA=RE=3, S=50x50x24) and varies the OBSERVATION quality instead.

Log: ../logs/e18_stress.json
"""
import json, os, random, re, sys, time
from math import isqrt
import clingo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hopa3d
from hopa3d import emit_facts, check_all
import e11_case
from e11_case import (OBJ, EXT, META, true_layout, build_constraints,
                      emit_min_gap, GHOST_27)
from e4_scenarios import geom_tables, model_layout

LOG = os.path.join(HERE, "..", "logs", "e18_stress.json")
PERC_TYPES = {"one_sided3d", "dist_rel", "azim_range", "distance_range"}
WORLD_TYPES = {"location", "direction", "min_gap", "pitch"}
BANDS = ["very_near", "near", "mid", "far", "very_far"]
TIMEOUT = 120.0


# ---------------- corruption model (realistic sensor error) ----------------

def corrupt(c, mh, rng):
    """Return a copy of perception constraint c with a faulty label that is
    guaranteed inconsistent with the true layout (layout is anchored)."""
    c = dict(c)
    t = c["t"]
    if t == "one_sided3d":
        # shift horizontal sector by 1..3 (of 4*mh=8) -> always a different sector
        c["i"] = (c["i"] + rng.choice([1, 2, 3])) % (4 * mh)
    elif t == "dist_rel":
        i = BANDS.index(c["u"])
        c["u"] = BANDS[(i + rng.choice([1, 2])) % len(BANDS)]
    elif t == "azim_range":
        sh = rng.choice([60, 90, 120])       # push true bearing outside window
        c["a1"] = (c["a1"] + sh) % 360
        c["a2"] = (c["a2"] + sh) % 360
    elif t == "distance_range":
        sh = rng.choice([6, 9, 12])          # push true range outside window
        c["d1"] = c["d1"] + sh
        c["d2"] = c["d2"] + sh
    return c


def assemble(cs, faulty_ids, mh, rng, free_pos=None):
    """Mark world knowledge mandatory, corrupt the chosen perceptions, optionally
    free one object's position (toinfer). Returns (facts, observed_cs)."""
    cs2 = []
    for c in cs:
        c = dict(c)
        if c["t"] in WORLD_TYPES:
            c["mandatory"] = True
        if c["n"] in faulty_ids:
            c = corrupt(c, mh, rng)
            c.pop("mandatory", None)         # faulty perceptions stay droppable
        cs2.append(c)
    extra = ["explain_mode."]
    if free_pos is not None:
        # remove the location fact of free_pos and ask to infer it
        loc_id = next(c["n"] for c in cs2
                      if c["t"] == "location" and c["k"] == free_pos)
        cs2 = [c for c in cs2 if c["n"] != loc_id]
        extra.append(f"toinfer_pos({free_pos}).")
    base = emit_facts(e11_case.true_layout(),
                      [c for c in cs2 if c["t"] != "min_gap"], META)
    base += emit_min_gap([c for c in cs2 if c["t"] == "min_gap"])
    base += "\n".join(extra) + "\n"
    return base, cs2


# ---------------- explain-mode runner (full optimal drop sets) -------------

def run_explain(facts, observed, faulty_ids, meta, max_models=200):
    t0 = time.perf_counter()
    ctl = clingo.Control(["--configuration=auto", "--models=0", "--opt-mode=optN"])
    enc = open(os.path.join(HERE, "proj.lp")).read()
    ctl.add("base", [], facts + geom_tables(meta) + enc)
    ctl.add("base", [], "#show drop/1. #show violated/1. #show xloc/2. "
                        "#show yloc/2. #show zloc/2.")
    ctl.ground([("base", [])])
    t_ground = time.perf_counter() - t0
    models, costs = [], []
    t1 = time.perf_counter()
    exhausted = False
    with ctl.solve(yield_=True, async_=True) as h:
        while len(models) < max_models:
            rem = TIMEOUT - (time.perf_counter() - t1)
            if rem <= 0 or not h.wait(max(rem, 0.0)):
                h.cancel(); h.wait(None); break
            m = h.model()
            if m is None:
                exhausted = True; break
            atoms = sorted(str(s) for s in m.symbols(shown=True))
            models.append(atoms)
            costs.append(list(m.cost))
            h.resume()
    t_solve = time.perf_counter() - t1
    # optimal models only
    best = min(c for c in costs if c) if costs else None
    opt = [i for i, c in enumerate(costs) if c == best]
    drop_sets = []
    for i in opt:
        d = {int(x) for x in (a[5:-1] for a in models[i] if a.startswith("drop("))}
        v = {int(x) for x in (a[9:-1] for a in models[i] if a.startswith("violated("))}
        drop_sets.append(sorted(d | v))     # repair = dropped or violated
    # precision / recall per optimal model, vs truly-faulty ids
    pr = []
    for ds in drop_sets:
        tp = len(set(ds) & faulty_ids)
        prec = tp / len(ds) if ds else (1.0 if not faulty_ids else 0.0)
        rec = tp / len(faulty_ids) if faulty_ids else 1.0
        pr.append((prec, rec, set(ds) == faulty_ids))
    return dict(n_models=len(models), n_optimal=len(opt), exhausted=exhausted,
                best_cost=best, t_ground=round(t_ground, 2),
                t_solve=round(t_solve, 2), drop_sets=drop_sets[:8],
                pr=pr[:8])


def agg_pr(pr_list):
    """Aggregate precision/recall/exact over all optimal models of all seeds."""
    allpr = [t for run in pr_list for t in run]
    if not allpr:
        return dict(precision=None, recall=None, exact_rate=None)
    p = sum(x[0] for x in allpr) / len(allpr)
    r = sum(x[1] for x in allpr) / len(allpr)
    e = sum(1 for x in allpr if x[2]) / len(allpr)
    return dict(precision=round(p, 3), recall=round(r, 3), exact_rate=round(e, 3))


# ---------------- Part A: multi-error fault localization ------------------

def part_A(nseeds):
    L = true_layout()
    cs = build_constraints(L)
    perc = [c for c in cs if c["t"] in PERC_TYPES]
    out = []
    for k in (1, 2, 3):
        for si in range(nseeds):
            rng = random.Random(18000 + k * 100 + si)
            faulty = rng.sample(perc, k)
            faulty_ids = {c["n"] for c in faulty}
            facts, obs = assemble(cs, faulty_ids, META["mh"], rng)
            r = run_explain(facts, obs, faulty_ids, META)
            rec = dict(k=k, seed=si, faulty_ids=sorted(faulty_ids),
                       faulty_types=[c["t"] for c in faulty],
                       best_cost=r["best_cost"], n_optimal=r["n_optimal"],
                       t_solve=r["t_solve"], drop_sets=r["drop_sets"],
                       pr=r["pr"])
            out.append(rec)
            print(f"[A k={k} seed={si}] faulty={sorted(faulty_ids)} "
                  f"cost={r['best_cost']} nopt={r['n_optimal']} "
                  f"drops={r['drop_sets'][:2]} t={r['t_solve']}s", flush=True)
    return out


# ---------------- Part A2: identifiability probe (one position free) -------

def part_A2(nseeds):
    L = true_layout()
    cs = build_constraints(L)
    # corrupt a perception whose TARGET is a moving object we then free
    out = []
    targets = [21, 27, 20]      # ship_transit, small_boat, ship_inbound
    for si in range(nseeds):
        rng = random.Random(18500 + si)
        tgt = targets[si % len(targets)]
        # perceptions constraining tgt
        cand = [c for c in cs if c["t"] in PERC_TYPES and c.get("k") == tgt]
        if not cand:
            continue
        faulty = [rng.choice(cand)]
        faulty_ids = {c["n"] for c in faulty}
        facts, obs = assemble(cs, faulty_ids, META["mh"], rng, free_pos=tgt)
        r = run_explain(facts, obs, faulty_ids, META)
        localized = any(set(ds) == faulty_ids for ds in r["drop_sets"])
        absorbed = any(len(ds) == 0 for ds in r["drop_sets"])
        rec = dict(seed=si, freed=tgt, faulty_ids=sorted(faulty_ids),
                   best_cost=r["best_cost"], n_optimal=r["n_optimal"],
                   drop_sets=r["drop_sets"], localized=localized,
                   absorbed=absorbed, t_solve=r["t_solve"])
        out.append(rec)
        print(f"[A2 seed={si} free={tgt}] cost={r['best_cost']} "
              f"localized={localized} absorbed={absorbed} "
              f"drops={r['drop_sets'][:3]}", flush=True)
    return out


# ---------------- Part B: dropout robustness (missing position) -----------

def part_B(nseeds):
    L = true_layout()
    cs = build_constraints(L)
    true_pos = OBJ[21][1]
    out = []
    for pct in (0, 20, 40):
        for si in range(nseeds):
            rng = random.Random(18800 + pct * 10 + si)
            # remove location of 21 -> toinfer; randomly drop pct% of ALL
            # perceptions (faithful "random observation dropout": on average
            # pct% of the bearings/ranges that pin object 21 are also lost, so
            # its candidate set should widen while ground truth is retained)
            perc_all = [c for c in cs if c["t"] in PERC_TYPES]
            ndrop = int(round(len(perc_all) * pct / 100.0))
            dropped = {c["n"] for c in rng.sample(perc_all, ndrop)} if ndrop else set()
            loc21 = next(c["n"] for c in cs if c["t"] == "location" and c["k"] == 21)
            cs2 = [dict(c) for c in cs
                   if c["n"] != loc21 and c["n"] not in dropped]
            for c in cs2:
                if c["t"] in WORLD_TYPES:
                    c["mandatory"] = True
            base = emit_facts(L, [c for c in cs2 if c["t"] != "min_gap"], META)
            base += emit_min_gap([c for c in cs2 if c["t"] == "min_gap"])
            base += "toinfer_pos(21).\n"
            # enumerate candidate positions for 21
            t0 = time.perf_counter()
            ctl = clingo.Control(["--configuration=auto", "--models=0"])
            enc = open(os.path.join(HERE, "proj.lp")).read()
            ctl.add("base", [], base + geom_tables(META) + enc)
            ctl.add("base", [], "#show inferred_pos/4.")
            ctl.ground([("base", [])])
            cand = set()
            nm = 0
            t1 = time.perf_counter()
            with ctl.solve(yield_=True, async_=True) as h:
                while nm < 4000:
                    rem = TIMEOUT - (time.perf_counter() - t1)
                    if rem <= 0 or not h.wait(max(rem, 0.0)):
                        h.cancel(); h.wait(None); break
                    m = h.model()
                    if m is None:
                        break
                    nm += 1
                    for a in m.symbols(shown=True):
                        mm = re.match(r"inferred_pos\(21,(-?\d+),(-?\d+),(-?\d+)\)", str(a))
                        if mm:
                            cand.add((int(mm.group(1)), int(mm.group(2)), int(mm.group(3))))
                    h.resume()
            t_solve = time.perf_counter() - t1
            rec = dict(pct=pct, seed=si, n_dropped=ndrop, n_models=nm,
                       n_cand=len(cand), true_in_cand=(true_pos in cand),
                       t_solve=round(t_solve, 2))
            out.append(rec)
            print(f"[B pct={pct} seed={si}] dropped={ndrop} cand={len(cand)} "
                  f"true_in={true_pos in cand} models={nm} t={rec['t_solve']}s",
                  flush=True)
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=4)
    a = ap.parse_args()
    res = dict(meta=META, n_obj=len(OBJ), seeds=a.seeds)
    print("=== E18 Part A: multi-error fault localization ===", flush=True)
    A = part_A(a.seeds)
    res["A"] = A
    res["A_agg"] = {k: agg_pr([r["pr"] for r in A if r["k"] == k]) for k in (1, 2, 3)}
    print("A aggregate:", json.dumps(res["A_agg"]), flush=True)

    print("=== E18 Part A2: identifiability probe ===", flush=True)
    A2 = part_A2(a.seeds)
    res["A2"] = A2
    res["A2_summary"] = dict(
        n=len(A2),
        localized=sum(1 for r in A2 if r["localized"]),
        absorbed=sum(1 for r in A2 if r["absorbed"]))
    print("A2 summary:", json.dumps(res["A2_summary"]), flush=True)

    print("=== E18 Part B: dropout robustness ===", flush=True)
    B = part_B(a.seeds)
    res["B"] = B
    byp = {}
    for pct in (0, 20, 40):
        rows = [r for r in B if r["pct"] == pct]
        if rows:
            cands = sorted(r["n_cand"] for r in rows)
            byp[pct] = dict(median_cand=cands[len(cands) // 2],
                            coverage=sum(1 for r in rows if r["true_in_cand"]) / len(rows),
                            n=len(rows))
    res["B_summary"] = byp
    print("B summary:", json.dumps(byp), flush=True)

    with open(LOG, "w") as f:
        json.dump(res, f, indent=1)
    print("E18 done ->", LOG, flush=True)


if __name__ == "__main__":
    main()
