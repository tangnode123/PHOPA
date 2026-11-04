"""Text patch 1: title/abstract/convention fixes per iter_2 review."""
import pathlib

P = pathlib.Path("/mnt/wisdisk-prod/agents/99879a279ec44eb989d8c38e80227bec/universal_run-99879a279ec44eb989d8c38e80227bec/artifacts/phopa3d-paper/phopa3d_paper.md")
s = P.read_text()
n0 = len(s)

def rep(old, new, cnt=1):
    global s
    assert s.count(old) >= 1, old[:60]
    s = s.replace(old, new, cnt)

# 1. English title
rep("**P-HOPA3D: A Validated, Projection-Decomposed ASP Framework",
    "**P-HOPA3D: A Cross-Validated, Projection-Decomposed ASP Framework")

# 2. Abstract: JEPD wording + explicit no-new-calculus
rep('这一"水平方位 + 绝对仰角"的分解在球坐标意义上是标准的；本文的贡献在于给出其规范整数语义（canonical integer semantics，全部判定化归为整数算术与预计算查找表，无浮点运算）、证明其扇区划分满足穷尽且互斥（JEPD，穷举审计 0 违例）、并给出投影分解 ASP 编码',
    '这一"水平方位 + 绝对仰角"的分解在球坐标意义上是标准的，本文不主张提出新的 3D qualitative calculus；贡献在于给出其规范整数语义（canonical integer semantics，全部判定化归为整数算术与预计算查找表，无浮点运算）、以命题与参数化证明刻画其扇区划分的穷尽互斥（JEPD）性质并以穷举机检审计验证实现（0 违例）、并给出投影分解 ASP 编码')

# 3. Abstract: "validated" -> "cross-validated" wording in 验证 part is already
#    三向交叉验证; check 摘要 uses "该方法学" - fine.

# 4. §1.1 positioning sentence
rep("因此本文的定位是一个经过严格验证的可执行框架（validated executable framework）",
    "因此本文的定位是一个经过三向交叉验证的可执行框架（cross-validated executable framework）")

# 5. §3.2 direction convention block after the vector display formula
rep("$$dx = x_K - x_L,\\quad dy = y_K - y_L,\\quad dz = z_K - z_L,\\quad q = \\lfloor\\sqrt{dx^2+dy^2}\\rfloor .$$",
    "$$dx = x_K - x_L,\\quad dy = y_K - y_L,\\quad dz = z_K - z_L,\\quad q = \\lfloor\\sqrt{dx^2+dy^2}\\rfloor .$$\n\n"
    "方向约定（全文统一）：one_sided3d、same3d、dist_rel/distance 系列与 toinfer 查询均以该 L→K 向量为参数；"
    "唯独 azim/azim_range 以反向向量 K→L（即 (x_L−x_K, y_L−y_K)）的绝对方位角为语义。"
    "ASP 编码层面该约定体现为 need_vec 的登记方向：one_sided3d(N,K,L,·,·) 登记 need_vec(P,R)（P=point(K)、R=point(L)，xdist(P,R)=x_K−x_L 即 L→K），"
    "azim(N,K,L,·) 登记 need_vec(R,P)（xdist(R,P)=x_L−x_K 即 K→L）；haz(A,B,ANG) 一律计算 (xdist(A,B),ydist(A,B)) 所构成向量的方位角。")

# 6. §1.2 contribution 1 wording (audit -> proposition + proof + machine-checked audit)
rep("水平与垂直扇区划分的 JEPD（jointly exhaustive, pairwise disjoint）性质经穷举审计验证",
    "水平与垂直扇区划分的 JEPD（jointly exhaustive, pairwise disjoint）性质以命题形式给出参数化证明，并由穷举机检审计验证实现")

# 7. §6.1 reference
rep("§3.6 的形式性质审计（JEPD 穷举 0 违例、MV≤2 时规范/实值语义零分歧）",
    "§3.6 的 JEPD 命题之穷举机检审计（0 违例）与 MV≤2 时规范/实值语义零分歧")

# 8. Conclusion wording
rep("其 JEPD 性质与算术安全性经穷举审计验证",
    "其 JEPD 性质以参数化证明给出、经穷举机检审计复核，算术安全性经实测验证")

# 9. §3.6 intro sentence + property labels renamed F1-F4 (avoid clash with
#    optimization names P1/P2/P3), and P2 upgraded to proposition+proof
rep("只要使用\"演算/关系\"词汇，就需要回答基本关系是否良定义。本节给出可机检的形式性质及其穷举验证结果（脚本 audit_semantics.py，结果 results/audit_semantics.json）。",
    "只要使用\"演算/关系\"词汇，就需要回答基本关系是否良定义。本节区分两个层级：对划分定义的数学性质，我们以命题+参数化证明给出（F1、F2）；对实现（生成器、ASP 编码、几何表），我们以穷举机检审计验证（脚本 audit_semantics.py，结果 results/audit_semantics.json）。审计不构成数学证明，它验证的是实现与定义的一致；证明不覆盖实现缺陷，二者互补。")

rep("**(P1) 水平 JEPD.** 对每个整除 90 的 MH 与每个满足对齐条件的 RA，任意 RA 对齐的 ψ∈[0,360) 恰好满足一个水平扇区条件（偶数精确射线 / 奇数开区间，含环绕）。穷举验证：28 个 (MH,RA) 组合 × 全部 ψ 值，未分类计数为 0。",
    "**(F1) 水平 JEPD（命题）.** 对每个整除 90 的 MH 与每个满足对齐条件的 RA，任意 RA 对齐的 ψ∈[0,360) 恰好满足一个水平扇区条件（偶数精确射线 / 奇数开区间，含环绕）。\n\n"
    "*证明思路.* 记 W=90/MH、边界集 B={ (I·W) mod 360 : I 偶 }。ψ∈B 时命中唯一偶扇区（B 中元素两两不同，因 W·2<360）；ψ∉B 时落在恰好一对相邻边界之间的开弧上，该弧即唯一奇扇区；环绕情形（LO>HI）下开弧跨 0°，判定条件 PS>LO ∨ PS<HI 等价于弧成员关系，仍互斥。∎\n\n"
    "*机检审计*：28 个 (MH,RA) 组合 × 全部 ψ 值，未分类计数为 0。")

rep("**(P2) 垂直 JEPD（含退化情形）.** 对任意非重合网格向量 (dx,dy,dz)≠(0,0,0)，恰好一个垂直扇区条件成立：q=0∧dz<0 → J=0；q=0∧dz>0 → J=2MV；q>0 时偶数射线条件与奇数开区间条件恰有一个成立（dz=0 的赤道向量落入 J=MV：MV 为偶数时经由精确射线条件 dz·1000=TB(MV)·q=0，MV 为奇数时经由包含 0° 的开区间）。穷举验证：S∈{20,30,50} 全网格 × MV∈{1,2,3,5,10,30}（S=50 为 MV∈{1,2,3}），共约 4.5×10⁶ 个 (点,粒度) 检查，多扇区/无扇区违例均为 0。",
    "**(F2) 垂直 JEPD（命题，含退化情形）.** 对任意 MV≥1 与任意非零网格向量 (dx,dy,dz)≠(0,0,0)，恰好一个垂直扇区条件成立。\n\n"
    "*证明.* (i) 退化分支：q=0 ⟺ dx=dy=0，此时 dz≠0，J=0（dz<0）与 J=2MV（dz>0）互斥且穷尽；q>0 时两退化分支的条件均不成立。(ii) q>0：令 r = dz·1000/q ∈ ℚ。考虑扩展边界序列 b₀=−∞ < b₁ < ⋯ < b_{2MV−1} < b_{2MV}=+∞，其中 b_J = TB(J)（0<J<2MV）。TB 严格递增：tan 在 (−90°,90°) 上严格递增，相邻内部边界的中心间距为 180/MV 度，其 tan 差经 1000 倍定点化后在所有受支持粒度（MV≤30）下最小为 52（MV=30 赤道处 tan(3°)·1000；实测各 MV 的相邻 TB 差 ≥52），远大于舍入步长 1，故取整不合并相邻值。于是单点集 {b_J}（J 偶、0<J<2MV）与开区间 (b_{J−1}, b_{J+1})（J 奇，含 ±∞ 哨兵）交替构成 ℝ 的完备划分，r 恰落在一块中；不等式两边同乘 q>0 即恢复编码形式 TB(J±1)·q ⋚ dz·1000，与奇偶 J 的条件一一对应。(iii) 赤道 dz=0（q>0）：r=0；MV 为偶数时 TB(MV)=0，命中精确射线 J=MV；MV 为奇数时 TB(MV−1)<0<TB(MV+1)，落入开区间 J=MV。互斥性与穷尽性得证。∎\n\n"
    "该证明针对划分的数学定义；定点/取整实现与 ASP 编码的一致性由下述机检审计验证。\n\n"
    "*机检审计*：S∈{20,30,50} 全网格 × MV∈{1,2,3,5,10,30}（S=50 为 MV∈{1,2,3}），共约 4.5×10⁶ 个 (点,粒度) 检查，多扇区/无扇区违例均为 0。")

rep("**(P3) same3d 与 one_sided3d 的关系.**", "**(F3) same3d 与 one_sided3d 的关系.**")
rep("**(P4) 规范整数语义 vs 实值语义.**", "**(F4) 规范整数语义 vs 实值语义.**")

# 10. F4 conclusion: add explicit supported-configuration recommendation (MV<=2)
rep("这是离散化的设计选择而非缺陷，但使用细粒度 MV 的应用应当以规范语义为准。",
    "这是离散化的设计选择而非缺陷，但使用细粒度 MV 的应用应当以规范语义为准。据此，本文正式将 MV≤2 界定为受支持且与实值语义等价的推荐配置；MV≥3 可用，但其语义应理解为网格规范语义而非连续仰角语义，且使用者应预期边界邻域内约 0.5%–11%（随 MV 增大）的分类偏离。")

P.write_text(s)
print("patch1 applied, delta chars:", len(s) - n0)
