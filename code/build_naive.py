"""Assemble naive.lp from proj.lp by swapping the three decomposed subsystems
for their 'straightforward 3D generalization' counterparts:
  (N1) orientation variables guessed for EVERY object (yaw AND pitch);
  (N2) vertical sector checks via full 3-way (DX,DY,DZ) join;
  (N3) distance checks via full 3-way (DX,DY,DZ) join;
and removing the two-step helper atoms hd/nd2/dsq.
"""
import re, pathlib

HERE = pathlib.Path(__file__).parent
src = (HERE / "proj.lp").read_text()

# --- header ---
src = src.replace(
    "% P-HOPA3D : projection-decomposed ASP encoding (proj.lp)",
    "% P-HOPA3D : NAIVE baseline encoding (naive.lp)\n"
    "% Straightforward 3D generalization of the HOPA ASP rules:\n"
    "%   (N1) yaw AND pitch guessed for EVERY object;\n"
    "%   (N2) elevation checks over the full 3-way (DX,DY,DZ) join;\n"
    "%   (N3) distance checks over the full 3-way (DX,DY,DZ) join.")
src = src.replace("% Key structural choices (vs naive.lp):", "% (Kept identical: input handling, disjunctive/presumed layer,\n"
                  "%  locations, horizontal azimuth via haz, azimuth/range/same3d checks,\n"
                  "%  extended objects, inference.)\n% REMOVED structural choices of proj.lp:")

# --- (N1) orientation guess for all objects ---
a = "{yawb(K,E) : ye(E)} = 1 :- need_yaw(K), not orient_specified(K)."
b = "{yawb(K,E) : ye(E)} = 1 :- object(K), not orient_specified(K)."
assert a in src; src = src.replace(a, b)
a = "{pitchb(K,F) : pe(F)} = 1 :- need_pitch(K), not pitch_specified(K)."
b = "{pitchb(K,F) : pe(F)} = 1 :- object(K), not pitch_specified(K)."
assert a in src; src = src.replace(a, b)

# --- drop hd helper block (between vertical-component marker and horizontal-checks marker) ---
m1 = "% ---------- vertical component (P2): hd via 2D join, then (Q,DZ) ----------"
m2 = "% ---------- one_sided3d horizontal sector checks ----------"
i1, i2 = src.index(m1), src.index(m2)
src = src[:i1] + src[i2:]

# --- (N2) swap vertical section ---
m3 = "% ---------- one_sided3d vertical sector checks (P2) ----------"
m4 = "% ---------- distance constraints (P3: two-step dedup joins) ----------"
i3, i4 = src.index(m3), src.index(m4)
naive_vert = (HERE / "naive_vertical.snip").read_text()
src = src[:i3] + naive_vert + "\n" + src[i4:]

# --- (N3) swap distance section ---
m5 = "% ---------- absolute azimuth constraints (vector K->L = order (R,P)) ----------"
i5 = src.index(m5)
i4b = src.index(m4)
naive_dist = (HERE / "naive_distance.snip").read_text()
src = src[:i4b] + naive_dist + "\n" + src[i5:]

# inference section references hd/nd2/dsq (absent in naive) -> declare optional
src = src.replace("#defined disj_index/2.",
                  "#defined disj_index/2.\n#defined hd/3.\n#defined nd2/3.\n#defined dsq/3.")

(HERE / "naive.lp").write_text(src)
print("naive.lp written:", len(src.splitlines()), "lines")
