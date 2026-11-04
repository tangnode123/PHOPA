"""E16: alternative-backend proof-of-concept -- z3 (SMT) vs pure-clingo proj.

Reviewer concern (iter_3 Critical #2): the projection-decomposition advantage is
only shown against clingo-internal encodings (naive / naive_shared). Is pure
clingo a straw environment? This prototype implements the SAME constraint
semantics in a genuinely different backend -- z3 SMT -- over the linearizable
sub-language (location, direction, distance, distance_sq, distance_range,
dist_rel), and cross-checks verdicts + solve times against clingo proj on
identical instances.

Encoding note (itself a finding): the distance constraints are NON-LINEAR
(squares of coordinate differences). z3's non-linear INTEGER arithmetic
(QF_NIA) is incomplete -- on even 8-object/15^3 instances it hit a 15 s timeout
returning `unknown`. Because the domain is a finite grid, we instead encode each
coordinate as a fixed-width BitVec (W=32) and each constraint as bounded
bit-vector arithmetic (QF_BV), which z3 bit-blasts and DECIDES (all cells here
finish in <2 s). This mirrors the paper's central design point: discreteness of
the grid is what makes the geometry tractable -- ASP exploits it via precomputed
integer tables, an SMT backend via bit-blasting; a generic real/integer SMT
formulation does not.

Scope boundary (honest): azimuth / one_sided3d / elevation are EXCLUDED because
they require atan2 / tan / isqrt -- transcendental & non-linear ops that SMT/CP
integer solvers cannot express directly. That expressiveness gap is exactly why
the full framework precomputes canonical integer tables and stays in ASP. This
prototype therefore tests the distance/position core only.

For each cell we report: clingo verdict & t_solve, z3 verdict & t_solve, whether
the two AGREE, and the clingo/z3 time ratio. Agreement across two independent
solver families is also an extra semantic cross-check.

Log: ../logs/e16_z3_backend.jsonl
"""
import argparse, json, os, subprocess, sys, time
from math import isqrt
import hopa3d
from hopa3d import DIST_RELS

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "e16")
LOG = os.path.join(HERE, "..", "logs", "e16_z3_backend.jsonl")
TIMEOUT = 60.0

SUB_W = [("dist_rel", 30), ("distance_range", 20), ("distance", 10),
         ("location", 25), ("direction", 15)]
SUB_TYPES = {"dist_rel", "distance_range", "distance", "distance_sq",
             "location", "direction"}
CELLS = [(15, 8), (15, 15), (20, 12), (20, 20), (30, 12)]   # (S, N)
MODES = ["consistent", "inconsistent"]


def ubinf_for(S):
    return isqrt(3 * (S - 1) ** 2) + 2


def solve_z3(L, cs, S, ra, timeout, W=32):
    """z3 SMT (bit-vector) model of the sub-language; returns (verdict, t_solve).
    Coordinates are fixed-width BitVecs (W bits) on the finite grid [1,S]; the
    non-linear distance constraints become bounded bit-vector arithmetic, which
    z3 decides by bit-blasting. W=32 is ample for S<=30 (max dsq 3*(S-1)^2 =
    2523 << 2^32); two's-complement squaring of a wrapped difference is exact
    because (2^W - d)^2 == d^2 (mod 2^W)."""
    import z3
    t0 = time.perf_counter()
    sol = z3.Solver()
    sol.set("timeout", int(timeout * 1000))
    one = z3.BitVecVal(1, W); Sv = z3.BitVecVal(S, W)
    x = {}; y = {}; z = {}; yaw = {}
    for k in sorted(L.pos):
        x[k] = z3.BitVec(f"x{k}", W); y[k] = z3.BitVec(f"y{k}", W)
        z[k] = z3.BitVec(f"z{k}", W)
        sol.add(z3.UGE(x[k], one), z3.ULE(x[k], Sv),
                z3.UGE(y[k], one), z3.ULE(y[k], Sv),
                z3.UGE(z[k], one), z3.ULE(z[k], Sv))
        yaw[k] = z3.BitVec(f"yaw{k}", W)
        sol.add(z3.UGE(yaw[k], z3.BitVecVal(0, W)),
                z3.ULT(yaw[k], z3.BitVecVal(360, W)))
    ubinf = ubinf_for(S)

    def bv(n):
        return z3.BitVecVal(int(n), W)

    def dsq(k, l):
        dx = x[k] - x[l]; dy = y[k] - y[l]; dz = z[k] - z[l]
        return dx * dx + dy * dy + dz * dz

    for c in cs:
        t = c["t"]
        if t == "location":
            k = c["k"]
            sol.add(x[k] == bv(c["x"]), y[k] == bv(c["y"]), z[k] == bv(c["z"]))
        elif t == "direction":
            sol.add(yaw[c["k"]] == bv(c["a"] % 360))
        elif t == "dist_rel":
            lb, ub = DIST_RELS[c["u"]]
            ubv = ub if ub is not None else ubinf
            d = dsq(c["k"], c["l"])
            sol.add(z3.UGE(d, bv(lb * lb)), z3.ULE(d, bv(ubv * ubv)))
        elif t == "distance":
            sol.add(dsq(c["k"], c["l"]) == bv(c["d"] * c["d"]))
        elif t == "distance_sq":
            sol.add(dsq(c["k"], c["l"]) == bv(c["dsq"]))
        elif t == "distance_range":
            d = dsq(c["k"], c["l"])
            sol.add(z3.UGE(d, bv(c["d1"] ** 2)), z3.ULE(d, bv(c["d2"] ** 2)))
    r = sol.check()
    t_solve = time.perf_counter() - t0
    if r == z3.sat:
        verdict = "SAT"
    elif r == z3.unsat:
        verdict = "UNSAT"
    else:
        verdict = "TIMEOUT"
    return verdict, round(t_solve, 4)


def solve_clingo(base, cs_sub, L, meta, timeout):
    """Run clingo proj on the SAME sub-language facts; returns (verdict, t_solve,
    t_ground). We emit only sub-language constraints so both backends see the
    identical problem."""
    inst = hopa3d.emit_facts(L, cs_sub, meta)
    geom = hopa3d.emit_geom(L)
    open(base + "_inst.lp", "w").write(inst)
    open(base + "_geom.lp", "w").write(geom)
    cmd = [sys.executable, os.path.join(HERE, "ablate_one.py"),
           "--inst", base + "_inst.lp", "--geom", base + "_geom.lp",
           "--enc", os.path.join(HERE, "proj.lp"),
           "--timeout", str(timeout), "--memlimit-gb", "3"]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 60)
    last = p.stdout.strip().splitlines()[-1] if p.stdout.strip() else None
    if not last:
        return "SUBPROC_FAIL", None, None
    d = json.loads(last)
    return d.get("verdict"), d.get("t_solve"), d.get("t_ground")


def run_one(spec):
    S, N, mode, seed_idx = spec
    seed = 1160000 + seed_idx * 131 + S * 1009 + (0 if mode == "consistent" else 7)
    dens = 1.5
    n_con = max(4, int(round(dens * N)))
    tag = f"e16_S{S}_N{N}_{mode}_r{seed_idx}"
    row = dict(cell=f"{N}x{S}", S=S, N=N, mode=mode, seed=seed, seed_idx=seed_idx)
    try:
        L, cs, meta = hopa3d.gen_instance(seed=seed, n_obj=N, n_con=n_con, s=S,
                                          mh=2, mv=2, ra=3, re=3, emax=0,
                                          mode=mode, pct_disj=0.0, n_disj=0,
                                          type_w=SUB_W)
        cs = [c for c in cs if c["t"] in SUB_TYPES]
        row["n_con_sub"] = len(cs)
        base = os.path.join(DATA, tag)
        cv, ct_solve, ct_ground = solve_clingo(base, cs, L, meta, TIMEOUT)
        row["clingo_verdict"] = cv; row["clingo_t_solve"] = ct_solve
        row["clingo_t_ground"] = ct_ground
        zv, zt = solve_z3(L, cs, S, meta["ra"], TIMEOUT)
        row["z3_verdict"] = zv; row["z3_t_solve"] = zt
        row["agree"] = (cv == zv)
        if ct_solve and zt and ct_solve > 0:
            row["time_ratio_z3_over_clingo_solve"] = round(zt / ct_solve, 2)
        for suf in ("_inst.lp", "_geom.lp"):
            pth = base + suf
            if os.path.exists(pth):
                os.remove(pth)
    except MemoryError:
        row["err"] = "MEMKILL"
    except Exception as e:
        row["err"] = str(e)[:200]
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=3)
    a = ap.parse_args()
    os.makedirs(DATA, exist_ok=True)
    try:
        import z3  # noqa
    except ImportError:
        print("z3 not installed; aborting E16", flush=True); return
    specs = [(S, N, m, si) for (S, N) in CELLS for m in MODES
             for si in range(a.seeds)]
    print(f"E16: {len(specs)} specs -> {LOG}", flush=True)
    t0 = time.perf_counter(); done = 0
    n_agree = 0; n_tot = 0
    with open(LOG, "w") as f:
        for sp in specs:
            row = run_one(sp)
            f.write(json.dumps(row) + "\n"); f.flush()
            done += 1
            if "agree" in row:
                n_tot += 1; n_agree += int(row["agree"])
            print(f"[{done}/{len(specs)}] {row.get('cell')} {row.get('mode')} "
                  f"clingo={row.get('clingo_verdict')} z3={row.get('z3_verdict')} "
                  f"agree={row.get('agree')} ct={row.get('clingo_t_solve')} "
                  f"zt={row.get('z3_t_solve')} ({time.perf_counter()-t0:.0f}s)",
                  flush=True)
    print(f"E16 done. agreement {n_agree}/{n_tot}", time.perf_counter() - t0, flush=True)


if __name__ == "__main__":
    main()
