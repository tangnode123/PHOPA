"""E4: application scenarios with knowledge inference (toinfer_*).
(a) UAV-maritime surveillance; (b) warehouse robot with shelves (extended
objects) + disjunctive perception. Enumerates answer sets (capped), computes
cautious (in all models) / brave (in some model) inferred knowledge, validates
every model layout with the independent Python verifier, saves 3D figures."""
import json, os, re, sys, time
import clingo
from hopa3d import Layout, check_all

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "e4")
FIGS = os.path.join(HERE, "..", "results", "figures")

COMMON = "ra(3). re(3). mh(2). mv(2).\n"

SCEN_A = COMMON + """
sx(30). sy(30). sz(20).
object(1). object(2). object(3). object(4). object(5).
point(1,1). point(2,2). point(3,3). point(4,4). point(5,5).
constraint_id(1). location(1,1,5,8,1).
constraint_id(2). location(2,2,20,12,1).
constraint_id(3). location(3,3,14,25,1).
constraint_id(4). direction(4,1,90).
constraint_id(5). pitch(5,4,30).
constraint_id(6). dist_rel(6,4,1,4).
constraint_id(7). azim_range(7,2,3,90,135).
constraint_id(8). one_sided3d(8,4,1,2,3).
constraint_id(9). location(9,5,12,3,15).
constraint_id(10). direction_range(10,5,300,60).
constraint_id(11). one_sided3d(11,3,5,1,1).
constraint_id(12). azim_range(12,4,3,54,57).
toinfer_orient(5).
toinfer_os3d(5,1,2,2).
toinfer_distrel(2,3).
toinfer_pos(4).
"""

SCEN_A_CS = [
    dict(n=1, t="location", k=1, x=5, y=8, z=1),
    dict(n=2, t="location", k=2, x=20, y=12, z=1),
    dict(n=3, t="location", k=3, x=14, y=25, z=1),
    dict(n=4, t="direction", k=1, a=90),
    dict(n=5, t="pitch", k=4, b=30),
    dict(n=6, t="dist_rel", k=4, l=1, u="far"),
    dict(n=7, t="azim_range", k=2, l=3, a1=90, a2=135),
    dict(n=8, t="one_sided3d", k=4, l=1, i=2, j=3),
    dict(n=9, t="location", k=5, x=12, y=3, z=15),
    dict(n=10, t="direction_range", k=5, a1=300, a2=60),
    dict(n=11, t="one_sided3d", k=3, l=5, i=1, j=1),
    dict(n=12, t="azim_range", k=4, l=3, a1=54, a2=57),
]
SCEN_A_META = dict(sx=30, sy=30, sz=20, mh=2, mv=2, ra=3, re=3)
SCEN_A_NAMES = {1: "ship_alpha", 2: "ship_beta", 3: "buoy", 4: "uav_recon", 5: "uav_scout"}

SCEN_B = COMMON + """
sx(20). sy(20). sz(12).
object(1). object(2). object(3). object(4).
point(1,1). point(2,2). point(3,3). point(4,4).
extent(1,3,1,3). extent(2,3,1,3).
constraint_id(1). location(1,1,5,5,4).
constraint_id(2). location(2,2,15,5,4).
constraint_id(3). location(3,4,8,16,2).
constraint_id(4). direction(4,4,0).
constraint_id(5). existdisj(5).
disj_index(5,1). disjrelation(5,1,11,3,5,5,8,0,0).
disj_index(5,2). disjrelation(5,2,11,3,15,5,8,0,0).
constraint_id(6). distance_range(6,4,3,12,13).
toinfer_os3d(3,4,2,2).
toinfer_distrel(1,2).
"""

SCEN_B_CS = [
    dict(n=1, t="location", k=1, x=5, y=5, z=4),
    dict(n=2, t="location", k=2, x=15, y=5, z=4),
    dict(n=3, t="location", k=4, x=8, y=16, z=2),
    dict(n=4, t="direction", k=4, a=0),
    dict(n=5, t="disj", disj=[dict(n=0, t="location", k=3, x=5, y=5, z=8),
                              dict(n=0, t="location", k=3, x=15, y=5, z=8)]),
    dict(n=6, t="distance_range", k=4, l=3, d1=12, d2=13),
]
SCEN_B_META = dict(sx=20, sy=20, sz=12, mh=2, mv=2, ra=3, re=3)
SCEN_B_NAMES = {1: "shelf_A", 2: "shelf_B", 3: "box", 4: "robot"}
SCEN_B_EXT = {1: (3, 1, 3), 2: (3, 1, 3)}


def geom_tables(meta):
    """Geometry library facts (az_angle/q/tb/drel) -- mirrors emit_facts/emit_geom."""
    from hopa3d import emit_geom, DIST_RELS, U_CODE
    from math import isqrt
    L = Layout(meta["sx"], meta["sy"], meta["sz"], meta["mh"], meta["mv"], meta["ra"], meta["re"])
    out = [emit_geom(L)]
    for j in range(1, 2 * L.mv):
        out.append(f"tb({j},{L.tb[j]}).")
    ubinf = isqrt(3 * (max(L.sx, L.sy, L.sz) - 1) ** 2) + 2
    for u, (lb, ub) in DIST_RELS.items():
        ubv = ub if ub is not None else ubinf
        out.append(f"drel({U_CODE[u]},{lb},{ubv}).")
    return "\n".join(out) + "\n"

def enumerate_models(facts, enc, max_models=2000, timeout=120.0):
    # NOTE: pyclingo here defaults to a single model; --models=0 = enumerate all
    ctl = clingo.Control(["--configuration=auto", "--models=0"])
    ctl.load(os.path.join(HERE, enc))
    ctl.add("base", [], facts)
    ctl.add("base", [], "#show xloc/2. #show yloc/2. #show zloc/2. #show yaw/2. "
                        "#show pitch/2. #show inferred_orient/2. #show inferred_pos/4. "
                        "#show inferred_distrel/3. #show inferred_os3d/4. "
                        "#show chosen/2. #show drop/1. #show violated/1.")
    ctl.ground([("base", [])])
    t0 = time.perf_counter()
    models, exhausted = [], False
    with ctl.solve(yield_=True, async_=True) as h:
        while len(models) < max_models:
            rem = timeout - (time.perf_counter() - t0)
            if rem <= 0 or not h.wait(max(rem, 0.0)):
                h.cancel(); h.wait(None); break
            m = h.model()
            if m is None:
                exhausted = True; break
            models.append(sorted(str(s) for s in m.symbols(shown=True)))
            h.resume()
    return models, exhausted, round(time.perf_counter() - t0, 3)

def model_layout(atoms, meta, ext=None):
    L = Layout(meta["sx"], meta["sy"], meta["sz"], meta["mh"], meta["mv"], meta["ra"], meta["re"])
    pos = {}
    for a in atoms:
        m = re.match(r"(xloc|yloc|zloc)\((\d+),(-?\d+)\)", a)
        if m: pos.setdefault(int(m.group(2)), {})[m.group(1)[0]] = int(m.group(3))
        m = re.match(r"yaw\((\d+),(-?\d+)\)", a)
        if m: L.yaw[int(m.group(1))] = int(m.group(2))
        m = re.match(r"pitch\((\d+),(-?\d+)\)", a)
        if m: L.pitch[int(m.group(1))] = int(m.group(2))
    for k, d in pos.items(): L.pos[k] = (d["x"], d["y"], d["z"])
    for k in L.pos:
        L.yaw.setdefault(k, 0); L.pitch.setdefault(k, 0)
        L.ext[k] = (ext or {}).get(k, (0, 0, 0))
    return L

def run_scenario(name, facts, cs, meta, ext=None):
    models, exhausted, t = enumerate_models(facts, "proj.lp")
    inferred_sets = []
    all_valid = True
    for atoms in models:
        L = model_layout(atoms, meta, ext)
        ok, bad = check_all(cs, L)
        if not ok:
            all_valid = False
            print(f"  [{name}] INVALID model: {bad}")
        inferred_sets.append(frozenset(a for a in atoms if a.startswith("inferred_")))
    cautious = set.intersection(*[set(s) for s in inferred_sets]) if inferred_sets else set()
    brave = set.union(*[set(s) for s in inferred_sets]) if inferred_sets else set()
    res = dict(scenario=name, n_models=len(models), exhausted=exhausted, t_enum=t,
               all_models_valid=all_valid,
               cautious=sorted(cautious), brave_only=sorted(brave - cautious))
    return res, models

def plot_scenario(name, atoms, meta, names, ext=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    L = model_layout(atoms, meta, ext)
    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection="3d")
    for k, (x, y, z) in sorted(L.pos.items()):
        e = (ext or {}).get(k)
        if e:
            ex, ey, ez = e
            verts = []
            for dx in (x - ex, x + ex):
                pass
            xs = [x - ex, x + ex]; ys = [y - ey, y + ey]; zs = [max(1, z - ez), min(meta["sz"], z + ez)]
            for s in range(2):
                verts.append([(xs[0],ys[0],zs[s]),(xs[1],ys[0],zs[s]),(xs[1],ys[1],zs[s]),(xs[0],ys[1],zs[s])])
            for t in range(2):
                verts.append([(xs[t],ys[0],zs[0]),(xs[t],ys[1],zs[0]),(xs[t],ys[1],zs[1]),(xs[t],ys[0],zs[1])])
            verts.append([(xs[0],ys[0],zs[0]),(xs[1],ys[0],zs[0]),(xs[1],ys[0],zs[1]),(xs[0],ys[0],zs[1])])
            verts.append([(xs[0],ys[1],zs[0]),(xs[1],ys[1],zs[0]),(xs[1],ys[1],zs[1]),(xs[0],ys[1],zs[1])])
            pc = Poly3DCollection(verts, alpha=0.25, facecolor="tab:orange", edgecolor="k")
            ax.add_collection3d(pc)
        ax.scatter([x], [y], [z], s=60, color="tab:blue" if not e else "tab:red")
        if k in L.yaw:
            import math as _m
            ax.quiver(x, y, z, 2*_m.cos(_m.radians(L.yaw[k])), 2*_m.sin(_m.radians(L.yaw[k])), 0,
                      color="green", arrow_length_ratio=0.2)
        ax.text(x, y, z + 0.6, names.get(k, str(k)), fontsize=9)
    ax.set_xlim(1, meta["sx"]); ax.set_ylim(1, meta["sy"]); ax.set_zlim(1, meta["sz"])
    ax.set_xlabel("X"); ax.set_ylabel("Y"); ax.set_zlabel("Z")
    ax.set_title(name)
    os.makedirs(FIGS, exist_ok=True)
    p = os.path.join(FIGS, f"e4_{name}.png")
    plt.savefig(p, dpi=150, bbox_inches="tight"); plt.close()
    return p

if __name__ == "__main__":
    os.makedirs(DATA, exist_ok=True)
    SCEN_A_FULL = SCEN_A + geom_tables(SCEN_A_META)
    SCEN_B_FULL = SCEN_B + geom_tables(SCEN_B_META)
    open(os.path.join(DATA, "scenA.lp"), "w").write(SCEN_A_FULL)
    open(os.path.join(DATA, "scenB.lp"), "w").write(SCEN_B_FULL)
    outs = []
    resA, modelsA = run_scenario("A_uav_maritime", SCEN_A_FULL, SCEN_A_CS, SCEN_A_META)
    outs.append(resA)
    print(json.dumps(resA, indent=1))
    resB, modelsB = run_scenario("B_warehouse", SCEN_B_FULL, SCEN_B_CS, SCEN_B_META, SCEN_B_EXT)
    outs.append(resB)
    print(json.dumps(resB, indent=1))
    if modelsA: print("figA:", plot_scenario("A_uav_maritime", modelsA[0], SCEN_A_META, SCEN_A_NAMES))
    if modelsB: print("figB:", plot_scenario("B_warehouse", modelsB[0], SCEN_B_META, SCEN_B_NAMES, SCEN_B_EXT))
    json.dump(outs, open(os.path.join(DATA, "e4_results.json"), "w"), indent=1)
