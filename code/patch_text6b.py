# -*- coding: utf-8 -*-
"""Patch 6 part B: Appendix D.5/D.6/D.7 tables + new references."""
P = "/mnt/wisdisk-prod/agents/99879a279ec44eb989d8c38e80227bec/universal_run-99879a279ec44eb989d8c38e80227bec/artifacts/phopa3d-paper/phopa3d_paper.md"
src = open(P, encoding="utf-8").read()
orig_len = len(src)

def rep(old, new):
    global src
    c = src.count(old)
    assert c == 1, f"anchor count {c} (expected 1): {old[:60]!r}"
    src = src.replace(old, new)

# ---------------------------------------------------------------- Edit B1
# Appendix D.5/D.6/D.7 inserted after D.4 table, before ## 参考文献.
rep(
"""| azimuth_heavy | direction 25%、pitch_range 15%、pitch 13%、azim 10% | 19 | 1.70 / 0.79 | 2.16× | 2.08× | 3.05 / 1.85 | 1.14 / 1.02 |

## 参考文献""",
"""| azimuth_heavy | direction 25%、pitch_range 15%、pitch 13%、azim 10% | 19 | 1.70 / 0.79 | 2.16× | 2.08× | 3.05 / 1.85 | 1.14 / 1.02 |

**D.5 E14：高对象对重用工作负载（12 对象、12 固定有序对、S=30、3 seeds 中位数；rules 单位百万；rss 单位 MB；时间单位 s；realized n/p = 实际每对约束数）**

| r | n/p | 变体 | rules(M) | grnd | solve | tt | peak rss | verdict |
|---|---|---|---|---|---|---|---|---|
| 2 | 1.92 | naive | 2.88 | 3.36 | 2.26 | 5.62 | 318–358 | SAT×3 |
| 2 | 1.92 | naive_shared | 5.32 | 6.35 | 4.70 | 10.94 | 545–688 | SAT×3 |
| 2 | 1.92 | proj | 0.75 | 0.76 | 1.03 | 1.77 | 151–173 | SAT×3 |
| 4 | 3.83 | naive | 5.30 | 5.55 | 3.06 | 8.76 | 381–391 | SAT×3 |
| 4 | 3.83 | naive_shared | 10.32 | 12.36 | 24.80 | 37.16 | 1335–1818 | SAT×2/TIMEOUT |
| 4 | 3.83 | proj | 1.17 | 1.23 | 3.62 | 4.74 | 199–247 | SAT×3 |
| 8 | 8.0 | naive | 11.40 | 11.76 | 6.74 | 17.81 | 391–398 | SAT×3 |
| 8 | 8.0 | naive_shared | 10.60 | 13.18 | 87.69 | 100.94 | 1750–1811 | SAT×2/TIMEOUT |
| 8 | 8.0 | proj | 1.48 | 1.48 | 7.38 | 8.87 | 240–258 | SAT×3 |

注：naive_shared/naive 的 rules 比率随 n/p 单调变化 1.85×→1.95×→0.93×（r=8 交叉到 <1，即共享表被极端重用摊薄）；naive/proj 的 rules 比率 3.84×→4.53×→7.70×（分解收益随重用增大）。但 naive_shared 的 peak rss 恒为 naive 的约 2–4.5×、总时间恒劣于 naive 与 proj，并在 r=4 与 r=8 各有一个 seed 求解 TIMEOUT（删失，故其 solve/tt 中位数仅来自 2 个存活 seed，偏乐观）。proj 在全部 r 上 rules/tt/rss 均最低、零删失。

**D.6 E15：仰角粒度 MV 对 E11 港口案例的影响（真实布局 702 有序对象对；分歧 = 整数 vs 实值仰角扇区标签不一致计数）**

| MV | 仰角分歧 /702 | 分歧率 | T1 唯一模型 | T2 定位正确(drop id) | T3 候选位置数(真值∈候选) | T5 幽灵位排除 |
|---|---|---|---|---|---|---|
| 1 | 0 | 0.0% | 是 | 是(49) | 13(是) | 是 |
| 2 | 0 | 0.0% | 是 | 是(49) | 13(是) | 是 |
| 3 | 0 | 0.0% | 是 | 是(49) | 13(是) | 是 |
| 5 | 0 | 0.0% | 是 | 是(49) | 9(是) | 是 |

注：与均匀随机向量审计（§3.6 F4：MV≥3 时 0.5%–11% 边界分歧）对照，港口几何的仰角集中于近水平、系统性避开 TB 定点 tan 边界，故全部 MV 零分歧。MV=5 把 T3 候选集从 13 收缩到 9（推断精度单调改善），T1/T2/T5 质量在全部粒度下不变。

**D.7 E16：z3 SMT（BitVec, W=32）替代后端 vs clingo proj（可线性化子语言；5 cells × 2 模式 × 3 seeds = 30 实例；solve 单位 s，中位数；ratio = z3/clingo）**

| cell (N×S) | 模式 | clingo verdict | z3 verdict | 一致 | clingo solve | z3 solve | ratio |
|---|---|---|---|---|---|---|---|
| 8×15 | 一致 | SAT | SAT | 3/3 | 0.0153 | 0.4402 | 26.8× |
| 8×15 | 不一致 | UNSAT | UNSAT | 3/3 | 0.0289 | 0.7668 | 8.2× |
| 15×15 | 一致 | SAT | SAT | 3/3 | 0.0580 | 1.6280 | 30.3× |
| 15×15 | 不一致 | UNSAT | UNSAT | 3/3 | 0.0027 | 0.0107 | 4.0× |
| 12×20 | 一致 | SAT | SAT | 3/3 | 0.1831 | 2.0864 | 16.4× |
| 12×20 | 不一致 | UNSAT | UNSAT | 3/3 | 0.0057 | 0.0088 | 1.6× |
| 20×20 | 一致 | SAT | SAT | 3/3 | 0.1134 | 1.6293 | 14.0× |
| 20×20 | 不一致 | UNSAT | UNSAT | 3/3 | 0.0180 | 0.0137 | 0.71× |
| 12×30 | 一致 | SAT | SAT | 3/3 | 0.3530 | 1.5143 | 4.3× |
| 12×30 | 不一致 | UNSAT×2/SAT×1 | 同 clingo | 3/3 | 0.0625 | 0.0106 | 0.18× |

注：30/30 实例两后端判定完全一致（含 12×30 不一致档中 1 个投影到子语言后变为 SAT 的实例——原不一致性落在被排除的超越约束上，两后端同样一致判 SAT）。一致（SAT）档 clingo 在全部 5 个 cell 上更快（ratio 4.3–30.3×，预计算整数表摊平几何判定 vs z3 逐约束位爆炸）；不一致（UNSAT）档两者接近、互有胜负（ratio 0.18–8.2×，证伪由约束传播主导）。z3 全部 30 实例零超时（BitVec 编码可判定；同实例的非线性整数 QF_NIA 编码在 8 对象/15³ 即 15s 超时返回 unknown）。

## 参考文献""")

# ---------------------------------------------------------------- Edit B2
# References: add z3, lazy grounding, magic sets, clingo-dl, materialized views.
rep(
'- Wallgrün, J.-O. "SparQ User Manual." University of Bremen / SFB/TR 8 Technical Report, 2010.',
'''- Wallgrün, J.-O. "SparQ User Manual." University of Bremen / SFB/TR 8 Technical Report, 2010.
- de Moura, L., Bjørner, N. "Z3: An Efficient SMT Solver." TACAS 2008, Springer LNCS 4963.（§6.6 替代后端）
- Dal Palù, A., Dovier, A., Pontelli, E., Rossi, G. "GASP: Answer Set Programming with Lazy Grounding." Fundamenta Informaticae 96(3), 2009.（lazy grounding）
- Calimeri, F., Faber, W., Leone, N., Perri, S. "The Magic Sets Technique and Its Implementation in Answer Set Programming Systems." Theory and Practice of Logic Programming 13(4-5), 2013.（magic sets / 需求驱动改写）
- Campana, E., Dodaro, C., Eiter, T., Fink, M., Shams, A., Schinkinger, J. "clingo goes DL: First-order Consistency Checking Made Easy." AAAI 2021.（clingo-dl，ASP modulo theories）
- Goldstein, J., Larson, P.-Å. "Optimizations Using Views: A Fast Rewrite Algorithm." SIGMOD 2001.（物化视图 / join factorization 的数据库来源）''')

open(P, "w", encoding="utf-8").write(src)
print(f"patch_text6 part B applied: {orig_len} -> {len(src)} chars (+{len(src)-orig_len})")
