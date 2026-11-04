# -*- coding: utf-8 -*-
"""Patch 6d: restructure two bold-dense glossary paragraphs (§5.1 verifier
independence, §5.2 metric definitions) into bullet lists -> <=1 bold per para."""
P = "/mnt/wisdisk-prod/agents/99879a279ec44eb989d8c38e80227bec/universal_run-99879a279ec44eb989d8c38e80227bec/artifacts/phopa3d-paper/phopa3d_paper.md"
lines = open(P, encoding="utf-8").read().split("\n")

new_288 = """**验证器独立性审计（诚实界定）。** 三向交叉验证的三条腿独立性并不均等，需明确区分：

- 共享代码路径：生成器（_make_basic）与 Python 验证器（check_basic/check_all）都调用 hopa3d.py 中的同一组几何原语（elev_sector、horiz_sector、az_table、Layout.geom、DIST_RELS）——因此“生成器标签 ↔ Python 验证器”这一腿不是完全独立：若这些原语本身有系统性偏差，二者会一致地错。
- ASP 编码腿：naive.lp 与 proj.lp 用 clingo 的规则/连接重新实现同一语义，与 Python 原语无共享代码（不同语言、不同求值机制），verdict 一致性因而是跨实现的强约束。
- 实值参照腿：§3.6 F4 用 hypot/atan2（双精度连续几何）而非 isqrt/定点 TB 重新实现仰角分类，与网格规范原语算法独立，其零分歧（MV≤2，247 万向量）排除了原语与连续几何的系统性偏离。

据此，本文的措辞是“cross-validated implementation（跨实现交叉验证）”而非“第三方认证”；生成器与验证器共享几何原语这一点已如实记录，独立性主要由 ASP 编码腿与实值参照腿承担。"""

new_310 = """指标定义（时间指标严格分段、互不重叠）：

- **t_ground**：ctl.ground 的墙钟时间（grounding 本身，不含解析/加载）。
- **t_solve**：从开始求解到首个模型/穷尽证明的时间（一致性判定，不枚举）。
- **t_total** = t_ground + t_solve，端到端主指标。

几何库表（geom.lp）、实例（inst.lp）与编码（.lp）的解析/加载发生在 ctl.load 阶段，不计入任何报告的时间；表文件本身的离线生成成本作为 cold-start 项在 §6.5 单独报告（cached 场景下跨实例复用，只付一次）。所有表格的 med 列均显式标注为 t_solve 中位或 t_total 中位；Δ 一律定义为 (naive−proj)/naive，正值代表投影编码更快。ground rules/bodies 取自 clingo --stats=2 的 statistics["problem"]["lpStep"]（rules、bodies、rules_choice 字段）；该平台 lpStep 的 atoms 字段恒为 0，故 ground atoms 以 ctl.symbolic_atoms 遍历计数。删失（censoring）处理：TIMEOUT/MEMKILL 在时间中位数中以 t_eff = timeout 计入，但每个 cell 同时报告删失计数 (naive/proj)；删失分布不对称时不对中位数差做强结论，改以存活计数/比率陈述。统计检验：逐 cell Wilcoxon signed-rank（按 seed 配对，单侧 alternative：naive > proj），16 个 cell 上做 Holm–Bonferroni 多重比较校正，同时报告原始 p 与校正后显著性。"""

# locate the two paragraphs by unique prefix
i288 = next(i for i,l in enumerate(lines) if l.startswith("**验证器独立性审计（诚实界定）。**"))
i310 = next(i for i,l in enumerate(lines) if l.startswith("指标定义：**t_ground**"))
assert lines[i288].count("**")//2 >= 6, lines[i288][:40]
assert lines[i310].count("**")//2 >= 5, lines[i310][:40]
# replace (do the later index first so the earlier index stays valid)
lines[i310] = new_310
lines[i288] = new_288

open(P, "w", encoding="utf-8").write("\n".join(lines))
print(f"patch_text6d applied: restructured L{i288+1} and L{i310+1} into bullets")
