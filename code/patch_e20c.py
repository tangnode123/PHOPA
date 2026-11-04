P = "/mnt/wisdisk-prod/agents/99879a279ec44eb989d8c38e80227bec/universal_run-99879a279ec44eb989d8c38e80227bec/artifacts/phopa3d-paper/phopa3d_paper.md"
s = open(P, encoding="utf-8").read()
orig = len(s)
def rep(old, new, n=1):
    global s
    c = s.count(old); assert c == n, f"count {c}!={n}: {old[:50]!r}"
    s = s.replace(old, new)

# ---- §7.3 threats: circularity/external validity now has real-data evidence ----
rep("但 E18 仍基于示意地理、未接入真实传感器量测，故应用 claim 止于半真实 proof-of-concept。",
    "E18 仍基于示意地理；该外部效度缺口由 E20（§6.4、附录 D.12）在真实 NOAA AIS 量测上部分弥合——"
    "真实船位/航向导出的 229 条约束在非循环粗差注入下故障定位 precision/recall=1.0、缺失位置唯一恢复（真值覆盖率 100%）。"
    "但 E20 是水面 2.5D（AIS 无高度），故 3D 仰角语义的真实数据验证仍缺，应用 claim 为“真实 2.5D proof-of-concept + 半真实 3D 演示”。")

# ---- §7.4 limitation (6) ----
rep("但地理仍为示意性、非真实传感器量测，故为 proof-of-concept 而非部署有效性验证。",
    "E20 进一步在真实 NOAA AIS 量测（纽约港 24 艘船、229 条导出约束）上完成一致性审计、非循环故障定位（precision/recall=1.0）"
    "与缺失位置唯一恢复，把应用验证从示意推进到真实 2.5D 数据；但水面 AIS 无高度，含真实高度的 3D 数据"
    "（ADS-B/3D 城市模型/室内定位）接入仍是未来工作，故为真实 2.5D proof-of-concept 而非完整 3D 部署验证。")

# ---- §8 conclusion: insert E20 sentence + update future work ----
rep("未来工作：增量/惰性 grounding 突破 50³ 内存墙、clingcon/外部原子混合后端、基于 AABB 区间语义的区域到区域方向关系、以及接入真实 AIS/3D 城市模型数据的应用验证。",
    "真实数据层面，E20 接入 NOAA MarineCadastre AIS（纽约港快照），把 24 艘真实船舶的位置/航向离散到度量网格、自动导出 229 条混合约束，"
    "在真实量测上完成一致性审计、非循环多错误故障定位（precision/recall/精确匹配率均 1.0）与缺失位置唯一恢复（真值覆盖率 100%），"
    "并显示真实约束图比合成生成器更集中于高重用对象对（p=64/229 条 vs 合成 135/225 条）——即投影分解收益最大的工作负载区间；"
    "水面 AIS 无高度，故为真实 2.5D 验证。未来工作：增量/惰性 grounding 突破 50³ 内存墙、clingcon/外部原子混合后端、"
    "基于 AABB 区间语义的区域到区域方向关系、以及接入含真实高度的 3D 空间数据（ADS-B/3D 城市模型/室内定位）的应用验证。")

# ---- Appendix A: register e20 ----
rep("→ `logs/e19_discretization.json`）；`hopa3d.gen_instance` 增加可选 `type_w` 参数（默认行为不变）",
    "→ `logs/e19_discretization.json`）、`e20_real_ais.py`（真实 NOAA AIS 纽约港 2.5D 案例：AIS→度量网格→混合约束→"
    "一致性/故障定位/缺失位置推断 + 真实 vs 合成分布对照，→ `logs/e20_real_ais.json`）；"
    "`hopa3d.gen_instance` 增加可选 `type_w` 参数（默认行为不变）")

# ---- Appendix D.12 table (insert before 参考文献) ----
D12 = (
"**D.12 E20：真实 NOAA AIS 纽约港 2.5D 案例（2023-01-01 05:20 UTC；24 艘船、网格 54×44×1、cell=200m；MH=3/MV=2/RA=RE=3）**\n\n"
"真实约束分布 vs 规模匹配合成实例（回答“投影分解收益是否只在作者生成器分布上成立”）：\n\n"
"| 维度 | 真实 AIS 工作负载 | 规模匹配合成实例 |\n"
"|---|---|---|\n"
"| 对象数 n_obj | 24 | 24 |\n"
"| 约束数 n_con | 229 | 225 |\n"
"| 有序 need_vec 对 p | 64 | 135 |\n"
"| 约束/对（重用度） | 3.58 | 1.67 |\n"
"| location 锚比例 | 0.583 | 0.708 |\n"
"| 类型分布 | one_sided3d 64 / distance_range 64 / azim_range 32 / dist_rel 31 / direction 24 / location 14 | one_sided3d 102 / distance_range 19 / dist_rel 31 / location 17 / direction 14 / direction_range 11 / distance_sq 8 / pitch 7 / pitch_range 8 / azim 4 / azim_range 4 |\n\n"
"grounding（真实 2.5D 实例，proj vs naive；新鲜进程、3GB 预算）：\n\n"
"| 编码 | verdict | ground atoms | ground rules | ground bodies | t_ground(s) | peak RSS(MB) |\n"
"|---|---|---|---|---|---|---|\n"
"| naive | SAT | 34,389 | 710,310 | 487,363 | 0.72 | 132 |\n"
"| proj | SAT | 99,515 | 785,543 | 284,210 | 0.81 | 132 |\n\n"
"注：sz=1 使 Θ(S³) 垂直连接退化，proj 的共享表原子开销（2.89×）无法被摊销，但连接体更少（0.58×）；"
"投影分解的 grounding 收益是 3D 特有的（见 §6.2 合成 3D 基准），2.5D 真实数据用于验证语言与任务而非 3D 加速。\n\n"
"真实数据任务结果：\n\n"
"| 任务 | 设置 | 结果 |\n"
"|---|---|---|\n"
"| 一致性审计 | clean 真实约束集（229 条） | Python 验证器 ✓ 且 clingo SAT（双向一致） |\n"
"| 多错误故障定位 | k∈{1,2,3} 粗差、2 seeds；感知可废止 / 世界知识 mandatory | precision=recall=精确匹配率=1.0（全部 k）；每次约 11 个等成本最优模型一致指向同一修复集；求解 4.9–15.1s |\n"
"| 缺失位置推断 | 移除 3 个目标的 location 锚、保留其 kNN 感知 | 候选集均唯一（cand=1）且=真实格元；真值覆盖率 100%；求解 <0.6s |\n\n"
"数据 provenance：NOAA MarineCadastre AIS（marinecadastre.gov），2023-01-01 全天文件，按 BBOX(40.58–40.72N, 74.10–73.97W) "
"切片得 82,092 条上纽约湾记录；E20 取 05:20:27 UTC 的 300s 快照。转换：等距柱面投影（1° lat=110,540m、1° lon=111,320·cos(40.68°)m）"
"→ 200m 方形格元；COG（罗经）→ 数学方位 (90−COG) mod 360 → RA=3 吸附。水面 AIS 无高度 → z=1（2.5D）。\n\n"
)
rep("## 参考文献", D12 + "## 参考文献")

open(P, "w", encoding="utf-8").write(s)
print("part3 ok, +%d chars, total %d" % (len(s)-orig, len(s)))
