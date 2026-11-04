#!/usr/bin/env python3
"""Conceptual figures for the P-HOPA3D manuscript (vector PDF).

Fig. 1  one_sided3d sector decomposition:
        (a) horizontal yaw-relative azimuth sectors (granularity MH)
        (b) gravity-aligned absolute elevation sectors (granularity MV)
        (c) the q = 0 degenerate case (due above / due below)

Fig. 2  projection decomposition of the grounding join.
"""
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, FancyArrowPatch, Rectangle, Wedge

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "latex_pkg")
QA = os.path.join(ROOT, "experiments", "results", "figures", "qa")
os.makedirs(QA, exist_ok=True)

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["DejaVu Serif"],
    "mathtext.fontset": "dejavuserif",
    "font.size": 8,
    "axes.labelsize": 8,
    "axes.titlesize": 8.0,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "axes.linewidth": 0.6,
    "lines.linewidth": 0.9,
    "pdf.fonttype": 42,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
})

C_OPEN = "#cfe3f5"
C_RAY = "#b3202c"
C_EDGE = "#4a4a4a"
C_ACC = "#1f5c99"
C_WARN = "#c8791a"

# identical data windows for every panel keep the three axes boxes aligned
XL, YL = (-1.42, 1.42), (-1.34, 1.44)


def _save(fig, base):
    fig.savefig(os.path.join(OUT, base + ".pdf"))
    fig.savefig(os.path.join(QA, base + ".png"), dpi=150)
    plt.close(fig)
    print("wrote", base + ".pdf")


def panel_horizontal(ax, yaw=60.0, psi_k=112.0):
    """(a) horizontal yaw-relative azimuth sectors, MH = 2 -> 8 sectors."""
    mh, wh = 2, 45.0
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(*XL)
    ax.set_ylim(*YL)

    for i in range(1, 4 * mh, 2):
        ax.add_patch(Wedge((0, 0), 1.0, yaw + (i - 1) * wh, yaw + (i + 1) * wh,
                           width=1.0, facecolor=C_OPEN, edgecolor="none",
                           alpha=0.85, zorder=1))
    ax.add_patch(plt.Circle((0, 0), 1.0, fill=False, edgecolor=C_EDGE, lw=0.7,
                            zorder=2))
    for i in range(0, 4 * mh, 2):
        a = math.radians(yaw + i * wh)
        ax.plot([0, math.cos(a)], [0, math.sin(a)], color=C_RAY, lw=1.3,
                zorder=3, solid_capstyle="butt")
        ax.text(1.15 * math.cos(a), 1.15 * math.sin(a), f"$I={i}$",
                ha="center", va="center", fontsize=7.2, color=C_RAY, zorder=5)
    for i in range(1, 4 * mh, 2):
        a = math.radians(yaw + i * wh)
        ax.text(0.66 * math.cos(a), 0.66 * math.sin(a), f"$I={i}$",
                ha="center", va="center", fontsize=7.2, color="#173f5f", zorder=5)

    a = math.radians(yaw)
    ax.add_patch(FancyArrowPatch((0, 0), (1.06 * math.cos(a), 1.06 * math.sin(a)),
                                 arrowstyle="-|>", mutation_scale=9, lw=1.2,
                                 color="k", zorder=6))
    ax.text(1.16 * math.cos(a) + 0.02, 1.16 * math.sin(a) + 0.08,
            "yaw$(L)$", fontsize=7.2, ha="left", va="bottom")

    ak = math.radians(yaw + psi_k)
    kx, ky = 0.86 * math.cos(ak), 0.86 * math.sin(ak)
    ax.plot([0, kx], [0, ky], ls=":", lw=0.8, color=C_ACC, zorder=4)
    ax.plot([kx], [ky], marker="s", ms=4.5, color=C_ACC, zorder=7)
    ax.text(kx + 0.06, ky + 0.10, "$K$", fontsize=9, color=C_ACC, zorder=7)
    ax.add_patch(Wedge((0, 0), 0.28, yaw, yaw + psi_k, width=0.0, facecolor="none",
                       edgecolor=C_ACC, lw=0.9, zorder=6))
    amid = math.radians(yaw + psi_k / 2)
    ax.text(0.36 * math.cos(amid), 0.36 * math.sin(amid), r"$\psi$", fontsize=8.5,
            color=C_ACC, ha="center", va="center")
    ax.plot([0], [0], marker="o", ms=4, color="k", zorder=8)
    ax.text(-0.06, -0.14, "$L$", fontsize=9, ha="center")
    ax.set_title("(a) horizontal: yaw-relative sectors", pad=3)
    ax.text(0, -1.26,
            r"$\psi=(\mathrm{AZ}(dx,dy)-\mathrm{yaw}(L))\;\mathrm{mod}\;360$"
            "\n"
            r"even $I$: $\psi=I\cdot W_H$ (exact ray);   odd $I$: open arc"
            "\n"
            r"here $\psi=112^{\circ}\;\Rightarrow\;I=3$",
            ha="center", va="top", fontsize=6.5, color="#333333")


def panel_vertical(ax):
    """(b) gravity-aligned absolute elevation sectors, MV = 2 -> 5 sectors."""
    mv, wv = 2, 45.0
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(*XL)
    ax.set_ylim(*YL)

    ax.add_patch(Wedge((0, 0), 1.0, 0.0, 90.0, width=1.0, facecolor=C_OPEN,
                       edgecolor="none", alpha=0.85, zorder=1))
    ax.add_patch(Wedge((0, 0), 1.0, -90.0, 0.0, width=1.0, facecolor="#f3ddc6",
                       edgecolor="none", alpha=0.85, zorder=1))
    ax.plot([0, 1.0], [0, 0], color=C_RAY, lw=1.5, zorder=3)
    ax.text(1.05, 0.02, r"$J=2$", fontsize=7.2, color=C_RAY, va="bottom")
    ax.plot([0, 0], [0, 1.0], color=C_WARN, lw=1.5, ls=(0, (3, 2)), zorder=3)
    ax.plot([0, 0], [0, -1.0], color=C_WARN, lw=1.5, ls=(0, (3, 2)), zorder=3)
    ax.text(0.05, 0.88, r"$J=2MV$", fontsize=7.2, color=C_WARN, ha="left",
            va="center")
    ax.text(0.05, -0.88, r"$J=0$", fontsize=7.2, color=C_WARN, ha="left",
            va="center")
    a = math.radians(45)
    ax.text(0.68 * math.cos(a), 0.68 * math.sin(a), r"$J=3$", fontsize=7.2,
            color="#173f5f", ha="center", va="center", zorder=5)
    ax.text(0.68 * math.cos(-a), 0.68 * math.sin(-a), r"$J=1$", fontsize=7.2,
            color="#7a4a10", ha="center", va="center", zorder=5)
    ax.add_patch(FancyArrowPatch((0, 0), (1.22, 0), arrowstyle="-|>",
                                 mutation_scale=8, lw=0.9, color=C_EDGE, zorder=2))
    ax.add_patch(FancyArrowPatch((0, 0), (0, 1.20), arrowstyle="-|>",
                                 mutation_scale=8, lw=0.9, color=C_EDGE, zorder=2))
    ax.text(1.26, -0.02, r"$q$", fontsize=8, ha="left", va="top")
    ax.text(-0.04, 1.24, r"$dz$", fontsize=8, ha="right", va="center")
    ax.plot([0, 0.80], [0, 0.52], ls=":", lw=0.8, color=C_ACC, zorder=4)
    ax.plot([0.80], [0.52], marker="s", ms=4.2, color=C_ACC, zorder=6)
    ax.text(0.86, 0.56, "$K$", fontsize=9, color=C_ACC)
    ax.text(-1.40, 1.24,
            "$J=0$:  below\n"
            "$J=1$:  $(-90,0)^{\\circ}$\n"
            "$J=2$:  equator\n"
            "$J=3$:  $(0,90)^{\\circ}$\n"
            "$J=4$:  above",
            ha="left", va="top", fontsize=6.6, color="#333333", linespacing=1.7)
    ax.text(0, -1.24,
            r"$c_J=-90+J\cdot W_V$;"
            "\n"
            r"$\mathrm{TB}(J)=\mathrm{round}(\tan c_J\cdot 10^{3})$;"
            "\n"
            r"odd $J$: $\mathrm{TB}(J{-}1)\,q<dz\cdot 10^{3}$"
            "\n"
            r"$<\mathrm{TB}(J{+}1)\,q$;  even $J$: $=$"
            "\n"
            r"$J\in\{0,2MV\}$: due below / above, only at $q=0$",
            ha="center", va="top", fontsize=6.4, color="#333333", linespacing=1.45)
    ax.set_title("(b) vertical: elevation sectors", pad=3)


def panel_degenerate(ax):
    """(c) q = 0: the full 3-D relation is unsatisfiable for every (I, J)."""
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(*XL)
    ax.set_ylim(*YL)

    ax.add_patch(Ellipse((0, -0.78), 1.55, 0.50, fill=False, edgecolor=C_EDGE,
                         lw=0.8, zorder=2))
    ax.add_patch(Ellipse((0, -0.78), 0.30, 0.10, facecolor="#e8e8e8",
                         edgecolor=C_EDGE, lw=0.6, zorder=3))
    ax.plot([0], [-0.78], marker="o", ms=5, color="k", zorder=6)
    ax.text(-0.14, -0.80, "$L$", fontsize=9, ha="right", va="center")
    ax.plot([0], [0.86], marker="s", ms=5, color=C_ACC, zorder=6)
    ax.text(0.14, 0.88, "$K$", fontsize=9, color=C_ACC, ha="left", va="center")
    ax.add_patch(FancyArrowPatch((0, -0.70), (0, 0.78), arrowstyle="-|>",
                                 mutation_scale=9, lw=1.2, color=C_ACC, zorder=5))
    ax.text(0.10, 0.10, r"$dz\neq 0$", fontsize=8, color=C_ACC, ha="left",
            va="center")
    th = [math.radians(t) for t in range(0, 360, 15)]
    ax.plot([0.46 * math.cos(t) for t in th],
            [-0.78 + 0.15 * math.sin(t) for t in th],
            color=C_WARN, lw=1.0, ls=(0, (2, 2)), zorder=4)
    ax.text(0, 1.34, r"$\mathrm{AZ}(dx,dy)$ undefined $\Rightarrow q=0$",
            ha="center", va="center", fontsize=7.4, color=C_WARN)
    ax.text(-1.38, 0.60,
            "projection collapses:\n"
            "$(dx,dy)=(0,0)$,\n"
            "so $q=0$",
            ha="left", va="top", fontsize=6.5, color="#333333", linespacing=1.6)
    ax.set_title("(c) degenerate case $q=0$", pad=3)
    ax.text(0, -1.26,
            "vertical part alone: $J=2MV$ (F2)\n"
            "horizontal part: false for every $I$\n"
            r"$\Rightarrow$ one\_sided3d$(\cdot,\cdot,\cdot,I,J)$ false $\forall\,(I,J)$",
            ha="center", va="top", fontsize=6.5, color="#333333")


def fig_sectors():
    fig, axes = plt.subplots(1, 3, figsize=(7.10, 3.05))
    panel_horizontal(axes[0])
    panel_vertical(axes[1])
    panel_degenerate(axes[2])
    _save(fig, "phopa_fig_sectors")


# --------------------------------------------------------------------------
def _box(ax, x, y, w, h, text, fc="#ffffff", ec=C_EDGE, fs=6.6, tc="#000000",
         z=3):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=fc, edgecolor=ec, lw=0.8,
                           zorder=z))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            color=tc, zorder=z + 1, linespacing=1.35)


def _arrow(ax, p1, p2, color=C_EDGE, lw=0.8):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=7,
                                 lw=lw, color=color, shrinkA=0, shrinkB=0,
                                 zorder=2))


def fig_decomp():
    fig, ax = plt.subplots(figsize=(7.10, 3.55))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7.05)
    ax.axis("off")

    ax.text(0.02, 6.84, "naive encoding", fontsize=8, fontweight="bold",
            va="center", ha="left")
    ax.text(9.98, 6.84, r"ground bodies $\Theta(n\cdot S^{3})$", fontsize=7.4,
            va="center", ha="right", color=C_RAY)
    ax.add_patch(Rectangle((0.0, 4.62), 10.0, 2.06, facecolor="#fbfbfb",
                           edgecolor="#cccccc", lw=0.6, zorder=0))
    y0 = 5.62
    for i, lbl in enumerate(["xdist$(A,B,DX)$", "ydist$(A,B,DY)$",
                             "zdist$(A,B,DZ)$"]):
        x = 0.35 + i * 1.62
        _box(ax, x, y0, 1.45, 0.62, lbl + "\n" + r"$\Theta(S)$ per pair",
             fc="#eef3f9", fs=6.4)
        _arrow(ax, (x + 0.725, y0), (x + 0.725, y0 - 0.42))
    _box(ax, 0.35, 4.80, 4.54, 0.40,
         "three-way Cartesian join over $(DX,DY,DZ)$,\n"
         "expanded separately for every object pair",
         fc="#f7ecec", ec=C_RAY, fs=6.3, tc="#6d1119")
    _box(ax, 5.45, 4.80, 4.20, 0.40,
         r"geometry table os3d$(DX,DY,DZ,I,J)$" + "\n"
         r"size $\Theta(S^{3})$, materialised per pair",
         fc="#f7ecec", ec=C_RAY, fs=6.3, tc="#6d1119")
    _arrow(ax, (4.89, 5.00), (5.45, 5.00), color=C_RAY)
    ax.text(7.55, 5.40, r"$n$ ordered pairs $\times S^{3}$ offsets", fontsize=6.4,
            ha="center", color=C_RAY)

    ax.text(0.02, 4.32, "projection-decomposed encoding (proj)", fontsize=8,
            fontweight="bold", va="center", ha="left")
    ax.text(9.98, 4.32,
            r"ground bodies $\Theta(p\cdot S^{2})+\Theta(p\cdot S)$",
            fontsize=7.4, va="center", ha="right", color=C_ACC)
    ax.add_patch(Rectangle((0.0, 0.30), 10.0, 3.82, facecolor="#fbfbfb",
                           edgecolor="#cccccc", lw=0.6, zorder=0))

    _box(ax, 0.35, 3.30, 2.55, 0.62,
         "P1  conditional orientation\nvariables\n"
         r"need\_yaw$(K)$ / need\_pitch$(K)$", fc="#f2f7ee", ec="#6f8f5f", fs=6.1)
    _box(ax, 3.30, 3.30, 2.55, 0.62,
         "P2  shared horizontal table\n"
         r"hd$(A,B,Q)$ :- need\_vec$(A,B)$,\n"
         r"xdist, ydist, q$(DX,DY,Q)$", fc="#eef3f9", ec=C_ACC, fs=6.1)
    _box(ax, 3.30, 2.36, 2.55, 0.62,
         "P3  shared squared horizontal\n"
         r"distance  nd2$(A,B,U)$," + "\n" + r"$U=DX^{2}+DY^{2}$",
         fc="#eef3f9", ec=C_ACC, fs=6.1)
    _arrow(ax, (2.90, 3.61), (3.30, 3.61))
    ax.text(1.62, 1.72,
            "each unordered pair contributes\n"
            "at most two ordered pairs, so\n"
            r"$p\leq\min(2n,N^{2})$; the shared\n"
            "table is built once per grid",
            fontsize=6.2, ha="center", va="center", color="#333333")

    _box(ax, 6.35, 3.30, 1.55, 0.62, "zdist$(A,B,DZ)$\n" + r"$\Theta(S)$",
         fc="#ffffff", fs=6.3)
    _box(ax, 6.35, 2.36, 1.55, 0.62, "tb$(J)$ bounds\n" + r"$\Theta(MV)$",
         fc="#ffffff", fs=6.3)
    _box(ax, 8.10, 2.62, 1.70, 1.02,
         "1-D join\n"
         r"$\mathrm{TB}(J{\pm}1)\,Q$" + "\n"
         r"vs.  $DZ\cdot 10^{3}$" + "\n"
         r"dsq $=U+DZ^{2}$",
         fc="#eaf2ea", ec="#4f7a4f", fs=6.1)
    _arrow(ax, (5.85, 3.61), (6.35, 3.61))
    _arrow(ax, (5.85, 2.67), (6.35, 2.67))
    _arrow(ax, (7.90, 3.55), (8.10, 3.30))
    _arrow(ax, (7.90, 2.72), (8.10, 2.95))

    _box(ax, 3.30, 1.20, 6.50, 0.72,
         r"shared 2-D part:  $p\times\Theta(S^{2})$  (offsets $DX,DY$ only)"
         "\n"
         r"vertical / distance part:  $p\times\Theta(S)$  (1-D in $DZ$)"
         "\n"
         r"$\Rightarrow$ the cubic term $\Theta(n\cdot S^{3})$ is eliminated",
         fc="#ffffff", ec=C_ACC, fs=6.4, tc="#123f68")
    _arrow(ax, (8.95, 2.62), (8.95, 1.92), color=C_ACC)
    ax.text(5.0, 0.62,
            r"$n$ = constraints, $N$ = objects, $S$ = grid side, "
            r"$p$ = distinct ordered need\_vec object pairs",
            fontsize=6.4, ha="center", va="center", color="#444444")
    _save(fig, "phopa_fig_decomp")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    fig_sectors()
    fig_decomp()
