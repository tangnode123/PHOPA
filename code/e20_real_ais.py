"""E20: REAL-DATA 2.5D harbor case study from NOAA MarineCadastre AIS.

Addresses the external-validity gap (a real, non-handcrafted spatial dataset).
Pipeline: real vessel positions/headings (NY Harbor, 2023-01-01 05:20 UTC) ->
equirectangular projection to a square metric grid -> discretize to integer cells
-> derive the SAME hybrid constraint language (location anchors, direction/yaw,
pairwise one_sided3d horizontal-sector + distance_range + dist_rel + azim_range)
from the REAL geometry -> inject realistic AIS error (gross bearing/range faults,
GPS cell jitter, observation dropout) -> run consistency audit, multi-error fault
localization (precision/recall vs ground truth), and missing-position candidate
inference (true-cell coverage + candidate-set size) with the proj.lp ASP encoding.

Honest scope: surface AIS carries NO altitude, so all vessels sit at sea level
(z=1, dz=0) -> the elevation sector is the equatorial band J=MV for every pair.
E20 therefore validates the constraint LANGUAGE and the reasoning TASKS on real
2.5D data; the full 3D elevation range and the Theta(S^3) grounding explosion are
exercised by the synthetic 3D benchmarks (E1-E14) and the q=0 audit (E17).

It also reports the REAL constraint distribution (n_obj, n_con, ordered need_vec
pairs p, type mix, location-anchor ratio) next to a size-matched synthetic
instance from hopa3d.gen_instance, to test whether the projection-decomposition
benefit is measured on a representative workload.

Log: ../logs/e20_real_ais.json
"""
import argparse, bisect, csv, json, os, random, re, subprocess, sys, time
from collections import defaultdict
from datetime import datetime
from math import isqrt, cos, radians
import clingo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hopa3d
from hopa3d import (Layout, emit_facts, check_all, horiz_sector, elev_sector,
                    DIST_RELS, U_CODE)
from e4_scenarios import geom_tables

AIS = os.path.join(HERE, "..", "data", "ais", "nybay_slice.csv")
LOG = os.path.join(HERE, "..", "logs", "e20_real_ais.json")
TIMEOUT = 120.0

# --- semantic config (gravity-aligned, yaw-relative; MV=2 -> exactly real-equiv) ---
MH, MV, RA, RE = 3, 2, 3, 3
CELL_M = 200.0          # metric grid cell (~harbor scale)
LAT_REF = 40.68
M_PER_DEG_LAT = 110540.0
M_PER_DEG_LON = 111320.0 * cos(radians(LAT_REF))
BANDS = ["very_near", "near", "mid", "far", "very_far"]
PERC_TYPES = {"one_sided3d", "dist_rel", "azim_range", "distance_range"}
WORLD_TYPES = {"location", "direction"}
T_SNAP = datetime(2023, 1, 1, 5, 20, 27)


# ---------------- real AIS -> snapshot ----------------

def load_snapshot(T=T_SNAP, win=300):
    rows = list(csv.DictReader(open(AIS)))
    for r in rows:
        r["t"] = datetime.strptime(r["BaseDateTime"], "%Y-%m-%dT%H:%M:%S")
    byv = defaultdict(list)
    for r in rows:
        byv[r["MMSI"]].append(r)
    for v in byv:
        byv[v].sort(key=lambda r: r["t"])
    snap = []
    for v, rs in byv.items():
        tl = [r["t"] for r in rs]
        i = bisect.bisect_right(tl, T) - 1
        if i < 0 or (T - tl[i]).total_seconds() > win:
            continue
        lr = rs[i]
        try:
            lat = float(lr["LAT"]); lon = float(lr["LON"])
            sog = float(lr["SOG"]); cog = float(lr["COG"])
        except (ValueError, KeyError):
            continue
        if not (sog > 0.5 and 0.0 <= cog < 360.0):
            continue
        snap.append(dict(mmsi=v, lat=lat, lon=lon, sog=sog, cog=cog,
                         name=lr.get("VesselName", ""), vtype=lr.get("VesselType", "")))
    return snap


def to_grid(snap, cell=CELL_M):
    """Equirectangular projection to a square metric grid; returns (sx, sy, items)
    with items[i] = dict(..., x, y in 1..S)."""
    xs = [(s["lon"]) * M_PER_DEG_LON for s in snap]
    ys = [(s["lat"]) * M_PER_DEG_LAT for s in snap]
    x0, y0 = min(xs), min(ys)
    items = []
    for s, xm, ym in zip(snap, xs, ys):
        gx = int(round((xm - x0) / cell)) + 1
        gy = int(round((ym - y0) / cell)) + 1
        items.append(dict(s, gx=gx, gy=gy))
    sx = max(it["gx"] for it in items)
    sy = max(it["gy"] for it in items)
    return sx, sy, items


def select_distinct(items, sx, sy, max_n=24):
    """Greedy by speed: keep vessels in distinct grid cells (q>0 for all pairs),
    cap at max_n. Returns (vessels, sx2, sy2) re-based to the selected subset."""
    items = sorted(items, key=lambda it: -it["sog"])
    used = set(); sel = []
    for it in items:
        c = (it["gx"], it["gy"])
        if c in used:
            continue
        used.add(c); sel.append(it)
        if len(sel) >= max_n:
            break
    sx = max(it["gx"] for it in sel); sy = max(it["gy"] for it in sel)
    return sel, sx, sy


def build_layout(vessels, sx, sy):
    L = Layout(sx, sy, 1, MH, MV, RA, RE)
    for i, v in enumerate(vessels, start=1):
        L.pos[i] = (v["gx"], v["gy"], 1)
        L.yaw[i] = int(round(((90.0 - v["cog"]) % 360.0) / RA)) * RA % 360
        L.pitch[i] = 0
        L.ext[i] = (0, 0, 0)
        v["k"] = i
    return L


# ---------------- real geometry -> hybrid constraints ----------------

def _knn_edges(L, vessels, knn=2):
    """Symmetrized k-nearest-neighbour undirected edges over grid distance."""
    ks = sorted(L.pos)
    d = {}
    for a in ks:
        for b in ks:
            if a < b:
                dx, dy, dz, q, dsq, az = L.geom(a, b)
                d[(a, b)] = dsq
    neigh = defaultdict(list)
    for a in ks:
        cand = sorted((b for b in ks if b != a),
                      key=lambda b: d[(min(a, b), max(a, b))])
        for b in cand[:knn]:
            neigh[a].append(b)
    edges = set()
    for a, bs in neigh.items():
        for b in bs:
            edges.add((min(a, b), max(a, b)))
    return sorted(edges)


def build_constraints(L, vessels, rng, anchor_frac=0.6, knn=2):
    """Derive the hybrid constraint set from the REAL layout (consistent mode).
    location/direction = mandatory world knowledge; pairwise bearings/ranges =
    defeasible perceptions. Returns (cs, stats)."""
    cs = []; n = 0
    ks = sorted(L.pos)
    # location anchors for a fraction of vessels (the rest are 'unanchored')
    anchored = set(rng.sample(ks, max(2, int(round(len(ks) * anchor_frac)))))
    for k in anchored:
        n += 1; x, y, z = L.pos[k]
        cs.append(dict(n=n, t="location", k=k, x=x, y=y, z=z))
    # direction (yaw) from real COG for every vessel
    for k in ks:
        n += 1
        cs.append(dict(n=n, t="direction", k=k, a=int(L.yaw[k])))
    # pairwise perceptions over the symmetrized kNN graph
    edges = _knn_edges(L, vessels, knn)
    ordered_pairs = set()
    for (a, b) in edges:
        for (k, l) in ((a, b), (b, a)):
            dx, dy, dz, q, dsq, az = L.geom(k, l)   # vector l->k
            if az is None or q == 0:
                continue
            psi = (az - L.yaw[l]) % 360
            I = horiz_sector(psi, L.mh); J = elev_sector(dz, q, L.mv, L.tb)
            if I is None or J is None:
                continue
            n += 1
            cs.append(dict(n=n, t="one_sided3d", k=k, l=l, i=I, j=J))
            ordered_pairs.add((k, l))
            d = isqrt(dsq)
            n += 1
            cs.append(dict(n=n, t="distance_range", k=k, l=l,
                           d1=max(0, d - 1), d2=d + 1))
            ordered_pairs.add((k, l))
        # one qualitative band + one absolute-azimuth window per undirected edge
        dx, dy, dz, q, dsq, az = L.geom(a, b)
        dd = (dsq) ** 0.5
        u = next((nm for nm in BANDS
                  if dd >= DIST_RELS[nm][0] and (DIST_RELS[nm][1] is None
                                                 or dd <= DIST_RELS[nm][1])), None)
        if u is not None:
            n += 1; cs.append(dict(n=n, t="dist_rel", k=a, l=b, u=u))
            ordered_pairs.add((a, b))
        _, _, _, _, _, az2 = L.geom(b, a)   # vector a->b absolute azimuth
        if az2 is not None:
            n += 1
            cs.append(dict(n=n, t="azim_range", k=a, l=b,
                           a1=(az2 - 9) % 360, a2=(az2 + 9) % 360))
            ordered_pairs.add((a, b))
    stats = dict(n_obj=len(ks), n_con=len(cs), p=len(ordered_pairs),
                 n_edges=len(edges), n_anchor=len(anchored),
                 anchor_ratio=round(len(anchored) / len(ks), 3))
    return cs, stats


def type_mix(cs):
    c = defaultdict(int)
    for x in cs:
        c[x["t"]] += 1
    return dict(sorted(c.items()))


# ---------------- realistic AIS error model ----------------

def corrupt(c, rng):
    """Gross fault guaranteed inconsistent with the (anchored) true layout."""
    c = dict(c); t = c["t"]
    if t == "one_sided3d":
        c["i"] = (c["i"] + rng.choice([1, 2, 3, 4])) % (4 * MH)
    elif t == "dist_rel":
        i = BANDS.index(c["u"]); c["u"] = BANDS[(i + rng.choice([1, 2])) % 5]
    elif t == "azim_range":
        sh = rng.choice([60, 90, 120])
        c["a1"] = (c["a1"] + sh) % 360; c["a2"] = (c["a2"] + sh) % 360
    elif t == "distance_range":
        sh = rng.choice([6, 9, 12])
        c["d1"] += sh; c["d2"] += sh
    return c


def assemble(L, cs, faulty_ids, meta, jitter_ids=None, free_pos=None):
    """World knowledge mandatory; corrupt faulty perceptions (kept droppable);
    optionally GPS-jitter some anchors (kept droppable) and free one position."""
    jitter_ids = jitter_ids or set()
    cs2 = []
    for c in cs:
        c = dict(c)
        if c["t"] in WORLD_TYPES:
            c["mandatory"] = True
        if c["n"] in faulty_ids:
            c = corrupt(c, random.Random(c["n"]))
            c.pop("mandatory", None)
        if c["t"] == "location" and c["n"] in jitter_ids:
            x, y, z = L.pos[c["k"]]
            c["x"] = min(meta["sx"], max(1, x + random.Random(c["n"]).choice([-1, 1])))
            c["y"] = min(meta["sy"], max(1, y + random.Random(c["n"] + 7).choice([-1, 1])))
            c.pop("mandatory", None)
        cs2.append(c)
    extra = ["explain_mode."]
    if free_pos is not None:
        loc_id = next((c["n"] for c in cs2 if c["t"] == "location" and c["k"] == free_pos), None)
        cs2 = [c for c in cs2 if c["n"] != loc_id]
        extra.append(f"toinfer_pos({free_pos}).")
    base = emit_facts(L, cs2, meta) + "\n".join(extra) + "\n"
    return base, cs2


# ---------------- explain-mode optimal-repair runner ----------------

def run_explain(facts, faulty_ids, meta, max_models=200):
    t0 = time.perf_counter()
    ctl = clingo.Control(["--configuration=auto", "--models=0", "--opt-mode=optN"])
    enc = open(os.path.join(HERE, "proj.lp")).read()
    ctl.add("base", [], facts + geom_tables(meta) + enc)
    ctl.add("base", [], "#show drop/1. #show violated/1.")
    ctl.ground([("base", [])])
    t_ground = time.perf_counter() - t0
    models, costs = [], []
    t1 = time.perf_counter(); exhausted = False
    with ctl.solve(yield_=True, async_=True) as h:
        while len(models) < max_models:
            rem = TIMEOUT - (time.perf_counter() - t1)
            if rem <= 0 or not h.wait(max(rem, 0.0)):
                h.cancel(); h.wait(None); break
            m = h.model()
            if m is None:
                exhausted = True; break
            models.append(sorted(str(s) for s in m.symbols(shown=True)))
            costs.append(list(m.cost)); h.resume()
    t_solve = time.perf_counter() - t1
    best = min(c for c in costs if c) if costs else None
    opt = [i for i, c in enumerate(costs) if c == best]
    drop_sets = []
    for i in opt:
        d = {int(x) for x in (a[5:-1] for a in models[i] if a.startswith("drop("))}
        v = {int(x) for x in (a[9:-1] for a in models[i] if a.startswith("violated("))}
        drop_sets.append(sorted(d | v))
    pr = []
    for ds in drop_sets:
        tp = len(set(ds) & faulty_ids)
        prec = tp / len(ds) if ds else (1.0 if not faulty_ids else 0.0)
        rec = tp / len(faulty_ids) if faulty_ids else 1.0
        pr.append((prec, rec, set(ds) == faulty_ids))
    return dict(n_models=len(models), n_optimal=len(opt), exhausted=exhausted,
                best_cost=best, t_ground=round(t_ground, 2),
                t_solve=round(t_solve, 2), drop_sets=drop_sets[:8], pr=pr[:8])


def agg_pr(pr_list):
    allpr = [t for run in pr_list for t in run]
    if not allpr:
        return dict(precision=None, recall=None, exact_rate=None)
    return dict(precision=round(sum(x[0] for x in allpr) / len(allpr), 3),
                recall=round(sum(x[1] for x in allpr) / len(allpr), 3),
                exact_rate=round(sum(1 for x in allpr if x[2]) / len(allpr), 3))


# ---------------- Part A: fault localization on real layout ----------------

def part_A(L, cs, meta, nseeds):
    perc = [c for c in cs if c["t"] in PERC_TYPES]
    out = []
    for k in (1, 2, 3):
        for si in range(nseeds):
            rng = random.Random(20000 + k * 100 + si)
            faulty = rng.sample(perc, k)
            faulty_ids = {c["n"] for c in faulty}
            facts, _ = assemble(L, cs, faulty_ids, meta)
            r = run_explain(facts, faulty_ids, meta)
            out.append(dict(k=k, seed=si, faulty_ids=sorted(faulty_ids),
                            faulty_types=[c["t"] for c in faulty],
                            best_cost=r["best_cost"], n_optimal=r["n_optimal"],
                            t_solve=r["t_solve"], drop_sets=r["drop_sets"], pr=r["pr"]))
            print(f"[A k={k} s={si}] faulty={sorted(faulty_ids)} cost={r['best_cost']} "
                  f"nopt={r['n_optimal']} drops={r['drop_sets'][:2]} t={r['t_solve']}s",
                  flush=True)
    return out


# ---------------- Part B: missing-position candidate inference ----------------

def part_B(L, cs, meta, ntargets=3):
    ks = sorted(L.pos)
    # choose target vessels that are anchored AND well-connected (in >=2 edges)
    perc_on = defaultdict(int)
    for c in cs:
        if c["t"] in PERC_TYPES:
            perc_on[c.get("k")] += 1; perc_on[c.get("l")] += 1
    anchored = {c["k"] for c in cs if c["t"] == "location"}
    cands = sorted((k for k in ks if k in anchored and perc_on[k] >= 3),
                   key=lambda k: -perc_on[k])[:ntargets]
    out = []
    for tgt in cands:
        true_pos = L.pos[tgt]
        cs2 = [dict(c) for c in cs
               if not (c["t"] == "location" and c["k"] == tgt)]
        for c in cs2:
            if c["t"] in WORLD_TYPES:
                c["mandatory"] = True
        base = emit_facts(L, cs2, meta) + f"toinfer_pos({tgt}).\n"
        t0 = time.perf_counter()
        ctl = clingo.Control(["--configuration=auto", "--models=0"])
        enc = open(os.path.join(HERE, "proj.lp")).read()
        ctl.add("base", [], base + geom_tables(meta) + enc)
        ctl.add("base", [], "#show inferred_pos/4.")
        ctl.ground([("base", [])])
        cand = set(); nm = 0; t1 = time.perf_counter()
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
                    mm = re.match(rf"inferred_pos\({tgt},(-?\d+),(-?\d+),(-?\d+)\)", str(a))
                    if mm:
                        cand.add((int(mm.group(1)), int(mm.group(2)), int(mm.group(3))))
                h.resume()
        t_solve = time.perf_counter() - t1
        out.append(dict(target=tgt, n_perc=perc_on[tgt], n_models=nm,
                        n_cand=len(cand), true_pos=list(true_pos),
                        true_in_cand=(true_pos in cand),
                        t_solve=round(t_solve, 2)))
        print(f"[B tgt={tgt}] perc={perc_on[tgt]} cand={len(cand)} "
              f"true_in={true_pos in cand} models={nm} t={round(t_solve,2)}s", flush=True)
    return out


# ---------------- grounding comparison + distribution comparison ----------------

def grounding_compare(L, cs, meta, tag):
    """Write the real instance and run naive.lp vs proj.lp via ablate_one.py
    (fresh process each -> clean peak RSS). Returns dict of ground-program stats."""
    data = os.path.join(HERE, "..", "data", "e20")
    os.makedirs(data, exist_ok=True)
    base = os.path.join(data, tag)
    open(base + "_inst.lp", "w").write(emit_facts(L, cs, meta))
    open(base + "_geom.lp", "w").write(hopa3d.emit_geom(L))
    res = {}
    for enc in ("naive", "proj"):
        cmd = [sys.executable, os.path.join(HERE, "ablate_one.py"),
               "--inst", base + "_inst.lp", "--geom", base + "_geom.lp",
               "--enc", os.path.join(HERE, enc + ".lp"),
               "--timeout", "60", "--memlimit-gb", "3"]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            last = p.stdout.strip().splitlines()[-1] if p.stdout.strip() else None
            res[enc] = json.loads(last) if last else dict(verdict="SUBPROC_FAIL",
                                                           err=p.stderr[-200:])
        except subprocess.TimeoutExpired:
            res[enc] = dict(verdict="TIMEOUT")
    for suf in ("_inst.lp", "_geom.lp"):
        if os.path.exists(base + suf):
            os.remove(base + suf)
    return res


def synthetic_distribution(n_obj, n_con, sx, sy, seed=999):
    """Size-matched synthetic instance for distribution comparison."""
    L, cs, meta = hopa3d.gen_instance(seed=seed, n_obj=n_obj, n_con=n_con,
                                      s=sx, mh=MH, mv=MV, ra=RA, re=RE,
                                      emax=0, mode="consistent", sx=sx, sy=sy, sz=1)
    pairs = set()
    for c in cs:
        if c["t"] in ("one_sided3d", "azim", "azim_range", "distance",
                      "distance_range", "dist_rel"):
            pairs.add((c["k"], c["l"]))
    nloc = sum(1 for c in cs if c["t"] == "location")
    return dict(n_obj=n_obj, n_con=len(cs), p=len(pairs),
                anchor_ratio=round(nloc / max(1, n_obj), 3),
                type_mix=type_mix(cs))


# ---------------- consistency audit on the clean real layout ----------------

def consistency_audit(L, cs, meta):
    ok, bad = check_all([c for c in cs if c["t"] != "min_gap"], L)
    facts = emit_facts(L, cs, meta)
    ctl = clingo.Control(["--configuration=auto"])
    ctl.add("base", [], facts + geom_tables(meta) +
            open(os.path.join(HERE, "proj.lp")).read())
    ctl.ground([("base", [])])
    r = ctl.solve()
    return dict(py_check_all=ok, py_bad=[str(b) for b in bad][:5],
                clingo_verdict=("SAT" if str(r) == "SAT" else "UNSAT"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--maxn", type=int, default=24)
    ap.add_argument("--cell", type=float, default=CELL_M)
    a = ap.parse_args()

    print("=== E20: loading real NOAA AIS snapshot (NY Harbor) ===", flush=True)
    snap = load_snapshot()
    print(f"  moving vessels with valid COG in window: {len(snap)}", flush=True)
    sx0, sy0, items = to_grid(snap, a.cell)
    vessels, sx, sy = select_distinct(items, sx0, sy0, a.maxn)
    print(f"  selected {len(vessels)} in distinct cells; grid {sx}x{sy}x1 "
          f"(cell={a.cell}m)", flush=True)
    L = build_layout(vessels, sx, sy)
    meta = dict(sx=sx, sy=sy, sz=1, mh=MH, mv=MV, ra=RA, re=RE, emax=0,
                mode="consistent", pct_disj=0.0, n_disj=0)
    rng = random.Random(20230101)
    cs, stats = build_constraints(L, vessels, rng, anchor_frac=0.6, knn=2)
    print(f"  constraints: {json.dumps(stats)}", flush=True)
    print(f"  real type_mix: {json.dumps(type_mix(cs))}", flush=True)

    res = dict(meta=meta, real_stats=stats, real_type_mix=type_mix(cs),
               vessels=[dict(k=v["k"], name=v["name"], mmsi=v["mmsi"],
                             lat=v["lat"], lon=v["lon"], sog=v["sog"], cog=v["cog"],
                             x=v["gx"], y=v["gy"]) for v in vessels])

    print("=== consistency audit (clean real layout) ===", flush=True)
    res["audit"] = consistency_audit(L, cs, meta)
    print("  ", json.dumps(res["audit"]), flush=True)

    print("=== synthetic size-matched distribution ===", flush=True)
    res["synth_dist"] = synthetic_distribution(stats["n_obj"], stats["n_con"], sx, sy)
    print("  ", json.dumps(res["synth_dist"]), flush=True)

    print("=== grounding: naive vs proj on the REAL instance ===", flush=True)
    res["grounding"] = grounding_compare(L, cs, meta, "e20_real")
    for enc in ("naive", "proj"):
        g = res["grounding"].get(enc, {})
        print(f"  {enc}: verdict={g.get('verdict')} n_atoms={g.get('n_atoms')} "
              f"n_rules={g.get('n_rules')} t_ground={g.get('t_ground')} "
              f"rss_kb={g.get('peak_rss_kb')}", flush=True)

    print("=== Part A: multi-error fault localization (real layout) ===", flush=True)
    A = part_A(L, cs, meta, a.seeds)
    res["A"] = A
    res["A_agg"] = {k: agg_pr([r["pr"] for r in A if r["k"] == k]) for k in (1, 2, 3)}
    print("  A aggregate:", json.dumps(res["A_agg"]), flush=True)

    print("=== Part B: missing-position candidate inference (real layout) ===", flush=True)
    B = part_B(L, cs, meta, ntargets=3)
    res["B"] = B
    res["B_summary"] = dict(
        n=len(B),
        coverage=round(sum(1 for r in B if r["true_in_cand"]) / max(1, len(B)), 3),
        median_cand=sorted(r["n_cand"] for r in B)[len(B) // 2] if B else None)
    print("  B summary:", json.dumps(res["B_summary"]), flush=True)

    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "w") as f:
        json.dump(res, f, indent=1)
    print("E20 done ->", LOG, flush=True)


if __name__ == "__main__":
    main()
