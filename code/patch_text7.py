"""patch_text7.py — iter_4 Critical #2: q=0 degenerate one_sided3d domain fix.
Makes §3.2/§3.3/F2b/F3 domain-explicit: the FULL one_sided3d relation is
well-defined iff q>0; due-above/below (q=0,dz!=0) admit zero full sectors
(horizontal azimuth undefined) though their vertical component alone is JEPD.
Cites the new E17 exhaustive audit. Every replacement asserts a unique match."""
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

# --- 1) §3.2 azimuth sentence: undefined for ALL q=0, not just coincident ---
rep(
"方位角 AZ(dx,dy) 由预计算表 az_angle(DX,DY,A) 给出：A 是 atan2(dy,dx) 的非负代表元按 RA 粒度四舍五入后的整数值；(dx,dy)=(0,0) 时方位角无定义（表中不含该项），任何需要方位角的约束在两点重合时直接判 UNSAT。",
"方位角 AZ(dx,dy) 由预计算表 az_angle(DX,DY,A) 给出：A 是 atan2(dy,dx) 的非负代表元按 RA 粒度四舍五入后的整数值。当水平投影 (dx,dy)=(0,0)（即 q=0）时方位角无定义，表中不含该项——这涵盖两类向量：两点重合（dz=0）与正上/正下（dz≠0）。任何依赖方位角的约束（one_sided3d 的水平分量、azim/azim_range）在 q=0 时对其全部取值直接判 UNSAT。其几何含义是：one_sided3d 的完整定义域为 q>0（见 §3.3 与 F2b），正上/正下这类纯垂直方向不在其中，需由独立的 above/below 谓词表达（本文未实现，留作未来工作）。",
"3.2-azimuth")

# --- 2) §3.3 one_sided3d bullet: state domain q>0; J=0/2MV are vertical-only ---
rep(
"- `one_sided3d(N,K,L,I,J)`：从 L 的视角看 K 的 3D 方向扇区。水平分量：ψ = (AZ(dx,dy) − yaw(L) + 360) mod 360；I 为奇数时要求 ψ 落在开扇区 (((I−1)W_H) mod 360, ((I+1)W_H) mod 360)（正确处理环绕），I 为偶数时要求 ψ = (I·W_H) mod 360。垂直分量：J 为奇数（0<J<2MV）时要求 TB(J−1)·q < dz·1000 < TB(J+1)·q；J 为偶数（0<J<2MV）时要求 dz·1000 = TB(J)·q；J=0 当且仅当 q=0 ∧ dz<0（正下方）；J=2MV 当且仅当 q=0 ∧ dz>0（正上方）。",
"- `one_sided3d(N,K,L,I,J)`：从 L 的视角看 K 的 3D 方向扇区，定义域为 q>0（水平投影非零）。它是水平分量与垂直分量的合取。水平分量：ψ = (AZ(dx,dy) − yaw(L) + 360) mod 360；I 为奇数时要求 ψ 落在开扇区 (((I−1)W_H) mod 360, ((I+1)W_H) mod 360)（正确处理环绕），I 为偶数时要求 ψ = (I·W_H) mod 360。垂直分量：J 为奇数（0<J<2MV）时要求 TB(J−1)·q < dz·1000 < TB(J+1)·q；J 为偶数（0<J<2MV）时要求 dz·1000 = TB(J)·q。需注意 J=0（正下方）与 J=2MV（正上方）这两个退化垂直扇区仅在 q=0 时由垂直分量单独成立，但此时水平分量因 AZ 无定义而不可满足，故完整原子 one_sided3d(·,·,·,I,J) 对 q=0 的任意 (I,J) 均为假——换言之，退化垂直扇区属于垂直分量的 JEPD（F2），却不属于完整 3D 方向关系（F2b）。",
"3.3-one_sided3d")

# --- 3) §3.6 intro: add F2b to the proved-properties list ---
rep(
"对划分定义的数学性质，我们以命题+参数化证明给出（F1、F2）；",
"对划分定义的数学性质，我们以命题+参数化证明给出（F1、F2、F2b）；",
"3.6-intro")

# --- 4) Insert F2b (full 3D sector domain) right after F2's audit line ---
rep(
"*机检审计*：S∈{20,30,50} 全网格 × MV∈{1,2,3,5,10,30}（S=50 为 MV∈{1,2,3}），共约 4.5×10⁶ 个 (点,粒度) 检查，多扇区/无扇区违例均为 0。\n",
"*机检审计*：S∈{20,30,50} 全网格 × MV∈{1,2,3,5,10,30}（S=50 为 MV∈{1,2,3}），共约 4.5×10⁶ 个 (点,粒度) 检查，多扇区/无扇区违例均为 0。\n\n"
"**(F2b) 完整 3D 扇区的定义域（命题）.** 完整关系 one_sided3d(K,L,I,J) 良定义（恰有一个 (I,J) 成立）当且仅当 q>0。q=0 的向量（两点重合，或正上/正下 dz≠0）使水平方位角无定义，完整原子对一切 (I,J) 为假。据此三条 JEPD 的适用域应分别陈述：水平 JEPD（F1）成立于 q>0；垂直 JEPD（F2）成立于全部非零向量；完整 3D 扇区的 JEPD 仅成立于 q>0 子域。正上/正下方向若需推理，应引入独立 above/below 谓词，本文未实现。\n\n"
"*证明.* one_sided3d 是水平分量与垂直分量的合取。垂直分量在全部非零向量上 JEPD（F2），故完整原子的可满足性完全由水平分量决定。水平分量需 ψ=(AZ(dx,dy)−yaw) mod 360，而 AZ 仅在 (dx,dy)≠(0,0)（即 q>0）时有定义：q>0 时水平分量恰命中一个 I（F1），与垂直分量唯一的 J 合成恰一个完整 (I,J)；q=0 时 AZ 无定义、水平分量对一切 I 为假，合取对一切 (I,J) 为假。∎\n\n"
"*机检审计（E17）*：枚举 S≤20 全部非零网格向量（S=20 时 59,318 个，其中正上/正下向量 38 个），逐一统计完整 (I,J) 命中数，覆盖 (MH,MV,RA) 共 6 组对齐配置（含 (2,2,3)、(1,1,3)、(3,3,3)、(2,5,3)、(2,2,5)、(3,3,3)）。结果：每个 q>0 向量（倾斜与赤道两类）恰命中 1 个完整扇区；每个 q=0∧dz≠0 向量命中 0 个完整扇区（其垂直分量单独仍恰命中 1 个）；F1/F2 分量级违例均为 0（脚本 e17_q0_audit.py，结果 logs/e17_q0_audit.json）。\n",
"F2b-insert")

# --- 5) F3: separate coincident vs due-above/below degenerate cases ---
rep(
"**(F3) same3d 与 one_sided3d 的关系.** 两谓词的适用范围互斥：same3d 要求 pos(K)=pos(L)，而 one_sided3d 在重合点上因方位角无定义、垂直扇区无定义而不可满足。框架中不存在一个几何配置同时满足两者。",
"**(F3) same3d 与 one_sided3d 的关系.** 两谓词的适用范围互斥：same3d 要求 pos(K)=pos(L)（重合点），而 one_sided3d 的定义域为 q>0（F2b），在重合点上既不满足 q>0、方位角与垂直扇区亦均无定义，故不可满足。框架中不存在一个几何配置同时满足两者。需区分两类 q=0 退化：重合点（dx=dy=dz=0）下水平与垂直分量都无定义；正上/正下（q=0,dz≠0）下垂直分量可分类（J=0/2MV）但水平分量无定义——两类都使完整 one_sided3d 不可满足，但成因不同。",
"F3")

io.open(P, "w", encoding="utf-8").write(s)
print(f"patch_text7 OK: {len(edits)} edits {edits}; {len(orig)} -> {len(s)} chars")
