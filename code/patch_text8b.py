"""patch_text8b.py — propagate E17/E18 into §7.3 threats, §7.4 limitations, §8 conclusion."""
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

# --- §7.3 semi-real case threat: add circularity mitigation via E18 ---
rep(
"- **半真实案例**：E11 的港口地理为示意性手工布局（非真实 AIS/GIS 数据），27 对象规模小于规模化实验；其价值在端到端可用性与机器导出约束下的推理质量，不在大规模性能。",
"- **半真实案例与循环性**：E11 的港口地理为示意性手工布局（非真实 AIS/GIS 数据），27 对象规模小于规模化实验；其价值在端到端可用性与机器导出约束下的推理质量，不在大规模性能。“约束由布局导出、再用于恢复布局”的循环性疑虑由 E18（§6.4、附录 D.9）部分缓解：在随机、不由布局导出的输入退化（多错误损坏、随机缺失观测）下，故障定位 precision/recall 在锚定布局时达 1.0、缺失观测下候选集真值覆盖率保持 100%，并暴露出释放目标位置时可辨识性下降的明确边界。但 E18 仍基于示意地理、未接入真实传感器量测，故应用 claim 止于半真实 proof-of-concept。",
"7.3-semireal")

# --- §7.4 limitation (6): note E18 robustness quantification ---
rep(
"（6）应用验证止于半真实示意场景：尚未接入真实 AIS/ADS-B 轨迹、3D 城市模型或室内导航数据集，E11 的约束由示意坐标自动导出而非真实传感器量测。",
"（6）应用验证止于半真实示意场景：尚未接入真实 AIS/ADS-B 轨迹、3D 城市模型或室内导航数据集；E11 的约束由示意坐标自动导出，E18 进一步在随机噪声/缺失/多错误下量化了鲁棒性（故障定位 precision/recall、候选集真值覆盖率、可辨识性边界），但地理仍为示意性、非真实传感器量测，故为 proof-of-concept 而非部署有效性验证。",
"7.4-lim6")

# --- §8 conclusion: 三项 -> 若干, add E17 + E18 boundary studies ---
rep(
"三项边界研究支撑该定位：高重用工作负载（E14）实测了 naive_shared 的解析交叉区并证实投影分解优势与重用度无关；仰角粒度扫描（E15，MV=1–5）表明推荐粒度是保守下界、细化只单调改善推断；一个独立的 z3 SMT 后端（E16）在可线性化子语言上判定 30/30 一致、且 SAT 实例上 clingo 表驱动更快，说明纯 clingo 设计点相对真正不同的求解范式仍然成立。",
"若干边界研究支撑该定位：高重用工作负载（E14）实测了 naive_shared 的解析交叉区并证实投影分解优势与重用度无关；仰角粒度扫描（E15，MV=1–5）表明推荐粒度是保守下界、细化只单调改善推断；一个独立的 z3 SMT 后端（E16）在可线性化子语言上判定 30/30 一致、且 SAT 实例上 clingo 表驱动更快，说明纯 clingo 设计点相对真正不同的求解范式仍然成立；完整 one_sided3d 扇区定义域的穷举审计（E17）确证其良定义当且仅当 q>0（正上/正下需独立 above/below 谓词，本文未实现）；对港口案例的非循环鲁棒性压力测试（E18）在随机多错误损坏与缺失观测下量化了故障定位 precision/recall（锚定布局时 1.0）与候选集真值覆盖率（100%），并界定了唯一可辨识性对 mandatory 锚定的依赖。",
"8-boundary")

# --- §8 conclusion (iv): note E18 robustness on the harbor case ---
rep(
"一个半真实港口监视案例（27 对象、74 条机器导出约束、5 类任务全部通过独立验证）与两个手工最小场景（463 个 answer set 全量验证）。",
"一个半真实港口监视案例（27 对象、74 条机器导出约束、5 类任务全部通过独立验证，并在 E18 随机噪声/缺失/多错误下经非循环压力测试验证鲁棒性）与两个手工最小场景（463 个 answer set 全量验证）。",
"8-iv")

io.open(P, "w", encoding="utf-8").write(s)
print(f"patch_text8b OK: {len(edits)} edits {edits}; {len(orig)} -> {len(s)} chars")
