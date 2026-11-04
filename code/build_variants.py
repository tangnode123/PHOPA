"""Build semi-naive ablation variants of proj.lp by selectively removing
optimizations P1/P2/P3 (the inverse transforms used by build_naive.py):

  N1 = remove P1 : orientation vars guessed for EVERY object (yaw AND pitch)
  N2 = remove P2 : vertical sector checks via full 3-way (DX,DY,DZ) join
  N3 = remove P3 : distance checks via full 3-way (DX,DY,DZ) join

Variants (name -> transforms applied):
  naive.lp      N1+N2+N3   (identical to build_naive.py output)
  naive_p1.lp   N2+N3      (P1 kept)
  naive_p2.lp   N1+N3      (P2 kept)
  naive_p3.lp   N1+N2      (P3 kept)
  naive_p23.lp  N1         (P2+P3 kept)
  proj.lp       none       (P1+P2+P3 kept)
"""
import pathlib

HERE = pathlib.Path(__file__).parent
BASE = (HERE / "proj.lp").read_text()
NAIVE_VERT = (HERE / "naive_vertical.snip").read_text()
NAIVE_DIST = (HERE / "naive_distance.snip").read_text()

# marker strings (must match proj.lp)
M_HD_START = "% ---------- vertical component (P2): hd via 2D join, then (Q,DZ) ----------"
M_HSEC     = "% ---------- one_sided3d horizontal sector checks ----------"
M_VSEC     = "% ---------- one_sided3d vertical sector checks (P2) ----------"
M_DIST     = "% ---------- distance constraints (P3: two-step dedup joins) ----------"
M_AZIM     = "% ---------- absolute azimuth constraints (vector K->L = order (R,P)) ----------"


def apply_n1(src: str) -> str:
    a = "{yawb(K,E) : ye(E)} = 1 :- need_yaw(K), not orient_specified(K)."
    b = "{yawb(K,E) : ye(E)} = 1 :- object(K), not orient_specified(K)."
    assert a in src, "P1 yaw choice rule not found"
    src = src.replace(a, b)
    a = "{pitchb(K,F) : pe(F)} = 1 :- need_pitch(K), not pitch_specified(K)."
    b = "{pitchb(K,F) : pe(F)} = 1 :- object(K), not pitch_specified(K)."
    assert a in src, "P1 pitch choice rule not found"
    return src.replace(a, b)


def apply_n2(src: str) -> str:
    # drop hd helper block
    i1, i2 = src.index(M_HD_START), src.index(M_HSEC)
    src = src[:i1] + src[i2:]
    # swap vertical section for 3-way join version
    i3, i4 = src.index(M_VSEC), src.index(M_DIST)
    return src[:i3] + NAIVE_VERT + "\n" + src[i4:]


def apply_n3(src: str) -> str:
    i4 = src.index(M_DIST)
    i5 = src.index(M_AZIM)
    return src[:i4] + NAIVE_DIST + "\n" + src[i5:]


def build(transforms, header_note: str) -> str:
    src = BASE
    src = src.replace(
        "% P-HOPA3D : projection-decomposed ASP encoding (proj.lp)",
        "% P-HOPA3D : ABLATION variant (proj.lp minus " + "+".join(transforms) + ")\n" + header_note)
    if "P1" in transforms:
        src = apply_n1(src)
    if "P2" in transforms:
        src = apply_n2(src)
    if "P3" in transforms:
        src = apply_n3(src)
    # helper atoms may be referenced by the inference section but absent here
    declared = []
    if "P2" in transforms:
        declared.append("#defined hd/3.")
    if "P3" in transforms:
        declared += ["#defined nd2/3.", "#defined dsq/3."]
    if declared:
        src = src.replace("#defined disj_index/2.",
                          "#defined disj_index/2.\n" + "\n".join(declared))
    return src


VARIANTS = {
    "naive_p1.lp":  (["P2", "P3"], "% keeps P1 (conditional orientation vars)"),
    "naive_p2.lp":  (["P1", "P3"], "% keeps P2 (vertical two-step join)"),
    "naive_p3.lp":  (["P1", "P2"], "% keeps P3 (distance two-step join)"),
    "naive_p23.lp": (["P1"],       "% keeps P2+P3 (both joins), drops P1"),
}

if __name__ == "__main__":
    for fname, (tr, note) in VARIANTS.items():
        out = build(tr, note)
        (HERE / fname).write_text(out)
        print(f"{fname}: removed {'+'.join(tr)}, {len(out.splitlines())} lines")
    print("done")
