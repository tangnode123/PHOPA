import json, re, itertools
from runner import solve_instance

src = open('/tmp/smoke_inst.lp').read()
lines = [l for l in src.split('\n') if l.strip()]

def parse(line):
    m = re.match(r'([a-z_0-9]+)\(([^)]*)\)\.', line)
    return (m.group(1), m.group(2)) if m else (None, None)

def cid(line):
    p, args = parse(line)
    if p == 'constraint_id': return int(args)
    return None

def ctype(line):
    # constraint body facts keyed by leading integer arg
    types = {'one_sided3d','same3d','dist_rel','distance','distance_sq','distance_range',
             'location','direction','direction_range','pitch','pitch_range','azim','azim_range',
             'presumed','mandatory','existdisj','disj_index','disjrelation'}
    p, args = parse(line)
    if p in types:
        a0 = args.split(',')[0]
        if a0.strip().isdigit(): return (p, int(a0))
    return (p, None)

base_lines, per_con = [], {}
for l in lines:
    p, args = parse(l)
    if p == 'constraint_id':
        per_con.setdefault(int(args), []).append(l)
    elif p in ('one_sided3d','same3d','dist_rel','distance','distance_sq','distance_range',
               'location','direction','direction_range','pitch','pitch_range','azim','azim_range',
               'presumed','mandatory','existdisj','disj_index','disjrelation'):
        a0 = args.split(',')[0]
        if a0.strip().isdigit():
            per_con.setdefault(int(a0), []).append(l)
            continue
        base_lines.append(l)
    else:
        base_lines.append(l)

layout = json.load(open('/tmp/smoke.json'))['layout']

def loc_facts():
    out = []
    nid = 9000
    for k, pos in layout['pos'].items():
        out.append(f'constraint_id({nid}). mandatory({nid}). location({nid},{k},{pos[0]},{pos[1]},{pos[2]}).')
        nid += 1
    return '\n'.join(out) + '\n'

def build(keep):
    sel = []
    for n in keep: sel += per_con.get(n, [])
    return '\n'.join(base_lines + sel) + '\n'

def run(name, text, extra=None):
    open('/tmp/bx_inst.lp','w').write(text)
    r = solve_instance('/tmp/bx_inst.lp','/tmp/smoke_geom.lp','proj.lp',timeout=30.0,extra=extra)
    print(f'{name}: {r["verdict"]}  (t_solve={r["t_solve"]:.3f})')
    return r

# control: base only, no constraints
run('base-only        ', build([]))
# all constraints free
run('all-free         ', build(range(1,9)))
# all constraints + true positions injected
run('all+truepos      ', build(range(1,9)), extra=loc_facts())
# incremental
for k in range(1,9):
    run(f'n1..n{k} free       ', build(range(1,k+1)))
# each constraint alone
for k in range(1,9):
    run(f'n{k} alone free     ', build([k]))
# all free but true pos injected only for objects in dropped ones: 1,5,4
def loc_facts_subset(objs):
    out=[]; nid=9000
    for k in objs:
        pos = layout['pos'][str(k)]
        out.append(f'constraint_id({nid}). mandatory({nid}). location({nid},{k},{pos[0]},{pos[1]},{pos[2]}).')
        nid+=1
    return '\n'.join(out)+'\n'
run('all+pos{1,5}     ', build(range(1,9)), extra=loc_facts_subset([1,5]))
run('all+pos{4,5}     ', build(range(1,9)), extra=loc_facts_subset([4,5]))
run('all+pos{2,3}     ', build(range(1,9)), extra=loc_facts_subset([2,3]))
