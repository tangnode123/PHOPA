"""patch_text8.py — iter_4 Critical #4: write E18 non-circular stress test into
the paper. Adds the §6.4 E18 paragraph, forward-refs it from the E11 honesty note,
registers e18_stress.py in Appendix A, and adds the D.9 results table."""
import io, sys

P = "../../artifacts/phopa3d-paper/phopa3d_paper.md"
s = io.open(P, encoding="utf-8").read()
orig = s
edits = []

def rep(old, new, tag):
    global s
    n = s.count(old)
    if n != 1:
        print(f"FAIL [{tag}]: found {n} matches (expected 1)"); sys.exit(1)
    s = s.replace(old, new)
    edits.append(tag)

# --- 1) E11 honesty note: forward-reference E18 ---
rep(
"它验证的是端到端可用性与推理能力（该规模下 grounding+solving 全部秒级），不是真实部署有效性。",
"它验证的是端到端可用性与推理能力（该规模下 grounding+solving 全部秒级），不是真实部署有效性；其相对真实观测的鲁棒性（多错误定位、缺失观测下的候选推断）由下述 E18 非循环压力测试单独量化。",
"E11-forwardref")

# --- 2) Insert E18 paragraph after the E15 paragraph, before 场景 A ---
e18 = (
"**非循环鲁棒性压力测试（E18）**：E11/E15 的约束由真实布局按规范语义导出、再用于恢复该布局，"
"这验证了系统内部一致性，但存在外部效度（循环性）疑虑。E18 对同一港口案例施加随机、带种子、"
"不由布局导出的输入退化，对照地面真值评估三类现实噪声下的鲁棒性（完整表见附录 D.9）。"
"（i）多错误故障定位：把全部 22 条感知约束（one_sided3d / dist_rel / azim_range / distance_range）"
"设为可废止、世界知识（location / direction / min_gap）设为 mandatory，随机损坏其中 k∈{1,2,3} 条"
"（水平扇区偏移 ±1~3、距离档跳变、方位/测距区间平移），在 explain 模式下最小化丢弃数。"
"4 seeds × 3 个 k 值共 12 次：最优 drop 集相对真实损坏集的 precision / recall / 精确匹配率均为 1.0，"
"最小修复规模恰为 k，求解均 <0.1s——求解器须在约 22 条可丢弃感知中识别出确切的故障子集，而非被迫答案。"
"（ii）可辨识性探针：在（i）基础上额外释放一个运动对象的位置（toinfer_pos），4 次探针中 0 次被"
"“零成本重定位”吸收（修复成本恒为 1），但仅 2/4 唯一定位到注入的故障，另 2/4 出现等成本的替代或误归属"
"最小修复——说明故障定位的唯一可辨识性依赖足够的 mandatory 锚定，这是约束图性质而非求解器缺陷。"
"（iii）缺失观测下的位置推断：移除过境轮 location 并随机丢弃 x%∈{0,20,40} 的全部感知，候选位置集中位数"
"13→13→36 单调扩大，而真值覆盖率在全部丢弃水平下保持 100%——纯缺失不会排除真实布局，框架随观测稀疏"
"优雅退化、从不丢失地面真值。网格/定性分辨率变化的影响由 E15（同一港口案例的 MV 扫描）与 E1b"
"（S∈{20,30,40,50}）覆盖；E18 固定推荐配置（MH=MV=2、S=50×50×24），改变的是观测质量。这组结果把 E11 "
"从“自洽演示”提升为“在现实噪声下可度量鲁棒的空间任务验证”，但仍是半真实地理（示意布局），"
"不构成对真实 AIS/GIS 数据部署有效性的主张。\n\n"
)
rep("**场景 A：UAV 海事监视**", e18 + "**场景 A：UAV 海事监视**", "E18-para")

# --- 3) Appendix A: register e18_stress.py ---
rep(
"`e16_z3_backend.py`（z3 SMT/BitVec 替代后端对照，→ `logs/e16_z3_backend.jsonl`）；`hopa3d.gen_instance` 增加可选 `type_w` 参数（默认行为不变）",
"`e16_z3_backend.py`（z3 SMT/BitVec 替代后端对照，→ `logs/e16_z3_backend.jsonl`）、`e17_q0_audit.py`（完整 one_sided3d 扇区定义域穷举，→ `logs/e17_q0_audit.json`）、`e18_stress.py`（E11 非循环鲁棒性压力测试：多错误定位 / 可辨识性 / 缺失观测，→ `logs/e18_stress.json`）；`hopa3d.gen_instance` 增加可选 `type_w` 参数（默认行为不变）",
"A-e18")

# --- 4) Appendix A logs line: add e17/e18 logs ---
rep(
"`e16_z3_backend.jsonl`（30）、`e17_q0_audit.json`、`audit_semantics.log`",
"`e16_z3_backend.jsonl`（30）、`e17_q0_audit.json`、`e18_stress.json`、`audit_semantics.log`",
"A-e18-logs")

# --- 5) D.9 table: insert before "## 参考文献" ---
d9 = (
"\n**D.9 E18：E11 港口案例的非循环鲁棒性压力测试（4 seeds；推荐配置 MH=MV=2、S=50×50×24）**\n\n"
"| 部分 | 设置 | 指标 | 结果 |\n"
"|---|---|---|---|\n"
"| A 多错误定位 | 22 条感知可废止、世界知识 mandatory，随机损坏 k 条 | precision / recall / 精确匹配率（k=1,2,3，各 4 seeds） | 1.0 / 1.0 / 1.0（全部 12 次）；最小修复规模 = k；求解 <0.1s |\n"
"| A2 可辨识性探针 | A 基础上释放一个运动对象位置（toinfer_pos） | 零成本吸收次数 / 唯一定位次数（4 探针） | 0 / 2（另 2 次为等成本替代或误归属修复） |\n"
"| B 缺失观测推断 | 移除过境轮 location + 随机丢弃 x% 全部感知 | 候选集中位数 / 真值覆盖率（x=0,20,40） | 13 / 13 / 36；覆盖率 100%（全部水平） |\n\n"
"注：A 部分在布局被 mandatory 世界知识锚定时故障定位精确且唯一（precision=recall=1.0）；A2 表明一旦释放目标位置，"
"单故障可被等成本的替代修复解释（2/4），即唯一可辨识性依赖锚定程度。B 部分纯缺失观测下候选集随丢弃率单调扩大但真值始终保留，"
"体现优雅退化。损坏模型：one_sided3d 水平扇区 ±1~3、dist_rel 档位跳变、azim_range/distance_range 区间平移（均保证与锚定真值不一致）。\n"
)
rep("\n## 参考文献\n", d9 + "\n## 参考文献\n", "D9-insert")

io.open(P, "w", encoding="utf-8").write(s)
print(f"patch_text8 OK: {len(edits)} edits {edits}; {len(orig)} -> {len(s)} chars")
