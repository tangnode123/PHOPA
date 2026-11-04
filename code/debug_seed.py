"""Regenerate a failing seed, inject true layout, bisect constraints to find
the one whose ASP check rejects the true layout."""
import json, sys, math
from hopa3d import gen_instance, check_all, save_instance, emit_facts, emit_geom, emit_basic
from runner import solve_instance

seed = int(sys.argv[1]); n_obj = int(sys.argv[2]); n_con = int(sys.argv[3]); s = int(sys.argv[4])
L, cs, meta = gen_instance(seed, n_obj, n_con, s, mh=2, mv=2, ra=3, re=3, mode="consistent")
ok, bad = check_all(cs, L)
print("selfcheck:", ok, bad)

def injection_facts():
    out = []; nid = 9000
    for k in sorted(L.pos):
        x, y, z = L.pos[k]
        out.append(f"constraint_id({nid}). mandatory({nid}). location({nid},{k},{x},{y},{z})."); nid += 1
    for k in sorted(L.yaw):
        out.append(f"constraint_id({nid}). mandatory({nid}). direction({nid},{k},{L.yaw[k]})."); nid += 1
    for k in sorted(L.pitch):
        out.append(f"constraint_id({nid}). mandatory({nid}). pitch({nid},{k},{L.pitch[k]})."); nid += 1
    return "\n".join(out) + "\n"

def base_lines(keep_cs):
    """instance facts with only the given constraints"""
    meta2 = dict(meta); 
    txt = emit_facts(L, keep_cs, meta2)
    return txt

inj = injection_facts()
open('/tmp/dbg_geom.lp','w').write(emit_geom(L))

def try_subset(keep, enc='proj.lp'):
    open('/tmp/dbg_inst.lp','w').write(base_lines(keep))
    r = solve_instance('/tmp/dbg_inst.lp','/tmp/dbg_geom.lp',enc,timeout=120.0,extra=[inj])
    return r['verdict']

v = try_subset(cs)
print("full+injection:", v)
if v == 'UNSAT':
    # bisect: find minimal failing subset
    cur = list(cs)
    changed = True
    while changed:
        changed = False
        for c in list(cur):
            trial = [x for x in cur if x is not c]
            if trial and try_subset(trial) == 'UNSAT':
                cur = trial; changed = True
    print("minimal UNSAT subset:")
    for c in cur: print("  ", json.dumps(c))
    # also: each single constraint alone with injection
    for c in cs:
        v1 = try_subset([c])
        if v1 != 'SAT': print("  single fails:", json.dumps(c), v1)
