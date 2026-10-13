"""M5 — Optimization Report: combine M1-M4 into baseline-vs-optimized (deck §1/§11).

Run: python missions/m5_report.py   ->  outputs/report.md + outputs/savings.png
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import os
import json
from missions._common import num, catalog_by_type, ROOT
from finops import report, sustainability
from missions import m1_efficiency_audit, m2_inference_levers, m3_purchasing, m4_allocation, extensions, submission

DAYS = 30
# one tier down for over-provisioned ("util-lie") GPUs
RIGHTSIZE_MAP = {"H100": "A100", "H200": "H100", "A100": "A10G", "A10G": "L4", "L4": "L4"}


def run(verbose: bool = True) -> dict:
    r1 = m1_efficiency_audit.run(verbose=False)
    r2 = m2_inference_levers.run(verbose=False)
    r3 = m3_purchasing.run(verbose=False)
    r4 = m4_allocation.run(verbose=False)
    carbon = extensions.run(verbose=False)
    cat = catalog_by_type()

    # --- buckets ---
    infer_savings = (r2["stages_daily"]["Baseline"] - r2["stages_daily"]["Batch"]) * DAYS
    purchasing_savings = r3["on_demand_monthly"] - r3["optimized_monthly"]

    idle_savings = r1["idle_waste_daily"] * DAYS
    rightsize_savings = 0.0
    for lie in r1["lies"]:
        cur = lie["gpu_type"]
        tgt = RIGHTSIZE_MAP.get(cur, cur)
        delta = num(cat[cur]["on_demand_hr"]) - num(cat[tgt]["on_demand_hr"])
        rightsize_savings += max(0.0, delta) * 24 * DAYS

    levers = {
        "Inference (cascade/cache/batch)": round(infer_savings, 2),
        "Purchasing (spot/reserved)": round(purchasing_savings, 2),
        "Right-size util-lies": round(rightsize_savings, 2),
        "Kill idle GPUs": round(idle_savings, 2),
    }
    baseline = round(r2["stages_daily"]["Baseline"] * DAYS + r3["on_demand_monthly"], 2)
    optimized = baseline - sum(levers.values())
    total_pct = sum(levers.values()) / baseline * 100 if baseline else 0.0

    # --- sustainability snapshot ---
    wh = r2["reasoning"]["energy_before_wh"] / r2["request_count"]
    sust = {
        "wh_per_query": wh,
        "carbon_g": sustainability.carbon_g(wh, "us-east-1"),
        "best_region": min(sustainability.REGION_CARBON, key=sustainability.REGION_CARBON.get),
    }

    md = report.build_report(baseline, optimized, levers, sustainability=sust)
    md += "\n\n" + submission.analysis(r1, r2, r3, r4, carbon, baseline, optimized, levers)
    out_md = os.path.join(ROOT, "outputs", "report.md")
    os.makedirs(os.path.dirname(out_md), exist_ok=True)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(md)
    with open(os.path.join(ROOT, "outputs", "writeup.md"), "w", encoding="utf-8") as f:
        f.write(submission.writeup(r1, r2, r3, carbon, baseline, optimized, levers))
    with open(os.path.join(ROOT, "outputs", "extension_results.json"), "w", encoding="utf-8") as f:
        json.dump({"reasoning_cap_10pct": r2["reasoning"], "reasoning_cap_5pct": r2["reasoning_strict"],
                   "carbon_scheduling": carbon}, f, indent=2, ensure_ascii=False)
    png = report.savings_waterfall(levers, os.path.join(ROOT, "outputs", "savings.png"), baseline=baseline)

    if verbose:
        print("== M5 Optimization Report ==")
        # Keep the console ASCII-compatible on Windows; report files are UTF-8.
        print(f"Baseline ${baseline:,.2f} -> optimized ${optimized:,.2f} ({total_pct:.2f}% saved)")
        print(f"Extensions: reasoning cap 10%/5%; carbon saved {carbon['carbon_saved_g']/1000:.2f} kgCO2e")
        print(f"\nWritten: outputs/report.md" + (f" + outputs/savings.png" if png else " (matplotlib absent: PNG skipped)"))

    return {"baseline_monthly": round(baseline, 2), "optimized_monthly": round(optimized, 2),
            "levers": levers, "total_savings_pct": round(total_pct, 1)}


if __name__ == "__main__":
    run()
