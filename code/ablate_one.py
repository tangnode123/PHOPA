"""Instrumented single-instance run for the P1/P2/P3 ablation (E8).

Runs clingo in-process on one (instance, encoding) pair and reports:
  verdict, t_ground, t_solve, t_total, ground program size
  (#atoms/#rules/#bodies/#choices), peak RSS (ru_maxrss, KB).
Fresh process per invocation -> peak RSS is clean. MemoryError -> MEMKILL.
Prints exactly one JSON line to stdout.
"""
import argparse, json, resource, time, os, sys
import clingo


def lp_get(stats, *path, default=0):
    node = stats
    for p in path:
        if p not in node:
            return default
        node = node[p]
    try:
        return int(node)
    except TypeError:
        return default


def run(inst_lp, geom_lp, enc_lp, timeout):
    out = dict(inst=os.path.basename(inst_lp), enc=os.path.basename(enc_lp))
    ctl = clingo.Control(["--configuration=auto", "--stats=2"])
    ctl.load(geom_lp)
    ctl.load(inst_lp)
    ctl.load(enc_lp)
    t0 = time.perf_counter()
    ctl.ground([("base", [])])
    out["t_ground"] = round(time.perf_counter() - t0, 4)
    st = ctl.statistics
    lp = st["problem"]["lpStep"]
    out["n_atoms"]   = sum(1 for _ in ctl.symbolic_atoms)  # ground atoms
    out["n_rules"]   = int(lp["rules"])
    out["n_bodies"]  = int(lp["bodies"])
    out["n_choices"] = int(lp["rules_choice"])
    t1 = time.perf_counter()
    verdict, deadline = "UNSAT", t1 + timeout
    try:
        with ctl.solve(yield_=True, async_=True) as handle:
            while True:
                remaining = deadline - time.perf_counter()
                if remaining <= 0 or not handle.wait(max(remaining, 0.0)):
                    verdict = "TIMEOUT"
                    handle.cancel()
                    handle.wait(None)
                    break
                m = handle.model()
                if m is None:
                    break  # exhausted -> UNSAT
                verdict = "SAT"
                handle.cancel()
                handle.wait(None)
                break
    except RuntimeError as e:
        verdict = "ERROR"
        out["error"] = str(e)
    out["t_solve"] = round(time.perf_counter() - t1, 4)
    out["t_total"] = round(out["t_ground"] + out["t_solve"], 4)
    out["verdict"] = verdict
    out["peak_rss_kb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inst", required=True)
    ap.add_argument("--geom", required=True)
    ap.add_argument("--enc", required=True, help="path to .lp encoding file")
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--memlimit-gb", type=float, default=3.0)
    args = ap.parse_args()
    lim = int(args.memlimit_gb * (1024 ** 3))
    resource.setrlimit(resource.RLIMIT_AS, (lim, lim))
    try:
        res = run(args.inst, args.geom, args.enc, args.timeout)
    except MemoryError:
        res = dict(inst=os.path.basename(args.inst), enc=os.path.basename(args.enc),
                   verdict="MEMKILL", t_ground=None, t_solve=None, t_total=None,
                   peak_rss_kb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    print(json.dumps(res))


if __name__ == "__main__":
    main()
