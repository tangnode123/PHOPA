"""Build naive_shared.lp: a *stronger* baseline than naive.lp.

Design point ("reasonable optimized direct encoding"):
  - keeps P1 (conditional orientation variables, need_yaw/need_pitch gates);
  - does NOT decompose the 3-way join into 2D x 1D (no P2/P3);
  - but materializes the full (DX,DY,DZ) join only ONCE per needed ordered
    point pair, as two shared tables:
        v3(A,B,DZ,Q)  -- vertical checks (shared across all one_sided3d)
        d3(A,B,D3)    -- distance checks (shared across all distance preds)
    All vertical/distance constraint rules consume v3/d3 instead of running
    their own per-constraint 3-way join (as naive.lp does).

This isolates the projection decomposition itself from generic
"share/reuse the join" optimizations, addressing the reviewer concern that
naive.lp might be a strawman.
"""
import pathlib

HERE = pathlib.Path(__file__).parent
src = (HERE / "proj.lp").read_text()

# --- header ---
src = src.replace(
    "% P-HOPA3D : projection-decomposed ASP encoding (proj.lp)",
    "% P-HOPA3D : SHARED-JOIN baseline encoding (naive_shared.lp)\n"
    "% Stronger baseline than naive.lp: keeps P1 (conditional orientation\n"
    "% variables) and materializes the full 3-way (DX,DY,DZ) join once per\n"
    "% needed ordered pair into shared tables v3/d3; vertical and distance\n"
    "% constraint rules consume these tables. NO 2D x 1D decomposition (P2/P3).")
old_hdr = """% Key structural choices (vs naive.lp):
%   (P1) orientation variables are created ONLY for objects that occur
%        in orientation-sensitive constraints (need_yaw/need_pitch);
%   (P2) vertical (elevation) sector checks run over the two-step join
%        hd(P,R,Q) [2D] x zdist(P,R,DZ) [1D]  -- never over the full
%        3-way (DX,DY,DZ) product;
%   (P3) distance checks run over nd2(P,R,U) [2D, dedup] x zdist [1D]."""
assert old_hdr in src
new_hdr = """% (Kept identical: input handling, disjunctive/presumed layer, locations,
%  horizontal azimuth via haz, azimuth/range/same3d checks, extended
%  objects, inference.)
% Structural differences vs proj.lp:
%   - keeps (P1) conditional orientation variables;
%   - vertical checks run over the SHARED full 3-way join v3(A,B,DZ,Q),
%     materialized once per needed ordered pair (not per constraint);
%   - distance checks run over the SHARED full 3-way join d3(A,B,D3);
%   - no 2D x 1D decomposition (P2/P3 removed)."""
src = src.replace(old_hdr, new_hdr)

# --- replace hd helper (P2 block) with shared 3-way join tables ---
old_hd = ("hd(A,B,Q) :- need_vec(A,B), xdist(A,B,DX), ydist(A,B,DY), q(DX,DY,Q).")
assert old_hd in src
new_v3 = (
    "v3(A,B,DZ,Q) :- need_vec(A,B), xdist(A,B,DX), ydist(A,B,DY),\n"
    "                 zdist(A,B,DZ), q(DX,DY,Q).\n"
    "d3(A,B,D3) :- need_vec(A,B), xdist(A,B,DX), ydist(A,B,DY), zdist(A,B,DZ),\n"
    "               D3 = DX*DX + DY*DY + DZ*DZ.")
src = src.replace(old_hd, new_v3)
src = src.replace(
    "% ---------- vertical component (P2): hd via 2D join, then (Q,DZ) ----------",
    "% ---------- shared 3-way join tables (once per needed pair) ----------")

# --- drop P3 two-step helpers ---
old_p3 = ("nd2(A,B,U) :- need_vec(A,B), xdist(A,B,DX), ydist(A,B,DY), U = DX*DX + DY*DY.\n"
          "dsq(A,B,D3) :- need_vec(A,B), nd2(A,B,U), zdist(A,B,DZ), D3 = U + DZ*DZ.")
assert old_p3 in src
src = src.replace(old_p3, "")
src = src.replace(
    "% ---------- distance constraints (P3: two-step dedup joins) ----------",
    "% ---------- distance constraints (over shared d3) ----------")
src = src.replace(
    "% ---------- one_sided3d vertical sector checks (P2) ----------",
    "% ---------- one_sided3d vertical sector checks (over shared v3) ----------")

# --- rewrite constraint/inference bodies to consume v3/d3 ---
src = src.replace("hd(P,R,Q), zdist(P,R,DZ)", "v3(P,R,DZ,Q)")
src = src.replace("hd(P,R,0), zdist(P,R,DZ)", "v3(P,R,DZ,0)")
src = src.replace("hd(P,R,Q)", "v3(P,R,DZ,Q)")
src = src.replace("hd(P,R,0)", "v3(P,R,DZ,0)")
src = src.replace("dsq(P,R,D3)", "d3(P,R,D3)")
for pat in ("hd(P,R", "nd2(P,R", "dsq(P,R"):
    assert pat not in src, pat

# --- declare removed helpers optional (inference paths may still name them) ---
src = src.replace("#defined disj_index/2.",
                  "#defined disj_index/2.\n#defined hd/3.\n#defined nd2/3.\n#defined dsq/3.")

(HERE / "naive_shared.lp").write_text(src)
print("naive_shared.lp written:", len(src.splitlines()), "lines")
