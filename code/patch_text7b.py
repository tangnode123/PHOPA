"""patch_text7b.py — register E17 in Appendix A (scripts + logs) and add the
D.8 full-sector-domain audit table after D.7."""
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

# --- Appendix A: semantic-audit line ---
rep(
"- 语义审计：`audit_semantics.py` → `results/audit_semantics.json`（水平/垂直 JEPD 穷举、az 覆盖、规范 vs 实值仰角对照）",
"- 语义审计：`audit_semantics.py` → `results/audit_semantics.json`（水平/垂直 JEPD 穷举、az 覆盖、规范 vs 实值仰角对照）；`e17_q0_audit.py` → `logs/e17_q0_audit.json`（完整 one_sided3d 3D 扇区定义域穷举：q>0 恰一完整扇区、q=0 零完整扇区，F1/F2 分量级零违例，对应 F2b）",
"A-audit")

# --- Appendix A: logs line ---
rep(
"`e15_mv.json`、`e16_z3_backend.jsonl`（30）、`audit_semantics.log`",
"`e15_mv.json`、`e16_z3_backend.jsonl`（30）、`e17_q0_audit.json`、`audit_semantics.log`",
"A-logs")

# --- Appendix D.8 table: insert before "## 参考文献" ---
d8 = (
"\n**D.8 E17：完整 one_sided3d 3D 扇区定义域穷举审计（S≤20 全部非零网格向量；完整命中数 = 同时满足水平 I 与垂直 J 的 (I,J) 对数；对应 F2b）**\n\n"
"| 配置 (S,MH,MV,RA) | 非零向量 | 正上/下 (q=0,dz≠0) | q>0 倾斜：完整命中 | q>0 赤道：完整命中 | q=0：完整命中 | F1 违例 | F2 违例 |\n"
"|---|---|---|---|---|---|---|---|\n"
"| (20,2,2,3) | 59,318 | 38 | 1×57,760 | 1×1,520 | 0×38 | 0 | 0 |\n"
"| (20,1,1,3) | 59,318 | 38 | 1×57,760 | 1×1,520 | 0×38 | 0 | 0 |\n"
"| (20,3,3,3) | 59,318 | 38 | 1×57,760 | 1×1,520 | 0×38 | 0 | 0 |\n"
"| (20,2,5,3) | 59,318 | 38 | 1×57,760 | 1×1,520 | 0×38 | 0 | 0 |\n"
"| (15,2,2,5) | 24,388 | 28 | 1×23,520 | 1×840 | 0×28 | 0 | 0 |\n"
"| (10,3,3,3) | 6,858 | 18 | 1×6,480 | 1×360 | 0×18 | 0 | 0 |\n\n"
"注：“1×k”表示 k 个向量各恰命中 1 个完整 (I,J) 扇区，“0×k”表示 k 个向量各命中 0 个完整扇区。结果证实 F2b：完整 one_sided3d 良定义当且仅当 q>0；正上/正下向量（每网格 18–38 个，非空）的完整扇区数为 0（水平方位角无定义），其垂直分量单独仍满足 JEPD（F2）。无效粒度（如 MH=4，因 90%MH≠0）被对齐检查自动排除。\n"
)
rep("\n## 参考文献\n", d8 + "\n## 参考文献\n", "D8-insert")

io.open(P, "w", encoding="utf-8").write(s)
print(f"patch_text7b OK: {len(edits)} edits {edits}; {len(orig)} -> {len(s)} chars")
