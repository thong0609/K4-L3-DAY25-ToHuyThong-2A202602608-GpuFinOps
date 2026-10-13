"""Run carbon-aware scheduling independently: python missions/extensions.py."""
from __future__ import annotations
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from missions._common import load_csv, catalog_by_type
from finops.scenarios import carbon_schedule


def run(verbose=True):
    result = carbon_schedule(load_csv("workloads.csv"), catalog_by_type())
    if verbose:
        print("== Carbon-aware scheduling (actual job days) ==")
        for r in result["regions"]:
            print(f"{r['region']:20} ${r['electricity_usd']:.2f} electricity; {r['carbon_g']/1000:.2f} kgCO2e")
        print(f"Cheapest: {result['cheapest']}; cleanest: {result['cleanest']}; balanced: {result['balanced']}")
        print(f"Carbon saved: {result['carbon_saved_g']/1000:.2f} kgCO2e")
    return result


if __name__ == "__main__":
    run()
