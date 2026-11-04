import io, sys
P = "/mnt/wisdisk-prod/agents/99879a279ec44eb989d8c38e80227bec/universal_run-99879a279ec44eb989d8c38e80227bec/artifacts/phopa3d-paper/phopa3d_paper.md"
s = open(P, encoding="utf-8").read()
orig_len = len(s)
def rep(old, new, n=1):
    global s
    c = s.count(old)
    assert c == n, f"anchor count {c}!={n}: {old[:60]!r}"
    s = s.replace(old, new)

# ---- 1) Abstract: append E20 real-data sentence ----
rep("并把它精化为一个可解性边界。",
    "并把它精化为一个可解性边界。真实数据层面，接入 NOAA MarineCadastre AIS（纽约港快照）构建真实 2.5D 案例：24 艘真实船舶位置/航向离散到度量网格、自动导出 229 条混合约束，clean 布局经独立验证器与 clingo 双向判定一致，非循环多错误故障定位（k∈{1,2,3} 粗差）precision/recall/精确匹配率均 1.0、缺失位置唯一恢复（真值覆盖率 100%），且真实约束图比合成生成器更集中于高重用对象对（p=64/229 条 vs 合成 135/225 条）——即投影分解收益最大的区间。")

# ---- 2) §1.1 venue positioning: real-data gap now partially closed by E20 ----
rep("但不构成对真实 AIS/GIS/轨迹数据部署有效性的主张；接入真实空间数据、并报告从连续坐标到网格约束的转换流程与误差影响，是本文最重要的未来工作之一。",
    "其本身不构成对真实数据部署有效性的主张；这一外部效度缺口已由 §6.4 的真实 NOAA AIS 纽约港案例（E20）部分弥合——它把真实船舶位置/航向经等距柱面投影离散到度量网格、自动导出 229 条混合约束，并在真实量测上完成一致性审计、非循环多错误故障定位（precision/recall=1.0）与缺失位置唯一恢复（真值覆盖率 100%）。水面 AIS 不含高度，故 E20 是真实 2.5D 案例；接入含真实高度的 3D 空间数据（ADS-B/3D 城市模型/室内定位）仍是未来工作。")

# ---- 3) §1.2 contributions: add E20 ----
rep("三者均不构成对真实 AIS/GIS 数据的部署有效性主张。",
    "在此基础上，E20 进一步接入真实 NOAA MarineCadastre AIS 数据（纽约港快照），把真实船位/航向离散到度量网格、自动导出 229 条混合约束，在真实量测上完成一致性审计、非循环多错误故障定位（k∈{1,2,3} 粗差下 precision/recall/精确匹配率均 1.0）与缺失位置唯一恢复（真值覆盖率 100%），并报告真实约束分布（高对象对重用、p=64/229 条）相对合成生成器的差异；水面 AIS 无高度，故为真实 2.5D 案例，含真实高度的 3D 数据接入留作未来工作。")

# ---- 4) §6 roadmap: add E20, bump appendix D range ----
rep("非循环鲁棒性 E18、离散化敏感性 E19）随主线就近呈现，其完整数据表统一收入附录 D（D.1–D.11）",
    "非循环鲁棒性 E18、离散化敏感性 E19、真实 AIS 数据案例 E20）随主线就近呈现，其完整数据表统一收入附录 D（D.1–D.12）")

open(P, "w", encoding="utf-8").write(s)
print("part1 ok, +%d chars" % (len(s)-orig_len))
