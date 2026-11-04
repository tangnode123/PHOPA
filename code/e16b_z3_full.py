"""E16b probe: z3 BitVec + Array-table encoding of the FULL direction language.

Extends E16 (distance sublanguage) to one_sided3d / azim / azim_range by feeding
z3 the SAME precomputed canonical integer tables the ASP encoding uses -- azimuth
az_angle(dx,dy) and horizontal radius q(dx,dy)=isqrt(dx^2+dy^2) -- as z3 Arrays
indexed by a flattened (dx,dy). This mirrors the framework's central design point:
discreteness lets the transcendental geometry (atan2 / isqrt / tan) be replaced by
finite table lookups, which BOTH backends exploit (ASP via grounded facts, SMT via
Array Select). The sector checks become bounded bit-vector arithmetic.

Signedness note: dz and TB(J) can be negative, so the vertical sector comparison
TB(J-1)*q < dz*1000 < TB(J+1)*q uses SIGNED BitVec ops (SLT/SGT). psi and q are
non-negative -> unsigned ops fine. q=0 (horizontal projection undefined) makes the
full one_sided3d unsatisfiable, matching F2b.

This is a PROBE: tiny instances only, three-way verdict cross-check
(clingo proj vs z3 vs the independent Python check_all validator).
Log: ../logs/e16b_z3_full.jsonl
"""
import argparse, json, os, subprocess, sys, time
from math import isqrt
import hopa3d
from hopa3d import DIST_RELS, elev_bounds

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "e16b")
LOG = os.path.join(HERE, "..", "logs", "e16b_z3_full.jsonl")
TIMEOUT = 30.0
W = 32


def build_arrays(z3, L, S):
    """z3 Arrays AZ[idx], Q[idx] over flattened idx=(dx+OFF)*R+(dy+OFF)."""
    OFF = S - 1
    R = 2 * S - 1
    bvs = z3.BitVecSort(W)
    AZ = z3.K(bvs, z3.BitVecVal(0, W))
    Q = z3.K(bvs, z3.BitVecVal(0, W))
    for dx in range(-(S - 1), S):
        for dy in range(-(S - 1), S):
            idx = (dx + OFF) * R + (dy + OFF)
            iv = z3.BitVecVal(idx, W)
            if (dx, dy) == (0, 0):
                az = 0; q = 0
            else:
                az = L.az[(dx, dy)]; q = isqrt(dx * dx + dy * dy)
            AZ = z3.Store(AZ, iv, z3.BitVecVal(az, W))
            Q = z3.Store(Q, iv, z3.BitVecVal(q, W))
    return AZ, Q, OFF, R


def solve_z3_full(L, cs, S, mh, mv, ra, timeout):
    import z3
    t0 = time.perf_counter()
    sol = z3.Solver(); sol.set("timeout", int(timeout * 1000))
    AZ, Q, OFF, R = build_arrays(z3, L, S)
    tb = elev_bounds(mv)
    WH = (90 // mh)            # horizontal sector width (deg)
    one = z3.BitVecVal(1, W); Sv = z3.BitVecVal(S, W)
    b360 = z3.BitVecVal(360, W); b1000 = z3.BitVecVal(1000, W)
    x = {}; y = {}; z = {}; yaw = {}
    for k in sorted(L.pos):
        x[k] = z3.BitVec(f"x{k}", W); y[k] = z3.BitVec(f"y{k}", W)
        z[k] = z3.BitVec(f"z{k}", W); yaw[k] = z3.BitVec(f"yaw{k}", W)
        sol.add(z3.UGE(x[k], one), z3.ULE(x[k], Sv),
                z3.UGE(y[k], one), z3.ULE(y[k], Sv),
                z3.UGE(z[k], one), z3.ULE(z[k], Sv),
                z3.UGE(yaw[k], z3.BitVecVal(0, W)),
                z3.ULT(yaw[k], b360))

    def bv(n): return z3.BitVecVal(int(n) % (2 ** W), W)
    def sv(n): return z3.BitVecVal(int(n), W)   # signed-capable constant

    def idx_of(dxd, dyd):
        return (dxd + sv(OFF)) * sv(R) + (dyd + sv(OFF))

    def azq(k, l):
        """(dx,dy,dz, az=AZ[idx], q=Q[idx]) for vector L->K."""
        dx = x[k] - x[l]; dy = y[k] - y[l]; dz = z[k] - z[l]
        idx = idx_of(dx, dy)
        return dx, dy, dz, z3.Select(AZ, idx), z3.Select(Q, idx)

    def horiz_eq(psi, I):
        if I % 2 == 0:
            return psi == sv((I * WH) % 360)
        lo = ((I - 1) * WH) % 360; hi = ((I + 1) * WH) % 360
        if lo < hi:
            return z3.And(z3.ULT(sv(lo), psi), z3.ULT(psi, sv(hi)))
        return z3.Or(z3.ULT(sv(lo), psi), z3.ULT(psi, sv(hi)))

    def vert_eq(dz, q, J):
        d1000 = dz * b1000
        if J == 0:                 # due below: needs q==0 (excluded by q>0)
            return z3.And(q == sv(0), dz < sv(0))
        if J == 2 * mv:            # due above
            return z3.And(q == sv(0), dz > sv(0))
        if J % 2 == 0:             # exact ray
            return d1000 == sv(tb[J]) * q
        lo = tb[J - 1]; hi = tb[J + 1]
        c = []
        if lo is not None: c.append(d1000 > sv(lo) * q)
        if hi is not None: c.append(d1000 < sv(hi) * q)
        return z3.And(*c) if c else z3.BoolVal(True)

    for c in cs:
        t = c["t"]
        if t == "location":
            k = c["k"]; sol.add(x[k] == bv(c["x"]), y[k] == bv(c["y"]), z[k] == bv(c["z"]))
        elif t == "direction":
            sol.add(yaw[c["k"]] == bv(c["a"] % 360))
        elif t == "one_sided3d":
            k, l, I, J = c["k"], c["l"], c["i"], c["j"]
            dx, dy, dz, az, q = azq(k, l)
            psi = z3.URem(az + (b360 - yaw[l]), b360)
            sol.add(z3.UGT(q, sv(0)), horiz_eq(psi, I), vert_eq(dz, q, J))
        elif t == "azim":          # vector K->L absolute azimuth
            k, l, A = c["k"], c["l"], c["a"]
            dx = x[l] - x[k]; dy = y[l] - y[k]
            az = z3.Select(AZ, idx_of(dx, dy)); q = z3.Select(Q, idx_of(dx, dy))
            sol.add(z3.UGT(q, sv(0)), az == bv(A))
        elif t == "azim_range":
            k, l, A1, A2 = c["k"], c["l"], c["a1"], c["a2"]
            dx = x[l] - x[k]; dy = y[l] - y[k]
            az = z3.Select(AZ, idx_of(dx, dy)); q = z3.Select(Q, idx_of(dx, dy))
            sol.add(z3.UGT(q, sv(0)))
            if A1 <= A2:
                sol.add(z3.UGE(az, bv(A1)), z3.ULE(az, bv(A2)))
            else:
                sol.add(z3.Or(z3.UGE(az, bv(A1)), z3.ULE(az, bv(A2))))
        elif t == "dist_rel":
            k, l = c["k"], c["l"]; lb, ub = DIST_RELS[c["u"]]
            ubinf = isqrt(3 * (S - 1) ** 2) + 2; ubv = ub if ub is not None else ubinf
            dx, dy, dz, _, _ = azq(k, l)
            d = dx * dx + dy * dy + dz * dz
            sol.add(z3.UGE(d, bv(lb * lb)), z3.ULE(d, bv(ubv * ubv)))
        elif t == "distance":
            k, l = c["k"], c["l"]; dx, dy, dz, _, _ = azq(k, l)
            sol.add(dx * dx + dy * dy + dz * dz == bv(c["d"] * c["d"]))
        elif t == "distance_sq":
            k, l = c["k"], c["l"]; dx, dy, dz, _, _ = azq(k, l)
            sol.add(dx * dx + dy * dy + dz * dz == bv(c["dsq"]))
        elif t == "distance_range":
            k, l = c["k"], c["l"]; dx, dy, dz, _, _ = azq(k, l)
            d = dx * dx + dy * dy + dz * dz
            sol.add(z3.UGE(d, bv(c["d1"] ** 2)), z3.ULE(d, bv(c["d2"] ** 2)))
        # min_gap / pitch / same3d not exercised in this probe
    r = sol.check()
    t_solve = time.perf_counter() - t0
    verdict = "SAT" if r == z3.sat else ("UNSAT" if r == z3.unsat else "TIMEOUT")
    return verdict, round(t_solve, 4)


def py_truth(L, cs):
    """Independent Python validator verdict on the TRUE layout (consistent mode):
    if check_all passes on the generating layout the instance is SAT."""
    ok, _ = hopa3d.check_all([c for c in cs if c["t"] != "min_gap"], L)
    return "SAT" if ok else "UNSAT"


def solve_clingo(base, cs, L, meta, timeout):
    inst = hopa3d.emit_facts(L, [c for c in cs if c["t"] != "min_gap"], meta)
    open(base + "_inst.lp", "w").write(inst)
    open(base + "_geom.lp", "w").write(hopa3d.emit_geom(L))
    cmd = [sys.executable, os.path.join(HERE, "ablate_one.py"),
           "--inst", base + "_inst.lp", "--geom", base + "_geom.lp",
           "--enc", os.path.join(HERE, "proj.lp"),
           "--timeout", str(timeout), "--memlimit-gb", "3"]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 60)
    last = p.stdout.strip().splitlines()[-1] if p.stdout.strip() else None
    if not last: return "SUBPROC_FAIL", None
    d = json.loads(last)
    return d.get("verdict"), d.get("t_solve")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cells", default="10,4;10,6;12,5;12,8")
    ap.add_argument("--seeds", type=int, default=3)
    a = ap.parse_args()
    os.makedirs(DATA, exist_ok=True)
    try:
        import z3  # noqa
    except ImportError:
        print("z3 not installed"); return
    cells = [tuple(int(v) for v in c.split(",")) for c in a.cells.split(";")]
    rows = []
    for (S, N) in cells:
        for mode in ("consistent", "inconsistent"):
            for si in range(a.seeds):
                seed = 162000 + si * 977 + S * 31 + N * 7 + (0 if mode == "consistent" else 5)
                n_con = max(4, int(round(1.5 * N)))
                L, cs, meta = hopa3d.gen_instance(seed=seed, n_obj=N, n_con=n_con, s=S,
                                                  mh=2, mv=2, ra=3, re=3, emax=0,
                                                  mode=mode, pct_disj=0.0, n_disj=0)
                cs = [c for c in cs if c["t"] != "min_gap"]
                has_dir = any(c["t"] in ("one_sided3d", "azim", "azim_range") for c in cs)
                tag = f"e16b_S{S}_N{N}_{mode}_r{si}"
                base = os.path.join(DATA, tag)
                cv, ct = solve_clingo(base, cs, L, meta, TIMEOUT)
                zv, zt = solve_z3_full(L, cs, S, meta["mh"], meta["mv"], meta["ra"], TIMEOUT)
                pt = py_truth(L, cs) if mode == "consistent" else None
                row = dict(cell=f"{N}x{S}", S=S, N=N, mode=mode, seed=seed,
                           has_dir=has_dir, n_con=len(cs),
                           clingo=cv, clingo_t=ct, z3=zv, z3_t=zt,
                           py_truth=pt,
                           agree_cz=(cv == zv),
                           agree_cp=(pt is None or cv == pt))
                rows.append(row)
                for suf in ("_inst.lp", "_geom.lp"):
                    p = base + suf
                    if os.path.exists(p): os.remove(p)
                print(f"[{row['cell']} {mode} r{si}] dir={has_dir} clingo={cv}({ct}) "
                      f"z3={zv}({zt}) py={pt} agreeCZ={row['agree_cz']} "
                      f"agreeCP={row['agree_cp']}", flush=True)
    with open(LOG, "w") as f:
        for r in rows: f.write(json.dumps(r) + "\n")
    ncz = sum(r["agree_cz"] for r in rows)
    ncp = sum(r["agree_cp"] for r in rows)
    ndir = sum(r["has_dir"] for r in rows)
    print(f"\nE16b probe: {len(rows)} instances, {ndir} with direction constraints; "
          f"clingo==z3 {ncz}/{len(rows)}; clingo==py {ncp}/{len(rows)}", flush=True)


if __name__ == "__main__":
    main()
