# -*- coding: utf-8 -*-
"""Patch 6: write E14/E15/E16 results into the paper (iter_3 Critical #2,
High-Risk #1/#2 responses). Exact-anchor replacements; each asserts count==1."""
P = "/mnt/wisdisk-prod/agents/99879a279ec44eb989d8c38e80227bec/universal_run-99879a279ec44eb989d8c38e80227bec/artifacts/phopa3d-paper/phopa3d_paper.md"
src = open(P, encoding="utf-8").read()
orig_len = len(src)

def rep(old, new):
    global src
    c = src.count(old)
    assert c == 1, f"anchor count {c} (expected 1): {old[:60]!r}"
    src = src.replace(old, new)

# ---------------------------------------------------------------- Edit 1
# §6.2: insert E14 high pair-reuse block between E9b and E7 paragraphs.
rep(
"naive_shared 的全部非删失运行与 naive/proj verdict 零分歧。\n\n**大网格内存前沿（E7，探索性）**",
"""naive_shared 的全部非删失运行与 naive/proj verdict 零分歧。

**高对象对重用工作负载（E14）**：E9b 承认其密度扫描把每对约束数 n/p 稳定在 1.5–1.8、始终未触及 naive_shared 与 naive 的解析交叉区（n/p>2），该区间上的表现此前依赖 §4.3 的结构分析而非实测。E14 直接构造该工作负载补上实测：固定 12 个对象、12 个有序对象对，每对堆叠 r∈{2,4,8} 条约束（one_sided3d/dist_rel/distance_range/azim_range 循环，realized n/p=1.92/3.83/8.0），S=30、3 个 seed，三编码同实例配对运行（RLIMIT_AS=3GB，timeout=120s；完整表见附录 D.5）。结果验证并强化了结构预测：naive_shared 的 ground rules 相对 naive 的比率从 r=2 的 1.85× 经 r=4 的 1.95× 降到 r=8 的 0.93×——解析交叉确实发生在 n/p≈8，此时共享三路表被足够多的约束摊薄；但即便在交叉点，naive_shared 仍被 proj 支配且自身崩溃：r=8 时其 peak RSS 达 naive 的约 4.5×（1787 vs 398MB）、总时间 100.9s（naive 17.8s、proj 8.9s），并在 r=4 与 r=8 各触发一次求解 TIMEOUT。proj 则在全部重用水平上稳定最优——ground rules 为 naive 的 1/3.8–1/7.7、总时间与 peak RSS 均最低、零删失。这与本节结论一致：连接共享只在极端重用下略微改善 rules 计数，却以内存与求解时间为代价；投影分解因消除 S³ 主导项，其优势与对象对重用度无关。E14 把 E9b 留下的“交叉区依赖结构分析”缺口补成了直接实测证据。

**大网格内存前沿（E7，探索性）**""")

# ---------------------------------------------------------------- Edit 2
# §6.4: insert E15 MV-granularity block between E11 case and 场景 A.
rep(
"不是真实部署有效性。\n\n**场景 A：UAV 海事监视**",
"""不是真实部署有效性。

**仰角粒度对应用推断的影响（E15）**：§3.6 F4 指出规范整数语义在 MV≤2 与实值语义零分歧、MV≥3 在扇区边界邻域出现 0.5%–11% 偏离（均匀随机向量审计）。一个自然的疑虑是：推荐的 MV≤2 是否过粗、不足以支撑 3D 应用？E15 在 E11 港口案例上把 MV 扫过 {1,2,3,5}，逐粒度记录（i）真实布局导出的全部 702 个有序对象对上 one_sided3d 仰角标签的整数-实值分歧率，（ii）T1 一致性、T2 故障定位、T3 缺失位置候选集、T5 析取判别的推断质量（完整表见附录 D.6）。两个发现：其一，分歧率在所有 MV∈{1,2,3,5} 上均为 0/702——港口几何的仰角集中在近水平（海面船舶与低空 UAV 之间），系统性避开 TB 定点 tan 的扇区边界，这与均匀随机审计的 0.5%–11% 形成对照，说明 F4 的偏离是边界局部现象、由具体几何是否触及边界决定，而非细粒度下必然发生；其二，更细的 MV=5 把 T3 过境轮的候选位置集从 13 收缩到 9（真值始终在候选集内），而 T1 唯一性、T2 精确定位（drop id 49）、T5 幽灵位排除在全部粒度下保持不变。即在本应用几何下，细化仰角粒度只带来推断精度的单调改善、不引入语义分歧——MV≤2 的推荐是保守下界而非能力上限；当应用几何触及扇区边界时，§3.6 F4 的偏离刻画与 §4.5 的定点算术审计给出何时需要更精确仰角判定的明确边界。

**场景 A：UAV 海事监视**""")

# ---------------------------------------------------------------- Edit 3
# New §6.6 (z3 backend) inserted after §6.5, before the ---/## 7 divider.
rep(
"""这直接回应"预处理成本是否被移出指标"的疑虑：它没有被隐藏，而是可忽略。

---

## 7. 讨论与局限""",
"""这直接回应"预处理成本是否被移出指标"的疑虑：它没有被隐藏，而是可忽略。

### 6.6 替代后端原型：z3 SMT 对照（E16）

§2.4 与 §7.2 论证了“纯 clingo + 预计算整数表”是有意的设计点，但一个合理的质疑是：投影分解的优势是否只在作者自定义的 clingo 编码空间内成立（即 naive 是稻草人、且未与真正不同的求解范式对照）？E16 给出最小可行的独立后端证据：用 z3 SMT 求解器在与 clingo 完全不同的求解范式下实现同一约束语义的可线性化子语言（location、direction、distance、distance_sq、distance_range、dist_rel），在 5 个 cell（S∈{15,20,30}、N∈{8,12,15,20}）× 2 模式（一致/不一致）× 3 seed = 30 个同实例上交叉验证判定与求解时间（完整表见附录 D.7）。

范围边界（诚实声明）：azimuth / one_sided3d / 仰角扇区被排除在 z3 后端之外，因为它们依赖 atan2 / tan / isqrt——超越且非线性的运算，SMT 整数/实数求解器无法直接表达。这一表达能力缺口恰恰是完整框架预计算规范整数表、留在 ASP 内的根本原因：替代后端只能覆盖距离/位置核心，而 ASP 表驱动编码覆盖完整的非线性方向语言。

编码发现：距离约束是非线性的（坐标差的平方）。z3 的非线性整数算术（QF_NIA）不完备——即便 8 对象/15³ 的实例也在 15s 超时返回 unknown。由于域是有限网格，我们改以定宽 BitVec（W=32）编码每个坐标、以有界位向量算术（QF_BV）编码每条约束，z3 经位爆炸（bit-blasting）即可判定（全部 cell <2s 完成）。这反过来印证了本文的中心设计点：网格的离散性是几何可解的来源——ASP 用预计算整数表利用它，SMT 后端用位爆炸利用它，而通用的实数/整数 SMT 公式则不能。

结果（中位数）：两个独立求解器家族在 30/30 实例上判定完全一致（0 分歧），这本身是对语义实现的额外交叉验证（独立于 §5.1 的三向验证）。求解时间上，clingo proj 在全部 15 个一致（SAT）实例上更快——中位 0.088s vs z3 的 1.51s（z3/clingo≈16×），因为预计算整数表把几何判定摊平为常数次表查找，而 z3 须对每个非线性距离约束做位爆炸；不一致（UNSAT）实例上两者接近（clingo 0.008s vs z3 0.011s，比率 1.65×），证伪由约束传播主导、两后端都迅速冲突。一个诚实注记：不一致模式下有 1 个 12×30 实例在投影到子语言后变为 SAT（原不一致性落在被排除的超越约束上），两后端对该实例同样判定一致（均 SAT）。结论：纯 clingo 表驱动设计点不是稻草环境——在可线性化子语言上，它相对一个真正独立的 SMT 后端不仅判定一致，且在 SAT 实例上求解更快；而完整方向语言（含超越运算）根本无法交给该 SMT 后端，这正是框架选择 ASP 的实质理由，而非便利。clingcon/外部原子混合后端对更大网格的潜在收益留作未来工作（§7.2）。

---

## 7. 讨论与局限""")

# ---------------------------------------------------------------- Edit 4
# §7.2: update backend-positioning closing sentence to reference §6.6.
rep(
"本文的消融与计量为这些替代后端提供了明确的对照基线；混合后端实现留作未来工作。",
"本文的消融与计量为这些替代后端提供了明确的对照基线；§6.6 的 z3 SMT 原型已对可线性化子语言做了最小可行的独立后端对照（30/30 判定一致、SAT 实例上 clingo 表驱动求解更快），证实纯 clingo 设计点不是稻草环境，同时暴露出完整方向语言（含 atan2/tan/isqrt 超越运算）无法直接交给 SMT/CP 整数求解器——这正是表驱动 ASP 的实质理由。clingcon/外部原子混合后端对更大网格的潜在收益留作未来工作。")

# ---------------------------------------------------------------- Edit 5
# §7.3: replace the "not measured" residual-risk clause with the E14 result.
rep(
"其二，扫描未覆盖每对约束数 >2 的高重用工作负载——那恰是 naive_shared 与 naive 的解析交叉区（§6.2），该区间上的表现依赖 §4.3 的结构分析而非实测。",
"其二，E10/E13 的密度与配比扫描未覆盖每对约束数 >2 的高重用工作负载——该缺口已由 E14（§6.2、附录 D.5）在 n/p=1.92/3.83/8.0 上实测补齐：naive_shared 的 rules 交叉确实发生在 n/p≈8，但即便在交叉点仍被 proj 支配、且自身 peak RSS 与求解时间崩溃，投影分解的优势与重用度无关。")

# ---------------------------------------------------------------- Edit 6
# Abstract: append the three boundary studies (E14/E15/E16).
rep(
"两个手工最小场景（析取感知判别、AABB 非重叠、谨慎/勇敢推理）作为表达能力示例保留。",
"两个手工最小场景（析取感知判别、AABB 非重叠、谨慎/勇敢推理）作为表达能力示例保留。三项边界研究进一步界定了主张的适用范围：高对象对重用工作负载（E14，n/p 至 8）实测了 naive_shared 与 naive 的解析交叉区，证实投影分解的优势与重用度无关；仰角粒度扫描（E15，MV=1–5）显示推荐粒度是保守下界、细化只单调改善推断且在应用几何下不引入语义分歧；一个独立的 z3 SMT 后端原型（E16）在可线性化子语言上与 clingo 判定 30/30 一致、且在 SAT 实例上 clingo 表驱动求解更快，证实纯 clingo 设计点不是稻草环境。")

# ---------------------------------------------------------------- Edit 7
# §8 conclusion: insert the three boundary studies before 未来工作.
rep(
"我们据此把框架定位为可扩展性机制。未来工作：",
"我们据此把框架定位为可扩展性机制。三项边界研究支撑该定位：高重用工作负载（E14）实测了 naive_shared 的解析交叉区并证实投影分解优势与重用度无关；仰角粒度扫描（E15，MV=1–5）表明推荐粒度是保守下界、细化只单调改善推断；一个独立的 z3 SMT 后端（E16）在可线性化子语言上判定 30/30 一致、且 SAT 实例上 clingo 表驱动更快，说明纯 clingo 设计点相对真正不同的求解范式仍然成立。未来工作：")

# ---------------------------------------------------------------- Edit 8
# §1.2 contributions: extend the empirical-study bullet with E14/E16.
rep(
"大网格压力测试（40³/50³，3GB 边界）与几何表冷启动成本计量（E12）。",
"大网格压力测试（40³/50³，3GB 边界）、几何表冷启动成本计量（E12）、高对象对重用工作负载（E14，n/p 至 8，实测 naive_shared 解析交叉区）、仰角粒度对应用推断的影响（E15，MV=1–5）与一个独立 z3 SMT 后端的 verdict 对照（E16，30/30 一致）。")

# ---------------------------------------------------------------- Edit 9
# Appendix A: add e16 script.
rep(
"`e15_mv.py`（MV 粒度应用影响，→ `logs/e15_mv.json`）；`hopa3d.gen_instance` 增加可选 `type_w` 参数（默认行为不变）",
"`e15_mv.py`（MV 粒度应用影响，→ `logs/e15_mv.json`）、`e16_z3_backend.py`（z3 SMT/BitVec 替代后端对照，→ `logs/e16_z3_backend.jsonl`）；`hopa3d.gen_instance` 增加可选 `type_w` 参数（默认行为不变）")

# ---------------------------------------------------------------- Edit 10
# Appendix A: add e14/e15/e16 logs.
rep(
"`e13_mix.jsonl`（24）、`audit_semantics.log`",
"`e13_mix.jsonl`（24）、`e14_pairreuse.jsonl`（27）、`e15_mv.json`、`e16_z3_backend.jsonl`（30）、`audit_semantics.log`")

open(P, "w", encoding="utf-8").write(src)
print(f"patch_text6 part A applied: {orig_len} -> {len(src)} chars (+{len(src)-orig_len})")
