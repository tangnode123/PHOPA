"""P-HOPA3D discrete semantics + instance generator + independent verifier.

Semantics (canonical, integer-arithmetic; the ASP encodings implement exactly this):

Domain: positions x in 1..SX, y in 1..SY, z in 1..SZ (grid slots).
        yaw   in {0, RA, 2RA, ..., 360-RA}           (RA | 360)
        pitch in {-90, -90+RE, ..., 90}               (RE | 180)

For a vector v = (dx, dy, dz) between two points:
  AZ(v)  : azimuth in degrees, snapped to nearest multiple of RA
           (atan2(dy,dx) mod 360, ties rounded half-up).  Table: az_angle(DX,DY,A).
  Q(v)   : isqrt(dx*dx + dy*dy)   (exact integer floor sqrt). Table: q(DX,DY,Q).
  Elevation sector membership (granularity MV; 2*MV sectors over [-90,90],
  centers c_J = -90 + J*(90/MV), J = 0..2*MV; J even = linear, J odd = angular):
    with S = 1000 and TB(J) = round(tan(radians(c_J))*S) (TB(0)=-INF, TB(2MV)=+INF):
    J odd :  DZ*S > TB(J-1)*Q  and  DZ*S < TB(J+1)*Q        (Q > 0)
    J even, 0<J<2MV :  DZ*S == TB(J)*Q
    J = 0 :  Q == 0 and DZ < 0        (straight down)
    J = 2MV: Q == 0 and DZ > 0        (straight up)
    (Q == 0 and DZ == 0 -> coincident points; relations undefined, never generated)
  Horizontal sector membership of K wrt L (one-sided OPRA3D, granularity MH,
  4*MH sectors of width 90/MH; relative to L's yaw):
    psi = (AZ(v_{L->K}) - yaw_L) mod 360
    I odd :  (I-1)*W < psi < (I+1)*W   (cyclic open interval, W = 90/MH)
    I even:  psi == I*W
  Distance: DSQ = dx^2+dy^2+dz^2.
    dist_rel(U) : LB2(U) <= DSQ <= UB2(U)     (squared bounds, closed)
    distance(D) : DSQ == D*D ;  distance_range(C1,C2): C1^2 <= DSQ <= C2^2
  Extended objects: extent(K,EX,EY,EZ) -> occupied box [x-EX,x+EX]x[y-EY,y+EY]x[z-EZ,z+EZ].
    no_overlap: for every pair with extents, NOT(all three axes overlap).
    min_gap(G): for some axis, |delta| >= EXK+EXL+G  (per-axis separation).

Constraint types (input atoms):
  one_sided3d(N,K,L,I,J,MH,MV)   K on horiz sector I (gran MH) & vert sector J (gran MV) wrt L
  same3d(N,K,L,I,J,MH,MV)        co-located; (yawK-yawL) mod 360 in horiz sector I (gran MH),
                                 (pitchK-pitchL) in vert sector-index J of pitch range
                                 (same TB arithmetic on pitch deltas, MV granularity over [-90,90]*2)
  dist_rel(N,K,L,U)              qualitative distance relation U
  distance(N,K,L,D) / distance_range(N,K,L,C1,C2)
  location(N,K,X,Y,Z)
  direction(N,K,A) / direction_range(N,K,A1,A2)      yaw exact / cyclic range
  pitch(N,K,B) / pitch_range(N,K,B1,B2)
  azim(N,K,L,A) / azim_range(N,K,L,A1,A2)            AZ(v_{K->L}) exact / cyclic range
  disjrelation(N,D,Type,...)     heterogeneous disjunctive constraints (choose exactly 1)
  presumed_*(N,...)              defeasible; violated(N) weak [1@2]
  mandatory(N)                   non-droppable; drop(N) weak [1@1]
  extent(K,EX,EY,EZ), invalid_loc(X,Y,Z)
"""
import math, random, json
from math import isqrt

S_SCALE = 1000  # tan scale for elevation arithmetic

# ---------------- geometry tables / predicates ----------------

def az_table(sx, sy, ra):
    """az_angle(DX,DY,A): azimuth snapped to multiple of RA, for all deltas."""
    t = {}
    for dx in range(-(sx - 1), sx):
        for dy in range(-(sy - 1), sy):
            if dx == 0 and dy == 0:
                continue
            a = math.degrees(math.atan2(dy, dx)) % 360.0
            snapped = int(math.floor(a / ra + 0.5)) * ra % 360
            t[(dx, dy)] = snapped
    return t

def elev_bounds(mv):
    """TB[J] for J = 0..2*MV; TB[0], TB[2MV] are None (infinities)."""
    tb = [None] * (2 * mv + 1)
    for j in range(1, 2 * mv):
        c = -90.0 + j * (90.0 / mv)
        tb[j] = int(round(math.tan(math.radians(c)) * S_SCALE))
    return tb

def elev_sector(dz, q, mv, tb):
    """Return the (unique) elevation sector J for given dz, q=isqrt(dx^2+dy^2).
    Canonical integer semantics; dz==0 and q==0 -> None (coincident)."""
    if q == 0:
        if dz > 0: return 2 * mv
        if dz < 0: return 0
        return None
    for j in range(0, 2 * mv + 1):
        if j % 2 == 0:  # linear
            if j == 0 or j == 2 * mv: continue
            if dz * S_SCALE == tb[j] * q: return j
        else:           # angular open interval
            lo = tb[j - 1] if tb[j - 1] is not None else -10**9
            hi = tb[j + 1] if tb[j + 1] is not None else 10**9
            if dz * S_SCALE > lo * q and dz * S_SCALE < hi * q: return j
    return None  # unreachable for valid inputs

def horiz_sector(psi, mh):
    """psi in [0,360); return sector I in 0..4*MH-1 (canonical)."""
    w = 90.0 / mh  # may be fractional only if MH>... we require (90/MH) integer*RA-aligned
    wi = (90 * RA_UNIT) // mh  # see check below; we use integer widths
    # width in degrees (integer by config check)
    wid = 90 // mh
    for i in range(4 * mh):
        if i % 2 == 0:
            if psi == (i * wid) % 360: return i
        else:
            lo = ((i - 1) * wid) % 360
            hi = ((i + 1) * wid) % 360
            if lo < hi:
                if lo < psi < hi: return i
            else:  # wraps 0
                if psi > lo or psi < hi: return i
    return None

RA_UNIT = 1  # placeholder; horiz_sector uses integer widths (90//MH)

def cyclic_in(psi, a1, a2):
    """psi within closed cyclic range [a1,a2] (degrees, mod 360)."""
    a1 %= 360; a2 %= 360; psi %= 360
    if a1 <= a2: return a1 <= psi <= a2
    return psi >= a1 or psi <= a2

# ---------------- layouts ----------------

class Layout:
    def __init__(self, sx, sy, sz, mh, mv, ra, re):
        self.sx, self.sy, self.sz = sx, sy, sz
        self.mh, self.mv, self.ra, self.re = mh, mv, ra, re
        assert (90 % mh) == 0 and ((90 // mh) % ra) == 0, "MH/RA alignment"
        assert (90 % mv) == 0, "MV must divide 90"
        assert 360 % ra == 0 and 180 % re == 0
        self.az = az_table(sx, sy, ra)
        self.tb = elev_bounds(mv)
        self.pos = {}    # K -> (x,y,z)
        self.yaw = {}    # K -> deg
        self.pitch = {}  # K -> deg
        self.ext = {}    # K -> (ex,ey,ez)

    def geom(self, k, l):
        """Vector L->K deltas and derived quantities."""
        xk, yk, zk = self.pos[k]; xl, yl, zl = self.pos[l]
        dx, dy, dz = xk - xl, yk - yl, zk - zl
        q = isqrt(dx * dx + dy * dy)
        dsq = dx * dx + dy * dy + dz * dz
        az = self.az.get((dx, dy)) if (dx, dy) != (0, 0) else None
        return dx, dy, dz, q, dsq, az

# ---------------- constraints ----------------
# Constraint = dict with keys: n (id), t (type), params..., optional flags:
#   disj (list of disjunct constraints), presumed (bool), mandatory (bool)

TYPES = ["one_sided3d", "same3d", "dist_rel", "distance", "distance_range",
         "location", "direction", "direction_range", "pitch", "pitch_range",
         "azim", "azim_range"]

DIST_RELS = {  # name -> (lb, ub) in grid units (ub None = infinity)
    "very_near": (0, 2), "near": (3, 6), "mid": (7, 12), "far": (13, 20),
    "very_far": (21, None),
}

def check_basic(c, L):
    """Check a single basic (non-disjunctive) constraint against layout L.
    Implements the canonical integer semantics. Returns True/False."""
    t = c["t"]
    if t == "one_sided3d":
        k, l, i, j = c["k"], c["l"], c["i"], c["j"]
        dx, dy, dz, q, dsq, az = L.geom(k, l)   # vector L->K
        if az is None or (dz == 0 and q == 0): return False
        psi = (az - L.yaw[l]) % 360
        return horiz_sector(psi, L.mh) == i and elev_sector(dz, q, L.mv, L.tb) == j
    if t == "same3d":
        k, l, i, j = c["k"], c["l"], c["i"], c["j"]
        if L.pos[k] != L.pos[l]: return False
        dyaw = (L.yaw[k] - L.yaw[l]) % 360
        if horiz_sector(dyaw, L.mh) != i: return False
        dp = L.pitch[k] - L.pitch[l]          # in [-180,180]
        # vertical-style sector check over pitch delta, range [-90..90] per 2MV sectors
        # map delta to sector via TB arithmetic on (dz=dp_scaled, q=const)? Simpler:
        # define pitch-delta sectors by equal-width partition of [-180,180) into 4*MV
        w = 360 // (4 * L.mv)
        dpm = dp % 360
        return horiz_sector(dpm, L.mv) == j if False else _pitch_delta_sector(dpm, L.mv) == j
    if t == "dist_rel":
        k, l, u = c["k"], c["l"], c["u"]
        _, _, _, _, dsq, _ = L.geom(k, l)
        lb, ub = DIST_RELS[u]
        d = math.isqrt(dsq) if dsq >= 0 else 0
        # semantics on squared bounds (closed): use squared to avoid sqrt ties
        if dsq < lb * lb: return False
        if ub is not None and dsq > ub * ub: return False
        return True
    if t == "distance":
        _, _, _, _, dsq, _ = L.geom(c["k"], c["l"])
        return dsq == c["d"] * c["d"]
    if t == "distance_range":
        _, _, _, _, dsq, _ = L.geom(c["k"], c["l"])
        return c["d1"] ** 2 <= dsq <= c["d2"] ** 2
    if t == "location":
        return L.pos[c["k"]] == (c["x"], c["y"], c["z"])
    if t == "direction":
        return L.yaw[c["k"]] % 360 == c["a"] % 360
    if t == "direction_range":
        return cyclic_in(L.yaw[c["k"]], c["a1"], c["a2"])
    if t == "pitch":
        return L.pitch[c["k"]] == c["b"]
    if t == "pitch_range":
        return c["b1"] <= L.pitch[c["k"]] <= c["b2"]
    if t == "azim":
        dx, dy, dz, q, dsq, az = L.geom(c["l"], c["k"])  # vector K->L: geom(l,k) gives L->K? fix below
        # geom(k,l) returns vector l->k. For AZ(v_{K->L}) call geom(l,k).
        _, _, _, _, _, az2 = L.geom(c["l"], c["k"])
        return az2 is not None and az2 % 360 == c["a"] % 360
    if t == "azim_range":
        _, _, _, _, _, az2 = L.geom(c["l"], c["k"])
        return az2 is not None and cyclic_in(az2, c["a1"], c["a2"])
    raise ValueError("unknown type " + t)

def _pitch_delta_sector(dpm, mv):
    """Partition [0,360) of pitch-delta into 4*MV equal sectors (width 90/MV),
    same linear/angular convention as horiz_sector with granularity mv."""
    return horiz_sector(dpm, mv)

def check_constraint(c, L):
    """Check a (possibly disjunctive/presumed) constraint. For disjunctive:
    satisfied if ANY disjunct holds. Returns (satisfied, chosen_disjunct_idx)."""
    if "disj" in c:
        for idx, sub in enumerate(c["disj"]):
            if check_basic(sub, L):
                return True, idx
        return False, None
    return check_basic(c, L), None

def check_all(cs, L):
    """Verifier entry: all constraints satisfied (disjunctive: any-disjunct)."""
    bad = []
    for c in cs:
        ok, _ = check_constraint(c, L)
        if not ok: bad.append(c["n"])
    # extended-object hard constraints
    ks = sorted(L.pos)
    for a_i in range(len(ks)):
        for b_i in range(a_i + 1, len(ks)):
            A, B = ks[a_i], ks[b_i]
            ea = L.ext.get(A, (0, 0, 0)); eb = L.ext.get(B, (0, 0, 0))
            ax = L.pos[A]; bx = L.pos[B]
            ov = all(abs(ax[d] - bx[d]) <= ea[d] + eb[d] for d in range(3))
            if ov and (any(ea) or any(eb)):
                bad.append(("overlap", A, B))
    return len(bad) == 0, bad

# ---------------- instance generator ----------------

TYPE_W = [("one_sided3d", 40), ("dist_rel", 15), ("distance_range", 8),
          ("distance", 5), ("location", 8), ("direction", 8),
          ("direction_range", 6), ("pitch", 3), ("pitch_range", 3),
          ("azim", 2), ("azim_range", 2)]

def _wchoice(rng, pairs):
    tot = sum(w for _, w in pairs)
    r = rng.uniform(0, tot)
    acc = 0
    for name, w in pairs:
        acc += w
        if r <= acc: return name
    return pairs[-1][0]

def gen_instance(seed, n_obj, n_con, s, mh=2, mv=2, ra=3, re=3, emax=0,
                 mode="consistent", pct_disj=0.0, n_disj=4, sx=None, sy=None, sz=None,
                 type_w=None):
    """Generate a P-HOPA3D benchmark instance. Returns (layout, constraints, meta).

    type_w: optional constraint-type weight list (same format as TYPE_W);
    defaults to TYPE_W, so existing callers/results are unaffected."""
    rng = random.Random(seed)
    tw = TYPE_W if type_w is None else type_w
    sx = sx or s; sy = sy or s; sz = sz or s
    L = Layout(sx, sy, sz, mh, mv, ra, re)
    Ks = list(range(1, n_obj + 1))
    # --- sample layout ---
    placed = []
    for k in Ks:
        for _ in range(10000):
            x, y, z = rng.randint(1, sx), rng.randint(1, sy), rng.randint(1, sz)
            ok = True
            ex = rng.randint(0, emax); ey = rng.randint(0, emax); ez = rng.randint(0, emax)
            for (x2, y2, z2, ex2, ey2, ez2) in placed:
                if (abs(x - x2) <= ex + ex2 and abs(y - y2) <= ey + ey2
                        and abs(z - z2) <= ez + ez2) and (ex or ey or ez or ex2 or ey2 or ez2):
                    ok = False; break
            if ok: break
        L.pos[k] = (x, y, z); L.ext[k] = (ex, ey, ez); placed.append((x, y, z, ex, ey, ez))
        L.yaw[k] = rng.randrange(0, 360, ra)
        L.pitch[k] = rng.randrange(-90, 91, re)
    # optional coincident pair for same3d
    same_pair = None
    if n_con >= 6 and rng.random() < 0.15 and emax == 0:
        a, b = rng.sample(Ks, 2)
        L.pos[b] = L.pos[a]; L.ext[b] = (0, 0, 0)
        same_pair = (a, b)
    # --- sample constraints ---
    cs = []
    used_pairs = set()
    for n_id in range(1, n_con + 1):
        if same_pair and n_id == 1:
            k, l = same_pair
            dyaw = (L.yaw[k] - L.yaw[l]) % 360
            dp = (L.pitch[k] - L.pitch[l]) % 360
            cs.append(dict(n=n_id, t="same3d", k=k, l=l,
                           i=horiz_sector(dyaw, mh), j=horiz_sector(dp, mv)))
            continue
        k, l = rng.sample(Ks, 2)
        t = _wchoice(rng, tw)
        c = _make_basic(rng, L, n_id, t, k, l, mode)
        if c is None: continue
        cs.append(c)
        used_pairs.add((min(k, l), max(k, l)))
    # --- disjunctive conversion ---
    if pct_disj > 0:
        n_d = max(1, int(round(len(cs) * pct_disj)))
        for c in rng.sample([c for c in cs if c["t"] != "same3d"], min(n_d, len(cs))):
            fakes = []
            while len(fakes) < n_disj - 1:
                k2, l2 = rng.sample(Ks, 2)
                t2 = _wchoice(rng, tw)
                f = _make_basic(rng, L, 0, t2, k2, l2, "inconsistent")
                if f is not None: fakes.append(f)
            c["disj"] = [dict(c, n=0)] + fakes
            for key in [kk for kk in c if kk not in ("n", "t", "disj")]:
                del c[key]
            c["t"] = "disj"
    meta = dict(seed=seed, n_obj=n_obj, n_con=len(cs), sx=sx, sy=sy, sz=sz,
                mh=mh, mv=mv, ra=ra, re=re, emax=emax, mode=mode,
                pct_disj=pct_disj, n_disj=n_disj)
    return L, cs, meta

def _make_basic(rng, L, n_id, t, k, l, mode):
    cons = (mode == "consistent")
    dx, dy, dz, q, dsq, az = L.geom(k, l)  # vector l->k
    def R(v): return v if cons else v
    if t == "one_sided3d":
        if az is None or (dz == 0 and q == 0): return None
        psi = (az - L.yaw[l]) % 360
        i = horiz_sector(psi, L.mh); j = elev_sector(dz, q, L.mv, L.tb)
        if i is None or j is None: return None
        if not cons:
            i = rng.randrange(0, 4 * L.mh); j = rng.randrange(0, 2 * L.mv + 1)
            if j % 2 == 0 and j not in (0, 2 * L.mv) and rng.random() < 0.5:
                j = rng.randrange(0, 2 * L.mv + 1)
        return dict(n=n_id, t=t, k=k, l=l, i=i, j=j)
    if t == "dist_rel":
        names = list(DIST_RELS)
        if cons:
            d = math.sqrt(dsq)
            u = next((nm for nm in names
                      if d >= DIST_RELS[nm][0] and (DIST_RELS[nm][1] is None or d <= DIST_RELS[nm][1])), None)
            if u is None: return None
        else:
            u = rng.choice(names)
        return dict(n=n_id, t=t, k=k, l=l, u=u)
    if t == "distance":
        d = isqrt(dsq)
        if cons and d * d != dsq:  # keep exact: emit squared semantics with true dsq
            return dict(n=n_id, t="distance_sq", k=k, l=l, dsq=dsq)
        return dict(n=n_id, t=t, k=k, l=l, d=(d if cons else rng.randint(1, max(2, L.sx))))
    if t == "distance_range":
        d = isqrt(dsq)
        if cons:
            m1 = rng.randint(0, max(1, d // 3)); m2 = rng.randint(0, max(1, d // 3))
            return dict(n=n_id, t=t, k=k, l=l, d1=max(0, d - m1), d2=d + m2 + 1)
        return dict(n=n_id, t=t, k=k, l=l, d1=rng.randint(1, L.sx), d2=rng.randint(1, L.sx) + L.sx)
    if t == "location":
        x, y, z = L.pos[k]
        if not cons:
            x = rng.randint(1, L.sx); y = rng.randint(1, L.sy); z = rng.randint(1, L.sz)
        return dict(n=n_id, t=t, k=k, x=x, y=y, z=z)
    if t == "direction":
        a = L.yaw[k] if cons else rng.randrange(0, 360, L.ra)
        return dict(n=n_id, t=t, k=k, a=a)
    if t == "direction_range":
        if cons:
            m = rng.randrange(L.ra, 31, L.ra)
            return dict(n=n_id, t=t, k=k, a1=(L.yaw[k] - m) % 360, a2=(L.yaw[k] + m) % 360)
        return dict(n=n_id, t=t, k=k, a1=rng.randrange(0, 360, L.ra), a2=rng.randrange(0, 360, L.ra))
    if t == "pitch":
        b = L.pitch[k] if cons else rng.randrange(-90, 91, L.re)
        return dict(n=n_id, t=t, k=k, b=b)
    if t == "pitch_range":
        if cons:
            m = rng.randrange(L.re, 21, L.re)
            return dict(n=n_id, t=t, k=k, b1=max(-90, L.pitch[k] - m), b2=min(90, L.pitch[k] + m))
        return dict(n=n_id, t=t, k=k, b1=rng.randint(-90, 89), b2=rng.randint(-89, 90))
    if t in ("azim", "azim_range"):
        _, _, _, _, _, az2 = L.geom(l, k)  # vector k->l
        if az2 is None: return None
        if t == "azim":
            a = az2 if cons else rng.randrange(0, 360, L.ra)
            return dict(n=n_id, t=t, k=k, l=l, a=a)
        if cons:
            m = rng.randrange(L.ra, 31, L.ra)
            return dict(n=n_id, t=t, k=k, l=l, a1=(az2 - m) % 360, a2=(az2 + m) % 360)
        return dict(n=n_id, t=t, k=k, l=l, a1=rng.randrange(0, 360, L.ra), a2=rng.randrange(0, 360, L.ra))
    raise ValueError(t)

# patch: distance_sq support in verifier
_check_basic_orig = check_basic
def check_basic(c, L):
    if c["t"] == "distance_sq":
        _, _, _, _, dsq, _ = L.geom(c["k"], c["l"])
        return dsq == c["dsq"]
    return _check_basic_orig(c, L)

U_CODE = {"very_near": 1, "near": 2, "mid": 3, "far": 4, "very_far": 5}
CODE_U = {v: k for k, v in U_CODE.items()}
# disjunct type codes
DJ = {"one_sided3d": 1, "dist_rel": 2, "distance": 3, "distance_range": 4,
      "direction": 5, "direction_range": 6, "pitch": 7, "pitch_range": 8,
      "azim": 9, "azim_range": 10, "location": 11, "distance_sq": 12, "same3d": 13}

def _params(c):
    t = c["t"]
    if t == "one_sided3d": return [c["k"], c["l"], c["i"], c["j"], 0, 0]
    if t == "same3d":      return [c["k"], c["l"], c["i"], c["j"], 0, 0]
    if t == "dist_rel":    return [c["k"], c["l"], U_CODE[c["u"]], 0, 0, 0]
    if t == "distance":    return [c["k"], c["l"], c["d"], 0, 0, 0]
    if t == "distance_sq": return [c["k"], c["l"], c["dsq"], 0, 0, 0]
    if t == "distance_range": return [c["k"], c["l"], c["d1"], c["d2"], 0, 0]
    if t == "location":    return [c["k"], c["x"], c["y"], c["z"], 0, 0]
    if t == "direction":   return [c["k"], c["a"], 0, 0, 0, 0]
    if t == "direction_range": return [c["k"], c["a1"], c["a2"], 0, 0, 0]
    if t == "pitch":       return [c["k"], c["b"], 0, 0, 0, 0]
    if t == "pitch_range": return [c["k"], c["b1"], c["b2"], 0, 0, 0]
    if t == "azim":        return [c["k"], c["l"], c["a"], 0, 0, 0]
    if t == "azim_range":  return [c["k"], c["l"], c["a1"], c["a2"], 0, 0]
    raise ValueError(t)

def emit_basic(c):
    t = c["t"]; n = c["n"]
    if t == "one_sided3d": return f'one_sided3d({n},{c["k"]},{c["l"]},{c["i"]},{c["j"]}).'
    if t == "same3d":      return f'same3d({n},{c["k"]},{c["l"]},{c["i"]},{c["j"]}).'
    if t == "dist_rel":    return f'dist_rel({n},{c["k"]},{c["l"]},{U_CODE[c["u"]]}).'
    if t == "distance":    return f'distance({n},{c["k"]},{c["l"]},{c["d"]}).'
    if t == "distance_sq": return f'distance_sq({n},{c["k"]},{c["l"]},{c["dsq"]}).'
    if t == "distance_range": return f'distance_range({n},{c["k"]},{c["l"]},{c["d1"]},{c["d2"]}).'
    if t == "location":    return f'location({n},{c["k"]},{c["x"]},{c["y"]},{c["z"]}).'
    if t == "direction":   return f'direction({n},{c["k"]},{c["a"]}).'
    if t == "direction_range": return f'direction_range({n},{c["k"]},{c["a1"]},{c["a2"]}).'
    if t == "pitch":       return f'pitch({n},{c["k"]},{c["b"]}).'
    if t == "pitch_range": return f'pitch_range({n},{c["k"]},{c["b1"]},{c["b2"]}).'
    if t == "azim":        return f'azim({n},{c["k"]},{c["l"]},{c["a"]}).'
    if t == "azim_range":  return f'azim({n},{c["k"]},{c["l"]},{c["a1"]},{c["a2"]}).' if False else f'azim_range({n},{c["k"]},{c["l"]},{c["a1"]},{c["a2"]}).'
    raise ValueError(t)

def emit_facts(L, cs, meta):
    """Emit input facts (instance file). Geometry tables go to a separate shared file."""
    out = []
    out.append(f'sx({L.sx}). sy({L.sy}). sz({L.sz}). ra({L.ra}). re({L.re}). mh({L.mh}). mv({L.mv}).')
    out.append(f'nc({len(cs)}).')
    for j in range(1, 2 * L.mv):
        out.append(f'tb({j},{L.tb[j]}).')
    # NOTE: clingo on this platform wraps arithmetic at 2^31; every product in
    # the encodings (LB*LB, UB*UB, D*D, DZ*1000, TB*Q, DX*DX+...) must stay
    # below 2^31-1. The very_far upper sentinel is therefore grid-derived,
    # not 10^6 (10^6 squared would overflow and reject every layout).
    ubinf = isqrt(3 * (max(L.sx, L.sy, L.sz) - 1) ** 2) + 2
    assert ubinf * ubinf < 2 ** 31 - 1
    for u, (lb, ub) in DIST_RELS.items():
        ubv = ub if ub is not None else ubinf
        assert ubv * ubv < 2 ** 31 - 1, f"drel overflow: {u}"
        out.append(f'drel({U_CODE[u]},{lb},{ubv}).')
    for k in sorted(L.pos):
        out.append(f'object({k}). point({k},{k}).')
        ex, ey, ez = L.ext[k]
        if ex or ey or ez:
            out.append(f'extent({k},{ex},{ey},{ez}).')
    for c in cs:
        n = c["n"]
        out.append(f'constraint_id({n}).')
        if c.get("t") == "disj":
            out.append(f'existdisj({n}).')
            for d_i, sub in enumerate(c["disj"], start=1):
                out.append(f'disj_index({n},{d_i}).')
                ps = ",".join(str(p) for p in _params(sub))
                out.append(f'disjrelation({n},{d_i},{DJ[sub["t"]]},{ps}).')
        else:
            out.append(emit_basic(c))
        if c.get("presumed"): out.append(f'presumed({n}).')
        if c.get("mandatory"): out.append(f'mandatory({n}).')
    return "\n".join(out) + "\n"

def emit_geom(L):
    """Shared geometry library tables (identical input for BOTH encodings):
    az_angle(DX,DY,A) and q(DX,DY,Q). Size depends only on grid dimensions."""
    out = []
    for (dx, dy), a in L.az.items():
        out.append(f'az_angle({dx},{dy},{a}).')
    for (dx, dy) in L.az:
        q = isqrt(dx * dx + dy * dy)
        out.append(f'q({dx},{dy},{q}).')
    return "\n".join(out) + "\n"

def save_instance(path_base, L, cs, meta):
    with open(path_base + "_inst.lp", "w") as f: f.write(emit_facts(L, cs, meta))
    with open(path_base + "_geom.lp", "w") as f: f.write(emit_geom(L))
    with open(path_base + ".json", "w") as f:
        json.dump(dict(meta=meta,
                       layout=dict(pos={str(k): v for k, v in L.pos.items()},
                                   yaw={str(k): v for k, v in L.yaw.items()},
                                   pitch={str(k): v for k, v in L.pitch.items()},
                                   ext={str(k): v for k, v in L.ext.items()}),
                       constraints=cs), f)

if __name__ == "__main__":
    import sys
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 42
    n, c, s = 6, 8, 10
    L, cs, meta = gen_instance(seed, n, c, s, mh=2, mv=2, ra=3, re=3)
    ok, bad = check_all(cs, L)
    print("selfcheck consistent instance:", ok, bad)
    save_instance("/tmp/t3d", L, cs, meta)
    print(open("/tmp/t3d_inst.lp").read()[:600])
