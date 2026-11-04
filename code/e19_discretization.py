"""E19: discretization sensitivity of the elevation-sector integer semantics.

Reviewer concern (iter_4 High-Risk #1): is the recommended q=isqrt(floor) +
TB=round(tan*1000) discretization an arbitrary choice that produces
unexplainable classification jumps? This study exhaustively compares the
elevation-sector label J over the WHOLE grid-vector space under four
discretization variants and an exact real-valued reference:

  canonical : q = isqrt(dx^2+dy^2) (floor),   TB = round(tan(c_J)*1e3)   [shipped]
  q_round   : q = round(sqrt(dx^2+dy^2)),     TB = round(tan(c_J)*1e3)
  tb4       : q = isqrt (floor),              TB = round(tan(c_J)*1e4)
  tb6       : q = isqrt (floor),              TB = round(tan(c_J)*1e6)
  real      : exact -- theta = atan2(dz, sqrt(dx^2+dy^2)), no q floor, no TB round

For each MV in {1,2,3,5} we report, per variant: the divergence count/rate vs
the real reference and vs canonical, and -- for every divergence -- the angular
distance |theta - nearest sector boundary| (the "boundary width" inside which
integer and real semantics can disagree). The claim under test: in the supported
range MV<=2 all variants coincide with real (zero divergence); for MV>=3
divergences are confined to a thin boundary shell whose width shrinks as TB scale
grows, and q_round does not beat q_floor. SAT-verdict / candidate-set sensitivity
to MV is covered separately by E15 (same harbor case, T1/T2/T3/T5); because the
ASP encoding materializes exactly these integer labels, label identity in the
supported range implies byte-identical ground programs and hence identical
verdicts/candidate sets.

Log: ../logs/e19_discretization.json
"""
import json, math, os, sys
from math import isqrt

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "..", "logs", "e19_discretization.json")
MVS = [1, 2, 3, 5]
S = 30                      # exhaustive over [-29,29]^3 (representative; F4/E15 cover S<=50 canonical-vs-real)
SCALES = {"canonical": 10**3, "q_round": 10**3, "tb4": 10**4, "tb6": 10**6}


def bounds(mv, scale):
    tb = [None] * (2 * mv + 1)
    for j in range(1, 2 * mv):
        c = -90.0 + j * (90.0 / mv)
        tb[j] = int(round(math.tan(math.radians(c)) * scale))
    return tb


def sector_int(dz, q, mv, tb, scale):
    """Integer elevation sector for given (dz, q); mirrors hopa3d.elev_sector
    but with explicit scale. q==0 handled by due above/below."""
    if q == 0:
        if dz > 0: return 2 * mv
        if dz < 0: return 0
        return None
    for j in range(0, 2 * mv + 1):
        if j % 2 == 0:
            if j == 0 or j == 2 * mv: continue
            if dz * scale == tb[j] * q: return j
        else:
            lo = tb[j - 1] if tb[j - 1] is not None else -10**12
            hi = tb[j + 1] if tb[j + 1] is not None else 10**12
            if dz * scale > lo * q and dz * scale < hi * q: return j
    return None


def sector_real(dz, dx, dy, mv):
    """Exact real-valued elevation sector (no q floor, no TB rounding)."""
    q = math.sqrt(dx * dx + dy * dy)
    if q == 0:
        if dz > 0: return 2 * mv
        if dz < 0: return 0
        return None
    th = math.degrees(math.atan2(dz, q))          # in (-90, 90)
    w = 90.0 / mv
    for j in range(0, 2 * mv + 1):
        if j % 2 == 0:
            if j == 0 or j == 2 * mv: continue
            c = -90.0 + j * w
            if abs(th - c) < 1e-12: return j
        else:
            clo = -90.0 + (j - 1) * w
            chi = -90.0 + (j + 1) * w
            if clo < th < chi: return j
    # exactly on an even boundary counts as that even sector
    for j in range(0, 2 * mv + 1):
        if j % 2 == 0 and j not in (0, 2 * mv):
            if abs(th - (-90.0 + j * w)) < 1e-9: return j
    return None


def boundary_dist(dz, dx, dy, mv):
    """Angular distance (deg) from theta to the NEAREST sector boundary c_J."""
    q = math.sqrt(dx * dx + dy * dy)
    if q == 0: return None
    th = math.degrees(math.atan2(dz, q))
    w = 90.0 / mv
    cs = [-90.0 + j * w for j in range(0, 2 * mv + 1)]
    return min(abs(th - c) for c in cs)


def run_mv(mv):
    tb = {k: bounds(mv, sc) for k, sc in SCALES.items()}
    n = 0
    div = {k: 0 for k in SCALES}              # vs real
    div_canon = {k: 0 for k in SCALES}        # vs canonical
    bwidth = {k: [] for k in SCALES}          # boundary dist at divergences vs real
    rng = range(-(S - 1), S)
    for dx in rng:
        for dy in rng:
            if dx == 0 and dy == 0:
                # q=0 column: only dz matters
                for dz in rng:
                    if dz == 0: continue
                    n += 1
                    jr = sector_real(dz, dx, dy, mv)
                    for k in SCALES:
                        q = 0
                        ji = sector_int(dz, q, mv, tb[k], SCALES[k])
                        if ji != jr: div[k] += 1
                        if k != "canonical":
                            jc = sector_int(dz, 0, mv, tb["canonical"], SCALES["canonical"])
                            if ji != jc: div_canon[k] += 1
                continue
            dsq = dx * dx + dy * dy
            q_floor = isqrt(dsq)
            q_round = int(math.floor(math.sqrt(dsq) + 0.5))
            for dz in rng:
                n += 1
                jr = sector_real(dz, dx, dy, mv)
                qs = {"canonical": q_floor, "q_round": q_round,
                      "tb4": q_floor, "tb6": q_floor}
                jc = sector_int(dz, q_floor, mv, tb["canonical"], SCALES["canonical"])
                for k in SCALES:
                    ji = sector_int(dz, qs[k], mv, tb[k], SCALES[k])
                    if ji != jr:
                        div[k] += 1
                        bd = boundary_dist(dz, dx, dy, mv)
                        if bd is not None: bwidth[k].append(bd)
                    if ji != jc: div_canon[k] += 1
    out = {"mv": mv, "n_vectors": n, "variants": {}}
    for k in SCALES:
        bw = sorted(bwidth[k])
        def q_(p):
            return round(bw[min(len(bw) - 1, int(p * len(bw)))], 4) if bw else None
        out["variants"][k] = {
            "scale": SCALES[k],
            "div_vs_real": div[k],
            "rate_vs_real": round(div[k] / n, 6),
            "div_vs_canonical": div_canon[k],
            "bwidth_deg_mean": round(sum(bw) / len(bw), 4) if bw else None,
            "bwidth_deg_max": round(bw[-1], 4) if bw else None,
            "bwidth_deg_p50": q_(0.5), "bwidth_deg_p90": q_(0.9),
        }
    return out


def main():
    res = {"S": S, "mvs": MVS, "note": "exhaustive over grid vectors; real=exact atan2 reference", "results": []}
    for mv in MVS:
        r = run_mv(mv)
        res["results"].append(r)
        c = r["variants"]["canonical"]; t6 = r["variants"]["tb6"]; qr = r["variants"]["q_round"]
        print(f"[MV={mv}] n={r['n_vectors']}  canonical div_vs_real={c['div_vs_real']} "
              f"({c['rate_vs_real']*100:.3f}%) bwidth_max={c['bwidth_deg_max']}  "
              f"tb6 div={t6['div_vs_real']} bwidth_max={t6['bwidth_deg_max']}  "
              f"q_round div={qr['div_vs_real']}", flush=True)
    with open(LOG, "w") as f:
        json.dump(res, f, indent=1)
    print("E19 done ->", LOG, flush=True)


if __name__ == "__main__":
    main()
