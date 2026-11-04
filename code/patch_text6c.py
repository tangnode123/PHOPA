# -*- coding: utf-8 -*-
"""Patch 6c: reduce bold density in §2.4 (4 bolds in one paragraph -> 0)."""
P = "/mnt/wisdisk-prod/agents/99879a279ec44eb989d8c38e80227bec/universal_run-99879a279ec44eb989d8c38e80227bec/artifacts/phopa3d-paper/phopa3d_paper.md"
src = open(P, encoding="utf-8").read()

def rep(old, new):
    global src
    c = src.count(old)
    assert c == 1, f"anchor count {c}: {old[:50]!r}"
    src = src.replace(old, new)

rep("但它们**不会自动得到 P2/P3 的结构收益**，原因有三", "但它们不会自动得到 P2/P3 的结构收益，原因有三")
rep("本文的收益来自**重写连接结构本身**（把 S³ 三路积拆成", "本文的收益来自重写连接结构本身（把 S³ 三路积拆成")
rep("但本文的扇区判定含 atan2/tan/isqrt 等**非线性、超越**运算", "但本文的扇区判定含 atan2/tan/isqrt 等非线性、超越运算")
rep("因此本文把 P2/P3 定位为**面向 3D 空间谓词、在纯 clingo 表驱动编码内的结构分解**，并以受控消融", "因此本文把 P2/P3 定位为面向 3D 空间谓词、在纯 clingo 表驱动编码内的结构分解，并以受控消融")

open(P, "w", encoding="utf-8").write(src)
print("patch_text6c applied (bold density fixed in §2.4)")
