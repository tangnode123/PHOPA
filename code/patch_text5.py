#!/usr/bin/env python3
"""patch_text5.py -- iter_3 revision: scope/terminology/related-work/metric edits.
Exact-anchor replacements with assert count==1. No E16 numbers here (separate)."""
import io, sys

PAPER = "/mnt/wisdisk-prod/agents/99879a279ec44eb989d8c38e80227bec/universal_run-99879a279ec44eb989d8c38e80227bec/artifacts/phopa3d-paper/phopa3d_paper.md"
src = open(PAPER, encoding="utf-8").read()
n_edit = 0

def rep(old, new):
    global src, n_edit
    c = src.count(old)
    assert c == 1, f"anchor count {c} != 1 for: {old[:70]!r}"
    src = src.replace(old, new)
    n_edit += 1

# ---- Edit 1: title scope qualifier (Critical #4) ----
rep("# P-HOPA3D：面向离散三维混合空间推理的投影分解 ASP 框架",
    "# P-HOPA3D：面向重力对齐离散三维点/AABB 中心混合空间约束的投影分解 ASP 框架")
rep("**P-HOPA3D: A Cross-Validated, Projection-Decomposed ASP Framework for Discrete 3D Hybrid Spatial Reasoning**",
    "**P-HOPA3D: A Cross-Validated, Projection-Decomposed ASP Framework for Gravity-Aligned Discrete 3D Point/AABB-Center Hybrid Spatial Constraints**")

# ---- Edit 2: grid-canonical terminology in abstract (Minor #1) ----
rep("贡献在于给出其规范整数语义（canonical integer semantics，全部判定化归为整数算术与预计算查找表，无浮点运算）",
    "贡献在于给出其网格规范整数语义（grid-canonical integer semantics；此处“规范”是相对于本文的离散化规范与算术界限而言，并非相对于连续 3D 几何的“自然/唯一”语义——全部判定化归为整数算术与预计算查找表，无浮点运算）")

# ---- Edit 3: F2 relabel (Part 3 item 7) ----
rep("**(F2) 垂直 JEPD（命题，含退化情形）.** 对任意 MV≥1 与任意非零网格向量 (dx,dy,dz)≠(0,0,0)，恰好一个垂直扇区条件成立。",
    "**(F2) 垂直 JEPD（命题，含退化情形）.** 对任意 MV≥1 与任意非零网格向量 (dx,dy,dz)≠(0,0,0)，恰好一个垂直扇区条件成立。（说明：下文证明中“TB 严格递增”一步在受支持范围 MV≤30 内是**实测有界验证**——逐一核对相邻 TB 差 ≥52 远大于舍入步长——而非对任意 MV 的参数化证明；超出该范围需重新审计。）")

# ---- Edit 4: p definition (Part 3 item 6) ----
rep("设网格边长 S、对象数 N、约束数 n、参与向量约束的对象对数 p ≤ min(2n, N²)、垂直/距离约束数 n_v/n_d ≤ n：",
    "设网格边长 S、对象数 N、约束数 n、垂直/距离约束数 n_v/n_d ≤ n。**p 精确定义为 need_vec 登记的相异有序对象对数**：它计入 one_sided3d/dist_rel/distance/distance_range 的 L→K 登记、azim/azim_range 的反向 K→L 登记（二者方向相反，故同一对无向对象至多贡献 2 个有序对），以及 toinfer_os3d/toinfer_distrel/toinfer_pos 等查询派生的 need_vec；因此 p ≤ min(2n, N²)。下文所有 Θ(p·…) 均以此 p 为准：")

# ---- Edit 5: metric hygiene -- fix contradictory t_ground sentence (Part 3 item 6) ----
rep("时间指标均不含几何库表（geom.lp）的生成与解析：t_ground 从 ctl.ground 起算，包含 geom.lp 的解析在内由 clingo 一并完成；表文件本身的离线生成成本作为 cold-start 项在 §6.5 单独报告（cached 场景下跨实例复用，只付一次）。",
    "时间指标严格分段、互不重叠：几何库表（geom.lp）、实例（inst.lp）与编码（.lp）的**解析/加载发生在 ctl.load 阶段，不计入任何报告的时间**；**t_ground 仅计 ctl.ground 的墙钟时间**（grounding 本身，不含解析/加载）；**t_solve** 自 grounding 完成后起算至首个模型或穷尽证明；t_total = t_ground + t_solve。表文件本身的离线生成成本作为 cold-start 项在 §6.5 单独报告（cached 场景下跨实例复用，只付一次）。")

# ---- Edit 6: §2.4 expansion (Critical #1) ----
rep("需要承认，P2/P3 在技术上属于数据库查询优化中标准的 join factorization 思想——把多路连接拆为可共享的中间结果；本文的贡献不是该一般技术，而是它对 3D 空间谓词的具体化（哪些中间表、在什么粒度上共享、与 need_vec 精确化如何配合）以及其收益的受控测量（§6.2 消融）。",
    """需要承认，P2/P3 在技术上属于数据库查询优化中标准的 join factorization / 公共子表达式共享思想——把多路连接拆为可共享的中间结果（物化视图）；本文的贡献不是该一般技术，而是它对 3D 空间谓词的具体化（哪些中间表、在什么粒度上共享、与 need_vec 精确化如何配合）以及其收益的受控测量（§6.2 消融）。

更一般地，ASP 社区已有多条降低 grounding 成本的路线：惰性接地（lazy grounding，按需生成规则体而非一次性物化）、magic sets / 需求驱动改写、领域谓词与多轮（multi-shot）增量接地、约束 ASP（CASP）与 ASP modulo theories（如 clingcon、clingo-dl 把线性/差分约束交给专用理论求解器）、以及外部原子（procedural attachment）把判定委托给 Python。这些技术与本文正交且互补，但它们**不会自动得到 P2/P3 的结构收益**，原因有三：其一，惰性接地与 magic sets 优化的是“按需生成已写好的规则”，它们能削减不可达的接地，却无法改变一条已写成的三路连接规则在被需要时的 Θ(S³) 展开——本文的收益来自**重写连接结构本身**（把 S³ 三路积拆成与约束数无关的共享 2D 表 × 每对 Θ(S) 的一维连接），这是编码级代数变换而非接地调度；其二，CASP/clingcon 把线性算术移出接地，但本文的扇区判定含 atan2/tan/isqrt 等**非线性、超越**运算（§3.2），无法直接交给线性理论求解器，必须先离散为整数查找表——这正是“纯 clingo + 预计算整数表”设计点的由来；其三，外部原子在 grounding 期对地面项求值，位置为猜测变量时仍须枚举对象对×网格的笛卡尔积，回调成本反而侵蚀求解阶段（§7.2）。因此本文把 P2/P3 定位为**面向 3D 空间谓词、在纯 clingo 表驱动编码内的结构分解**，并以受控消融（§6.2）与一个独立后端原型（§6.6，z3 SMT 对照）共同界定其适用边界，而非主张一种通用接地优化器。""")

# ---- Edit 7: §3.3 vector-direction table (Minor #3) ----
rep("约束带唯一 id N，原子如下：",
    """约束带唯一 id N。下表先统一各二元谓词的**向量方向约定**（消除 §3.2 所述 azim 反向带来的实现/阅读歧义），再逐条给出语义：

| 谓词 | 参数向量 | 方向 | 备注 |
|---|---|---|---|
| one_sided3d(N,K,L,I,J) | (x_K−x_L, y_K−y_L, z_K−z_L) | L→K | 水平分量随 yaw(L) 旋转；need_vec(P,R) |
| same3d(N,K,L,I,J) | 朝向差（非位置向量） | — | 要求 pos(K)=pos(L) |
| dist_rel / distance / distance_sq / distance_range(N,K,L,…) | (x_K−x_L, …) | L→K（距离对称，方向不影响 dsq） | need_vec(P,R) |
| azim / azim_range(N,K,L,…) | (x_L−x_K, y_L−y_K) | **K→L（唯一反向）** | need_vec(R,P) |

原子语义如下：""")

# ---- Edit 8: §4.5 overflow safety-bound table (High-Risk #5) ----
rep("本平台的 clingo 5.8.2 整数运算在 2³¹ 处回绕（实测 10⁶×10⁶ = −727379968）。编码中所有乘积（LB·LB、UB·UB、D·D、DZ·1000、TB·Q、DX²+DY²+DZ²、角度乘积）必须保持在 2³¹−1 以内。据此：very_far 上哨兵取网格导出值而非 10⁶；TB 以 1000 倍定点表示（MV≤30 时 TB·Q ≤ 2.6×10⁶ 安全）；S≤50 时 dsq ≤ 7350、DZ·1000 ≤ 49000 均安全。E1b 调试过程定位并修复了该回绕导致的 very_far 误判（§5.3）。",
    """本平台的 clingo 5.8.2 整数运算在 2³¹ 处回绕（实测 10⁶×10⁶ = −727379968）。编码中所有乘积（LB·LB、UB·UB、D·D、DZ·1000、TB·Q、DX²+DY²+DZ²、角度乘积）必须保持在 2³¹−1 以内。据此：very_far 上哨兵取网格导出值而非 10⁶；TB 以 1000 倍定点表示；S≤50 时 dsq ≤ 7350、DZ·1000 ≤ 49000 均安全。E1b 调试过程定位并修复了该回绕导致的 very_far 误判（§5.3）。

下表给出各乘积项的**形式安全界限**（M=max(SX,SY,SZ)；要求每个量 < 2³¹−1 ≈ 2.147×10⁹），并据此界定受支持配置：

| 乘积项 | 上界（用 M、MV、距离档界 UB 表示） | 安全条件 | 受支持范围 |
|---|---|---|---|
| DZ·1000（仰角定点） | 1000·(M−1) | M ≤ 2.1×10⁶ | 远宽于实验范围 |
| TB·Q（仰角界×水平投影） | round(tan(c)·1000)·⌊√2·(M−1)⌋ ≈ 1000·√2·(M−1)（tan 在 MV≤30 内 ≤ tan(87°)≈19.1，但相邻界差 ≥52 保证可分辨） | MV≤30 且 M≤50 时 ≤ 2.6×10⁶ | MV≤30, S≤50 |
| DX²+DY²+DZ²（dsq） | 3·(M−1)² | M ≤ 26,756 | 远宽于实验范围 |
| UB²（very_far 上哨兵平方） | (⌊√(3(M−1)²)⌋+2)² ≈ 3(M−1)² | M ≤ 26,756 | 同上 |
| LB²/UB²（定性档界平方） | UB≤21（very_far 下界）或网格导出 ubinf | ubinf² < 2³¹−1 | S≤50 实测安全 |

**运行前审计工具**：实例生成侧（hopa3d.emit_facts）在写出 drel/tb 事实前对 ubinf²、TB·Q、dsq 逐项断言 < 2³¹−1，任一越界即抛错并拒绝生成该实例，而非静默回绕；这把“平台整数安全”从隐藏限制变为可机检的使用边界。超出 S≤50 / MV≤30 的配置须重跑该审计。""")

# ---- Edit 9: §5.1 verifier-independence audit (High-Risk #3) ----
rep("Pilot E1a：240 个实例，4 变体（plain / disjunctive(25%,4) / extended(emax=1) / granularity(mh=mv=3)）× 2 模式 × 3 规模（N∈{5,10,20}），240/240 通过，124 个 SAT 模型全部通过独立验证。闸门在每次编码修改后重跑（共 3 次，均 100%）。",
    """Pilot E1a：240 个实例，4 变体（plain / disjunctive(25%,4) / extended(emax=1) / granularity(mh=mv=3)）× 2 模式 × 3 规模（N∈{5,10,20}），240/240 通过，124 个 SAT 模型全部通过独立验证。闸门在每次编码修改后重跑（共 3 次，均 100%）。

**验证器独立性审计（诚实界定）。** 三向交叉验证的三条腿独立性并不均等，需明确区分。**共享代码路径**：生成器（_make_basic）与 Python 验证器（check_basic/check_all）都调用 hopa3d.py 中的同一组几何原语（elev_sector、horiz_sector、az_table、Layout.geom、DIST_RELS）——因此“生成器标签 ↔ Python 验证器”这一腿**不是完全独立**：若这些原语本身有系统性偏差，二者会一致地错。真正提供独立性的是另外两条腿：(i) **ASP 编码腿**——naive.lp 与 proj.lp 用 clingo 的规则/连接重新实现同一语义，与 Python 原语**无共享代码**（不同语言、不同求值机制），verdict 一致性因而是跨实现的强约束；(ii) **实值参照腿**——§3.6 F4 用 hypot/atan2（双精度连续几何）而非 isqrt/定点 TB 重新实现仰角分类，与网格规范原语**算法独立**，其零分歧（MV≤2，247 万向量）排除了原语与连续几何的系统性偏离。据此，本文的措辞是“cross-validated implementation（跨实现交叉验证）”而非“第三方认证”；生成器与验证器共享几何原语这一点已如实记录，独立性主要由 ASP 编码腿与实值参照腿承担。""")

# ---- Edit 10: §6.4 inexpressible-task stress (Critical #4) ----
rep("两个场景的 3D 可视化（扩展对象以半透明 AABB 绘制、朝向以箭头绘制）见实验产物 figures/e4_A_uav_maritime.png 与 e4_B_warehouse.png。E4 的两个手工场景与 E11 的港口案例构成互补的表达能力证据链：前者是可逐条阅读的最小示例（463 个 answer set 全量验证），后者是 27 对象、74 条机器导出约束、5 类任务的半真实工作负载。我们仍未在真实地理空间数据（AIS 轨迹、3D 城市模型、室内导航数据集）上验证——E11 的地理是示意性的；该缺口列入 §7.4 局限。",
    """两个场景的 3D 可视化（扩展对象以半透明 AABB 绘制、朝向以箭头绘制）见实验产物 figures/e4_A_uav_maritime.png 与 e4_B_warehouse.png。E4 的两个手工场景与 E11 的港口案例构成互补的表达能力证据链：前者是可逐条阅读的最小示例（463 个 answer set 全量验证），后者是 27 对象、74 条机器导出约束、5 类任务的半真实工作负载。我们仍未在真实地理空间数据（AIS 轨迹、3D 城市模型、室内导航数据集）上验证——E11 的地理是示意性的；该缺口列入 §7.4 局限。

**表达能力边界（负例 stress test）。** 为主动界定标题/摘要中“3D 混合空间约束”的范围、避免读者误以为本框架覆盖一般 3D 空间推理，下表列出**当前语言无法表达**的任务类别及其根因——这些是有意的非目标（§3.4、§3.6），而非待修缺陷：

| 不可表达任务 | 根因 | 当前框架的最近能力 |
|---|---|---|
| 区域到区域方向（“A 楼在 B 楼的西北方”，按 AABB 面/角而非中心） | 方向谓词一律 center-based（§3.4） | 仅中心点方向 + AABB 占据/非重叠/min_gap |
| 完整 3D 姿态相关自我中心方向（roll/pitch 旋转方向扇区） | one_sided3d 视点依赖只经由 yaw；pitch 不旋转扇区（§3.1） | yaw 相对水平扇区 × 重力对齐绝对仰角扇区 |
| 拓扑关系（连通/包含/相邻，RCC-8 式） | 语言无拓扑谓词 | AABB 非重叠（一种特例占据约束） |
| 连续空间 / 任意实数坐标 | 域是离散网格 [1,S]³（§3.1） | 网格规范整数语义；细粒度仰角为设计偏离（§3.6 F4） |
| 旋转对象（OBB）非重叠 | extent 限于轴对齐 AABB（§7.4） | 轴对齐盒占据 |
| 组合表 / 弱组合封闭推理、converse 运算 | 非目标（§3.6） | 约束求解式一致性检查/修复/推断 |

这张表与标题限定词（“重力对齐”“点/AABB 中心”）共同界定 scope：本框架是 gravity-aligned、yaw-relative、point/AABB-center 的离散 3D 混合空间**约束**系统，不主张完整 3D 姿态感知或区域方向推理。""")

# ---- Edit 11: §5.2 add E14/E15 bullets (experiment matrix) ----
rep("- **E12 几何库表冷启动成本**：S∈{20,30,40,50} 下 geom.lp 的生成时间、文件大小、事实数、冷/热加载解析时间。",
    """- **E12 几何库表冷启动成本**：S∈{20,30,40,50} 下 geom.lp 的生成时间、文件大小、事实数、冷/热加载解析时间。
- **E14 高对象对重用工作负载**：S=30、n_obj=12、固定 12 个相异有序对象对、每对堆叠 r∈{2,4,8} 条向量约束（实现 n/p≈2/4/8，覆盖 E9b 未触及的 n/p>2 交叉区），3 seeds，naive / naive_shared / proj 三编码同实例配对，记录 ground rules、peak RSS、t_ground/t_solve/t_total 与 verdict。
- **E15 垂直粒度对应用推断质量的影响**：在 E11 港口案例上运行 MV∈{1,2,3,5}，记录全部 702 个有序对象对的网格规范整数仰角扇区与实值（hypot/atan2）参照扇区的分歧率、T1 唯一性、T2 故障定位正确性、T3 缺失位置候选集大小、T5 析取判别。""")

# ---- Edit 12: Appendix A add new scripts/logs ----
rep("- 语义审计：`audit_semantics.py` → `results/audit_semantics.json`（水平/垂直 JEPD 穷举、az 覆盖、规范 vs 实值仰角对照）",
    """- 语义审计：`audit_semantics.py` → `results/audit_semantics.json`（水平/垂直 JEPD 穷举、az 覆盖、规范 vs 实值仰角对照）
- 本轮新增实验脚本：`e14_pairreuse.py`（高重用工作负载，→ `logs/e14_pairreuse.jsonl`）、`e15_mv.py`（MV 粒度应用影响，→ `logs/e15_mv.json`）；`hopa3d.gen_instance` 增加可选 `type_w` 参数（默认行为不变）""")

open(PAPER, "w", encoding="utf-8").write(src)
print(f"patch_text5 applied {n_edit} edits; new length {len(src)} chars, {src.count(chr(10))+1} lines")
