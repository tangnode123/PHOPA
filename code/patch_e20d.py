P = "/mnt/wisdisk-prod/agents/99879a279ec44eb989d8c38e80227bec/universal_run-99879a279ec44eb989d8c38e80227bec/artifacts/phopa3d-paper/phopa3d_paper.md"
s = open(P, encoding="utf-8").read()
orig = len(s)
def rep(old, new, n=1):
    global s
    c = s.count(old); assert c == n, f"count {c}!={n}: {old[:50]!r}"
    s = s.replace(old, new)

# ---- new §2.5 application-side related work; renumber table to §2.6 ----
APP = (
"### 2.5 空间数据质量、观测一致性与轨迹异常检测\n\n"
"本文的三类推理任务——观测一致性审计、过约束下的最小修正故障定位、欠约束下的缺失位置/朝向候选推断——"
"与空间信息科学中的一类经典问题同构：带误差的空间量测之质量评估与一致性检查。地理数据质量研究早已指出，"
"位置误差是空间数据的固有成分而非偶然噪声（Goodchild & Gopal 1989；Chrisman 1991），而对互相矛盾的量测做检测与修复"
"正是数据质量评估的核心算子。在海事/航空监视领域，AIS 与 ADS-B 轨迹的异常检测与数据质量清洗已形成专门文献"
"（Pallotta et al. 2013；Riveiro et al. 2018）：典型任务包括识别报告位置/航向与其他观测或先验相矛盾的船舶、"
"在缺报或错报下重建可信态势。这类工作多以统计/机器学习方法在连续轨迹上进行；本文提供一条互补的符号化路线——"
"把离散化后的方位/距离/位置观测表达为定性-定量混合约束，用 ASP 答案集语义同时得到（i）冲突的可解释最小修正集"
"（drop/violated 的非单调层）、（ii）缺失对象位置的候选枚举（brave reasoning），二者天然带可解释性与可枚举性。"
"§6.4 的真实 NOAA AIS 案例（E20）正是沿这条路线，把真实船位/航向转为约束并在其上执行故障定位与缺失位置恢复，"
"以衔接本文的形式化贡献与上述应用文献。室内定位与多源量测融合中的约束式求解（以有限域约束/CP 表达测距、方位与地图约束）"
"是另一相邻方向；与之以有限域 CSP/CP-SAT 表约束实现定性演算的工作相比，本文的差异在于纯 clingo 整数语义、"
"非单调修复与逐模型独立验证的组合（§2.3、§2.6 对照表）。\n\n"
"### 2.6 定位对照表"
)
rep("### 2.5 定位对照表", APP)

# ---- §1.3 structure: 四个方面 -> 五个方面 ----
rep("第 2 节从四个方面定位相关工作", "第 2 节从五个方面定位相关工作")

# ---- add references (append before the final reference line anchor) ----
rep("- Goldstein, J., Larson, P.-Å. \"Optimizations Using Views: A Fast Rewrite Algorithm.\" SIGMOD 2001.（物化视图 / join factorization 的数据库来源）",
    "- Goldstein, J., Larson, P.-Å. \"Optimizations Using Views: A Fast Rewrite Algorithm.\" SIGMOD 2001.（物化视图 / join factorization 的数据库来源）\n"
    "- Goodchild, M.F., Gopal, S. \"The Accuracy of Spatial Databases.\" Taylor & Francis, 1989.（地理数据质量；空间误差作为数据成分）\n"
    "- Chrisman, N.R. \"The Error Component in Spatial Data.\" In GIS: Principles and Applications, Longman, 1991.（空间数据误差成分）\n"
    "- Pallotta, G., Vespe, M., Bryan, K. \"Vessel Pattern Knowledge Discovery from AIS Data: A Framework for Anomaly Detection and Identification.\" Entropy 15(6), 2013.（AIS 轨迹异常检测）\n"
    "- Riveiro, M., Pallotta, G., Vespe, M. \"Maritime Anomaly Detection: A Review.\" WIREs Data Mining and Knowledge Discovery 8(5), 2018.（海事异常检测综述；§2.5 应用侧）")

open(P, "w", encoding="utf-8").write(s)
print("part4 ok, +%d chars" % (len(s)-orig))
