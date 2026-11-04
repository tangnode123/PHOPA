"""E11: semi-real case study -- harbor low-altitude/surface surveillance.

Geography: a schematic harbor layout hand-digitized from approximate public
real-world geography of a generic container port (breakwater + light at the
south, approach channel marked by two buoys entering from the SE, container
quay with four ship-to-shore cranes along the north edge, container yard,
harbor control tower, three berthed ships, one inbound ship, one transiting
ship, one ferry, one small boat, four patrol/relay UAVs at ~100-115 m AGL).
Grid: 50 x 50 x 24; units ~10 m horizontally, ~5 m vertically (z=1 = sea
level, UAV z=22..24 ~ 105-115 m AGL). HONEST LABEL: coordinates are
approximate/schematic, not survey-grade; the scientific content is that ALL
constraints are AUTO-DERIVED from the coordinate layout via the canonical
integer semantics (no hand-invented labels), and that the framework then
performs non-trivial 3D reasoning tasks on them.

Tasks:
  T1 consistency check (full knowledge -> unique answer set, validated)
  T2 faulty-perception localization (corrupt one presumed perception ->
     explain_mode optimum must drop exactly the corrupted constraint)
  T3 missing-position inference (transit ship position unknown -> enumerate
     candidate 3D positions from bearing/azimuth/range/dist_rel constraints)
  T4 missing-orientation inference (UAV yaw unknown -> infer from two
     one_sided3d observations)
  T5 disjunctive perception (radar multipath: two candidate small-boat
     positions; tower range measurement discriminates -> chosen inferred)

Log: ../logs/e11_case.json ; figures: ../results/figures/e11_*.png
"""
import json, os, re, sys, time
from math import isqrt
import clingo
import hopa3d
from hopa3d import Layout, horiz_sector, elev_sector, check_all, DIST_RELS

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from e4_scenarios import geom_tables, model_layout, plot_scenario

DATA = os.path.join(HERE, "..", "data", "e11")
FIGS = os.path.join(HERE, "..", "results", "figures")
LOG = os.path.join(HERE, "..", "logs", "e11_case.json")
os.makedirs(DATA, exist_ok=True)

META = dict(sx=50, sy=50, sz=24, mh=2, mv=2, ra=3, re=3)

# id: (name, (x,y,z), yaw, extent)   yaw=None -> not given
OBJ = {
    1:  ("control_tower",   (8, 34, 15), 270, (0, 0, 0)),
    2:  ("breakwater_light", (38, 5, 8), None, (0, 0, 0)),
    3:  ("buoy_port",       (33, 15, 1), None, (0, 0, 0)),
    4:  ("buoy_starboard",  (39, 21, 1), None, (0, 0, 0)),
    5:  ("crane_1",         (6, 45, 10), 180, (2, 1, 9)),
    6:  ("crane_2",         (12, 45, 10), 180, (2, 1, 9)),
    7:  ("crane_3",         (18, 45, 10), 180, (2, 1, 9)),
    8:  ("crane_4",         (24, 45, 10), 180, (2, 1, 9)),
    9:  ("stack_1",         (5, 48, 2), None, (1, 1, 1)),
    10: ("stack_2",         (10, 48, 2), None, (1, 1, 1)),
    11: ("stack_3",         (15, 48, 2), None, (1, 1, 1)),
    12: ("stack_4",         (20, 48, 2), None, (1, 1, 1)),
    13: ("stack_5",         (25, 48, 2), None, (1, 1, 1)),
    14: ("stack_6",         (30, 48, 2), None, (1, 1, 1)),
    15: ("stack_7",         (35, 48, 2), None, (1, 1, 1)),
    16: ("stack_8",         (40, 48, 2), None, (1, 1, 1)),
    17: ("ship_berth_A",    (7, 42, 1), 0,   (0, 0, 0)),
    18: ("ship_berth_B",    (17, 42, 1), 0,  (0, 0, 0)),
    19: ("ship_berth_C",    (27, 42, 1), 180, (0, 0, 0)),
    20: ("ship_inbound",    (33, 24, 1), 132, (0, 0, 0)),
    21: ("ship_transit",    (28, 16, 1), 90,  (0, 0, 0)),
    22: ("ferry",           (16, 10, 1), 270, (0, 0, 0)),
    23: ("uav_patrol_1",    (35, 22, 22), 315, (0, 0, 0)),
    24: ("uav_patrol_2",    (39, 21, 18), 225, (0, 0, 0)),
    25: ("uav_port",        (10, 44, 20), 0,   (0, 0, 0)),
    26: ("uav_relay",       (24, 30, 24), 180, (0, 0, 0)),
    27: ("small_boat",      (36, 28, 1), None, (0, 0, 0)),
}
GHOST_27 = (31, 31, 1)   # radar multipath ghost for T5
EXT = {k: v[3] for k, v in OBJ.items() if any(v[3])}


def true_layout():
    L = Layout(META["sx"], META["sy"], META["sz"], META["mh"], META["mv"],
               META["ra"], META["re"])
    for k, (name, pos, yaw, ext) in OBJ.items():
        L.pos[k] = pos
        L.yaw[k] = yaw if yaw is not None else 0
        L.pitch[k] = 0
        L.ext[k] = ext
    return L


# ---------------- derivation helpers (canonical integer semantics) ----------

def derive_os3d(L, K, V):
    """one_sided3d sectors (I,J) for target K seen from viewpoint V."""
    dx, dy, dz, q, dsq, az = L.geom(K, V)   # vector V->K
    assert az is not None, (K, V)
    psi = (az - L.yaw[V]) % 360
    return horiz_sector(psi, L.mh), elev_sector(dz, q, L.mv, L.tb)


def derive_azim(L, K, Lobj):
    """absolute azimuth of vector K->Lobj."""
    dx, dy, dz, q, dsq, az = L.geom(Lobj, K)
    assert az is not None
    return az


def derive_band(L, A, B):
    dx, dy, dz, q, dsq, az = L.geom(A, B)
    ubinf = isqrt(3 * (max(L.sx, L.sy, L.sz) - 1) ** 2) + 2
    for name, (lb, ub) in DIST_RELS.items():
        ubv = ub if ub is not None else ubinf
        if lb * lb <= dsq <= ubv * ubv:
            return name
    raise AssertionError((A, B, dsq))


def derive_drange(L, A, B, slack=1):
    dx, dy, dz, q, dsq, az = L.geom(A, B)
    f = isqrt(dsq)
    return max(1, f - slack), f + 1 + slack


def derive_azrange(L, K, Lobj, tol=3):
    a = derive_azim(L, K, Lobj)
    return (a - tol) % 360, (a + tol) % 360


# ---------------- constraint assembly (all labels derived) -----------------

def build_constraints(L):
    cs = []
    nid = [0]

    def add(c):
        nid[0] += 1
        c = dict(c); c["n"] = nid[0]
        cs.append(c)
        return c

    # known locations (static infra, yard, berthed + reported moving objects)
    for k, (name, pos, yaw, ext) in OBJ.items():
        add(dict(t="location", k=k, x=pos[0], y=pos[1], z=pos[2]))
    # known headings
    for k, (name, pos, yaw, ext) in OBJ.items():
        if yaw is not None:
            add(dict(t="direction", k=k, a=yaw))
    # tower surveillance: one_sided3d to moving surface traffic
    for tgt in (20, 21, 22, 27):
        I, J = derive_os3d(L, tgt, 1)
        add(dict(t="one_sided3d", k=tgt, l=1, i=I, j=J, obs="tower"))
    # UAV observations
    I, J = derive_os3d(L, 20, 23); add(dict(t="one_sided3d", k=20, l=23, i=I, j=J, obs="uav1"))
    I, J = derive_os3d(L, 3, 23);  add(dict(t="one_sided3d", k=3,  l=23, i=I, j=J, obs="uav1"))
    I, J = derive_os3d(L, 21, 24); add(dict(t="one_sided3d", k=21, l=24, i=I, j=J, obs="uav2"))
    I, J = derive_os3d(L, 18, 25); add(dict(t="one_sided3d", k=18, l=25, i=I, j=J, obs="uav_port"))
    I, J = derive_os3d(L, 21, 26); add(dict(t="one_sided3d", k=21, l=26, i=I, j=J, obs="relay"))
    # ship reports patrol UAV
    I, J = derive_os3d(L, 23, 20); add(dict(t="one_sided3d", k=23, l=20, i=I, j=J, obs="inbound"))
    # separation monitoring (coarse qualitative distance)
    for a, b in ((20, 21), (21, 22), (17, 18), (18, 19), (21, 27), (22, 27)):
        add(dict(t="dist_rel", k=a, l=b, u=derive_band(L, a, b)))
    # channel bearings from navigational references (azim uses vector K->L)
    a1, a2 = derive_azrange(L, 4, 20); add(dict(t="azim_range", k=4, l=20, a1=a1, a2=a2))
    a1, a2 = derive_azrange(L, 4, 21); add(dict(t="azim_range", k=4, l=21, a1=a1, a2=a2))
    a1, a2 = derive_azrange(L, 2, 22); add(dict(t="azim_range", k=2, l=22, a1=a1, a2=a2))
    # tower radar ranges (quantitative)
    d1, d2 = derive_drange(L, 1, 21); add(dict(t="distance_range", k=1, l=21, d1=d1, d2=d2, obs="radar21"))
    d1, d2 = derive_drange(L, 1, 27); add(dict(t="distance_range", k=1, l=27, d1=d1, d2=d2, obs="radar27"))
    d1, d2 = derive_drange(L, 2, 21); add(dict(t="distance_range", k=2, l=21, d1=d1, d2=d2, obs="light21"))
    # yard/quay spacing constraints (extended objects)
    for a, b in ((5, 6), (6, 7), (7, 8)):
        add(dict(t="min_gap", k=a, l=b, g=2))
    for a, b in ((9, 10), (10, 11), (11, 12), (12, 13), (13, 14), (14, 15), (15, 16)):
        add(dict(t="min_gap", k=a, l=b, g=1))
    return cs


def emit_min_gap(cs):
    """min_gap is not covered by emit_basic -> emit manually."""
    extra = []
    for c in cs:
        if c["t"] == "min_gap":
            extra.append(f'min_gap({c["n"]},{c["k"]},{c["l"]},{c["g"]}).')
    return "\n".join(extra) + ("\n" if extra else "")


def facts_for(L, cs, extra_lines=(), transform=None):
    """Emit full fact string. transform(c)->(keep, replacement_lines) allows
    task-specific surgery (drop a constraint, corrupt one, add disjunction)."""
    keep = []
    extras = []
    for c in cs:
        if transform:
            keep_c, repl = transform(c)
            if repl:
                extras.extend(repl)
            if not keep_c:
                continue
        keep.append(c)
    base = hopa3d.emit_facts(L, [c for c in keep if c["t"] != "min_gap"], META)
    base += emit_min_gap([c for c in keep if c["t"] == "min_gap"])
    base += "\n".join(extras) + ("\n" if extras else "")
    base += "\n".join(extra_lines) + ("\n" if extra_lines else "")
    return base, keep


# ---------------- task-specific surgery -------------------------------------

def find(cs, **kw):
    for c in cs:
        if all(c.get(k) == v for k, v in kw.items()):
            return c
    raise KeyError(kw)


def task_facts(L, cs, task):
    if task == "T1":
        return facts_for(L, cs)
    if task == "T2":
        corrupt = find(cs, t="one_sided3d", obs="uav2")

        def tr(c):
            if c["n"] == corrupt["n"]:
                bad = dict(c); bad["i"] = (c["i"] + 2) % (4 * META["mh"])
                line = (f'presumed_one_sided3d({c["n"]},{c["k"]},{c["l"]},'
                        f'{bad["i"]},{bad["j"]}).')
                return False, [line]
            if c["t"] == "one_sided3d" and c.get("obs") in ("tower", "uav1"):
                return True, None
            return True, None
        facts, keep = facts_for(
            L, cs,
            extra_lines=["explain_mode.", f'constraint_id({corrupt["n"]}).'],
            transform=tr)
        facts += f'presumed({corrupt["n"]}).\n'
        # world-knowledge constraints are mandatory; only perceptions are
        # defeasible in explain mode (HOPA-style single-fault assumption)
        facts += "".join(f'mandatory({c["n"]}).\n'
                         for c in keep if c["n"] != corrupt["n"])
        # validator list: corrupted constraint with its corrupted label
        vcs = []
        for c in keep:
            vcs.append(c)
        bad = dict(corrupt); bad["i"] = (corrupt["i"] + 2) % (4 * META["mh"])
        vcs.append(bad)
        return (facts, vcs), corrupt["n"]
    if task == "T3":
        loc = find(cs, t="location", k=21)
        facts, keep = facts_for(L, cs, extra_lines=["toinfer_pos(21)."],
                                transform=lambda c: (c["n"] != loc["n"], None))
        return facts, keep
    if task == "T4":
        dirn = find(cs, t="direction", k=23)
        facts, keep = facts_for(L, cs, extra_lines=["toinfer_orient(23)."],
                                transform=lambda c: (c["n"] != dirn["n"], None))
        return facts, keep
    if task == "T5":
        loc = find(cs, t="location", k=27)
        nid = max(c["n"] for c in cs) + 1
        tpos = OBJ[27][1]
        disj = dict(n=nid, t="disj", disj=[
            dict(n=0, t="location", k=27, x=tpos[0], y=tpos[1], z=tpos[2]),
            dict(n=0, t="location", k=27, x=GHOST_27[0], y=GHOST_27[1], z=GHOST_27[2])])

        def tr(c):
            if c["n"] == loc["n"]:
                return False, None
            return True, None
        cs2 = [c for c in cs if c["n"] != loc["n"]] + [disj]
        base = hopa3d.emit_facts(L, [c for c in cs2 if c["t"] != "min_gap"], META)
        base += emit_min_gap([c for c in cs2 if c["t"] == "min_gap"])
        base += "toinfer_pos(27).\n"
        return base, cs2
    raise ValueError(task)


# ---------------- runner ----------------------------------------------------

def run_task(name, facts, vcs, meta, corrupt_id=None, max_models=3000,
             timeout=300.0):
    t0 = time.perf_counter()
    args = ["--configuration=auto", "--models=0"]
    if corrupt_id is not None:
        args.append("--opt-mode=optN")
    ctl = clingo.Control(args)
    enc = open(os.path.join(HERE, "proj.lp")).read()
    ctl.add("base", [], facts + geom_tables(meta) + enc)
    ctl.add("base", [], "#show xloc/2. #show yloc/2. #show zloc/2. "
                        "#show yaw/2. #show pitch/2. #show inferred_orient/2. "
                        "#show inferred_pos/4. #show inferred_distrel/3. "
                        "#show inferred_os3d/4. #show chosen/2. #show drop/1. "
                        "#show violated/1.")
    ctl.ground([("base", [])])
    t_ground = time.perf_counter() - t0
    models, costs, exhausted = [], [], False
    t1 = time.perf_counter()
    with ctl.solve(yield_=True, async_=True) as h:
        while len(models) < max_models:
            rem = timeout - (time.perf_counter() - t1)
            if rem <= 0 or not h.wait(max(rem, 0.0)):
                h.cancel(); h.wait(None); break
            m = h.model()
            if m is None:
                exhausted = True; break
            models.append(sorted(str(s) for s in m.symbols(shown=True)))
            costs.append(list(m.cost) if corrupt_id is not None else None)
            h.resume()
    t_solve = time.perf_counter() - t1
    # optimal-model filtering for T2
    opt_idx = range(len(models))
    if corrupt_id is not None and costs:
        best = min(c for c in costs if c)
        opt_idx = [i for i, c in enumerate(costs) if c == best]
    # validation
    n_valid, invalid = 0, []
    inferred_sets = []
    drops, viols, chosens = [], [], []
    cand_pos = {}
    cand_yaw = {}
    for i in opt_idx:
        atoms = models[i]
        active = [c for c in vcs]
        if corrupt_id is not None:
            d = {int(x) for x in (a[5:-1] for a in atoms if a.startswith("drop("))}
            v = {int(x) for x in (a[9:-1] for a in atoms if a.startswith("violated("))}
            active = [c for c in vcs if c["n"] not in d and c["n"] not in v]
            drops.append(sorted(d)); viols.append(sorted(v))
        L = model_layout(atoms, meta, EXT)
        ok, bad = check_all([c for c in active if c["t"] != "min_gap"], L)
        # min_gap + overlap are enforced by the encoding itself; check_all
        # re-checks overlap hard constraints on the model layout
        if ok:
            n_valid += 1
        else:
            invalid.append(bad)
        inferred_sets.append(frozenset(a for a in atoms if a.startswith("inferred_")))
        for a in atoms:
            m = re.match(r"chosen\((\d+),(\d+)\)", a)
            if m: chosens.append((int(m.group(1)), int(m.group(2))))
            m = re.match(r"inferred_pos\((\d+),(-?\d+),(-?\d+),(-?\d+)\)", a)
            if m:
                cand_pos.setdefault(int(m.group(1)), set()).add(
                    (int(m.group(2)), int(m.group(3)), int(m.group(4))))
            m = re.match(r"inferred_orient\((\d+),(-?\d+)\)", a)
            if m:
                cand_yaw.setdefault(int(m.group(1)), set()).add(int(m.group(2)))
    cautious = set.intersection(*[set(s) for s in inferred_sets]) if inferred_sets else set()
    brave = set.union(*[set(s) for s in inferred_sets]) if inferred_sets else set()
    res = dict(task=name, n_models=len(models), n_optimal=len(list(opt_idx)),
               exhausted=exhausted, t_ground=round(t_ground, 2),
               t_solve=round(t_solve, 2), n_valid=n_valid,
               n_invalid=len(invalid), invalid_sample=invalid[:2],
               cautious=sorted(cautious)[:40], n_brave=len(brave),
               drops=drops[:5], violated=viols[:5],
               chosen=sorted(set(chosens))[:5])
    if cand_pos:
        for k, v in cand_pos.items():
            res[f"cand_pos_{k}"] = sorted(v)
            res[f"n_cand_pos_{k}"] = len(v)
    if cand_yaw:
        for k, v in cand_yaw.items():
            res[f"cand_yaw_{k}"] = sorted(v)
            res[f"n_cand_yaw_{k}"] = len(v)
    return res


def main():
    L = true_layout()
    cs = build_constraints(L)
    ok, bad = check_all([c for c in cs if c["t"] != "min_gap"], L)
    hist = {}
    for c in cs:
        hist[c["t"]] = hist.get(c["t"], 0) + 1
    print("derivation self-check (true layout satisfies all derived labels):", ok, bad)
    assert ok, bad
    out = dict(meta=META, n_obj=len(OBJ), n_con=len(cs), con_types=hist,
               density=round(len(cs) / len(OBJ), 2),
               derivation_selfcheck=bool(ok), tasks=[])
    names = {k: v[0] for k, v in OBJ.items()}
    out["names"] = names

    # T1 consistency
    (f1, k1), = [task_facts(L, cs, "T1")]
    out["tasks"].append(run_task("T1_consistency", f1, k1, META))
    print("T1 done")

    # T2 faulty perception
    (f2, k2), cid = task_facts(L, cs, "T2")
    r2 = run_task("T2_fault_localization", f2, k2, META, corrupt_id=cid)
    r2["corrupt_id"] = cid
    out["tasks"].append(r2)
    print("T2 done")

    # T3 missing position
    (f3, k3), = [task_facts(L, cs, "T3")]
    r3 = run_task("T3_missing_position", f3, k3, META)
    r3["true_pos_21"] = OBJ[21][1]
    r3["true_in_candidates"] = OBJ[21][1] in set(map(tuple, r3.get("cand_pos_21", [])))
    out["tasks"].append(r3)
    print("T3 done")

    # T4 missing orientation
    (f4, k4), = [task_facts(L, cs, "T4")]
    r4 = run_task("T4_missing_orientation", f4, k4, META)
    r4["true_yaw_23"] = OBJ[23][2]
    r4["true_in_candidates"] = OBJ[23][2] in set(r4.get("cand_yaw_23", []))
    out["tasks"].append(r4)
    print("T4 done")

    # T5 disjunctive perception
    (f5, k5), = [task_facts(L, cs, "T5")]
    r5 = run_task("T5_disjunctive_perception", f5, k5, META)
    r5["true_pos_27"] = OBJ[27][1]
    r5["true_in_candidates"] = OBJ[27][1] in set(map(tuple, r5.get("cand_pos_27", [])))
    out["tasks"].append(r5)
    print("T5 done")

    with open(LOG, "w") as f:
        json.dump(out, f, indent=1)
    open(os.path.join(DATA, "e11_T1_facts.lp"), "w").write(
        f1 + geom_tables(META) + open(os.path.join(HERE, "proj.lp")).read())
    print("E11 done ->", LOG)


if __name__ == "__main__":
    main()
