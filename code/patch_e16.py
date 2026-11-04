import io
p = "e16_z3_backend.py"
src = open(p).read()

def rep(old, new):
    global src
    assert src.count(old) == 1, f"anchor count {src.count(old)}: {old[:60]!r}"
    src = src.replace(old, new)

# 1) docstring: document the BV choice + the non-linear-Int finding
rep(
"""semantics in a genuinely different backend -- z3 SMT integer arithmetic -- over
the linearizable sub-language (location, direction, distance, distance_sq,
distance_range, dist_rel), and cross-checks verdicts + solve times against
clingo proj on identical instances.""",
"""semantics in a genuinely different backend -- z3 SMT -- over the linearizable
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
formulation does not.""")

# 2) replace the whole solve_z3 body with a BitVec version
old_fn = '''def solve_z3(L, cs, S, ra, timeout):
    """z3 SMT model of the sub-language; returns (verdict, t_solve)."""
    import z3
    t0 = time.perf_counter()
    sol = z3.Solver()
    sol.set("timeout", int(timeout * 1000))
    x = {}; y = {}; z = {}; yaw = {}
    for k in sorted(L.pos):
        x[k] = z3.Int(f"x{k}"); y[k] = z3.Int(f"y{k}"); z[k] = z3.Int(f"z{k}")
        sol.add(x[k] >= 1, x[k] <= S, y[k] >= 1, y[k] <= S, z[k] >= 1, z[k] <= S)
        yaw[k] = z3.Int(f"yaw{k}")
        sol.add(yaw[k] >= 0, yaw[k] < 360)
    ubinf = ubinf_for(S)

    def dsq(k, l):
        return (x[k] - x[l]) ** 2 + (y[k] - y[l]) ** 2 + (z[k] - z[l]) ** 2

    for c in cs:
        t = c["t"]
        if t == "location":
            k = c["k"]; sol.add(x[k] == c["x"], y[k] == c["y"], z[k] == c["z"])
        elif t == "direction":
            sol.add(yaw[c["k"]] == c["a"] % 360)
        elif t == "dist_rel":
            lb, ub = DIST_RELS[c["u"]]
            ubv = ub if ub is not None else ubinf
            d = dsq(c["k"], c["l"])
            sol.add(d >= lb * lb, d <= ubv * ubv)
        elif t == "distance":
            sol.add(dsq(c["k"], c["l"]) == c["d"] * c["d"])
        elif t == "distance_sq":
            sol.add(dsq(c["k"], c["l"]) == c["dsq"])
        elif t == "distance_range":
            d = dsq(c["k"], c["l"])
            sol.add(d >= c["d1"] ** 2, d <= c["d2"] ** 2)
    r = sol.check()
    t_solve = time.perf_counter() - t0
    verdict = {z3.sat: "SAT", z3.unsat: "UNSAT"}.get(r, "TIMEOUT")
    return verdict, round(t_solve, 4)'''

new_fn = '''def solve_z3(L, cs, S, ra, timeout, W=32):
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
    return verdict, round(t_solve, 4)'''

rep(old_fn, new_fn)

open(p, "w").write(src)
print("patched e16_z3_backend.py OK")
