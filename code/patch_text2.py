"""Text patch 2: §2 comparison table, §6.3 effect sizes, §5.2 metric hygiene."""
import pathlib

P = pathlib.Path("/mnt/wisdisk-prod/agents/99879a279ec44eb989d8c38e80227bec/universal_run-99879a279ec44eb989d8c38e80227bec/artifacts/phopa3d-paper/phopa3d_paper.md")
s = P.read_text()
n0 = len(s)

def rep(old, new):
    global s
    assert s.count(old) == 1, ("NOT UNIQUE/FOUND: " + old[:70], s.count(old))
    s = s.replace(old, new)

# ---- (a) §2.5 explicit comparison table (insert before "---\n\n## 3.") ----
anchor = "本文的贡献不是该一般技术，而是它对 3D 空间谓词的具体化（哪些中间表、在什么粒度上共享、与 need_vec 精确化如何配合）以及其收益的受控测量（§6.2 消融）。\n\n---"
assert anchor in s
table = """本文的贡献不是该一般技术，而是它对 3D 空间谓词的具体化（哪些中间表、在什么粒度上共享、与 need_vec 精确化如何配合）以及其收益的受控测量（§6.2 消融）。

### 2.5 定位对照表

| 系统/演算 | 维度 | 参考系 | 定性+定量混合 | 可执行求解 | 非单调修复 | 扩展对象 | grounding 规模研究 | 逐模型验证 |
|---|---|---|---|---|---|---|---|---|
| OPRA_m (Dylla & Wallgrün 2007) | 2D | 视角相关 | 否（纯定性） | 组合表推理 | 否 | schematized objects | — | — |
| 3D 卡片方向 / 锥体 / block algebra (Goyal–Egenhofer 2001; Balbiani et al. 1999) | 3D | 绝对 | 部分（区间定量） | CSP/表推理 | 否 | 区域/盒 | — | — |
| QSRLib / SparQ (Dylla et al. 2016; Wallgrün 2010) | 2D/3D | 依演算 | 否（定性为主） | 约束传播/组合表 | 否 | 依演算 | — | 单元测试 |
| clingcon / clingo 5 理论求解 (Ostrowski & Schaub 2012; Gebser et al. 2016) | — | — | 线性算术+ASP | 是（混合后端） | 依编码 | — | 惰性 grounding 可选 | — |
| HOPA (Izmirlioglu et al., AAAI 2025) | 2D | 视角相关+绝对混合 | 是 | 纯 clingo | 是 | 否（点对象） | 否 | 否 |
| **本文 P-HOPA3D** | 3D（离散网格） | yaw 相对水平 + 绝对仰角 | 是 | 纯 clingo（整数语义） | 是（继承） | AABB 占据/间距 | 是（核心贡献） | 是（三向交叉验证） |

据我们所知，"3D 混合方向/距离约束 + 纯 clingo 整数语义 + grounding 分解与规模计量 + 逐模型独立验证"的组合此前未被同时给出；单列上的每一成分均有先行工作（表中已标注），本文不主张它们各自的原创性。

---"""
s = s.replace(anchor, table)

# ---- (b) §5.2 metric hygiene ----
rep("指标定义：**t_ground** 为 ctl.ground 墙钟时间；**t_solve** 为从开始求解到首个模型/穷尽证明的时间（一致性判定，不枚举）；**t_total** = t_ground + t_solve，是端到端主指标。",
    "指标定义：**t_ground** 为 ctl.ground 墙钟时间；**t_solve** 为从开始求解到首个模型/穷尽证明的时间（一致性判定，不枚举）；**t_total** = t_ground + t_solve，是端到端主指标。所有表格的 med 列均显式标注为 t_solve 中位或 t_total 中位；Δ 一律定义为 (naive−proj)/naive，正值代表投影编码更快。ground rules/bodies 取自 clingo --stats=2 的 statistics[\"problem\"][\"lpStep\"]（rules、bodies、rules_choice 字段）；该平台 lpStep 的 atoms 字段恒为 0，故 ground atoms 以 ctl.symbolic_atoms 遍历计数。时间指标均不含几何库表（geom.lp）的生成与解析：t_ground 从 ctl.ground 起算，包含 geom.lp 的解析在内由 clingo 一并完成；表文件本身的离线生成成本作为 cold-start 项在 §6.5 单独报告（cached 场景下跨实例复用，只付一次）。")

# ---- (c) §6.3 effect sizes paragraph ----
rep("工程建议：若应用以困难一致性求解/枚举/大网格为主，投影分解是明确正确的选择；若以亚秒级快速证伪为主且网格很小，naive 的求解中位数可能略低，但计入 grounding 后仍无优势。",
    """**效应量（配对比率分布）**：小样本 p 值之外，我们报告逐实例配对比率 proj/naive 的分布：总时间比率中位数在 16 个 cell 上为 0.36–0.84（IQR 最宽 [0.32,0.76]），Cliff's δ 全部 ≥0.73（10/16 个 cell 为 1.00，即无一实例反转）；求解时间比率中位数 0.39–4.05，Cliff's δ 介于 −0.80（100@30³ 不一致，naive 系统性更快）与 +0.73（60@20³ 一致）之间——效应量层面同样支持"总时间稳定占优、求解时间工作负载相关"的结论。逐 cell 数值见 results/e1b_effect_sizes.json。

工程建议：若应用以困难一致性求解/枚举/大网格为主，投影分解是明确正确的选择；若以亚秒级快速证伪为主且网格很小，naive 的求解中位数可能略低，但计入 grounding 后仍无优势。""")

P.write_text(s)
print("patch2 applied, delta chars:", len(s) - n0)
