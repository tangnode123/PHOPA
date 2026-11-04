"""E12: geometry-library preprocessing cost (cold-start accounting).

The paper's t_ground excludes offline generation of the geometry library
tables (az_angle/q). This measures the full cold-start pipeline per grid
size S in {20,30,40,50} on a trivial instance, separating:
  t_gen      : Python generation (Layout + emit_geom) + file write
  geom_bytes : geom.lp size on disk
  t_load     : clingo ctl.load(geom.lp) parse time (in-process, cold)
  t_load2    : clingo ctl.load(geom.lp) parse time (warm OS cache, 2nd proc)
  t_ground   : ctl.ground time AFTER geom already loaded (the paper's metric)
  n_geomfacts: number of az_angle + q facts

Run each S twice: once to populate OS cache, once cold-ish. Reports per-S
numbers; the point is that geom.lp is generated ONCE per grid resolution and
reused across all instances at that resolution (cached regime), so t_gen is
amortized to ~0 for the scalability experiments, while t_load + t_ground is
what every run pays.

Log: ../logs/e12_geomcost.jsonl
"""
import json, os, subprocess, sys, time
import clingo
import hopa3d

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "e12")
LOG = os.path.join(HERE, "..", "logs", "e12_geomcost.jsonl")
os.makedirs(DATA, exist_ok=True)


def measure_load_ground(geom_path, inst_path):
    """Fresh clingo control: time load(geom), load(inst), ground separately."""
    ctl = clingo.Control(["--configuration=auto"])
    t0 = time.perf_counter()
    ctl.load(geom_path)
    t1 = time.perf_counter()
    ctl.load(inst_path)
    t2 = time.perf_counter()
    ctl.ground([("base", [])])
    t3 = time.perf_counter()
    return dict(t_load_geom=t1 - t0, t_load_inst=t2 - t1, t_ground=t3 - t2)


def run_S(S):
    tag = f"e12_s{S}"
    base = os.path.join(DATA, tag)
    # 1) generation cost (cold): build Layout + emit geom + write file
    t0 = time.perf_counter()
    L, cs, meta = hopa3d.gen_instance(seed=120000 + S, n_obj=5,
                                      n_con=8, s=S, mh=2, mv=2, ra=3, re=3,
                                      emax=0, mode="consistent",
                                      pct_disj=0.0, n_disj=0)
    geom_txt = hopa3d.emit_geom(L)
    inst_txt = hopa3d.emit_facts(L, cs, meta)
    gp = base + "_geom.lp"; ip = base + "_inst.lp"
    with open(gp, "w") as f: f.write(geom_txt)
    with open(ip, "w") as f: f.write(inst_txt)
    t1 = time.perf_counter()
    geom_bytes = os.path.getsize(gp)
    n_az = geom_txt.count("az_angle(")
    n_q = geom_txt.count("q(")
    # 2) cold load+ground (fresh process, first touch of file)
    cold = measure_load_ground(gp, ip)
    # 3) warm load+ground (file now in OS page cache)
    warm = measure_load_ground(gp, ip)
    row = dict(S=S, t_gen=t1 - t0, geom_bytes=geom_bytes,
               n_az=n_az, n_q=n_q, n_geomfacts=n_az + n_q,
               cold=cold, warm=warm)
    return row, gp, ip


def main():
    rows = []
    for S in (20, 30, 40, 50):
        row, gp, ip = run_S(S)
        rows.append(row)
        print(json.dumps(row), flush=True)
        for p in (gp, ip):
            if os.path.exists(p): os.remove(p)
    with open(LOG, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print("E12 done ->", LOG, flush=True)


if __name__ == "__main__":
    main()
