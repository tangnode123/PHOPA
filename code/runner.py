"""Runner: solve P-HOPA3D instances with a given encoding, single-thread clingo,
record grounding time / solve time / verdict. Emits JSON Lines logs."""
import argparse, json, time, os, sys
import clingo

HERE = os.path.dirname(os.path.abspath(__file__))

def solve_instance(inst_lp, geom_lp, enc_lp, timeout=300.0, extra=None, optimize=False):
    """Solve one instance. Returns dict(verdict, t_ground, t_solve, t_total, model?).

    verdict in {SAT, UNSAT, TIMEOUT, ERROR}. With optimize=True, enumerates
    (within timeout) keeping the LAST model -- for weak-constraint programs
    clingo improves objective over time, so the last model is (near-)optimal.
    """
    ctl = clingo.Control(["--configuration=auto"])
    # single-thread solving is clingo default
    ctl.load(geom_lp)
    ctl.load(inst_lp)
    ctl.load(enc_lp)
    if extra:
        if isinstance(extra, str):
            extra = [extra]
        for e in extra:
            ctl.add("base", [], e)
    t0 = time.perf_counter()
    ctl.ground([("base", [])])
    t_grnd = time.perf_counter() - t0
    t1 = time.perf_counter()
    verdict, keep = "UNSAT", None
    deadline = t1 + timeout
    PREFIX = ("xloc(", "yloc(", "zloc(", "yaw(", "pitch(", "inferred_",
              "drop(", "violated(", "chosen(")
    try:
        with ctl.solve(yield_=True, async_=True) as handle:
            while True:
                remaining = deadline - time.perf_counter()
                if remaining <= 0 or not handle.wait(max(remaining, 0.0)):
                    verdict = "TIMEOUT" if keep is None else "SAT"
                    handle.cancel()
                    handle.wait(None)
                    break
                m = handle.model()
                if m is None:
                    break  # exhausted; UNSAT unless a model was kept (optimize)
                syms = [str(s) for s in m.symbols(shown=True)]
                keep = [s for s in syms if s.startswith(PREFIX)]
                verdict = "SAT"
                if not optimize:
                    break
                handle.resume()
    except RuntimeError as e:
        verdict = "ERROR"
        keep = None
        print("solver error:", e, file=sys.stderr)
    t_solve = time.perf_counter() - t1
    out = dict(verdict=verdict, t_ground=round(t_grnd, 4), t_solve=round(t_solve, 4),
               t_total=round(t_grnd + t_solve, 4))
    if keep is not None:
        out["model"] = keep
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inst", required=True)
    ap.add_argument("--geom", required=True)
    ap.add_argument("--enc", required=True, choices=["proj", "naive"])
    ap.add_argument("--timeout", type=float, default=300.0)
    ap.add_argument("--extra", default=None, help="extra ASP facts string")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    enc = os.path.join(HERE, args.enc + ".lp")
    res = solve_instance(args.inst, args.geom, enc, args.timeout,
                         [args.extra] if args.extra else None)
    res.update(inst=args.inst, enc=args.enc)
    line = json.dumps(res)
    if args.out:
        with open(args.out, "a") as f:
            f.write(line + "\n")
    print(line)

if __name__ == "__main__":
    main()
