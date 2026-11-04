#!/usr/bin/env python3
"""Data-driven figures for the P-HOPA3D manuscript (vector PDF).

All numbers are read directly from the experiment logs; nothing is hard-coded
except axis cosmetics.
"""
import json
import math
import os
import statistics as st

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
LOGS = os.path.join(ROOT, "experiments", "logs")
RES = os.path.join(ROOT, "experiments", "results")
OUT = os.path.join(ROOT, "latex_pkg")
QA = os.path.join(RES, "figures", "qa")
os.makedirs(QA, exist_ok=True)

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["DejaVu Serif"],
    "mathtext.fontset": "dejavuserif",
    "font.size": 8,
    "axes.labelsize": 8,
    "axes.titlesize": 8.5,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 6.8,
    "axes.linewidth": 0.6,
    "lines.linewidth": 0.9,
    "pdf.fonttype": 42,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
})

C_NAIVE = "#b3202c"
C_PROJ = "#1f5c99"
GREY = "#4a4a4a"

VAR = ["naive", "naive_p1", "naive_p2", "naive_p3", "naive_p23", "proj"]
VARLBL = ["naive", "+P1", "+P2", "+P3", "+P2+P3", "proj"]
VARCOL = ["#b3202c", "#e0a03a", "#4f8f4f", "#8a6fb0", "#2f9e9e", "#1f5c99"]


def jl(name):
    return [json.loads(l) for l in open(os.path.join(LOGS, name))]


def save(fig, base):
    fig.savefig(os.path.join(OUT, base + ".pdf"))
    fig.savefig(os.path.join(QA, base + ".png"), dpi=150)
    plt.close(fig)
    print("wrote", base + ".pdf")


# --------------------------------------------------------------------------
def fig_scale():
    """E21 scale-boundary: ground bodies / peak RSS / grounding time vs S."""
    rows = jl("e21_scale_boundary.jsonl")
    fig, axes = plt.subplots(1, 3, figsize=(7.10, 2.30),
                             gridspec_kw={"wspace": 0.52})
    panels = [("n_bodies", "ground bodies (millions)", 1e6, "(a)"),
              ("peak_rss_kb", "peak RSS (MB)", 1024.0, "(b)"),
              ("t_ground", "grounding time (s)", 1.0, "(c)")]
    for ax, (key, ylab, sc, tag) in zip(axes, panels):
        for enc, col, mk in (("naive", C_NAIVE, "o"), ("proj", C_PROJ, "s")):
            r = sorted([x for x in rows if x["enc"] == enc], key=lambda z: z["S"])
            S = np.array([x["S"] for x in r], float)
            y = np.array([x[key] for x in r], float) / sc
            k, b = np.polyfit(np.log(S), np.log(y), 1)
            ax.plot(S, y, mk + "-", color=col, ms=3.4, lw=0.9, label=enc,
                    mfc=col, mec="white", mew=0.4)
            xs = np.linspace(S.min(), S.max(), 50)
            ax.plot(xs, np.exp(b) * xs ** k, ls="--", lw=0.8, color=col, alpha=0.75)
            ax.text(0.04, 0.94 if enc == "naive" else 0.10,
                    f"{enc}: $\\sim S^{{{k:.2f}}}$", transform=ax.transAxes,
                    fontsize=6.6, color=col, va="top")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("grid side $S$")
        ax.set_ylabel(ylab)
        ax.set_xticks([20, 30, 40, 50])
        ax.set_xticklabels(["20", "30", "40", "50"])
        ax.grid(True, which="major", lw=0.35, color="#dddddd")
        ax.set_title(f"{tag} {ylab}", pad=3)
    axes[0].legend(loc="lower right", frameon=False, ncol=1)
    save(fig, "phopa_fig_scale")


# --------------------------------------------------------------------------
def fig_ablation():
    """E8 six-variant ablation: ground rules per cell + normalised cost at 60@40^3."""
    rows = jl("e8_ablation.jsonl")
    cells = []
    for r in rows:
        c = (r["n_obj"], r["s"])
        if c not in cells:
            cells.append(c)

    def med(cell, var, key):
        v = [r[key] for r in rows if (r["n_obj"], r["s"]) == cell
             and r["variant"] == var and key in r]
        return st.median(v) if v else np.nan

    fig = plt.figure(figsize=(7.10, 2.55))
    ax = fig.add_axes([0.062, 0.20, 0.615, 0.70])
    ncell, nvar = len(cells), len(VAR)
    w = 0.80 / nvar
    for j, (v, lbl, col) in enumerate(zip(VAR, VARLBL, VARCOL)):
        xs = np.arange(ncell) + (j - (nvar - 1) / 2) * w
        ys = [med(c, v, "n_rules") / 1e6 for c in cells]
        ax.bar(xs, ys, width=w * 0.92, color=col, edgecolor="white", lw=0.25,
               label=lbl)
    ax.set_yscale("log")
    ax.set_xticks(np.arange(ncell))
    ax.set_xticklabels([f"{n}@{s}$^3$" for n, s in cells], fontsize=6.6)
    ax.set_ylabel("ground rules (millions, median of 4 seeds)")
    ax.set_xlabel("workload cell  ($N$ objects @ $S^3$ grid)")
    ax.grid(True, axis="y", lw=0.35, color="#dddddd")
    ax.set_axisbelow(True)
    ax.legend(ncol=3, loc="upper left", frameon=True, framealpha=0.92,
              edgecolor="#cccccc", handlelength=1.0, columnspacing=0.9,
              fontsize=6.2, borderpad=0.35)
    ax.set_title("(a) separated ablation of P1 / P2 / P3 (E8)", pad=3)

    ax2 = fig.add_axes([0.735, 0.20, 0.25, 0.70])
    cell = (60, 40)
    x = np.arange(len(VAR))
    base_g = med(cell, "naive", "t_ground")
    base_r = med(cell, "naive", "peak_rss_kb")
    base_b = med(cell, "naive", "n_bodies")
    g = [med(cell, v, "t_ground") / base_g for v in VAR]
    rr = [med(cell, v, "peak_rss_kb") / base_r for v in VAR]
    bb = [med(cell, v, "n_bodies") / base_b for v in VAR]
    ax2.bar(x - 0.27, g, width=0.26, color="#6d6d6d", label="grounding time")
    ax2.bar(x, rr, width=0.26, color="#c8791a", label="peak RSS")
    ax2.bar(x + 0.27, bb, width=0.26, color="#1f5c99", label="ground bodies")
    ax2.axhline(1.0, color=C_NAIVE, lw=0.7, ls=":")
    ax2.set_xticks(x)
    ax2.set_xticklabels(VARLBL, rotation=90, fontsize=6.2)
    ax2.set_ylabel("ratio to naive")
    ax2.set_ylim(0, 1.18)
    ax2.grid(True, axis="y", lw=0.35, color="#dddddd")
    ax2.set_axisbelow(True)
    ax2.legend(frameon=False, loc="upper center", ncol=3, fontsize=6.0,
               handlelength=1.0, columnspacing=0.9,
               bbox_to_anchor=(0.42, -0.30))
    ax2.set_title("(b) heaviest cell 60@40$^3$", pad=3)
    save(fig, "phopa_fig_ablation")


# --------------------------------------------------------------------------
def fig_effect():
    """E1b full: paired per-instance ratio distributions over the 16 cells."""
    eff = json.load(open(os.path.join(RES, "e1b_effect_sizes.json")))
    keys = sorted(eff.keys(),
                  key=lambda k: (int(k.split("x")[0]), int(k.split("x")[1]),
                                 k.split("x")[2]))
    fig, axes = plt.subplots(1, 2, figsize=(7.10, 3.05),
                             gridspec_kw={"wspace": 0.72})
    ylab = [f"{k.split('x')[0]}@{k.split('x')[1]}$^3$ "
            f"{'cons.' if k.endswith('consistent') and not k.endswith('inconsistent') else 'incons.'}"
            for k in keys]
    y = np.arange(len(keys))
    for ax, mk, cl, ttl, tag in (
            (axes[0], "total_ratio_median", "total_ratio_iqr",
             "(a) total time (grounding + solving)", "total"),
            (axes[1], "solve_ratio_median", "solve_ratio_iqr",
             "(b) solving time only", "solve")):
        m = np.array([eff[k][mk] for k in keys])
        lo = np.array([eff[k][cl][0] for k in keys])
        hi = np.array([eff[k][cl][1] for k in keys])
        cols = [C_PROJ if v <= 1.0 else C_NAIVE for v in m]
        ax.hlines(y, lo, hi, color="#999999", lw=1.0, zorder=1)
        ax.plot(m, y, "o", color="white", mec="none", ms=0.1)
        for yi, mi, c in zip(y, m, cols):
            ax.plot([mi], [yi], "o", color=c, ms=4.0, mec="white", mew=0.4,
                    zorder=3)
        ax.axvline(1.0, color="k", lw=0.7, ls="--")
        ax.set_yticks(y)
        ax.set_yticklabels(ylab, fontsize=6.2)
        ax.invert_yaxis()
        ax.set_xscale("log")
        ax.set_xlim(0.20, 6.0)
        ax.set_xticks([0.25, 0.5, 1, 2, 4])
        ax.set_xticklabels(["0.25", "0.5", "1", "2", "4"])
        ax.minorticks_off()
        ax.set_xlabel("paired ratio proj / naive (median, IQR)")
        ax.grid(True, axis="x", lw=0.35, color="#dddddd")
        ax.set_axisbelow(True)
        ax.set_title(ttl, pad=3)
        d = [eff[k]["cliff_" + tag] for k in keys]
        ax.text(0.97, 0.03,
                f"Cliff's $\\delta$:  min {min(d):+.2f} / max {max(d):+.2f}",
                transform=ax.transAxes, ha="right", va="bottom", fontsize=6.3,
                bbox=dict(fc="white", ec="#cccccc", lw=0.4, pad=1.4))
    axes[0].text(0.02, 0.97, "proj faster", transform=axes[0].transAxes,
                 fontsize=6.3, color=C_PROJ, va="top")
    axes[0].text(0.985, 0.97, "naive faster", transform=axes[0].transAxes,
                 fontsize=6.3, color=C_NAIVE, va="top", ha="right")
    save(fig, "phopa_fig_effect")


# --------------------------------------------------------------------------
def fig_backend():
    """E16 (distance sub-language) and E16b (full direction language): clingo vs z3."""
    e16 = jl("e16_z3_backend.jsonl")
    e16b = jl("e16b_z3_full.jsonl")

    fig, axes = plt.subplots(1, 2, figsize=(7.10, 2.65),
                             gridspec_kw={"wspace": 0.35})

    ax = axes[0]
    for mode, col, mk in (("consistent", C_PROJ, "o"), ("inconsistent", C_NAIVE, "^")):
        pts = [(r["clingo_t_solve"], r["z3_t_solve"]) for r in e16 if r["mode"] == mode]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        ax.plot(xs, ys, mk, color=col, ms=3.6, mec="white", mew=0.4,
                label=f"{mode} (SAT)" if mode == "consistent" else f"{mode} (UNSAT)")
    lim = [2e-3, 20]
    ax.plot(lim, lim, ls="--", lw=0.7, color=GREY)
    ax.text(0.97, 0.06, "parity", transform=ax.transAxes, ha="right",
            fontsize=6.3, color=GREY)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(lim)
    ax.set_ylim(lim)
    ax.set_xlabel("clingo proj solving time (s)")
    ax.set_ylabel("z3 QF_BV solving time (s)")
    ax.grid(True, which="major", lw=0.35, color="#dddddd")
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper left", fontsize=6.2)
    ax.set_title("(a) E16: distance sub-language,\n30/30 verdicts agree", pad=2)

    ax = axes[1]
    TO = 30.0
    for has, col, mk, lbl in ((True, C_NAIVE, "^", "with one_sided3d"),
                              (False, C_PROJ, "o", "distance only")):
        pts = [r for r in e16b if bool(r["has_dir"]) is has]
        xs = [r["clingo_t"] for r in pts]
        ys = [r["z3_t"] for r in pts]
        to = [(x, y) for x, y in zip(xs, ys) if y >= TO - 0.5]
        ok = [(x, y) for x, y in zip(xs, ys) if y < TO - 0.5]
        if ok:
            ax.plot([p[0] for p in ok], [p[1] for p in ok], mk, color=col,
                    ms=4.0, mec="white", mew=0.4, label=lbl + " (decided)")
        if to:
            ax.plot([p[0] for p in to], [TO] * len(to), "x", color=col, ms=4.6,
                    mew=1.0, label=lbl + " (z3 timeout)")
    ax.axhline(TO, color="k", lw=0.7, ls=":")
    ax.text(0.98, TO * 1.18, "z3 budget 30 s", transform=ax.get_yaxis_transform(),
            ha="right", va="bottom", fontsize=6.3)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(8e-4, 0.6)
    ax.set_ylim(0.03, 90)
    ax.set_xlabel("clingo proj total time (s)")
    ax.set_ylabel("z3 Array+BitVec time (s)")
    ax.grid(True, which="major", lw=0.35, color="#dddddd")
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="lower right", fontsize=6.0)
    ax.set_title("(b) E16b: full direction language,\n9/9 decidable verdicts agree", pad=2)
    save(fig, "phopa_fig_backend")


# --------------------------------------------------------------------------
def fig_discret():
    """E19: integer-vs-real elevation label divergence and its boundary shell."""
    d = json.load(open(os.path.join(LOGS, "e19_discretization.json")))
    res = {r["mv"]: r["variants"] for r in d["results"]}
    mvs = sorted(res)
    variants = ["canonical", "q_round", "tb4", "tb6"]
    vl = ["canonical ($q{=}\\lfloor\\sqrt{\\cdot}\\rfloor$, TB$=10^3$)",
          "$q\\_$round ($q$ rounded, TB$=10^3$)",
          "tb4 (TB$=10^4$)", "tb6 (TB$=10^6$)"]
    vc = ["#1f5c99", "#4f8f4f", "#c8791a", "#8a6fb0"]

    fig, axes = plt.subplots(1, 2, figsize=(7.10, 2.45),
                             gridspec_kw={"wspace": 0.42})
    ax = axes[0]
    n = len(variants)
    w = 0.80 / n
    x = np.arange(len(mvs))
    for j, (v, l, c) in enumerate(zip(variants, vl, vc)):
        ys = [100.0 * res[m][v]["rate_vs_real"] for m in mvs]
        ax.bar(x + (j - (n - 1) / 2) * w, ys, width=w * 0.92, color=c,
               edgecolor="white", lw=0.25, label=l)
    ax.set_xticks(x)
    ax.set_xticklabels([f"MV={m}\n$W_V={90 // m}^\\circ$" for m in mvs])
    ax.set_ylabel("divergence from exact real semantics (%)")
    ax.set_xlabel("elevation granularity  (S=30, 205,378 grid vectors)")
    ax.grid(True, axis="y", lw=0.35, color="#dddddd")
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=5.9, loc="upper left")
    ax.set_title("(a) divergence rate by variant", pad=3)
    ax.annotate("zero divergence", xy=(0.5, 0.12), xycoords=("data", "axes fraction"),
                fontsize=6.4, color="#2f6f2f", ha="center")

    ax = axes[1]
    stats = ["bwidth_deg_mean", "bwidth_deg_p90", "bwidth_deg_max"]
    sl = ["mean", "p90", "max"]
    groups = [("MV=3", 3), ("MV=5", 5)]
    x = np.arange(len(stats))
    w = 0.18
    for gi, (gl, mv) in enumerate(groups):
        for si, (v, c, hatch) in enumerate((("canonical", "#1f5c99", ""),
                                            ("q_round", "#4f8f4f", ""))):
            vals = [res[mv][v][s] for s in stats]
            ax.bar(x + (gi * 2 + si - 1.5) * w, vals, width=w * 0.94, color=c,
                   edgecolor="white", lw=0.25,
                   label=f"{gl} {v}" if True else None)
    ax.set_xticks(x)
    ax.set_xticklabels(sl)
    ax.set_ylabel("angular distance to nearest sector boundary ($^\\circ$)")
    ax.set_xlabel("percentile of the diverging vectors")
    ax.grid(True, axis="y", lw=0.35, color="#dddddd")
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=5.9, ncol=2, loc="upper left")
    ax.set_title("(b) divergences sit in a thin boundary shell", pad=3)
    save(fig, "phopa_fig_discret")


# --------------------------------------------------------------------------
def fig_case():
    """E11 semi-realistic harbour case: scene layout + missing-position candidate set."""
    case = json.load(open(os.path.join(LOGS, "e11_case.json")))
    names = {int(k): v for k, v in case["names"].items()}
    facts = os.path.join(ROOT, "experiments", "data", "e11", "e11_T1_facts.lp")
    pos = {}
    for line in open(facts):
        line = line.strip()
        if line.startswith("location(") and line.endswith(").") and ":-" not in line:
            a = [int(t) for t in line[len("location("):-2].split(",")]
            pos[a[1]] = (a[2], a[3], a[4])
    t3 = [t for t in case["tasks"] if t["task"] == "T3_missing_position"][0]
    cand = [tuple(c) for c in t3["cand_pos_21"]]
    true_pos = tuple(t3["true_pos_21"])

    groups = {
        "shore infrastructure": ([1, 2, 3, 4], "#6d6d6d", "o"),
        "quay cranes": ([5, 6, 7, 8], "#c8791a", "^"),
        "yard stacks": list(range(9, 17)),
        "vessels": ([17, 18, 19, 20, 21, 22, 27], "#1f5c99", "s"),
        "UAVs": ([23, 24, 25, 26], "#4f8f4f", "D"),
    }
    groups["yard stacks"] = (groups["yard stacks"], "#8a6fb0", "v")

    fig = plt.figure(figsize=(7.10, 3.00))
    fig.subplots_adjust(left=0.01, right=0.99, wspace=0.10)
    ax = fig.add_subplot(1, 2, 1, projection="3d")
    for lbl, (ids, col, mk) in groups.items():
        xs = [pos[i][0] for i in ids]
        ys = [pos[i][1] for i in ids]
        zs = [pos[i][2] for i in ids]
        ax.scatter(xs, ys, zs, c=col, marker=mk, s=17, depthshade=False,
                   edgecolors="white", linewidths=0.3, label=lbl)
    ax.set_xlabel("$x$")
    ax.set_ylabel("$y$")
    ax.set_zlabel("$z$")
    ax.set_xlim(0, 50)
    ax.set_ylim(0, 50)
    ax.set_zlim(0, 26)
    ax.set_box_aspect((1, 1, 0.52))
    ax.view_init(elev=22, azim=-58)
    ax.tick_params(labelsize=6)
    ax.xaxis.pane.set_alpha(0.06)
    ax.yaxis.pane.set_alpha(0.06)
    ax.zaxis.pane.set_alpha(0.06)
    ax.legend(frameon=False, fontsize=5.8, loc="upper left", ncol=2,
              handletextpad=0.2, columnspacing=0.8)
    ax.set_title("(a) semi-realistic harbour scene,\n"
                 "27 objects / 74 machine-derived constraints",
                 fontsize=7.6, pad=0)

    ax2 = fig.add_subplot(1, 2, 2, projection="3d")
    zs = sorted({c[2] for c in cand})
    cmap = plt.get_cmap("Blues")
    for i, z in enumerate(zs):
        pts = [c for c in cand if c[2] == z]
        ax2.scatter([p[0] for p in pts], [p[1] for p in pts], [z] * len(pts),
                    c=[cmap(0.45 + 0.5 * i / max(1, len(zs) - 1))], marker="s",
                    s=52, depthshade=False, edgecolors="#333333", linewidths=0.3,
                    label=f"$z={z}$" if len(zs) <= 5 else None)
    ax2.plot([true_pos[0], true_pos[0]], [true_pos[1], true_pos[1]],
             [0.15, 1.0], color="#b3202c", lw=1.0, zorder=9)
    ax2.scatter([true_pos[0]], [true_pos[1]], [0.15], c="#b3202c",
                marker="*", s=150, depthshade=False, edgecolors="white",
                linewidths=0.4, label="ground truth $(28,16,1)$")
    ax2.set_xlabel("$x$")
    ax2.set_ylabel("$y$")
    ax2.set_zlabel("$z$")
    ax2.set_xlim(25, 32)
    ax2.set_ylim(13, 20)
    ax2.set_zlim(0, 6)
    ax2.set_box_aspect((1, 1, 0.85))
    ax2.view_init(elev=24, azim=-62)
    ax2.tick_params(labelsize=6)
    ax2.xaxis.pane.set_alpha(0.06)
    ax2.yaxis.pane.set_alpha(0.06)
    ax2.zaxis.pane.set_alpha(0.06)
    ax2.legend(frameon=False, fontsize=5.8, loc="upper left", ncol=2,
               handletextpad=0.2, columnspacing=0.8)
    ax2.set_title("(b) T3: 13 brave-inferred candidate cells\n"
                  "for the transiting ship; ground truth retained",
                  fontsize=7.6, pad=0)
    save(fig, "phopa_fig_case")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    fig_scale()
    fig_ablation()
    fig_effect()
    fig_backend()
    fig_discret()
    fig_case()
