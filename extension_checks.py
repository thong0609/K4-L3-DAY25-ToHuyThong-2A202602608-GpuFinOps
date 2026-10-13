"""Additional checks; original tests/ remains unchanged.

Run: python -m pytest -q extension_checks.py
"""
import csv
from pathlib import Path

import pytest
from finops.scenarios import reasoning_budget, carbon_schedule
from missions import m2_inference_levers as m2, m3_purchasing as m3, m4_allocation as m4
from missions._common import load_csv


def request(reasoning=1):
    return {"input_tokens": "1000", "output_tokens": "600", "cached_input_tokens": "0",
            "is_batch": "0", "is_reasoning": str(reasoning), "route_tier": "small"}


def test_reasoning_zero_cap_known_cost_and_energy():
    r = reasoning_budget([request()], m2.MODEL_PRICES, 0)
    assert r["downgraded_requests"] == 1
    assert r["cost_before_usd"] == pytest.approx(0.00044)
    assert r["cost_after_usd"] == pytest.approx(0.00024)
    assert r["energy_before_wh"] == pytest.approx(38.4)
    assert r["energy_after_wh"] == pytest.approx(0.33)


def test_noop_cap_and_empty_input():
    r = reasoning_budget([request(), request(0)], m2.MODEL_PRICES, 1)
    assert r["savings_usd"] == 0
    assert r["savings_wh"] == 0
    assert reasoning_budget([], m2.MODEL_PRICES)["reasoning_after"] == 0


@pytest.mark.parametrize("cap", [-0.1, 1.1])
def test_invalid_cap(cap):
    with pytest.raises(ValueError):
        reasoning_budget([], m2.MODEL_PRICES, cap)


def test_cap_keeps_request_count_and_meets_budget():
    r = reasoning_budget([request() for _ in range(5)], m2.MODEL_PRICES, 0.5)
    assert r["reasoning_after"] == 2
    assert r["downgraded_requests"] == 3
    assert sum(g["requests"] for g in r["groups"].values()) == 5


def test_carbon_uses_actual_days_and_excludes_noninterruptible():
    job = {"job_id": "test", "hours_per_day": "2", "days": "3", "num_gpus": "2",
           "gpu_type": "TEST", "interruptible": "1"}
    r = carbon_schedule([job, dict(job, interruptible="0")], {"TEST": {"watts": "100"}})
    assert len(r["jobs"]) == 1
    assert r["energy_wh"] == 1200
    assert r["carbon_saved_g"] == pytest.approx(420)
    assert r["cheapest"] == "us-east-wa"
    assert r["cleanest"] == "europe-north1"
    assert r["balanced"] == "us-east-wa"


def test_m2_attribution_and_reasoning_reconcile():
    r = m2.run(False)
    amounts = list(r["stages_daily"].values())
    assert all(a >= b for a, b in zip(amounts, amounts[1:]))
    assert sum(a-b for a, b in zip(amounts, amounts[1:])) == pytest.approx(amounts[0]-amounts[-1])
    assert r["reasoning"]["cost_before_usd"] == pytest.approx(amounts[-1])
    assert r["reasoning"]["downgraded_requests"] == 0
    assert r["reasoning_strict"]["savings_wh"] > 0


def test_reserved_bills_unused_hours():
    result = m3.run(False)
    row = next(r for r in result["recommendations"] if r["job_id"] == "job-infer-search")
    assert row["optimized"] == pytest.approx(24 * 30 * 4 * 0.45)
    assert sum(r["optimized"] for r in result["recommendations"]) == pytest.approx(result["optimized_monthly"])


def test_full_export_reconciles_with_inference():
    m4.run(False)
    with (Path(__file__).parent / "outputs" / "focus_export.csv").open(newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == len(load_csv("token_usage.csv"))
    assert sum(float(r["BilledCost"]) for r in rows) == pytest.approx(m2.run(False)["stages_daily"]["Batch"], abs=1e-6)
