"""Extract layout from a clingo model and cross-validate with the Python verifier."""
import json, re, sys
import hopa3d
from hopa3d import Layout, check_all
from runner import solve_instance

def model_to_layout(model_atoms, meta):
    L = Layout(meta['sx'], meta['sy'], meta['sz'], meta['mh'], meta['mv'], meta['ra'], meta['re'])
    pos = {}
    for a in model_atoms:
        m = re.match(r'(xloc|yloc|zloc)\((\d+),(-?\d+)\)', a)
        if m:
            axis, k, v = m.group(1)[0], int(m.group(2)), int(m.group(3))
            pos.setdefault(k, {})[axis] = v
        m = re.match(r'yaw\((\d+),(-?\d+)\)', a)
        if m: L.yaw[int(m.group(1))] = int(m.group(2))
        m = re.match(r'pitch\((\d+),(-?\d+)\)', a)
        if m: L.pitch[int(m.group(1))] = int(m.group(2))
    for k, d in pos.items():
        L.pos[k] = (d['x'], d['y'], d['z'])
    # fill unconstrained yaw/pitch with 0 so verifier doesn't KeyError
    for k in L.pos:
        L.yaw.setdefault(k, 0); L.pitch.setdefault(k, 0); L.ext.setdefault(k, (0,0,0))
    return L

def run_case(inst, geom, jf, enc, label):
    meta = json.load(open(jf))['meta']
    cs = json.load(open(jf))['constraints']
    r = solve_instance(inst, geom, enc, timeout=60.0)
    if r['verdict'] != 'SAT':
        print(f'{label}: {r["verdict"]}  <-- unexpected'); return False
    L = model_to_layout(r['model'], meta)
    ok, bad = check_all(cs, L)
    print(f'{label}: SAT, verifier_on_model={ok} {bad if bad else ""}  t_solve={r["t_solve"]}')
    return ok

if __name__ == '__main__':
    a = run_case('/tmp/smoke_inst.lp', '/tmp/smoke_geom.lp', '/tmp/smoke.json', 'proj.lp', 'proj ')
    b = run_case('/tmp/smoke_inst.lp', '/tmp/smoke_geom.lp', '/tmp/smoke.json', 'naive.lp', 'naive')
    sys.exit(0 if (a and b) else 1)
