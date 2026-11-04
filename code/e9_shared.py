"""E9: stronger-baseline run. naive_shared (P1 + shared full 3-way join
tables v3/d3, no projection decomposition) on the SAME 8 cells x 4 seeds as
E8, so rows join directly with e8_ablation.jsonl (proj/naive reference).

Log: ../logs/e9_shared.jsonl
"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e8_ablation as E

E.VARIANTS = ["naive_shared"]
E.LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs", "e9_shared.jsonl")

if __name__ == "__main__":
    sys.argv = ["e9", "--seeds", "4", "--workers", "2"]
    E.main()
