P = "/mnt/wisdisk-prod/agents/99879a279ec44eb989d8c38e80227bec/universal_run-99879a279ec44eb989d8c38e80227bec/artifacts/phopa3d-paper/phopa3d_paper.md"
s = open(P, encoding="utf-8").read()
orig = len(s)
def rep(old, new, n=1):
    global s
    c = s.count(old); assert c == n, f"count {c}!={n}: {old[:50]!r}"
    s = s.replace(old, new)

# ---- §6.3 scale-boundary component analysis (insert after 工程建议, before §6.4) ----
SB = (
"**内存墙的组件归因（scale-boundary 分析，E21）.** “投影分解推迟而非消除内存墙”这一主张需要被解释、而非仅被观察。"
"我们在固定对象数（N=10）下把 S 从 20 扫到 50，对 naive 与 proj 分别记录地面程序各组件（atoms / rules / bodies）与 peak RSS"
"（新鲜进程、3GB 预算），并对 log–log 斜率做拟合（完整数据见附录 D.13）。两点结论。其一，主导内存的组件是 ground bodies 而非 atoms："
"naive 的 bodies 从 S=20 的 0.52M 增至 S=45 的 5.59M，而 atoms 仅 0.011M→0.028M——内存墙由规则体（连接展开）而非原子数驱动，"
"这与“投影分解针对的是三路连接的结构”一致。其二，两编码的 bodies 增长指数显著不同：naive 的 bodies ~ S^2.45、RSS ~ S^2.2，"
"proj 的 bodies ~ S^1.88、RSS ~ S^1.66（log–log 拟合），即 naive 趋近其每对象对 Θ(S³) 三路 (DX,DY,DZ) 连接的理论上界、"
"而 proj 趋近共享 2D 表的 Θ(S²)。把这一组件归因与 §6.2 的 N×S 网格（附录 C）合看即可解释 E1b 观测到的 50³ 边界："
"在 N=60、S=40 处 naive 的 RSS 已达 2530MB（逼近 3GB），而 proj 仅 1478MB；naive/proj 的 bodies 比随 S 单调扩大"
"（N=40 时 S=20→40 为 2.61→3.66），故 naive 在更小的 N·S³ 处即触墙。投影分解把可行前沿外推（相同 3GB 预算下 proj 在 40³ 存活、"
"naive 0/5 存活），但因共享 2D 表本身仍按 Θ(S²) 增长、每对象对仍按 Θ(N·S²) 增长，墙只是被推迟而非消除。"
"这直接指明下一步路径：per-pair 按需（lazy）表生成与增量/多轮 grounding——仅为实际出现于约束中的 (DX,DY) 偏移物化共享表、"
"并按对象对惰性接地垂直/距离子系统，从而把 Θ(S²) 的全域表收缩到 Θ(实际偏移数)。\n\n"
)
rep("但计入 grounding 后仍无优势。\n\n### 6.4",
    "但计入 grounding 后仍无优势。\n\n" + SB + "### 6.4")

# ---- soften "可扩展性机制" (two sites) ----
rep("投影分解的价值应被定位为可扩展性机制（避免病态 grounding、推迟内存墙、改善困难实例尾部）",
    "投影分解的价值应被定位为 grounding 可扩展性机制——相对朴素纯 clingo 编码而言避免病态 grounding、推迟内存墙、改善困难实例尾部")
rep("我们据此把框架定位为可扩展性机制。",
    "我们据此把框架定位为 grounding 可扩展性机制（相对朴素纯 clingo 编码，而非一般意义的大规模 3D 体素处理）。")

# ---- Appendix D.13 table (before 参考文献) ----
D13 = (
"**D.13 E21：scale-boundary 组件分析（固定 N=10、n_con=20，S 扫描；新鲜进程、3GB 预算；rss 单位 MB）**\n\n"
"| S | naive atoms | naive bodies | naive rss | naive t_grnd(s) | proj atoms | proj bodies | proj rss | proj t_grnd(s) |\n"
"|---|---|---|---|---|---|---|---|---|\n"
"| 20 | 10,842 | 523,231 | 99 | 0.58 | 18,769 | 182,793 | 77 | 0.26 |\n"
"| 30 | 16,583 | 1,723,130 | 265 | 2.03 | 40,563 | 508,457 | 163 | 0.66 |\n"
"| 40 | 21,819 | 1,918,502 | 306 | 2.08 | 53,924 | 487,507 | 184 | 0.69 |\n"
"| 45 | 27,665 | 5,590,406 | 849 | 6.79 | 89,816 | 1,338,357 | 464 | 1.90 |\n"
"| 50 | 28,765 | 4,802,646 | 693 | 5.70 | 77,225 | 934,751 | 294 | 1.39 |\n\n"
"log–log 拟合指数（over 5 surviving S）：naive atoms~S^1.09、bodies~S^2.45、rss~S^2.2；proj atoms~S^1.64、bodies~S^1.88、rss~S^1.66。"
"即 naive 的地面程序体趋近 Θ(S³)（每对象对三路连接），proj 趋近 Θ(S²)（共享 2D 表）；内存墙由 bodies 主导而非 atoms。\n\n"
"与 §6.2 / 附录 C 的 N×S 网格合看的触墙证据：N=60、S=40 时 naive RSS=2530MB（逼近 3GB 预算）、proj=1478MB；"
"naive/proj 的 bodies 比随 S 扩大（N=40：S=20→40 为 2.61→3.66；N=100：S=20→30 为 2.62→3.44）。"
"注：N=10 下 S=50 的 naive bodies 略低于 S=45，源于逐 S 实例的几何/对象对差异（每 S 独立种子），不影响整体指数拟合。\n\n"
)
rep("## 参考文献", D13 + "## 参考文献")

# ---- register e21 in Appendix A ----
rep("→ `logs/e20_real_ais.json`）；`hopa3d.gen_instance` 增加可选 `type_w` 参数（默认行为不变）",
    "→ `logs/e20_real_ais.json`）、`e21_scale_boundary.py`（scale-boundary 组件分析：固定 N 扫 S，"
    "记录 naive/proj 的 atoms/bodies/RSS 并拟合增长指数，→ `logs/e21_scale_boundary.jsonl`）；"
    "`hopa3d.gen_instance` 增加可选 `type_w` 参数（默认行为不变）")

open(P, "w", encoding="utf-8").write(s)
print("part5 ok, +%d chars" % (len(s)-orig))
