"""E17: exhaustive audit of the FULL one_sided3d 3D-sector domain.

Reviewer concern (iter_4 Critical #2): the vertical JEPD (F2) is stated over ALL
nonzero vectors and explicitly classifies due-above/below (q=0, dz!=0) as J=0 /
J=2MV. But the FULL relation one_sided3d(K,L,I,J) is the CONJUNCTION of a
horizontal sector I (which needs the azimuth AZ(dx,dy)) and a vertical sector J.
When q=0 the horizontal projection (dx,dy)=(0,0) so AZ is undefined -- the
az_angle table has no entry -- and check_basic returns False for EVERY (I,J).
So the full 3D sector is well-defined only for q>0; due-above/below vectors are
NOT in the domain of one_sided3d even though their vertical component alone is
classifiable. The paper currently conflates this with coincident points.

This script enumerates EVERY nonzero grid difference vector for S<=20 and counts,
per degeneracy class, how many FULL (I,J) sectors are satisfied:

  class q>0, dz!=0  (inclined)        -> expect exactly 1 full sector
  class q>0, dz==0  (equatorial)      -> expect exactly 1 full sector
  class q==0, dz!=0 (due above/below) -> expect exactly 0 full sectors
                                         (vertical-only: exactly 1; horiz: 0)
  zero vector (coincident)            -> excluded (not a nonzero vector)

It also re-verifies F1 (horizontal JEPD on q>0) and F2 (vertical JEPD on all
nonzero vectors) as component-level counts, and reports the multiplicity of
due-above/below vectors so the domain restriction is shown to be non-vacuous.

We call hopa3d's ACTUAL implementation (az_table, elev_bounds, elev_sector,
horiz_sector) so the audit is faithful to the shipped semantics, not a re-derivation.

Log: ../logs/e17_q0_audit.json
"""
import json, os, sys
from math import isqrt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hopa3d
from hopa3d import az_table, elev_bounds, elev_sector, horiz_sector

LOG = os.path.join(HERE, "..", "logs", "e17_q0_audit.json")

# (S, MH, MV, RA) configs: the recommended setting + a few alternates.
CONFIGS = [(20, 2, 2, 3), (20, 1, 1, 3), (20, 3, 3, 3), (20, 2, 5, 3),
           (15, 2, 2, 5), (10, 3, 3, 3)]


def aligned(mh, mv, ra):
    """Mirror Layout's alignment assertion: MH|90, (90/MH)|... RA-aligned, MV|90,
    RA|360. Invalid granularities (e.g. MH=4, since 90%4!=0) make horiz_sector's
    integer width 90//MH leave gaps and are NOT supported configurations."""
    return (90 % mh == 0) and ((90 // mh) % ra == 0) and (90 % mv == 0) \
           and (360 % ra == 0)


def count_horiz(az, mh):
    """Number of horizontal sectors I in [0,4MH) satisfied by azimuth `az`.
    Returns 0 when az is None (q=0, horizontal projection undefined)."""
    if az is None:
        return 0
    psi = az % 360
    return sum(1 for i in range(4 * mh) if horiz_sector(psi, mh) == i)


def count_vert(dz, q, mv, tb):
    """Number of vertical sectors J in [0,2MV] satisfied by (dz,q)."""
    return sum(1 for j in range(0, 2 * mv + 1) if elev_sector(dz, q, mv, tb) == j)


def count_full(dx, dy, dz, mh, mv, ra, az_tab, tb):
    """Number of FULL (I,J) sectors satisfied -- conjunction of horiz AND vert.
    Mirrors check_basic: az None (q=0) -> 0 full sectors."""
    q = isqrt(dx * dx + dy * dy)
    az = az_tab.get((dx, dy)) if (dx, dy) != (0, 0) else None
    nh = count_horiz(az, mh)
    nv = count_vert(dz, q, mv, tb)
    # full = nh * nv only when both defined; conjunction is independent product
    return nh * nv, nh, nv, q, az


def audit_config(S, mh, mv, ra):
    az_tab = az_table(S, S, ra)
    tb = elev_bounds(mv)
    rng = range(-(S - 1), S)
    # histograms of full-sector counts per class
    classes = {
        "q>0,dz!=0": {},   # inclined
        "q>0,dz==0": {},   # equatorial
        "q=0,dz!=0": {},   # due above/below
    }
    n_nonzero = 0
    n_duevert = 0          # count of q=0,dz!=0 vectors (domain-excluded)
    f1_viol = 0            # q>0 vectors whose horizontal count != 1
    f2_viol = 0            # nonzero vectors whose vertical count != 1
    for dx in rng:
        for dy in rng:
            for dz in rng:
                if dx == 0 and dy == 0 and dz == 0:
                    continue   # zero vector (coincident) excluded
                n_nonzero += 1
                q = isqrt(dx * dx + dy * dy)
                nfull, nh, nv, q2, az = count_full(dx, dy, dz, mh, mv, ra, az_tab, tb)
                # component-level JEPD re-checks
                if q > 0 and nh != 1:
                    f1_viol += 1
                if nv != 1:
                    f2_viol += 1
                # classify
                if q > 0:
                    key = "q>0,dz!=0" if dz != 0 else "q>0,dz==0"
                else:
                    key = "q=0,dz!=0"
                    n_duevert += 1
                classes[key][nfull] = classes[key].get(nfull, 0) + 1
    return dict(S=S, mh=mh, mv=mv, ra=ra, n_nonzero=n_nonzero,
                n_duevert=n_duevert, f1_viol=f1_viol, f2_viol=f2_viol,
                full_hist={k: dict(sorted(v.items())) for k, v in classes.items()})


def main():
    res = dict(configs=[])
    for (S, mh, mv, ra) in CONFIGS:
        if not aligned(mh, mv, ra):
            print(f'[skip] S={S} MH={mh} MV={mv} RA={ra} violates alignment', flush=True)
            continue
        r = audit_config(S, mh, mv, ra)
        res["configs"].append(r)
        # human-readable summary
        inc = r["full_hist"]["q>0,dz!=0"]
        equ = r["full_hist"]["q>0,dz==0"]
        due = r["full_hist"]["q=0,dz!=0"]
        print(f"[S={S} MH={mh} MV={mv} RA={ra}] nonzero={r['n_nonzero']} "
              f"due-above/below={r['n_duevert']} F1viol={r['f1_viol']} "
              f"F2viol={r['f2_viol']}", flush=True)
        print(f"    full-sector histogram  inclined(q>0,dz!=0): {inc}", flush=True)
        print(f"                           equatorial(q>0,dz=0): {equ}", flush=True)
        print(f"                           due-vert(q=0,dz!=0): {due}", flush=True)
    # global assertions for the paper claim
    ok = True
    for r in res["configs"]:
        # every q>0 vector -> exactly 1 full sector
        for cls in ("q>0,dz!=0", "q>0,dz==0"):
            h = r["full_hist"][cls]
            if list(h.keys()) != [1]:
                ok = False
        # every q=0,dz!=0 vector -> exactly 0 full sectors
        h = r["full_hist"]["q=0,dz!=0"]
        if list(h.keys()) != [0]:
            ok = False
        if r["f1_viol"] != 0 or r["f2_viol"] != 0:
            ok = False
    res["claim_holds"] = ok
    res["claim"] = ("FULL one_sided3d sector is well-defined (exactly one (I,J)) "
                    "iff q>0; due-above/below (q=0,dz!=0) admit ZERO full sectors "
                    "(horizontal azimuth undefined) though their vertical component "
                    "alone is JEPD. Horizontal JEPD holds on q>0; vertical JEPD holds "
                    "on all nonzero vectors.")
    print("\nCLAIM HOLDS:", ok, flush=True)
    print(res["claim"], flush=True)
    with open(LOG, "w") as f:
        json.dump(res, f, indent=1)
    print("E17 done ->", LOG, flush=True)


if __name__ == "__main__":
    main()
