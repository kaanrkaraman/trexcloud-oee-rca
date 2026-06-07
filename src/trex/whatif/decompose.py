"""Decompose ΔOEE into ΔA / ΔP / ΔQ contributions.

OEE = A·P·Q is multiplicative, so a naive (A2-A1)+(P2-P1)+(Q2-Q1) does NOT sum to ΔOEE.
Sequential attribution sums exactly:
  ΔOEE = (A2-A1)·P1·Q1  +  A2·(P2-P1)·Q1  +  A2·P2·(Q2-Q1)
"""
from __future__ import annotations


def decompose_oee(before: dict, after: dict) -> dict:
    A1, P1, Q1 = before["A"], before["P"], before["Q"]
    A2, P2, Q2 = after["A"], after["P"], after["Q"]
    dA = (A2 - A1) * P1 * Q1
    dP = A2 * (P2 - P1) * Q1
    dQ = A2 * P2 * (Q2 - Q1)
    total = after["OEE"] - before["OEE"]
    return {"dA_contrib": round(dA, 5), "dP_contrib": round(dP, 5),
            "dQ_contrib": round(dQ, 5), "total": round(total, 5),
            "residual": round(total - (dA + dP + dQ), 6)}


def waterfall_rows(before: dict, after: dict) -> list[tuple]:
    """Ordered [(label, value)] for a plotly waterfall (Baseline -> ΔA -> ΔP -> ΔQ -> Scenario)."""
    d = decompose_oee(before, after)
    return [("Baseline OEE", round(before["OEE"], 4)),
            ("ΔA", d["dA_contrib"]), ("ΔP", d["dP_contrib"]), ("ΔQ", d["dQ_contrib"]),
            ("Scenario OEE", round(after["OEE"], 4))]
